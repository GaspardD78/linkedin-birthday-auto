"""
API Router pour les statistiques et insights du Visitor Bot.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import subprocess
import os
import signal
import sys
import logging

from src.core.database import get_database
from src.config.config_manager import get_config
from src.utils.logging import get_logger
from ..security import verify_api_key

router = APIRouter(prefix="/visitor", tags=["Visitor Bot"])
logger = get_logger(__name__)

# Global variable to store the subprocess
VISITOR_PROCESS: Optional[subprocess.Popen] = None

# --- Pydantic Models ---

class SkillCount(BaseModel):
    name: str
    count: int

class FunnelStats(BaseModel):
    visited: int
    scraped: int
    qualified: int

class VisitorInsights(BaseModel):
    avg_fit_score: float
    open_to_work_count: int
    top_skills: List[SkillCount]
    funnel: FunnelStats

class VisitorRunRequest(BaseModel):
    limit: Optional[int] = Field(None, description="Limite de profils à visiter", ge=1)
    keywords: Optional[List[str]] = Field(None, description="Override des mots-clés de recherche")

class BotStatusResponse(BaseModel):
    status: str
    pid: Optional[int] = None
    message: Optional[str] = None

class ProfileResponse(BaseModel):
    profile_url: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    current_company: Optional[str] = None
    years_experience: Optional[int] = None
    fit_score: Optional[float] = None
    scraped_at: Optional[str] = None
    # Add other fields as needed, keeping it lightweight for list view

class ProfileListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    profiles: List[Dict[str, Any]] # Using Dict to accommodate all flexible fields

# --- Endpoints ---

@router.get("/stats", response_model=VisitorInsights)
async def get_visitor_stats(days: int = 30, authenticated: bool = Depends(verify_api_key)):
    """
    Récupère les insights qualitatifs du Visitor Bot.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        stats = db.get_visitor_insights(days=days)
        return VisitorInsights(**stats)
    except Exception as e:
        logger.error(f"Failed to get visitor insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profiles", response_model=ProfileListResponse)
async def get_profiles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Récupère la liste paginée des profils scrapés.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        offset = (page - 1) * page_size
        profiles = db.get_all_scraped_profiles(limit=page_size, offset=offset)
        total = db.get_scraped_profiles_count()

        return ProfileListResponse(
            total=total,
            page=page,
            page_size=page_size,
            profiles=profiles
        )
    except Exception as e:
        logger.error(f"Failed to get profiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/count", response_model=Dict[str, int])
async def get_profiles_count(authenticated: bool = Depends(verify_api_key)):
    """
    Retourne le nombre total de profils scrapés.
    """
    config = get_config()
    if not config.database.enabled:
        raise HTTPException(status_code=503, detail="Database not enabled")

    try:
        db = get_database(config.database.db_path)
        count = db.get_scraped_profiles_count()
        return {"count": count}
    except Exception as e:
        logger.error(f"Failed to get count: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run", response_model=BotStatusResponse)
async def run_visitor_bot(
    request: VisitorRunRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Lance le Visitor Bot en background via subprocess.
    """
    global VISITOR_PROCESS

    # Check if already running
    if VISITOR_PROCESS is not None:
        if VISITOR_PROCESS.poll() is None: # Still running
            return BotStatusResponse(
                status="running",
                pid=VISITOR_PROCESS.pid,
                message="Visitor Bot is already running."
            )
        else:
             # Finished, cleanup
             VISITOR_PROCESS = None

    try:
        # Build command
        cmd = [sys.executable, "-m", "src.bots.visitor_bot"]

        if request.limit:
            cmd.extend(["--limit", str(request.limit)])

        if request.keywords:
            cmd.append("--keywords")
            cmd.extend(request.keywords)

        logger.info(f"Starting Visitor Bot with command: {' '.join(cmd)}")

        # Launch subprocess
        VISITOR_PROCESS = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # preexec_fn=os.setsid # Create new session group (optional, helpful for full kill)
            # Not using preexec_fn to stay cross-platform safe if needed, though Pi is Linux
        )

        return BotStatusResponse(
            status="running",
            pid=VISITOR_PROCESS.pid,
            message="Visitor Bot started successfully."
        )

    except Exception as e:
        logger.error(f"Failed to start Visitor Bot: {e}", exc_info=True)
        VISITOR_PROCESS = None
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")

@router.post("/stop", response_model=BotStatusResponse)
async def stop_visitor_bot(authenticated: bool = Depends(verify_api_key)):
    """
    Arrête le Visitor Bot s'il est en cours d'exécution.
    """
    global VISITOR_PROCESS

    if VISITOR_PROCESS is None:
        return BotStatusResponse(status="stopped", message="No bot running.")

    if VISITOR_PROCESS.poll() is not None:
        VISITOR_PROCESS = None
        return BotStatusResponse(status="stopped", message="Bot was already stopped.")

    try:
        logger.info(f"Stopping Visitor Bot (PID: {VISITOR_PROCESS.pid})...")
        os.kill(VISITOR_PROCESS.pid, signal.SIGTERM)

        # Wait a bit? No, return immediately as requested "non-blocking" feel
        # But maybe we should wait to confirm?
        # Let's set it to None, assuming it will die.
        VISITOR_PROCESS = None

        return BotStatusResponse(status="stopped", message="Stop signal sent to Visitor Bot.")
    except Exception as e:
        logger.error(f"Failed to stop bot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop bot: {str(e)}")

@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status(authenticated: bool = Depends(verify_api_key)):
    """
    Retourne l'état actuel du processus Visitor Bot.
    """
    global VISITOR_PROCESS

    if VISITOR_PROCESS is None:
        return BotStatusResponse(status="stopped")

    if VISITOR_PROCESS.poll() is None:
        return BotStatusResponse(status="running", pid=VISITOR_PROCESS.pid)
    else:
        # It finished recently
        return_code = VISITOR_PROCESS.returncode
        VISITOR_PROCESS = None
        return BotStatusResponse(status="stopped", message=f"Finished with code {return_code}")

@router.get("/export")
async def export_profiles(authenticated: bool = Depends(verify_api_key)):
    """
    Exporte les profils scrapés en CSV et retourne le fichier.
    """
    config = get_config()
    try:
        db = get_database(config.database.db_path)

        # Define export path
        export_dir = "data/exports"
        os.makedirs(export_dir, exist_ok=True)
        filename = "scraped_profiles_export.csv"
        file_path = os.path.join(export_dir, filename)

        # Execute export
        db.export_scraped_data_to_csv(file_path)

        if not os.path.exists(file_path):
             raise HTTPException(status_code=404, detail="Export file creation failed")

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='text/csv'
        )
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
