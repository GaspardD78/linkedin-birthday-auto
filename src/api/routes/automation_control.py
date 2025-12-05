from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import subprocess
import os
import re
from types import MappingProxyType
from src.api.security import verify_api_key
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/automation", tags=["Automation Control"])

# Liste des services systemd gérés (immuable pour sécurité)
MANAGED_SERVICES = MappingProxyType({
    "monitor": "linkedin-bot-monitor.timer",
    "backup": "linkedin-bot-backup.timer",
    "cleanup": "linkedin-bot-cleanup.timer",
    "main": "linkedin-bot.service"
})

# Pattern de validation pour les noms de services (sécurité)
SAFE_SERVICE_PATTERN = re.compile(r'^[a-z0-9\-\.]+\.(?:service|timer)$')

# Models
class ServiceStatus(BaseModel):
    name: str
    display_name: str
    active: bool
    enabled: bool
    status: str
    description: str

class ServicesStatusResponse(BaseModel):
    services: List[ServiceStatus]
    is_systemd_available: bool

class ServiceActionRequest(BaseModel):
    service: str = Field(..., description="Service key (monitor, backup, cleanup, main)")
    action: str = Field(..., description="Action to perform (start, stop, enable, disable)")

# Helper functions
def is_systemd_available() -> bool:
    """Check if systemd is available on the system."""
    try:
        result = subprocess.run(
            ["systemctl", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False

def get_service_status(service_name: str) -> Dict:
    """Get the status of a systemd service/timer."""
    try:
        # Check if service is active
        active_result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_active = active_result.stdout.strip() == "active"

        # Check if service is enabled
        enabled_result = subprocess.run(
            ["systemctl", "is-enabled", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_enabled = enabled_result.stdout.strip() == "enabled"

        # Get detailed status
        status_result = subprocess.run(
            ["systemctl", "status", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        status_text = status_result.stdout.strip()

        return {
            "active": is_active,
            "enabled": is_enabled,
            "status": status_text[:200] if status_text else "N/A"  # Limit status text
        }
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout checking status for {service_name}")
        return {"active": False, "enabled": False, "status": "Timeout"}
    except Exception as e:
        logger.error(f"Error getting status for {service_name}: {e}", exc_info=True)
        return {"active": False, "enabled": False, "status": f"Error: {str(e)}"}

def execute_service_action(service_name: str, action: str) -> bool:
    """Execute a systemd action on a service."""
    # Validation stricte de l'action (whitelist)
    valid_actions = {"start", "stop", "enable", "disable", "restart"}
    if action not in valid_actions:
        raise ValueError(f"Invalid action: {action}")

    # Validation stricte du service name (protection contre injection)
    if not SAFE_SERVICE_PATTERN.match(service_name):
        raise ValueError(f"Invalid service name pattern: {service_name}")

    try:
        # Try without sudo first (works in Docker with privileged mode)
        # If that fails, try with sudo (works on host with sudoers config)
        commands = [
            ["systemctl", action, service_name],
            ["sudo", "systemctl", action, service_name]
        ]

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    logger.info(f"Successfully executed {action} on {service_name} using: {' '.join(cmd)}")
                    return True
                else:
                    logger.debug(f"Command {' '.join(cmd)} failed: {result.stderr}")
            except FileNotFoundError:
                # Command not found, try next one
                continue
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout executing {' '.join(cmd)}")
                continue

        logger.error(f"Failed to {action} {service_name} with all attempted commands")
        return False
    except Exception as e:
        logger.error(f"Error executing {action} on {service_name}: {e}", exc_info=True)
        return False

# API Routes
@router.get("/services/status", response_model=ServicesStatusResponse)
async def get_services_status(authenticated: bool = Depends(verify_api_key)):
    """Get status of all managed automation services."""
    systemd_available = is_systemd_available()

    if not systemd_available:
        logger.info("Systemd is not available - using Docker/RQ worker mode")
        # In Docker mode, return RQ worker status as "services"
        try:
            from src.api.routes.bot_control import redis_conn
            from rq import Worker, Queue

            if not redis_conn:
                return ServicesStatusResponse(
                    services=[],
                    is_systemd_available=False
                )

            # Get RQ workers status
            workers = Worker.all(connection=redis_conn)
            queue = Queue("linkedin-bot", connection=redis_conn)

            services = []

            # Create a virtual "service" for RQ workers
            if workers:
                for idx, worker in enumerate(workers):
                    worker_state = worker.get_state()
                    is_active = worker_state in ["busy", "idle"]
                    current_job = worker.get_current_job()

                    # Format job ID safely
                    job_info = "idle"
                    if current_job:
                        try:
                            job_info = current_job.id[:8] if hasattr(current_job, 'id') else "processing"
                        except Exception:
                            job_info = "processing"

                    services.append(ServiceStatus(
                        name=f"rq_worker_{idx}",
                        display_name=f"Worker RQ {idx + 1}",
                        active=is_active,
                        enabled=True,  # Workers are always "enabled" in Docker
                        status=f"{worker_state} - Jobs: ✓{worker.successful_job_count} ✗{worker.failed_job_count}",
                        description=f"Worker RQ pour tâches asynchrones ({job_info})"
                    ))

            # Add queue status as a service
            queued_jobs = queue.count
            services.append(ServiceStatus(
                name="rq_queue",
                display_name="File d'attente",
                active=True,
                enabled=True,
                status=f"{queued_jobs} job(s) en attente",
                description="File d'attente Redis pour les tâches LinkedIn"
            ))

            return ServicesStatusResponse(
                services=services,
                is_systemd_available=False  # Indicate Docker mode
            )

        except Exception as e:
            logger.error(f"Error getting RQ workers status: {e}", exc_info=True)
            return ServicesStatusResponse(
                services=[],
                is_systemd_available=False
            )

    # Systemd mode (Raspberry Pi)
    services = []

    # Service descriptions
    descriptions = {
        "monitor": "Surveillance système toutes les heures",
        "backup": "Sauvegarde quotidienne à 3h00",
        "cleanup": "Nettoyage hebdomadaire le dimanche à 2h00",
        "main": "Service principal LinkedIn Bot"
    }

    display_names = {
        "monitor": "Monitoring",
        "backup": "Backup",
        "cleanup": "Cleanup",
        "main": "Bot Principal"
    }

    for key, service_name in MANAGED_SERVICES.items():
        status = get_service_status(service_name)
        services.append(ServiceStatus(
            name=key,
            display_name=display_names.get(key, key),
            active=status["active"],
            enabled=status["enabled"],
            status=status["status"],
            description=descriptions.get(key, "")
        ))

    return ServicesStatusResponse(
        services=services,
        is_systemd_available=True
    )

@router.post("/services/action")
async def execute_service_action_endpoint(
    request: ServiceActionRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """Execute an action on a systemd service."""
    if not is_systemd_available():
        raise HTTPException(
            status_code=503,
            detail="Systemd is not available on this system"
        )

    if request.service not in MANAGED_SERVICES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service: {request.service}. Valid services: {list(MANAGED_SERVICES.keys())}"
        )

    service_name = MANAGED_SERVICES[request.service]

    try:
        success = execute_service_action(service_name, request.action)

        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to {request.action} {service_name}"
            )

        return {
            "status": "success",
            "message": f"Successfully executed {request.action} on {request.service}",
            "service": request.service,
            "action": request.action
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in service action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workers/status")
async def get_workers_status(authenticated: bool = Depends(verify_api_key)):
    """Get status of RQ workers."""
    try:
        # Import Redis connection from bot_control
        from src.api.routes.bot_control import redis_conn

        if not redis_conn:
            raise HTTPException(status_code=503, detail="Redis not available")

        # Get worker information from RQ
        from rq import Worker
        workers = Worker.all(connection=redis_conn)

        worker_info = []
        for worker in workers:
            worker_info.append({
                "name": worker.name,
                "state": worker.get_state(),
                "current_job": worker.get_current_job_id(),
                "successful_jobs": worker.successful_job_count,
                "failed_jobs": worker.failed_job_count,
                "total_working_time": worker.total_working_time
            })

        return {
            "workers": worker_info,
            "total_workers": len(workers)
        }
    except Exception as e:
        logger.error(f"Error getting workers status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
