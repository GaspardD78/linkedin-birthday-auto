"""FastAPI routes for automation scheduler."""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any

from src.api.security import verify_api_key
from src.scheduler.scheduler import AutomationScheduler
from src.scheduler.models import (
    ScheduledJobConfig,
    JobExecutionLog,
    BotType,
    ScheduleType,
    BirthdayBotConfig,
    VisitorBotConfig
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/scheduler", tags=["Automation Scheduler"])

# Get scheduler instance (singleton)
scheduler = AutomationScheduler()


# ============================================================================
# DTOs (Data Transfer Objects)
# ============================================================================

class CreateJobRequest(BaseModel):
    """Request model for creating a new scheduled job."""
    name: str = Field(..., min_length=1, max_length=200, description="Job name")
    description: Optional[str] = Field(None, max_length=500, description="Job description")
    bot_type: BotType = Field(..., description="Bot type (birthday or visitor)")
    enabled: bool = Field(True, description="Whether job is enabled")
    schedule_type: ScheduleType = Field(..., description="Schedule type")
    schedule_config: Dict[str, Any] = Field(..., description="Schedule configuration")
    bot_config: Dict[str, Any] = Field(..., description="Bot-specific configuration")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Daily Birthday Messages",
            "description": "Send birthday messages every day at 8am",
            "bot_type": "birthday",
            "enabled": True,
            "schedule_type": "daily",
            "schedule_config": {"hour": 8, "minute": 0},
            "bot_config": {
                "dry_run": False,
                "process_late": True,
                "max_days_late": 7,
                "max_messages_per_run": 10
            }
        }
    })


class UpdateJobRequest(BaseModel):
    """Request model for updating an existing job."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    enabled: Optional[bool] = None
    schedule_type: Optional[ScheduleType] = None
    schedule_config: Optional[Dict[str, Any]] = None
    bot_config: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "enabled": False,
            "schedule_config": {"hour": 9, "minute": 30}
        }
    })


class ToggleJobRequest(BaseModel):
    """Request model for toggling job enable/disable."""
    enabled: bool = Field(..., description="True to enable, False to disable")


class JobResponse(BaseModel):
    """Response model for job operations."""
    id: str
    name: str
    description: Optional[str]
    bot_type: str
    enabled: bool
    schedule_type: str
    schedule_config: Dict[str, Any]
    bot_config: Dict[str, Any]
    created_at: str
    updated_at: str
    last_run_at: Optional[str]
    last_run_status: Optional[str]
    last_run_error: Optional[str]
    next_run_at: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Routes
# ============================================================================

@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    enabled_only: bool = False,
    authenticated: bool = Depends(verify_api_key)
):
    """
    List all scheduled jobs.

    Args:
        enabled_only: If True, only return enabled jobs

    Returns:
        List of job configurations
    """
    try:
        jobs = scheduler.list_jobs(enabled_only=enabled_only)

        # Convert to response model
        return [
            JobResponse(
                id=job.id,
                name=job.name,
                description=job.description,
                bot_type=job.bot_type.value,
                enabled=job.enabled,
                schedule_type=job.schedule_type.value,
                schedule_config=job.schedule_config,
                bot_config=job.bot_config.model_dump(),
                created_at=job.created_at.isoformat(),
                updated_at=job.updated_at.isoformat(),
                last_run_at=job.last_run_at.isoformat() if job.last_run_at else None,
                last_run_status=job.last_run_status,
                last_run_error=job.last_run_error,
                next_run_at=job.next_run_at.isoformat() if job.next_run_at else None
            )
            for job in jobs
        ]

    except Exception as e:
        logger.error(f"Failed to list jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get a specific scheduled job by ID.

    Args:
        job_id: Job identifier

    Returns:
        Job configuration
    """
    job = scheduler.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    return JobResponse(
        id=job.id,
        name=job.name,
        description=job.description,
        bot_type=job.bot_type.value,
        enabled=job.enabled,
        schedule_type=job.schedule_type.value,
        schedule_config=job.schedule_config,
        bot_config=job.bot_config.model_dump(),
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        last_run_at=job.last_run_at.isoformat() if job.last_run_at else None,
        last_run_status=job.last_run_status,
        last_run_error=job.last_run_error,
        next_run_at=job.next_run_at.isoformat() if job.next_run_at else None
    )


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: CreateJobRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Create a new scheduled job.

    Args:
        request: Job creation request

    Returns:
        Created job configuration
    """
    try:
        # Validate and convert bot_config to appropriate model
        if request.bot_type == BotType.BIRTHDAY:
            bot_config = BirthdayBotConfig(**request.bot_config)
        elif request.bot_type == BotType.VISITOR:
            bot_config = VisitorBotConfig(**request.bot_config)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid bot_type: {request.bot_type}"
            )

        # Create job configuration
        job_config = ScheduledJobConfig(
            name=request.name,
            description=request.description,
            bot_type=request.bot_type,
            enabled=request.enabled,
            schedule_type=request.schedule_type,
            schedule_config=request.schedule_config,
            bot_config=bot_config
        )

        # Add to scheduler
        created = scheduler.add_job(job_config)

        logger.info(f"Job created: {created.name} ({created.id})")

        return JobResponse(
            id=created.id,
            name=created.name,
            description=created.description,
            bot_type=created.bot_type.value,
            enabled=created.enabled,
            schedule_type=created.schedule_type.value,
            schedule_config=created.schedule_config,
            bot_config=created.bot_config.model_dump(),
            created_at=created.created_at.isoformat(),
            updated_at=created.updated_at.isoformat(),
            last_run_at=created.last_run_at.isoformat() if created.last_run_at else None,
            last_run_status=created.last_run_status,
            last_run_error=created.last_run_error,
            next_run_at=created.next_run_at.isoformat() if created.next_run_at else None
        )

    except ValueError as e:
        logger.warning(f"Validation error creating job: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    request: UpdateJobRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Update an existing scheduled job.

    Args:
        job_id: Job identifier
        request: Update request

    Returns:
        Updated job configuration
    """
    try:
        # Build updates dict (only include provided fields)
        updates = request.model_dump(exclude_unset=True)

        # If bot_config is provided, validate it
        if 'bot_config' in updates:
            # Get existing job to know bot_type
            existing_job = scheduler.get_job(job_id)
            if not existing_job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Job {job_id} not found"
                )

            # Validate bot_config according to bot_type
            if existing_job.bot_type == BotType.BIRTHDAY:
                updates['bot_config'] = BirthdayBotConfig(**updates['bot_config'])
            elif existing_job.bot_type == BotType.VISITOR:
                updates['bot_config'] = VisitorBotConfig(**updates['bot_config'])

        # Update job
        updated = scheduler.update_job(job_id, updates)

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        logger.info(f"Job updated: {updated.name} ({job_id})")

        return JobResponse(
            id=updated.id,
            name=updated.name,
            description=updated.description,
            bot_type=updated.bot_type.value,
            enabled=updated.enabled,
            schedule_type=updated.schedule_type.value,
            schedule_config=updated.schedule_config,
            bot_config=updated.bot_config.model_dump(),
            created_at=updated.created_at.isoformat(),
            updated_at=updated.updated_at.isoformat(),
            last_run_at=updated.last_run_at.isoformat() if updated.last_run_at else None,
            last_run_status=updated.last_run_status,
            last_run_error=updated.last_run_error,
            next_run_at=updated.next_run_at.isoformat() if updated.next_run_at else None
        )

    except ValueError as e:
        logger.warning(f"Validation error updating job: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Delete a scheduled job.

    Args:
        job_id: Job identifier
    """
    success = scheduler.delete_job(job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    logger.info(f"Job deleted: {job_id}")


@router.post("/jobs/{job_id}/toggle", response_model=JobResponse)
async def toggle_job(
    job_id: str,
    request: ToggleJobRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Toggle job enabled/disabled state.

    Args:
        job_id: Job identifier
        request: Toggle request

    Returns:
        Updated job configuration
    """
    updated = scheduler.toggle_job(job_id, request.enabled)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    action = "enabled" if request.enabled else "disabled"
    logger.info(f"Job {action}: {updated.name} ({job_id})")

    return JobResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        bot_type=updated.bot_type.value,
        enabled=updated.enabled,
        schedule_type=updated.schedule_type.value,
        schedule_config=updated.schedule_config,
        bot_config=updated.bot_config.model_dump(),
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
        last_run_at=updated.last_run_at.isoformat() if updated.last_run_at else None,
        last_run_status=updated.last_run_status,
        last_run_error=updated.last_run_error,
        next_run_at=updated.next_run_at.isoformat() if updated.next_run_at else None
    )


@router.post("/jobs/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_job_now(
    job_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Execute a job immediately (outside of schedule).

    Args:
        job_id: Job identifier

    Returns:
        Confirmation message
    """
    success = scheduler.run_job_now(job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    logger.info(f"Job queued for immediate execution: {job_id}")

    return {
        "message": f"Job {job_id} queued for immediate execution",
        "status": "queued"
    }


@router.get("/jobs/{job_id}/history", response_model=List[JobExecutionLog])
async def get_job_history(
    job_id: str,
    limit: int = 50,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get execution history for a job.

    Args:
        job_id: Job identifier
        limit: Maximum number of logs to return (default: 50, max: 200)

    Returns:
        List of execution logs
    """
    # Validate limit
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 200"
        )

    # Verify job exists
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    # Get history
    history = scheduler.get_job_history(job_id, limit=limit)

    return history


@router.get("/health")
async def scheduler_health():
    """
    Check scheduler health.

    Returns:
        Scheduler status information
    """
    return {
        "status": "healthy",
        "scheduler_running": scheduler.scheduler.running,
        "redis_connected": scheduler.redis_conn is not None,
        "total_jobs": len(scheduler.list_jobs()),
        "enabled_jobs": len(scheduler.list_jobs(enabled_only=True))
    }
