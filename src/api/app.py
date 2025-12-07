"""
API REST FastAPI pour LinkedIn Birthday Bot.

Cette API permet de :
- Vérifier la santé du service (/health)
- Consulter les métriques (/metrics)
- Déclencher manuellement le bot (/trigger)
- Consulter les logs (/logs)
"""

from contextlib import asynccontextmanager
from datetime import datetime
import os
from pathlib import Path
from typing import Any, Optional

import aiofiles
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field
from redis import Redis
from rq import Queue
import yaml

from ..config.config_manager import get_config
from ..core.database import get_database
from ..monitoring.tracing import instrument_app, setup_tracing
from ..utils.exceptions import LinkedInBotError
from ..utils.logging import get_logger
from ..utils.data_files import initialize_data_files  # 🚀 Refactored: no more duplication
import pickle
from . import auth_routes  # Import the new auth router
from .routes import deployment, bot_control, debug_routes, automation_control, notifications, scheduler_routes  # Import the routers
from .security import verify_api_key

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION REDIS (RQ)
# ═══════════════════════════════════════════════════════════════════
REDIS_HOST = os.getenv("REDIS_HOST", "redis-bot")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Connexion Redis pour enqueuing
try:
    redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)
    # Queue 'linkedin-bot' (doit matcher src/queue/worker.py)
    job_queue = Queue("linkedin-bot", connection=redis_conn)
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
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
    messages: dict[str, int]
    contacts: dict[str, int]
    profile_visits: dict[str, int]
    errors: dict[str, int]


# Bot configuration models moved to src/api/routes/bot_control.py
# to avoid duplication and maintain single source of truth


class ConfigUpdate(BaseModel):
    content: str


# --- Config ---
CONFIG_PATH = Path("config/config.yaml")
# Messages files are stored in /app/data/ (persistent volume shared with dashboard)
MESSAGES_PATH = Path("/app/data/messages.txt")
LATE_MESSAGES_PATH = Path("/app/data/late_messages.txt")


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
active_jobs: dict[str, dict[str, Any]] = {}


# ═══════════════════════════════════════════════════════════════════
# LIFECYCLE DE L'API
# ═══════════════════════════════════════════════════════════════════




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gère le lifecycle de l'application."""
    # Startup
    logger.info("starting_api")

    # Initialiser les fichiers de données avant de démarrer
    initialize_data_files()

    config = get_config()

    setup_tracing(service_name="linkedin-bot-api")

    # Start automation scheduler
    try:
        from src.scheduler.scheduler import AutomationScheduler
        scheduler = AutomationScheduler()
        scheduler.start()
        logger.info("automation_scheduler_started")
    except Exception as e:
        logger.error(f"Failed to start automation scheduler: {e}", exc_info=True)

    logger.info("api_started", mode=config.bot_mode, dry_run=config.dry_run)

    yield  # L'application tourne

    # Shutdown
    logger.info("shutting_down_api")

    # Shutdown automation scheduler
    try:
        from src.scheduler.scheduler import AutomationScheduler
        scheduler = AutomationScheduler()
        scheduler.shutdown(wait=True)
        logger.info("automation_scheduler_stopped")
    except Exception as e:
        logger.warning(f"Error stopping automation scheduler: {e}", exc_info=True)

    # Close any active Playwright browser sessions to prevent memory leaks
    try:
        from . import auth_routes
        await auth_routes.close_browser_session()
        logger.info("playwright_sessions_closed")
    except Exception as e:
        logger.warning(f"Error closing Playwright sessions during shutdown: {e}", exc_info=True)


# ═══════════════════════════════════════════════════════════════════
# APPLICATION FASTAPI
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="LinkedIn Birthday Bot API",
    description="API REST pour automatiser les messages d'anniversaire LinkedIn",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Instrument the app with OpenTelemetry BEFORE adding routes/middleware
# This must be done before the app starts serving requests
# Only instrument if telemetry is explicitly enabled (saves CPU/RAM on Pi4)
if os.getenv("ENABLE_TELEMETRY", "false").lower() in ("true", "1", "yes"):
    instrument_app(app)
    logger.info("opentelemetry_instrumentation_enabled")
else:
    logger.debug("opentelemetry_instrumentation_disabled")

# Expose Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include the authentication router
app.include_router(auth_routes.router)

# Include the deployment router
app.include_router(deployment.router)

# Include the bot control router (Granular Control)
app.include_router(bot_control.router)

# Include the automation control router
app.include_router(automation_control.router)

# Include the debug router
app.include_router(debug_routes.router)

# Include the notifications router
app.include_router(notifications.router)

# Include the scheduler router
app.include_router(scheduler_routes.router)


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
        "health": "/health",
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
    # Si get_config() a réussi, la config est valide (Pydantic v2 valide à la création)
    config_valid = True

    # Vérifier auth
    auth_available = False
    try:
        from ..core.auth_manager import validate_auth

        auth_available = validate_auth()
    except Exception as e:
        logger.warning(f"Auth check failed: {e}", exc_info=True)
        issues.append("auth_unavailable")

    # Vérifier database
    database_connected = False
    try:
        if config.database.enabled:
            db = get_database(config.database.db_path)
            db.get_statistics(days=1)
            database_connected = True
    except Exception as e:
        logger.warning(f"Database check failed: {e}", exc_info=True)
        issues.append("database_unavailable")

    # Déterminer le statut global
    # Note: auth_available n'est pas requis pour que l'API soit healthy
    # L'auth peut être uploadé plus tard via le dashboard
    if not config_valid:
        status = "unhealthy"
    elif not auth_available or issues:
        status = "degraded"

    return HealthResponse(
        status=status,
        version="2.0.0",
        timestamp=datetime.now().isoformat(),
        config_valid=config_valid,
        auth_available=auth_available,
        database_connected=database_connected,
    )


@app.get("/stats", tags=["Metrics"])
async def get_stats(days: int = 30, authenticated: bool = Depends(verify_api_key)):
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

    # Valeurs par défaut si la base de données n'est pas accessible
    default_stats = {
        "wishes_sent_total": 0,
        "wishes_sent_today": 0,
        "wishes_sent_week": 0,
        "profiles_visited_total": 0,
        "profiles_visited_today": 0,
    }

    if not config.database.enabled:
        logger.warning("Database not enabled, returning default stats")
        return default_stats

    try:
        db = get_database(config.database.db_path)
        # Utiliser la nouvelle méthode qui retourne le format attendu
        stats = db.get_today_statistics()
        return stats

    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        # Retourner des valeurs par défaut au lieu d'une erreur
        # pour permettre au dashboard de s'afficher correctement
        logger.warning("Returning default stats due to database error", exc_info=True)
        return default_stats


@app.get("/detailed-stats", response_model=MetricsResponse, tags=["Metrics"])
async def get_detailed_stats(days: int = 30, authenticated: bool = Depends(verify_api_key)):
    """
    Récupère les statistiques détaillées d'activité (DB).

    Format détaillé avec messages, contacts, visites et erreurs.

    Args:
        days: Nombre de jours d'historique (défaut: 30)
    """
    config = get_config()

    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled in configuration")

    try:
        db = get_database(config.database.db_path)
        stats = db.get_statistics(days=days)
        return MetricsResponse(**stats)

    except Exception as e:
        logger.error(f"Failed to get detailed stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve detailed stats: {e!s}")


@app.get("/activity", tags=["Metrics"])
async def get_activity(days: int = 30, authenticated: bool = Depends(verify_api_key)):
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
        logger.warning("Database not enabled, returning empty activity")
        return {"activity": [], "days": days}

    try:
        db = get_database(config.database.db_path)
        activity = db.get_daily_activity(days=days)
        return {"activity": activity, "days": days}

    except Exception as e:
        logger.error(f"Failed to get activity: {e}", exc_info=True)
        # Retourner une liste vide au lieu d'une erreur
        logger.warning("Returning empty activity due to database error", exc_info=True)
        return {"activity": [], "days": days}


@app.get("/contacts", tags=["Metrics"])
async def get_contacts(limit: Optional[int] = None, sort: str = "messages", authenticated: bool = Depends(verify_api_key)):
    """
    Récupère la liste des contacts.

    Args:
        limit: Nombre maximum de contacts à retourner
        sort: Tri (messages, name, date)

    Returns:
        Liste des contacts avec leurs statistiques
    """
    config = get_config()

    if not config.database.enabled:
        logger.warning("Database not enabled, returning empty contacts")
        return {"contacts": []}

    try:
        db = get_database(config.database.db_path)

        if sort == "messages":
            # Récupérer les top contacts triés par nombre de messages
            contacts = db.get_top_contacts(limit=limit or 50)
        else:
            # Pour les autres tris, retourner une liste vide pour l'instant
            # TODO: implémenter d'autres méthodes de tri si nécessaire
            contacts = []

        return {"contacts": contacts}

    except Exception as e:
        logger.error(f"Failed to get contacts: {e}", exc_info=True)
        logger.warning("Returning empty contacts due to database error", exc_info=True)
        return {"contacts": []}


# ═══════════════════════════════════════════════════════════════════
# DEPRECATED ROUTES - Removed in favor of /bot/* routes (bot_control.py)
# ═══════════════════════════════════════════════════════════════════
# Legacy routes /trigger, /start-birthday-bot, /start-visitor-bot, /stop
# have been removed to avoid duplication with the new granular bot control
# endpoints in src/api/routes/bot_control.py
#
# Dashboard now uses:
# - POST /bot/start/birthday (instead of /start-birthday-bot)
# - POST /bot/start/visitor (instead of /start-visitor-bot)
# - POST /bot/stop (instead of /stop)
# - GET /bot/status (for detailed status)
# ═══════════════════════════════════════════════════════════════════


@app.get("/jobs/{job_id}", tags=["Bot"])
async def get_job_status(job_id: str, authenticated: bool = Depends(verify_api_key)):
    """
    Récupère le statut d'un job.

    Args:
        job_id: ID du job à consulter
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return active_jobs[job_id]


@app.get("/logs", tags=["Logs"])
async def get_recent_logs(
    limit: int = 100,
    service: str = "worker",
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère les logs récents d'un service spécifique.

    Args:
        limit: Nombre de lignes à retourner
        service: Service cible ('worker', 'api', 'dashboard' ou 'all')
    """
    try:
        import os
        import glob
        from collections import deque
        from pathlib import Path

        # Validation de l'entrée
        allowed_services = ["worker", "api", "dashboard", "all"]
        if service not in allowed_services:
            raise HTTPException(status_code=400, detail=f"Invalid service. Must be one of {allowed_services}")

        log_dir = Path("/app/logs")

        # Déterminer les fichiers à lire
        files_to_read = []
        if service == "all":
            files_to_read = glob.glob(str(log_dir / "*.log"))
            # Trier par date de modification (plus récent en dernier)
            files_to_read.sort(key=os.path.getmtime)
        else:
            # Gestion du suffixe ajouté par logging.py (ex: linkedin_bot_worker.log)
            base_name = os.getenv("LOG_FILE", "linkedin_bot.log")
            base_root, ext = os.path.splitext(base_name)

            # Essayer le fichier exact, puis avec suffixe
            target_files = [
                log_dir / f"{base_root}_{service}{ext}", # linkedin_bot_worker.log
                log_dir / f"{service}.log",               # worker.log (fallback)
                log_dir / base_name                       # linkedin_bot.log (fallback générique)
            ]

            for f in target_files:
                if f.exists():
                    files_to_read.append(f)
                    break # On prend le premier qui matche

        if not files_to_read:
            return {"logs": [], "message": f"No log files found for service '{service}'"}

        all_lines = []
        total_lines_estimate = 0

        for file_path in files_to_read:
            try:
                # Utiliser deque pour lire efficacement les dernières lignes sans tout charger en mémoire
                # Lecture asynchrone avec aiofiles pour ne pas bloquer l'event loop
                async with aiofiles.open(file_path, encoding="utf-8") as f:
                    last_lines = deque(maxlen=limit)
                    async for line in f:
                        last_lines.append(line)

                    prefix = f"[{Path(file_path).stem}] " if len(files_to_read) > 1 else ""
                    all_lines.extend([f"{prefix}{line.strip()}" for line in last_lines])

                    # Estimation approximative
                    total_lines_estimate += 100 # On ne sait pas vraiment sans tout lire
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}", exc_info=True)

        # Si on a lu plusieurs fichiers, on prend globalement les dernières lignes
        # Note: ce n'est pas un tri parfait par timestamp inter-fichiers,
        # mais ça respecte l'ordre chronologique approximatif (fichiers triés par mtime)
        recent_lines = all_lines[-limit:] if len(all_lines) > limit else all_lines

        return {
            "logs": recent_lines,
            "count": len(recent_lines),
            "total_lines": "unknown (optimized reading)",
            "files_read": [str(f) for f in files_to_read]
        }

    except Exception as e:
        logger.error(f"Failed to read logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {e!s}")


@app.get("/config/yaml")
async def get_yaml_config(authenticated: bool = Depends(verify_api_key)):
    """Lit le fichier config.yaml (async I/O)"""
    if not CONFIG_PATH.exists():
        raise HTTPException(404, "Config file not found")
    async with aiofiles.open(CONFIG_PATH, encoding="utf-8") as f:
        content = await f.read()
    return {"content": content}


@app.post("/config/yaml")
async def update_yaml_config(config: ConfigUpdate, authenticated: bool = Depends(verify_api_key)):
    """Met à jour config.yaml (async I/O)"""
    try:
        # Vérifier que c'est du YAML valide
        yaml.safe_load(config.content)
        async with aiofiles.open(CONFIG_PATH, 'w', encoding="utf-8") as f:
            await f.write(config.content)
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(400, f"Invalid YAML: {e!s}")


@app.get("/config/messages")
async def get_messages(authenticated: bool = Depends(verify_api_key)):
    """Lit le fichier messages.txt (async I/O)"""
    if not MESSAGES_PATH.exists():
        return {"content": ""}
    async with aiofiles.open(MESSAGES_PATH, encoding="utf-8") as f:
        content = await f.read()
    return {"content": content}


@app.post("/config/messages")
async def update_messages(config: ConfigUpdate, authenticated: bool = Depends(verify_api_key)):
    """Met à jour messages.txt (async I/O)"""
    async with aiofiles.open(MESSAGES_PATH, 'w', encoding="utf-8") as f:
        await f.write(config.content)
    return {"status": "updated"}


@app.get("/config/late-messages")
async def get_late_messages(authenticated: bool = Depends(verify_api_key)):
    """Lit le fichier late_messages.txt (async I/O)"""
    if not LATE_MESSAGES_PATH.exists():
        return {"content": ""}
    async with aiofiles.open(LATE_MESSAGES_PATH, encoding="utf-8") as f:
        content = await f.read()
    return {"content": content}


@app.post("/config/late-messages")
async def update_late_messages(config: ConfigUpdate, authenticated: bool = Depends(verify_api_key)):
    """Met à jour late_messages.txt (async I/O)"""
    async with aiofiles.open(LATE_MESSAGES_PATH, 'w', encoding="utf-8") as f:
        await f.write(config.content)
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
            "details": exc.details,
        },
    )


@app.exception_handler(pickle.PicklingError)
async def pickling_error_handler(request, exc: pickle.PicklingError):
    """Handler pour les erreurs de sérialisation (APScheduler)."""
    logger.error(f"Pickling error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "SerializationError",
            "detail": f"Impossible de sérialiser les données de la tâche: {exc!s}"
        }
    )


@app.exception_handler(TypeError)
async def type_error_handler(request, exc: TypeError):
    """Handler pour les TypeError (souvent liés au pickling)."""
    # On ne veut attraper que les erreurs liées au pickling, mais c'est difficile à distinguer.
    # On loggue l'erreur et on renvoie un 500 propre si c'est une erreur "cannot pickle".
    if "pickle" in str(exc) or "serialize" in str(exc):
        logger.error(f"Serialization/Type error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "SerializationError",
                "detail": f"Erreur de sérialisation: {exc!s}"
            }
        )

    # Pour les autres TypeError, on laisse FastAPI gérer ou on renvoie un 500 générique
    logger.error(f"Internal Type Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "detail": str(exc)
        }
    )


# Point d'entrée pour uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
