"""
API REST FastAPI pour LinkedIn Birthday Bot.

Cette API permet de :
- Vérifier la santé du service (/health)
- Consulter les métriques (/metrics)
- Déclencher manuellement le bot (/trigger)
- Consulter les logs (/logs)
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header, Security
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue
import os

from ..config.config_manager import get_config
from ..core.database import get_database
from ..bots.birthday_bot import BirthdayBot
import yaml
from pathlib import Path

from ..bots.unlimited_bot import UnlimitedBirthdayBot
from ..utils.exceptions import LinkedInBotError
from ..utils.logging import get_logger
from .security import verify_api_key
from ..queue.tasks import run_bot_task, run_profile_visit_task
from ..monitoring.tracing import instrument_app, setup_tracing
from prometheus_client import make_asgi_app
from . import auth_routes # Import the new auth router

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION REDIS (RQ)
# ═══════════════════════════════════════════════════════════════════
REDIS_HOST = os.getenv('REDIS_HOST', 'redis-bot')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Connexion Redis pour enqueuing
try:
    redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)
    # Queue 'linkedin-bot' (doit matcher src/queue/worker.py)
    job_queue = Queue('linkedin-bot', connection=redis_conn)
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    job_queue = None

# ═══════════════════════════════════════════════════════════════════
# MODELS PYDANTIC POUR L'API
# ═══════════════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    """Modèle de réponse pour /health."""
    status: str = Field(description="Statut du service (healthy, degraded, unhealthy)")
    version: str = Field(description="Version de l'application")
    timestamp: str = Field(description="Timestamp ISO 8601")
    config_valid: bool = Field(description="Configuration valide")
    auth_available: bool = Field(description="Authentification disponible")
    database_connected: bool = Field(description="Base de données connectée")


class MetricsResponse(BaseModel):
    """Modèle de réponse pour /metrics."""
    period_days: int
    messages: Dict[str, int]
    contacts: Dict[str, int]
    profile_visits: Dict[str, int]
    errors: Dict[str, int]


class TriggerRequest(BaseModel):
    job_type: str = Field(..., description="Type de job: 'birthday' ou 'visit'")
    bot_mode: str = "standard"
    dry_run: bool = True
    max_days_late: Optional[int] = 10

class BirthdayConfig(BaseModel):
    """Configuration pour le bot d'anniversaire."""
    dry_run: bool = Field(default=True, description="Mode test sans envoi réel")
    process_late: bool = Field(default=False, description="Traiter les anniversaires en retard")
    max_days_late: Optional[int] = Field(default=10, description="Nombre de jours maximum de retard")

class VisitorConfig(BaseModel):
    """Configuration pour le bot de visite de profils."""
    dry_run: bool = Field(default=True, description="Mode test sans visite réelle")
    limit: int = Field(default=10, description="Nombre de profils à visiter")

class ConfigUpdate(BaseModel):
    content: str

# --- Config ---
CONFIG_PATH = Path("config/config.yaml")
MESSAGES_PATH = Path("messages.txt")
LATE_MESSAGES_PATH = Path("late_messages.txt")


class TriggerResponse(BaseModel):
    """Modèle de réponse pour /trigger."""
    job_id: str
    status: str
    message: str


class BotExecutionResult(BaseModel):
    """Modèle pour les résultats d'exécution du bot."""
    success: bool
    bot_mode: str
    messages_sent: int
    contacts_processed: int
    errors: int
    duration_seconds: float
    timestamp: str


# ═══════════════════════════════════════════════════════════════════
# STOCKAGE DES JOBS EN COURS
# ═══════════════════════════════════════════════════════════════════

# Stockage simple en mémoire (dans une vraie app, utiliser Redis/DB)
active_jobs: Dict[str, Dict[str, Any]] = {}


# ═══════════════════════════════════════════════════════════════════
# LIFECYCLE DE L'API
# ═══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gère le lifecycle de l'application."""
    # Startup
    logger.info("starting_api")
    config = get_config()

    setup_tracing(service_name="linkedin-bot-api")

    logger.info("api_started", mode=config.bot_mode, dry_run=config.dry_run)

    yield  # L'application tourne

    # Shutdown
    logger.info("shutting_down_api")


# ═══════════════════════════════════════════════════════════════════
# APPLICATION FASTAPI
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="LinkedIn Birthday Bot API",
    description="API REST pour automatiser les messages d'anniversaire LinkedIn",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Instrument the app with OpenTelemetry BEFORE adding routes/middleware
# This must be done before the app starts serving requests
instrument_app(app)

# Expose Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include the authentication router
app.include_router(auth_routes.router)


# Authentification importée de security.py


# ═══════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.get("/", tags=["Root"])
async def root():
    """Route racine avec informations de base."""
    return {
        "name": "LinkedIn Birthday Bot API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Vérifie la santé du service.

    Returns:
        - healthy: Tout fonctionne
        - degraded: Fonctionne mais problèmes mineurs
        - unhealthy: Service non fonctionnel
    """
    config = get_config()
    status = "healthy"
    issues = []

    # Vérifier config
    config_valid = config.validate() if hasattr(config, 'validate') else True

    # Vérifier auth
    auth_available = False
    try:
        from ..core.auth_manager import validate_auth
        auth_available = validate_auth()
    except Exception as e:
        logger.warning(f"Auth check failed: {e}")
        issues.append("auth_unavailable")

    # Vérifier database
    database_connected = False
    try:
        if config.database.enabled:
            db = get_database(config.database.db_path)
            db.get_statistics(days=1)
            database_connected = True
    except Exception as e:
        logger.warning(f"Database check failed: {e}")
        issues.append("database_unavailable")

    # Déterminer le statut global
    if not config_valid or not auth_available:
        status = "unhealthy"
    elif issues:
        status = "degraded"

    return HealthResponse(
        status=status,
        version="2.0.0",
        timestamp=datetime.now().isoformat(),
        config_valid=config_valid,
        auth_available=auth_available,
        database_connected=database_connected
    )


@app.get("/stats", tags=["Metrics"])
async def get_stats(
    days: int = 30,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère les statistiques d'activité pour le dashboard.

    Retourne les stats au format attendu par le dashboard Next.js:
    - wishes_sent_total: Total des messages envoyés
    - wishes_sent_today: Messages envoyés aujourd'hui
    - profiles_visited_total: Total des profils visités
    - profiles_visited_today: Profils visités aujourd'hui

    Args:
        days: Non utilisé mais conservé pour compatibilité
    """
    config = get_config()

    if not config.database.enabled:
        raise HTTPException(
            status_code=503,
            detail="Database not enabled in configuration"
        )

    try:
        db = get_database(config.database.db_path)
        # Utiliser la nouvelle méthode qui retourne le format attendu
        stats = db.get_today_statistics()
        return stats

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats: {str(e)}"
        )


@app.get("/detailed-stats", response_model=MetricsResponse, tags=["Metrics"])
async def get_detailed_stats(
    days: int = 30,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère les statistiques détaillées d'activité (DB).

    Format détaillé avec messages, contacts, visites et erreurs.

    Args:
        days: Nombre de jours d'historique (défaut: 30)
    """
    config = get_config()

    if not config.database.enabled:
        raise HTTPException(
            status_code=503,
            detail="Database not enabled in configuration"
        )

    try:
        db = get_database(config.database.db_path)
        stats = db.get_statistics(days=days)
        return MetricsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get detailed stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve detailed stats: {str(e)}"
        )


@app.get("/activity", tags=["Metrics"])
async def get_activity(
    days: int = 30,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère l'activité quotidienne détaillée (messages, visites, etc.).

    Args:
        days: Nombre de jours d'historique (défaut: 30)

    Returns:
        Liste des activités par jour avec le format:
        - date: Date au format YYYY-MM-DD
        - messages: Nombre total de messages envoyés
        - late_messages: Nombre de messages envoyés en retard
        - visits: Nombre de profils visités
        - contacts: Nombre de nouveaux contacts
    """
    config = get_config()

    if not config.database.enabled:
        raise HTTPException(
            status_code=503,
            detail="Database not enabled in configuration"
        )

    try:
        db = get_database(config.database.db_path)
        activity = db.get_daily_activity(days=days)
        return {"activity": activity, "days": days}

    except Exception as e:
        logger.error(f"Failed to get activity: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve activity: {str(e)}"
        )


@app.post("/trigger")
async def trigger_job(
    request: TriggerRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """Déclenche une tâche (Anniversaire ou Visite) via Redis Queue"""
    if not job_queue:
        raise HTTPException(status_code=503, detail="Redis Queue not available")

    try:
        if request.job_type == "birthday":
            job = job_queue.enqueue(
                run_bot_task,
                bot_mode=request.bot_mode,
                dry_run=request.dry_run,
                max_days_late=request.max_days_late,
                job_timeout='30m' # Timeout généreux pour le bot
            )
        elif request.job_type == "visit":
            job = job_queue.enqueue(
                run_profile_visit_task,
                dry_run=request.dry_run,
                job_timeout='45m'
            )
        else:
            raise HTTPException(status_code=400, detail="Unknown job type")

        logger.info(f"🚀 Job triggered: {job.id} ({request.job_type})")
        return {"job_id": job.id, "status": "queued", "type": request.job_type}
    except Exception as e:
        logger.error(f"Failed to enqueue job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enqueue job: {str(e)}")


@app.post("/start-birthday-bot", tags=["Bot"])
async def start_birthday_bot(
    config: BirthdayConfig,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Démarre le bot d'anniversaire avec la configuration fournie (via RQ).
    """
    if not job_queue:
        raise HTTPException(status_code=503, detail="Redis Queue not available")

    # Calculer max_days_late en fonction de process_late
    max_days = config.max_days_late if config.process_late else 0

    try:
        job = job_queue.enqueue(
            run_bot_task,
            bot_mode="standard",
            dry_run=config.dry_run,
            max_days_late=max_days,
            job_timeout='30m'
        )

        logger.info(f"✅ [BIRTHDAY BOT] Job {job.id} queued successfully")

        return {
            "job_id": job.id,
            "status": "queued",
            "message": f"Bot d'anniversaire mis en file d'attente (id={job.id})"
        }
    except Exception as e:
        logger.error(f"Failed to enqueue birthday bot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")


@app.post("/start-visitor-bot", tags=["Bot"])
async def start_visitor_bot(
    config: VisitorConfig,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Démarre le bot de visite de profils avec la configuration fournie (via RQ).
    """
    if not job_queue:
        raise HTTPException(status_code=503, detail="Redis Queue not available")

    try:
        job = job_queue.enqueue(
            run_profile_visit_task,
            dry_run=config.dry_run,
            limit=config.limit,
            job_timeout='45m'
        )

        logger.info(f"✅ [VISITOR BOT] Job {job.id} queued successfully")

        return {
            "job_id": job.id,
            "status": "queued",
            "message": f"Bot de visite mis en file d'attente (id={job.id})"
        }
    except Exception as e:
        logger.error(f"Failed to enqueue visitor bot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")


@app.post("/stop", tags=["Bot"])
async def stop_bot(
    authenticated: bool = Depends(verify_api_key)
):
    """
    Arrête tous les bots actifs.

    Annule les jobs en cours et vide la queue des jobs en attente.

    Returns:
        status: Statut de l'arrêt
        message: Message de confirmation
        cancelled_jobs: Nombre de jobs annulés
        emptied_queue: Nombre de jobs supprimés de la queue
    """
    logger.info("🛑 [STOP] Requête d'arrêt d'urgence reçue")

    if not job_queue or not redis_conn:
        logger.error("❌ [STOP] Redis Queue non disponible")
        raise HTTPException(
            status_code=503,
            detail="Redis Queue not available - cannot stop jobs"
        )

    try:
        cancelled_count = 0
        emptied_count = 0

        # 1. Annuler tous les jobs actuellement en cours (started)
        from rq.job import JobStatus
        from rq.registry import StartedJobRegistry

        started_registry = StartedJobRegistry('linkedin-bot', connection=redis_conn)
        started_job_ids = started_registry.get_job_ids()

        logger.info(f"📋 [STOP] Jobs en cours trouvés: {len(started_job_ids)}")

        for job_id in started_job_ids:
            try:
                from rq.job import Job
                job = Job.fetch(job_id, connection=redis_conn)
                # Marquer le job comme annulé
                job.cancel()
                cancelled_count += 1
                logger.info(f"   ✅ Job {job_id} annulé")
            except Exception as e:
                logger.warning(f"   ⚠️  Impossible d'annuler le job {job_id}: {e}")

        # 2. Vider la queue des jobs en attente (queued)
        queued_job_ids = job_queue.job_ids
        logger.info(f"📋 [STOP] Jobs en attente trouvés: {len(queued_job_ids)}")

        for job_id in queued_job_ids:
            try:
                from rq.job import Job
                job = Job.fetch(job_id, connection=redis_conn)
                job.delete()
                emptied_count += 1
                logger.info(f"   🗑️  Job {job_id} supprimé de la queue")
            except Exception as e:
                logger.warning(f"   ⚠️  Impossible de supprimer le job {job_id}: {e}")

        # 3. Vider complètement la queue
        job_queue.empty()

        total_stopped = cancelled_count + emptied_count
        logger.info(f"✅ [STOP] Arrêt d'urgence terminé: {cancelled_count} jobs annulés, {emptied_count} jobs supprimés")

        return {
            "status": "success",
            "message": f"Arrêt d'urgence effectué avec succès ({total_stopped} jobs arrêtés)",
            "cancelled_jobs": cancelled_count,
            "emptied_queue": emptied_count,
            "total_stopped": total_stopped
        }

    except Exception as e:
        logger.error(f"❌ [STOP] Erreur lors de l'arrêt: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'arrêt d'urgence: {str(e)}"
        )


@app.get("/jobs/{job_id}", tags=["Bot"])
async def get_job_status(
    job_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère le statut d'un job.

    Args:
        job_id: ID du job à consulter
    """
    if job_id not in active_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )

    return active_jobs[job_id]


@app.get("/logs", tags=["Logs"])
async def get_recent_logs(
    limit: int = 100,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère les logs récents.

    Args:
        limit: Nombre de lignes à retourner
    """
    try:
        from pathlib import Path
        import os

        # Chemin absolu Docker (cohérent avec le volume monté)
        log_file = Path(os.getenv('LOG_FILE', '/app/logs/linkedin_bot.log'))

        if not log_file.exists():
            return {"logs": [], "message": "Log file not found"}

        # Lire les dernières lignes
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        recent_lines = lines[-limit:] if len(lines) > limit else lines

        return {
            "logs": [line.strip() for line in recent_lines],
            "count": len(recent_lines),
            "total_lines": len(lines)
        }

    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read logs: {str(e)}"
        )


@app.get("/config/yaml")
async def get_yaml_config(authenticated: bool = Depends(verify_api_key)):
    """Lit le fichier config.yaml"""
    if not CONFIG_PATH.exists():
        raise HTTPException(404, "Config file not found")
    return {"content": CONFIG_PATH.read_text(encoding="utf-8")}

@app.post("/config/yaml")
async def update_yaml_config(config: ConfigUpdate, authenticated: bool = Depends(verify_api_key)):
    """Met à jour config.yaml"""
    try:
        # Vérifier que c'est du YAML valide
        yaml.safe_load(config.content)
        CONFIG_PATH.write_text(config.content, encoding="utf-8")
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(400, f"Invalid YAML: {str(e)}")

@app.get("/config/messages")
async def get_messages(authenticated: bool = Depends(verify_api_key)):
    """Lit le fichier messages.txt"""
    if not MESSAGES_PATH.exists():
        return {"content": ""}
    return {"content": MESSAGES_PATH.read_text(encoding="utf-8")}

@app.post("/config/messages")
async def update_messages(config: ConfigUpdate, authenticated: bool = Depends(verify_api_key)):
    """Met à jour messages.txt"""
    MESSAGES_PATH.write_text(config.content, encoding="utf-8")
    return {"status": "updated"}

@app.get("/config/late-messages")
async def get_late_messages(authenticated: bool = Depends(verify_api_key)):
    """Lit le fichier late_messages.txt"""
    if not LATE_MESSAGES_PATH.exists():
        return {"content": ""}
    return {"content": LATE_MESSAGES_PATH.read_text(encoding="utf-8")}

@app.post("/config/late-messages")
async def update_late_messages(config: ConfigUpdate, authenticated: bool = Depends(verify_api_key)):
    """Met à jour late_messages.txt"""
    LATE_MESSAGES_PATH.write_text(config.content, encoding="utf-8")
    return {"status": "updated"}
# ═══════════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# EXCEPTION HANDLERS
# ═══════════════════════════════════════════════════════════════════

@app.exception_handler(LinkedInBotError)
async def linkedin_bot_error_handler(request, exc: LinkedInBotError):
    """Handler pour les exceptions LinkedInBotError."""
    return JSONResponse(
        status_code=500,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "code": exc.error_code.name,
            "recoverable": exc.recoverable,
            "details": exc.details
        }
    )


# Point d'entrée pour uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
