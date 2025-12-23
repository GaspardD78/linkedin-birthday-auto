from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app_v2.api.routers import control, data
from app_v2.core.config import Settings
from app_v2.db.engine import init_db

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB
    logger.info("🚀 Initializing Database...")
    settings = Settings()
    await init_db(settings)
    logger.info("✅ Database initialized.")
    yield
    # Shutdown
    logger.info("🛑 Shutting down...")

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

@app.get("/")
async def root():
    return {"message": "LinkedIn Automation API V2 is running", "docs": "/docs"}
