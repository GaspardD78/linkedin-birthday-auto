from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging
from src.core.database import get_database
from src.api.security import verify_api_key
import redis
from rq import Queue

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])
logger = logging.getLogger(__name__)

# Pydantic Models
class CampaignCreate(BaseModel):
    name: str
    search_url: Optional[str] = None
    filters: Dict[str, Any]  # Keywords, location, etc.

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    search_url: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class CampaignResponse(BaseModel):
    id: int
    name: str
    search_url: Optional[str]
    filters: Optional[Dict[str, Any]]
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

# Helper to get Redis queue
def get_redis_queue():
    redis_host = "redis-bot" # Docker service name
    redis_port = 6379
    try:
        conn = redis.Redis(host=redis_host, port=redis_port)
        return Queue(connection=conn)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None

@router.post("/", response_model=Dict[str, Any], dependencies=[Depends(verify_api_key)])
async def create_campaign(campaign: CampaignCreate):
    """Create a new prospecting campaign."""
    db = get_database()
    try:
        campaign_id = db.create_campaign(
            name=campaign.name,
            search_url=campaign.search_url,
            filters=campaign.filters
        )
        return {"id": campaign_id, "message": "Campaign created successfully"}
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_api_key)])
async def list_campaigns():
    """List all campaigns."""
    db = get_database()
    try:
        campaigns = db.get_campaigns()
        # Parse filters JSON back to dict
        for c in campaigns:
            if c.get("filters") and isinstance(c["filters"], str):
                try:
                    c["filters"] = json.loads(c["filters"])
                except:
                    c["filters"] = {}
        return campaigns
    except Exception as e:
        logger.error(f"Error listing campaigns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{campaign_id}", dependencies=[Depends(verify_api_key)])
async def get_campaign(campaign_id: int):
    """Get campaign details."""
    db = get_database()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Campaign not found")

        campaign = dict(row)
        if campaign.get("filters") and isinstance(campaign["filters"], str):
            try:
                campaign["filters"] = json.loads(campaign["filters"])
            except:
                campaign["filters"] = {}
        return campaign

@router.post("/{campaign_id}/start", dependencies=[Depends(verify_api_key)])
async def start_campaign(campaign_id: int, background_tasks: BackgroundTasks):
    """Start a campaign (enqueue VisitorBot task)."""
    db = get_database()

    # 1. Get Campaign
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Campaign not found")
        campaign = dict(row)

    # 2. Parse Filters
    filters = {}
    if campaign.get("filters"):
        try:
            filters = json.loads(campaign["filters"]) if isinstance(campaign["filters"], str) else campaign["filters"]
        except:
            filters = {}

    # 3. Prepare Config for VisitorBot
    # We construct the arguments that will be passed to the worker task
    task_kwargs = {
        "keywords": filters.get("keywords", []),
        "location": filters.get("location", "France"),
        "limit": filters.get("limit", 10),
        "campaign_id": campaign_id,
        "dry_run": False # Can be parametrized if needed
    }

    # 4. Enqueue Task
    q = get_redis_queue()
    if not q:
        raise HTTPException(status_code=500, detail="Redis connection failed")

    # Use the string path to the task function to avoid import issues
    job = q.enqueue(
        "src.queue.tasks.run_visitor_task",
        kwargs=task_kwargs,
        job_timeout=3600 # 1 hour timeout
    )

    # 5. Update Status
    with db.get_connection() as conn:
        conn.execute("UPDATE campaigns SET status = 'running', updated_at = ? WHERE id = ?",
                     (datetime.now().isoformat(), campaign_id))

    return {"message": "Campaign started", "job_id": job.get_id()}

@router.get("/{campaign_id}/export", dependencies=[Depends(verify_api_key)])
async def export_campaign_data(campaign_id: int):
    """Export campaign scraped data to JSON (or CSV in future)."""
    db = get_database()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scraped_profiles WHERE campaign_id = ?", (campaign_id,))
        rows = [dict(r) for r in cursor.fetchall()]

    return rows

@router.delete("/{campaign_id}", dependencies=[Depends(verify_api_key)])
async def delete_campaign(campaign_id: int):
    """Delete a campaign and its data."""
    db = get_database()
    with db.get_connection() as conn:
        conn.execute("DELETE FROM scraped_profiles WHERE campaign_id = ?", (campaign_id,))
        conn.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
    return {"message": "Campaign deleted"}
