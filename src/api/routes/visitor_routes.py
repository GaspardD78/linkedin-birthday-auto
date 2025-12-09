"""
API Router pour les statistiques et insights du Visitor Bot.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from src.core.database import get_database
from src.config.config_manager import get_config
from src.utils.logging import get_logger
from ..security import verify_api_key

router = APIRouter(prefix="/visitor", tags=["Visitor Bot"])
logger = get_logger(__name__)

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
