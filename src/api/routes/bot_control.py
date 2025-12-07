from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import StartedJobRegistry
import os
from src.api.security import verify_api_key
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/bot", tags=["Bot Control"])

# Configuration Redis
REDIS_HOST = os.getenv("REDIS_HOST", "redis-bot")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)
    job_queue = Queue("linkedin-bot", connection=redis_conn)
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
    redis_conn = None
    job_queue = None

# Models
class BirthdayConfig(BaseModel):
    dry_run: bool = Field(default=True)
    process_late: bool = Field(default=False)
    max_days_late: Optional[int] = Field(default=10)

class VisitorConfig(BaseModel):
    dry_run: bool = Field(default=True)
    limit: Optional[int] = Field(default=None)

class StopRequest(BaseModel):
    job_type: Optional[str] = Field(None, description="Specific job type to stop (birthday, visit)")
    job_id: Optional[str] = Field(None, description="Specific job ID to stop")

class JobStatus(BaseModel):
    id: str
    status: str
    type: str
    enqueued_at: str
    started_at: Optional[str] = None

class BotStatusResponse(BaseModel):
    active_jobs: List[JobStatus]
    queued_jobs: List[JobStatus]
    worker_status: str

@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status(authenticated: bool = Depends(verify_api_key)):
    """Get granular status of all bots."""
    if not redis_conn:
        raise HTTPException(status_code=503, detail="Redis not available")

    registry = StartedJobRegistry("linkedin-bot", connection=redis_conn)
    started_ids = registry.get_job_ids()
    queued_ids = job_queue.job_ids

    active_jobs = []
    queued_jobs = []

    def get_job_details(job_id, status_list, status_label):
        try:
            job = Job.fetch(job_id, connection=redis_conn)
            job_type = job.meta.get('job_type', 'unknown')

            # Helper to safely format dates
            def fmt_date(d):
                return d.isoformat() if d else None

            status_list.append(JobStatus(
                id=job.id,
                status=status_label,
                type=job_type,
                enqueued_at=fmt_date(job.enqueued_at) or "",
                started_at=fmt_date(job.started_at)
            ))
        except Exception as e:
            logger.warning(f"Could not fetch details for job {job_id}: {e}", exc_info=True)

    for jid in started_ids:
        get_job_details(jid, active_jobs, "running")

    for jid in queued_ids:
        get_job_details(jid, queued_jobs, "queued")

    # Determine worker status roughly
    worker_status = "idle"
    if active_jobs:
        worker_status = "working"

    return BotStatusResponse(
        active_jobs=active_jobs,
        queued_jobs=queued_jobs,
        worker_status=worker_status
    )

@router.post("/start/birthday")
async def start_birthday_bot(config: BirthdayConfig, authenticated: bool = Depends(verify_api_key)):
    """Start the Birthday Bot."""
    if not job_queue:
        raise HTTPException(status_code=503, detail="Redis Queue not available")

    max_days = config.max_days_late if config.process_late else 0
    bot_mode = "unlimited" if config.process_late else "standard"

    # FIX: Augmenter le timeout pour le mode unlimited (peut prendre 2-3h avec beaucoup de contacts)
    timeout = "180m" if bot_mode == "unlimited" else "30m"

    try:
        job = job_queue.enqueue(
            "src.queue.tasks.run_bot_task",
            bot_mode=bot_mode,
            dry_run=config.dry_run,
            max_days_late=max_days,
            job_timeout=timeout,
            meta={'job_type': 'birthday'} # Metadata for granular control
        )
        logger.info(f"✅ [BIRTHDAY] Job {job.id} queued (mode: {bot_mode}, timeout: {timeout}, meta: birthday)")
        return {"job_id": job.id, "status": "queued", "type": "birthday"}
    except Exception as e:
        logger.error(f"Failed to enqueue birthday bot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start/visitor")
async def start_visitor_bot(config: VisitorConfig, authenticated: bool = Depends(verify_api_key)):
    """Start the Visitor Bot."""
    if not job_queue:
        raise HTTPException(status_code=503, detail="Redis Queue not available")

    try:
        job = job_queue.enqueue(
            "src.queue.tasks.run_profile_visit_task",
            dry_run=config.dry_run,
            limit=config.limit,
            job_timeout="45m",
            meta={'job_type': 'visit'} # Metadata for granular control
        )
        logger.info(f"✅ [VISITOR] Job {job.id} queued (meta: visit)")
        return {"job_id": job.id, "status": "queued", "type": "visit"}
    except Exception as e:
        logger.error(f"Failed to enqueue visitor bot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_bot(request: StopRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Stop bots.
    If 'job_type' is provided, stops only that type.
    If 'job_id' is provided, stops that specific job.
    If neither, stops everything (Emergency Stop).
    """
    if not redis_conn:
        raise HTTPException(status_code=503, detail="Redis not available")

    stopped_count = 0
    registry = StartedJobRegistry("linkedin-bot", connection=redis_conn)

    # helper to cancel a job
    def cancel_job(job_id):
        try:
            job = Job.fetch(job_id, connection=redis_conn)
            job.cancel()
            return True
        except Exception:
            return False

    # 1. Stop Specific Job ID
    if request.job_id:
        if cancel_job(request.job_id):
            return {"status": "success", "message": f"Job {request.job_id} stopped"}
        raise HTTPException(status_code=404, detail="Job not found or already stopped")

    # 2. Stop by Type or All
    started_ids = registry.get_job_ids()
    queued_ids = job_queue.job_ids

    for job_id in started_ids + queued_ids:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
            job_meta_type = job.meta.get('job_type')

            should_stop = False
            if request.job_type:
                # Granular stop
                if job_meta_type == request.job_type:
                    should_stop = True
            else:
                # Emergency stop (all)
                should_stop = True

            if should_stop:
                job.cancel()
                if job_id in queued_ids:
                    job.delete() # Remove from queue if not started
                stopped_count += 1

        except Exception as e:
            logger.warning(f"Error checking job {job_id}: {e}", exc_info=True)

    action_name = f"stopped ({request.job_type})" if request.job_type else "EMERGENCY STOP"
    return {
        "status": "success",
        "message": f"{action_name} executed",
        "stopped_count": stopped_count
    }
