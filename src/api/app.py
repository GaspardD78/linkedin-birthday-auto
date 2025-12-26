import os
import signal
import sys
import logging
import asyncio
import uvicorn
import yaml
import json
import collections
import pickle
import time
from contextlib import asynccontextmanager
from typing import List, Optional, Deque, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from prometheus_client import make_asgi_app
import redis

from src.api.security import verify_api_key, API_KEY_NAME
from src.core.database import get_database
from src.utils.logging import setup_logging
from src.utils.data_files import initialize_data_files
from src.monitoring.tracing import setup_tracing, instrument_app

# Configure logging using structlog
setup_logging(log_file="logs/linkedin_bot.log")
logger = logging.getLogger(__name__)

# --- Models ---

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    database: str

class MetricsResponse(BaseModel):
    messages_sent_today: int
    profiles_visited_today: int
    errors_today: int

class ConfigUpdate(BaseModel):
    config_yaml: str

class TriggerResponse(BaseModel):
    status: str
    job_id: str
    message: str

class BotExecutionResult(BaseModel):
    status: str
    details: Optional[Dict[str, Any]] = None

# --- Application Lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gère le cycle de vie de l'application (démarrage/arrêt)"""
    logger.info("🚀 API Starting up...")

    # Vérification des fichiers critiques
    log_file = "logs/linkedin_bot.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    if not os.path.exists(log_file):
        with open(log_file, "w") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [INFO] Log file initialized\n")

    # Initialisation des fichiers de données (messages.txt, late_messages.txt)
    initialize_data_files()

    # Initialisation de la BDD
    try:
        db = get_database()
        logger.info(f"Database connected: {db.db_path}")
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}")
        # Do not exit immediately, allowing the dashboard to see the error via /health

    # Vérification Redis avec retry logic
    redis_host = os.getenv("REDIS_HOST", "redis-bot")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    max_retries = 10
    logger.info(f"Attempting to connect to Redis at {redis_host}:{redis_port}...")

    for attempt in range(max_retries):
        try:
            redis_conn = redis.Redis(
                host=redis_host,
                port=redis_port,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            redis_conn.ping()
            logger.info(f"✅ Redis connection verified at {redis_host}:{redis_port}")
            break
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            if attempt == max_retries - 1:
                logger.error(f"❌ Failed to connect to Redis after {max_retries} attempts: {e}")
                logger.warning("⚠️ API will start but Redis-dependent endpoints may fail")
            else:
                wait_time = 2 ** attempt
                logger.warning(f"Redis connection attempt {attempt + 1}/{max_retries} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Unexpected error during Redis connection: {e}")
            break

    # Validation finale des routes
    validate_api_routes()

    yield

    logger.info("🛑 API Shutting down...")
    # Nettoyage si nécessaire

# --- App Definition ---

app = FastAPI(
    title="LinkedIn Automation API",
    description="API de contrôle pour le bot d'automatisation LinkedIn (Raspberry Pi 4 Optimized)",
    version="2.3.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- OpenTelemetry Tracing Setup ---
setup_tracing(service_name="linkedin-bot-api")
instrument_app(app)

# --- Middleware ---

# CORS Configuration Sécurisée (Whitelist explicite)
# Lire les origines autorisées depuis l'environnement
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://192.168.1.50:3000"
).split(",")

logger.info(f"CORS configured with allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ✅ Origines explicites uniquement
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # ✅ Méthodes spécifiques
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],  # ✅ Headers spécifiques
    max_age=3600,  # Cache preflight 1h
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )

# --- Routes Inclusion ---

# Helper for safe inclusion
def include_safe(module_path: str, router_name: str = "router"):
    try:
        module = __import__(module_path, fromlist=[router_name])
        router_obj = getattr(module, router_name)
        app.include_router(router_obj)
        logger.info(f"✅ Router included: {module_path}")
    except (ImportError, SyntaxError, AttributeError) as e:
        logger.critical(f"FATAL: Cannot load {module_path}.{router_name}: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"UNEXPECTED ERROR loading {module_path}: {type(e).__name__}: {e}")
        raise


def validate_api_routes():
    """Vérifie que suffisamment de routes sont chargées."""
    total_routes = len(app.routes)
    routes_by_prefix = collections.defaultdict(int)

    for route in app.routes:
        if hasattr(route, "path"):
            # Simple prefix extraction (e.g., /api/bot -> /api/bot)
            parts = route.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "api":
                prefix = f"/{parts[0]}/{parts[1]}"
            elif len(parts) >= 1:
                prefix = f"/{parts[0]}"
            else:
                prefix = "/"
            routes_by_prefix[prefix] += 1

    logger.info(f"✅ {total_routes} routes loaded: {dict(routes_by_prefix)}")

    if total_routes < 10:
        raise RuntimeError(f"FATAL: API has only {total_routes} routes loaded. Some imports failed. Check logs above.")

# 1. Critical Routers (Auth, Bot Control)
include_safe("src.api.auth_routes", "router")
include_safe("src.api.routes.bot_control", "router")
include_safe("src.api.routes.automation_control", "router")

# 1b. Configuration & Messages
include_safe("src.api.routes.config_routes", "router")

# 2. Features
include_safe("src.api.routes.sourcing", "router")
include_safe("src.api.routes.campaign_routes", "router")
include_safe("src.api.routes.crm", "router")
include_safe("src.api.routes.visitor_routes", "router")
include_safe("src.api.routes.notifications", "router")
include_safe("src.api.routes.blacklist", "router")
include_safe("src.api.routes.nurturing", "router")
include_safe("src.api.routes.deployment", "router")

# 3. Utilities & Streaming
include_safe("src.api.routes.stream_routes", "router")
include_safe("src.api.routes.debug_routes", "router")

# 4. Scheduler (Often problematic due to DB/deps)
include_safe("src.api.routes.scheduler_routes", "router")


# --- Prometheus Metrics ---

try:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
except Exception as e:
    logger.error(f"Failed to mount metrics: {e}")

# --- Core Endpoints ---

@app.get("/", tags=["General"])
async def root():
    return {
        "name": "LinkedIn Automation API",
        "version": "2.3.0",
        "status": "running",
        "docs": "/docs"
    }

START_TIME = time.time()

@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Vérifie l'état de santé de l'API"""
    uptime = time.time() - START_TIME

    # Check DB
    try:
        db = get_database()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "version": "2.3.0",
        "uptime_seconds": uptime,
        "database": db_status
    }

@app.get("/health/api-routes", tags=["General"])
async def health_api_routes():
    """Diagnostic des routes API chargées."""
    total_routes = len(app.routes)
    routes_by_prefix = collections.defaultdict(int)

    for route in app.routes:
        if hasattr(route, "path"):
            parts = route.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "api":
                prefix = f"/{parts[0]}/{parts[1]}"
            elif len(parts) >= 1:
                prefix = f"/{parts[0]}"
            else:
                prefix = "/"
            routes_by_prefix[prefix] += 1

    return {
        "status": "healthy" if total_routes >= 10 else "degraded",
        "total_routes": total_routes,
        "routes_by_prefix": dict(routes_by_prefix)
    }

@app.get("/health/db-schema-version", tags=["General"])
async def health_db_schema():
    """Diagnostic de la version du schéma BDD."""
    try:
        db = get_database()
        current = db.get_current_schema_version()
        return {
            "current_version": current,
            "expected_version": db.SCHEMA_VERSION,
            "status": "healthy" if current == db.SCHEMA_VERSION else "migration_pending"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# --- Config Management ---

@app.get("/config/yaml", tags=["Configuration"], dependencies=[Security(verify_api_key)])
async def get_config_yaml():
    """Lit le fichier de configuration YAML"""
    config_path = "config/config.yaml"
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                content = f.read()
            return {"content": content}
        return {"content": ""}
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/yaml", tags=["Configuration"], dependencies=[Security(verify_api_key)])
async def update_config_yaml(update: ConfigUpdate):
    """Met à jour le fichier de configuration YAML"""
    config_path = "config/config.yaml"
    try:
        # Validate YAML syntax
        try:
            yaml.safe_load(update.config_yaml)
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML syntax: {e}")

        # Backup existing
        if os.path.exists(config_path):
            os.rename(config_path, f"{config_path}.bak")

        with open(config_path, "w") as f:
            f.write(update.config_yaml)

        logger.info("Configuration updated successfully")
        return {"status": "success", "message": "Configuration updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Log Access ---

@app.get("/logs", tags=["Logs"], dependencies=[Security(verify_api_key)])
async def get_logs(lines: int = 100, service: str = "all"):
    """Récupère les derniers logs"""
    log_file = "logs/linkedin_bot.log"
    if not os.path.exists(log_file):
        return {"logs": []}

    try:
        # Efficient last N lines reading
        with open(log_file, "r") as f:
            # Using deque to keep only last N lines in memory
            last_lines = collections.deque(f, maxlen=lines)

        return {"logs": list(last_lines)}
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return {"logs": [], "error": str(e)}

# --- Bot Stats ---

@app.get("/stats", tags=["Bot Stats"])
async def get_bot_stats():
    """Récupère les statistiques d'exécution du bot (JSON file)"""
    stats_file = "logs/bot_stats.json"

    if not os.path.exists(stats_file):
        return {
            "last_run": None,
            "status": "pending",
            "messages_sent": 0,
            "messages_failed": 0,
            "birthdays_today": 0,
            "birthdays_late": 0,
            "duration_seconds": 0,
            "errors": [],
            "created_at": None
        }

    try:
        with open(stats_file, "r") as f:
            stats = json.load(f)
        return stats
    except Exception as e:
        logger.error(f"Error reading stats file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read stats file")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
