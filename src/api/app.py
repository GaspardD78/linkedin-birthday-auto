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

logger = get_logger(__name__)

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

class ConfigUpdate(BaseModel):
    content: str

# --- Config ---
CONFIG_PATH = Path("config/config.yaml")
MESSAGES_PATH = Path("messages.txt")


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
    instrument_app(app)

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

# Expose Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


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


@app.get("/stats", response_model=MetricsResponse, tags=["Metrics"])
async def get_stats(
    days: int = 30,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère les statistiques d'activité (DB).

    Note: /metrics est réservé pour Prometheus.

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
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )


@app.post("/trigger")
async def trigger_job(
    request: TriggerRequest,
    background_tasks: BackgroundTasks,
    authenticated: bool = Depends(verify_api_key)
):
    """Déclenche une tâche (Anniversaire ou Visite)"""
    job_id = f"{request.job_type}-{int(datetime.now().timestamp())}"

    if request.job_type == "birthday":
        # On utilise RQ ou BackgroundTasks selon votre infra. Ici BackgroundTasks pour simplifier l'exemple docker autonome
        # Dans une vraie prod avec beaucoup de charge, utilisez queue.enqueue(run_bot_task, ...)
        background_tasks.add_task(
            run_bot_task,
            bot_mode=request.bot_mode,
            dry_run=request.dry_run,
            max_days_late=request.max_days_late
        )
    elif request.job_type == "visit":
        background_tasks.add_task(
            run_profile_visit_task,
            dry_run=request.dry_run
        )
    else:
        raise HTTPException(status_code=400, detail="Unknown job type")

    logger.info(f"🚀 Job triggered: {job_id}")
    return {"job_id": job_id, "status": "started", "type": request.job_type}


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

        log_file = Path("logs/linkedin_bot.log")

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
