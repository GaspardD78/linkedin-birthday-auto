from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Tuple, Generator, Any
from contextlib import contextmanager
from redis import Redis, ConnectionPool
from rq import Queue
from rq.job import Job
from rq.registry import StartedJobRegistry
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.api.security import verify_api_key
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/bot", tags=["Bot Control"])

# Configuration Redis avec Connection Pooling
REDIS_HOST = os.getenv("REDIS_HOST", "redis-bot")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# ✅ Pool de connexions Redis (max 10 connexions simultanées)
redis_pool = ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    max_connections=10,
    socket_connect_timeout=5,
    socket_timeout=5,
    decode_responses=False
)


@contextmanager
def get_redis_queue() -> Generator[Tuple[Redis, Queue], None, None]:
    """
    Context manager pour obtenir une connexion Redis + Queue.
    Garantit la fermeture de la connexion après utilisation.

    Yields:
        Tuple (Redis, Queue)

    Raises:
        HTTPException: Si Redis non disponible
    """
    redis_conn = None
    try:
        # Connexion depuis le pool
        redis_conn = Redis(connection_pool=redis_pool)

        # Tester la connexion
        redis_conn.ping()

        # Créer la queue
        job_queue = Queue("linkedin-bot", connection=redis_conn)

        yield redis_conn, job_queue

    except (Exception) as e:
        logger.error(f"Redis connection failed: {e}")
        raise HTTPException(status_code=503, detail="Redis service unavailable")

    finally:
        # ✅ Fermer la connexion explicitement (retourne au pool)
        if redis_conn:
            try:
                redis_conn.close()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")

# Models
class BirthdayConfig(BaseModel):
    dry_run: bool = Field(default=True)
    process_late: bool = Field(default=False)
    max_days_late: Optional[int] = Field(default=10)

class VisitorConfig(BaseModel):
    dry_run: bool = Field(default=True)
    limit: Optional[int] = Field(default=None, ge=1, le=1000, description="Max profiles to visit (1-1000)")

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

class BotActionRequest(BaseModel):
    action: str = Field(..., description="Action to perform: start, stop")
    job_type: str = Field(..., description="Job type: birthday, visitor")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Configuration parameters")

# Helper function with retry logic for Redis operations
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True
)
def get_redis_job_ids(connection):
    """Get job IDs from Redis with retry logic."""
    registry = StartedJobRegistry("linkedin-bot", connection=connection)
    started_ids = registry.get_job_ids()
    queue = Queue("linkedin-bot", connection=connection)
    queued_ids = queue.job_ids
    return started_ids, queued_ids

@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status(authenticated: bool = Depends(verify_api_key)):
    """Get granular status of all bots."""

    with get_redis_queue() as (redis_conn, job_queue):
        try:
            started_ids, queued_ids = get_redis_job_ids(redis_conn)
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Redis connection failed after retries: {e}")
            raise HTTPException(status_code=503, detail="Redis service temporarily unavailable")

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

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_single_job_status(job_id: str, authenticated: bool = Depends(verify_api_key)):
    """Get status of a single job by ID (Replacement for legacy /jobs/{id})."""

    with get_redis_queue() as (redis_conn, job_queue):
        try:
            job = Job.fetch(job_id, connection=redis_conn)
            job_type = job.meta.get('job_type', 'unknown')

            # Determine status
            status = job.get_status()
            if status == 'started':
                status = 'running'
            elif status == 'queued':
                status = 'queued'
            elif status == 'finished':
                status = 'completed'
            elif status == 'failed':
                status = 'failed'

            return JobStatus(
                id=job.id,
                status=status,
                type=job_type,
                enqueued_at=job.enqueued_at.isoformat() if job.enqueued_at else "",
                started_at=job.started_at.isoformat() if job.started_at else None
            )
        except Exception as e:
            logger.warning(f"Job {job_id} not found: {e}")
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

@router.post("/start/birthday")
async def start_birthday_bot(config: BirthdayConfig, authenticated: bool = Depends(verify_api_key)):
    """Start the Birthday Bot."""

    with get_redis_queue() as (redis_conn, job_queue):
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

    with get_redis_queue() as (redis_conn, job_queue):
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

@router.post("/action")
async def bot_action_endpoint(request: BotActionRequest, authenticated: bool = Depends(verify_api_key)):
    """Unified endpoint for bot actions (start/stop). Async & Idempotent."""

    if request.action == "start":
        with get_redis_queue() as (redis_conn, job_queue):
            # Check for existing running jobs of same type to ensure idempotence/single instance?
            # For now, we allow queueing multiple.

            if request.job_type == "birthday":
                cfg = request.config or {}
                bot_mode = "unlimited" if cfg.get("process_late") else "standard"
                timeout = "180m" if bot_mode == "unlimited" else "30m"

                job = job_queue.enqueue(
                    "src.queue.tasks.run_bot_task",
                    bot_mode=bot_mode,
                    dry_run=cfg.get("dry_run", True),
                    max_days_late=cfg.get("max_days_late", 10),
                    job_timeout=timeout,
                    meta={'job_type': 'birthday'}
                )
                logger.info(f"✅ [BIRTHDAY] Started via /action. Job ID: {job.id}")
                return {"status": "queued", "job_id": job.id, "type": "birthday", "message": "Birthday bot queued"}

            elif request.job_type == "visitor":
                cfg = request.config or {}
                job = job_queue.enqueue(
                    "src.queue.tasks.run_profile_visit_task",
                    dry_run=cfg.get("dry_run", True),
                    limit=cfg.get("limit", 10),
                    job_timeout="45m",
                    meta={'job_type': 'visit'}
                )
                logger.info(f"✅ [VISITOR] Started via /action. Job ID: {job.id}")
                return {"status": "queued", "job_id": job.id, "type": "visit", "message": "Visitor bot queued"}

            else:
                raise HTTPException(400, f"Unknown job_type: {request.job_type}")

    elif request.action == "stop":
        # Delegate to stop logic
        # Construct StopRequest compatible object or call logic directly?
        # We can call the stop_bot function if we extract logic, but for now reuse code.
        # Actually, let's call the stop_bot handler logic? No, that requires request object.
        # I'll instantiate StopRequest and call stop_bot.
        stop_req = StopRequest(job_type=request.job_type)
        return await stop_bot(stop_req, authenticated)

    raise HTTPException(400, f"Unknown action: {request.action}")

@router.post("/stop")
async def stop_bot(request: StopRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Stop bots.
    If 'job_type' is provided, stops only that type.
    If 'job_id' is provided, stops that specific job.
    If neither, stops everything (Emergency Stop).
    """

    with get_redis_queue() as (redis_conn, job_queue):
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
