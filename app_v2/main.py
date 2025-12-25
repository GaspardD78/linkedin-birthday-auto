from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime, timezone

from app_v2.api.routers import control, data
from app_v2.core.config import Settings
from app_v2.db.engine import init_db, get_engine, get_session_maker
from app_v2.core.redis_client import get_redis_client, close_redis_client

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and Redis
    logger.info("🚀 Initializing Database...")
    settings = Settings()
    await init_db(settings)
    logger.info("✅ Database initialized.")

    # Initialize Redis (optional, for rate limiter)
    try:
        logger.info("🚀 Connecting to Redis...")
        await get_redis_client(settings)
        logger.info("✅ Redis connected.")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}. Continuing without Redis.")

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")
    try:
        await close_redis_client()
        logger.info("✅ Redis closed.")
    except Exception as e:
        logger.warning(f"⚠️ Redis close failed: {e}")
    logger.info("✅ Shutdown complete.")

app = FastAPI(
    title="LinkedIn Automation API V2",
    description="API REST pour les services Birthday et Visitor (Sourcing).",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Configuration
# Autoriser le Dashboard (localhost:3000) et autres origines si nécessaire
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://dashboard:3000" # Docker service name
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(control.router)
app.include_router(data.router)


# =========================================================================
# HEALTH CHECK ENDPOINTS (PHASE 1 - PRODUCTION READY)
# =========================================================================


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "LinkedIn Automation API V2 is running",
        "docs": "/docs",
        "version": "2.0.0",
        "status": "operational",
    }


@app.get("/health", tags=["Health"])
async def health():
    """
    Liveness probe - Indicates if the application is running.

    Used by Kubernetes/Docker for container health monitoring.
    Returns immediately if the app is responsive.

    Returns:
        {
            "status": "healthy",
            "timestamp": "2025-12-25T12:00:00Z",
            "version": "2.0.0"
        }
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.0.0",
        },
    )


@app.get("/ready", tags=["Health"])
async def readiness(settings: Settings = Depends(lambda: Settings())):
    """
    Readiness probe - Indicates if the application is ready to serve requests.

    Checks:
    - Database connectivity and status
    - Redis availability (optional)
    - Required tables and indexes

    Returns:
        {
            "status": "ready",
            "database": "ok",
            "redis": "ok|unavailable",
            "dependencies": [list of OK dependencies],
            "timestamp": "2025-12-25T12:00:00Z"
        }

    Status codes:
        - 200: Application is ready
        - 503: Application is not ready (dependency issues)
    """
    checks = {"database": None, "redis": None}
    dependencies = []

    # Check Database
    try:
        engine = get_engine(settings)
        async with engine.connect() as conn:
            await conn.execute(conn.dialect.statement_compiler.process("SELECT 1"))
        checks["database"] = "ok"
        dependencies.append("database")
        logger.debug("✅ Database check passed")
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        logger.error(f"❌ Database check failed: {e}")

    # Check Redis (optional)
    try:
        redis_client = await get_redis_client(settings)
        await redis_client.ping()
        checks["redis"] = "ok"
        dependencies.append("redis")
        logger.debug("✅ Redis check passed")
    except Exception as e:
        checks["redis"] = "unavailable"  # Not critical
        logger.warning(f"⚠️ Redis check failed: {e}")

    # Determine overall status
    is_ready = checks["database"] == "ok"

    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={
            "status": "ready" if is_ready else "not_ready",
            "database": checks["database"],
            "redis": checks["redis"],
            "dependencies": dependencies,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.0.0",
        },
    )
