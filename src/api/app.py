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

from src.api.security import verify_api_key, API_KEY_NAME
from src.core.database import get_database
from src.utils.logging import setup_logging

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

    # Initialisation de la BDD
    try:
        db = get_database()
        logger.info(f"Database connected: {db.db_path}")
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Log registered routes
    logger.info("✅ Registered Routes:")
    for route in app.routes:
        if hasattr(route, "path"):
            methods = ",".join(route.methods) if hasattr(route, "methods") else "ALL"
            logger.info(f" - {route.path} [{methods}]")

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

# --- Middleware ---

# CORS (Restrictive in production, but open for dashboard on local network)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en prod si exposé internet
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Import routers safely
try:
    from src.api.routes import bot_control
    from src.api.routes import automation_control
    from src.api.routes import scheduler_routes
    from src.api.routes import crm
    from src.api.routes import visitor_routes
    from src.api.routes import notifications
    from src.api.routes import blacklist
    from src.api.routes import nurturing
    from src.api.routes import deployment
    from src.api.routes import sourcing
    from src.api.routes import campaign_routes
    from src.api.routes import stream_routes
    from src.api.routes import debug_routes
    from src.api.auth_routes import router as auth_router

    # Include routers.
    # Note: Routers already have their 'prefix' defined in their files.
    # We include them WITHOUT an additional prefix argument to avoid double prefixes (e.g. /scheduler/scheduler).

    app.include_router(auth_router)             # prefix="/auth"
    app.include_router(bot_control.router)      # prefix="/bot"
    app.include_router(automation_control.router) # prefix="/automation"
    app.include_router(scheduler_routes.router) # prefix="/scheduler"
    app.include_router(crm.router)              # prefix="/crm"
    app.include_router(visitor_routes.router)   # prefix="/visitor"
    app.include_router(notifications.router)    # prefix="/notifications"
    app.include_router(blacklist.router)        # prefix="/blacklist"
    app.include_router(nurturing.router)        # prefix="/nurturing"
    app.include_router(deployment.router)       # prefix="/deployment"
    app.include_router(sourcing.router)         # prefix="/sourcing"
    app.include_router(campaign_routes.router)  # prefix="/campaigns"
    app.include_router(stream_routes.router)    # prefix="/stream"
    app.include_router(debug_routes.router)     # prefix="/debug"

except ImportError as e:
    logger.error(f"Failed to import some routers: {e}")

# --- Prometheus Metrics ---

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
