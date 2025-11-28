"""
Routes API pour le déploiement et la maintenance.

Ce module fournit des endpoints pour :
- Surveillance des services Docker (API, Worker, Redis)
- Gestion des jobs RQ (liste, annulation, statistiques)
- Opérations de maintenance (nettoyage logs, queue, DB)
- Déploiement (git pull, rebuild, restart)
"""

from datetime import datetime
import os
from pathlib import Path
import subprocess
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import (
    FailedJobRegistry,
    FinishedJobRegistry,
    StartedJobRegistry,
)

from ...utils.logging import get_logger
from ..security import verify_api_key

logger = get_logger(__name__)

router = APIRouter(prefix="/deployment", tags=["Deployment"])

# Configuration Redis
REDIS_HOST = os.getenv("REDIS_HOST", "redis-bot")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)
    job_queue = Queue("linkedin-bot", connection=redis_conn)
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_conn = None
    job_queue = None

# ═══════════════════════════════════════════════════════════════════
# MODELS PYDANTIC
# ═══════════════════════════════════════════════════════════════════


class ServiceStatus(BaseModel):
    """Statut d'un service."""

    name: str
    status: str  # running, stopped, error
    uptime: Optional[str] = None
    memory_usage: Optional[str] = None
    cpu_usage: Optional[str] = None


class ServicesStatusResponse(BaseModel):
    """Réponse pour le statut des services."""

    services: list[ServiceStatus]
    timestamp: str


class JobInfo(BaseModel):
    """Information sur un job RQ."""

    job_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    result: Optional[str] = None
    exc_info: Optional[str] = None
    meta: dict[str, Any] = {}


class JobsResponse(BaseModel):
    """Réponse pour la liste des jobs."""

    queued: list[JobInfo]
    started: list[JobInfo]
    finished: list[JobInfo]
    failed: list[JobInfo]
    total: int


class MaintenanceRequest(BaseModel):
    """Requête de maintenance."""

    action: str = Field(
        ..., description="Action: 'clean_logs', 'clean_queue', 'clean_finished_jobs', 'vacuum_db'"
    )


class MaintenanceResponse(BaseModel):
    """Réponse de maintenance."""

    action: str
    status: str
    message: str
    details: Optional[dict[str, Any]] = None


class DeploymentRequest(BaseModel):
    """Requête de déploiement."""

    action: str = Field(..., description="Action: 'pull', 'rebuild', 'restart', 'full_deploy'")
    service: Optional[str] = Field(
        None, description="Service spécifique à redémarrer (api, worker, dashboard)"
    )


class DeploymentResponse(BaseModel):
    """Réponse de déploiement."""

    action: str
    status: str
    message: str
    output: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# ROUTES - STATUS DES SERVICES
# ═══════════════════════════════════════════════════════════════════


@router.get("/services/status", response_model=ServicesStatusResponse)
async def get_services_status(authenticated: bool = Depends(verify_api_key)):
    """
    Récupère le statut de tous les services Docker.

    Vérifie :
    - API (FastAPI)
    - Worker (RQ)
    - Redis (bot)
    - Redis (dashboard)
    - Dashboard (Next.js)
    """
    services = []

    try:
        # Vérifier Redis Bot
        try:
            if redis_conn:
                redis_conn.ping()
                services.append(ServiceStatus(name="Redis Bot", status="running", uptime="N/A"))
            else:
                services.append(ServiceStatus(name="Redis Bot", status="error"))
        except Exception as e:
            services.append(ServiceStatus(name="Redis Bot", status="error"))
            logger.error(f"Redis Bot check failed: {e}")

        # Vérifier Worker RQ
        try:
            if redis_conn:
                # Compter les workers actifs
                from rq import Worker

                workers = Worker.all(connection=redis_conn)
                if workers:
                    services.append(
                        ServiceStatus(
                            name="Bot Worker",
                            status="running",
                            uptime=f"{len(workers)} worker(s) actif(s)",
                        )
                    )
                else:
                    services.append(
                        ServiceStatus(
                            name="Bot Worker", status="stopped", uptime="Aucun worker actif"
                        )
                    )
            else:
                services.append(ServiceStatus(name="Bot Worker", status="error"))
        except Exception as e:
            services.append(ServiceStatus(name="Bot Worker", status="error"))
            logger.error(f"Worker check failed: {e}")

        # L'API elle-même est forcément running si on répond
        services.append(ServiceStatus(name="API", status="running", uptime="Active"))

        # Dashboard : vérifier via healthcheck
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get("http://dashboard:3000/api/system/health", timeout=5.0)
                if response.status_code == 200:
                    services.append(ServiceStatus(name="Dashboard", status="running"))
                else:
                    services.append(ServiceStatus(name="Dashboard", status="error"))
        except Exception as e:
            services.append(ServiceStatus(name="Dashboard", status="unknown"))
            logger.warning(f"Dashboard check failed: {e}")

        return ServicesStatusResponse(services=services, timestamp=datetime.now().isoformat())

    except Exception as e:
        logger.error(f"Failed to get services status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve services status: {e!s}")


# ═══════════════════════════════════════════════════════════════════
# ROUTES - GESTION DES JOBS
# ═══════════════════════════════════════════════════════════════════


@router.get("/jobs", response_model=JobsResponse)
async def get_jobs(authenticated: bool = Depends(verify_api_key)):
    """
    Récupère la liste de tous les jobs RQ (en cours, terminés, échoués).
    """
    if not redis_conn or not job_queue:
        raise HTTPException(status_code=503, detail="Redis Queue not available")

    try:
        queued_jobs = []
        started_jobs = []
        finished_jobs = []
        failed_jobs = []

        # Jobs en attente
        for job_id in job_queue.job_ids:
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                queued_jobs.append(
                    JobInfo(
                        job_id=job.id,
                        status="queued",
                        created_at=job.created_at.isoformat() if job.created_at else "N/A",
                        meta=job.meta,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to fetch queued job {job_id}: {e}")

        # Jobs en cours
        started_registry = StartedJobRegistry("linkedin-bot", connection=redis_conn)
        for job_id in started_registry.get_job_ids():
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                started_jobs.append(
                    JobInfo(
                        job_id=job.id,
                        status="started",
                        created_at=job.created_at.isoformat() if job.created_at else "N/A",
                        started_at=job.started_at.isoformat() if job.started_at else "N/A",
                        meta=job.meta,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to fetch started job {job_id}: {e}")

        # Jobs terminés (limité aux 10 derniers)
        finished_registry = FinishedJobRegistry("linkedin-bot", connection=redis_conn)
        for job_id in list(finished_registry.get_job_ids())[-10:]:
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                finished_jobs.append(
                    JobInfo(
                        job_id=job.id,
                        status="finished",
                        created_at=job.created_at.isoformat() if job.created_at else "N/A",
                        started_at=job.started_at.isoformat() if job.started_at else "N/A",
                        ended_at=job.ended_at.isoformat() if job.ended_at else "N/A",
                        result=str(job.result) if job.result else None,
                        meta=job.meta,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to fetch finished job {job_id}: {e}")

        # Jobs échoués (limité aux 10 derniers)
        failed_registry = FailedJobRegistry("linkedin-bot", connection=redis_conn)
        for job_id in list(failed_registry.get_job_ids())[-10:]:
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                failed_jobs.append(
                    JobInfo(
                        job_id=job.id,
                        status="failed",
                        created_at=job.created_at.isoformat() if job.created_at else "N/A",
                        started_at=job.started_at.isoformat() if job.started_at else "N/A",
                        ended_at=job.ended_at.isoformat() if job.ended_at else "N/A",
                        exc_info=job.exc_info if hasattr(job, "exc_info") else None,
                        meta=job.meta,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to fetch failed job {job_id}: {e}")

        total = len(queued_jobs) + len(started_jobs) + len(finished_jobs) + len(failed_jobs)

        return JobsResponse(
            queued=queued_jobs,
            started=started_jobs,
            finished=finished_jobs,
            failed=failed_jobs,
            total=total,
        )

    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve jobs: {e!s}")


# ═══════════════════════════════════════════════════════════════════
# ROUTES - MAINTENANCE
# ═══════════════════════════════════════════════════════════════════


@router.post("/maintenance", response_model=MaintenanceResponse)
async def run_maintenance(
    request: MaintenanceRequest, authenticated: bool = Depends(verify_api_key)
):
    """
    Exécute des opérations de maintenance.

    Actions disponibles :
    - clean_logs: Nettoyer les anciens logs
    - clean_queue: Vider complètement la queue Redis
    - clean_finished_jobs: Supprimer les jobs terminés/échoués
    - vacuum_db: Optimiser la base de données SQLite
    """
    logger.info(f"🔧 [MAINTENANCE] Action demandée: {request.action}")

    try:
        if request.action == "clean_logs":
            # Nettoyer les logs de plus de 7 jours
            log_file = Path(os.getenv("LOG_FILE", "/app/logs/linkedin_bot.log"))
            if log_file.exists():
                size_before = log_file.stat().st_size
                # Garder uniquement les 1000 dernières lignes
                with open(log_file, encoding="utf-8") as f:
                    lines = f.readlines()
                with open(log_file, "w", encoding="utf-8") as f:
                    f.writelines(lines[-1000:])
                size_after = log_file.stat().st_size

                return MaintenanceResponse(
                    action=request.action,
                    status="success",
                    message=f"Logs nettoyés ({len(lines)} -> 1000 lignes)",
                    details={
                        "size_before_mb": round(size_before / 1024 / 1024, 2),
                        "size_after_mb": round(size_after / 1024 / 1024, 2),
                        "lines_removed": len(lines) - 1000 if len(lines) > 1000 else 0,
                    },
                )
            else:
                return MaintenanceResponse(
                    action=request.action, status="error", message="Fichier de logs introuvable"
                )

        elif request.action == "clean_queue":
            if not job_queue or not redis_conn:
                raise HTTPException(status_code=503, detail="Redis Queue not available")

            # Compter avant nettoyage
            queued_count = len(job_queue.job_ids)

            # Vider la queue
            job_queue.empty()

            return MaintenanceResponse(
                action=request.action,
                status="success",
                message=f"Queue vidée ({queued_count} jobs supprimés)",
                details={"jobs_removed": queued_count},
            )

        elif request.action == "clean_finished_jobs":
            if not redis_conn:
                raise HTTPException(status_code=503, detail="Redis not available")

            finished_count = 0
            failed_count = 0

            # Nettoyer les jobs terminés
            finished_registry = FinishedJobRegistry("linkedin-bot", connection=redis_conn)
            finished_job_ids = finished_registry.get_job_ids()
            for job_id in finished_job_ids:
                try:
                    job = Job.fetch(job_id, connection=redis_conn)
                    job.delete()
                    finished_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete finished job {job_id}: {e}")

            # Nettoyer les jobs échoués
            failed_registry = FailedJobRegistry("linkedin-bot", connection=redis_conn)
            failed_job_ids = failed_registry.get_job_ids()
            for job_id in failed_job_ids:
                try:
                    job = Job.fetch(job_id, connection=redis_conn)
                    job.delete()
                    failed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete failed job {job_id}: {e}")

            total_removed = finished_count + failed_count

            return MaintenanceResponse(
                action=request.action,
                status="success",
                message=f"{total_removed} jobs nettoyés (terminés: {finished_count}, échoués: {failed_count})",
                details={
                    "finished_removed": finished_count,
                    "failed_removed": failed_count,
                    "total_removed": total_removed,
                },
            )

        elif request.action == "vacuum_db":
            # Optimiser la base de données SQLite
            from ...config.config_manager import get_config
            from ...core.database import get_database

            config = get_config()
            if not config.database.enabled:
                return MaintenanceResponse(
                    action=request.action, status="error", message="Base de données non activée"
                )

            db = get_database(config.database.db_path)
            # Exécuter VACUUM
            db.conn.execute("VACUUM")

            return MaintenanceResponse(
                action=request.action,
                status="success",
                message="Base de données optimisée (VACUUM exécuté)",
            )

        else:
            raise HTTPException(status_code=400, detail=f"Action inconnue: {request.action}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [MAINTENANCE] Erreur: {e}")
        return MaintenanceResponse(
            action=request.action,
            status="error",
            message=f"Erreur lors de la maintenance: {e!s}",
        )


# ═══════════════════════════════════════════════════════════════════
# ROUTES - DÉPLOIEMENT
# ═══════════════════════════════════════════════════════════════════


@router.post("/deploy", response_model=DeploymentResponse)
async def deploy(request: DeploymentRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Exécute des opérations de déploiement.

    Actions disponibles :
    - pull: Git pull pour récupérer les dernières modifications
    - rebuild: Rebuild les images Docker
    - restart: Redémarrer un ou tous les services
    - full_deploy: Git pull + rebuild + restart (déploiement complet)

    ATTENTION : Ces opérations peuvent causer une interruption de service.
    """
    logger.info(f"🚀 [DEPLOYMENT] Action demandée: {request.action}")

    # Vérification de sécurité : ces opérations sont dangereuses
    # Dans un environnement de production, il faudrait des protections supplémentaires

    try:
        if request.action == "pull":
            # Git pull
            result = subprocess.run(
                ["git", "pull"], cwd="/app", capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                return DeploymentResponse(
                    action=request.action,
                    status="success",
                    message="Code mis à jour depuis Git",
                    output=result.stdout,
                )
            else:
                return DeploymentResponse(
                    action=request.action,
                    status="error",
                    message="Erreur lors du git pull",
                    output=result.stderr,
                )

        elif request.action == "rebuild":
            # Rebuild Docker images
            # ATTENTION : Cette opération nécessite d'être exécutée depuis l'hôte Docker
            return DeploymentResponse(
                action=request.action,
                status="error",
                message="Rebuild doit être exécuté depuis l'hôte Docker. Utilisez: docker compose build",
            )

        elif request.action == "restart":
            # Restart service(s)
            # ATTENTION : Cette opération nécessite d'être exécutée depuis l'hôte Docker
            service_name = request.service or "tous les services"
            return DeploymentResponse(
                action=request.action,
                status="error",
                message=f"Restart de {service_name} doit être exécuté depuis l'hôte Docker. Utilisez: docker compose restart {request.service or ''}",
            )

        elif request.action == "full_deploy":
            # Déploiement complet
            return DeploymentResponse(
                action=request.action,
                status="error",
                message="Déploiement complet doit être exécuté depuis l'hôte Docker. Utilisez le script de déploiement.",
            )

        else:
            raise HTTPException(status_code=400, detail=f"Action inconnue: {request.action}")

    except subprocess.TimeoutExpired:
        return DeploymentResponse(
            action=request.action,
            status="error",
            message="Timeout lors de l'exécution de la commande",
        )
    except Exception as e:
        logger.error(f"❌ [DEPLOYMENT] Erreur: {e}")
        return DeploymentResponse(
            action=request.action, status="error", message=f"Erreur lors du déploiement: {e!s}"
        )
