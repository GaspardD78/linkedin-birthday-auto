from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import subprocess
import os
import re
from types import MappingProxyType
from src.api.security import verify_api_key
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/automation", tags=["Automation Control"])

# Map internal service names to Container names or Systemd services
# Priority: 1. Docker Container, 2. Systemd Service
MANAGED_SERVICES = MappingProxyType({
    "monitor": {
        "type": "systemd",
        "target": "linkedin-bot-monitor.timer",
        "desc": "Surveillance système"
    },
    "backup": {
        "type": "systemd",
        "target": "linkedin-bot-backup.timer",
        "desc": "Sauvegarde BDD"
    },
    "cleanup": {
        "type": "systemd",
        "target": "linkedin-bot-cleanup.timer",
        "desc": "Nettoyage"
    },
    "main": {
        "type": "docker",
        "target": "bot-worker",  # Container name
        "desc": "Worker Bot Principal"
    },
    "dashboard": {
        "type": "docker",
        "target": "dashboard",   # Container name
        "desc": "Interface Web"
    }
})

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
    mode: str  # 'docker' or 'systemd'

class ServiceActionRequest(BaseModel):
    service: str = Field(..., description="Service key (monitor, backup, cleanup, main, dashboard)")
    action: str = Field(..., description="Action to perform (start, stop, restart)")

# --- Docker Management Logic ---

def get_docker_client():
    """Lazy load docker client to avoid import errors if not installed."""
    try:
        import docker
        return docker.from_env()
    except ImportError:
        logger.error("Docker python library not found.")
        return None
    except Exception as e:
        logger.error(f"Failed to connect to Docker socket: {e}")
        return None

def manage_docker_container(container_name: str, action: str) -> bool:
    """Manage a Docker container (start, stop, restart)."""
    client = get_docker_client()
    if not client:
        return False

    try:
        container = client.containers.get(container_name)
        if action == "start":
            container.start()
        elif action == "stop":
            container.stop()
        elif action == "restart":
            container.restart()
        else:
            return False
        return True
    except Exception as e:
        logger.error(f"Docker action {action} failed for {container_name}: {e}")
        return False

def get_container_status(container_name: str) -> Dict:
    """Get status of a Docker container."""
    client = get_docker_client()
    if not client:
        return {"active": False, "enabled": False, "status": "Docker API Error"}

    try:
        container = client.containers.get(container_name)
        state = container.status  # running, exited, etc.
        return {
            "active": state == "running",
            "enabled": True, # Containers in compose are 'enabled'
            "status": f"{state} ({container.short_id})"
        }
    except Exception:
        return {"active": False, "enabled": False, "status": "Not Found"}

# --- Systemd Management Logic (Fallback/Hybrid) ---

def is_systemd_available() -> bool:
    try:
        # Check if we are in a container without systemd access
        if not os.path.exists("/run/systemd/system"):
            return False
        subprocess.run(["systemctl", "--version"], capture_output=True, timeout=2)
        return True
    except Exception:
        return False

def execute_systemd_action(service_name: str, action: str) -> bool:
    # Whitelist validation
    if not re.match(r'^[a-z0-9\-\.]+$', service_name): return False
    valid_actions = {"start", "stop", "restart", "enable", "disable"}
    if action not in valid_actions: return False

    cmd = ["sudo", "systemctl", action, service_name]
    try:
        subprocess.run(cmd, check=True, timeout=10)
        return True
    except Exception as e:
        logger.error(f"Systemd action failed: {e}")
        return False

def get_systemd_status(service_name: str) -> Dict:
    try:
        active = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, text=True).stdout.strip() == "active"
        enabled = subprocess.run(["systemctl", "is-enabled", service_name], capture_output=True, text=True).stdout.strip() == "enabled"
        return {"active": active, "enabled": enabled, "status": "active" if active else "inactive"}
    except Exception:
        return {"active": False, "enabled": False, "status": "Error"}

# --- Routes ---

@router.get("/services/status", response_model=ServicesStatusResponse)
async def get_services_status(authenticated: bool = Depends(verify_api_key)):
    """Get status of managed services (Docker containers or Systemd units)."""

    services = []
    has_systemd = is_systemd_available()

    # Try to import Redis connection to check workers
    try:
        from src.api.routes.bot_control import get_redis_queue
        # We don't need the queue here, just checking import
    except ImportError:
        pass

    for key, config in MANAGED_SERVICES.items():
        # Handle Systemd services in Docker environment
        if config["type"] == "systemd" and not has_systemd:
            # Instead of hiding them, we show them as "Host Managed" or "Unavailable"
            # This preserves UI structure
            services.append(ServiceStatus(
                name=key,
                display_name=key.capitalize(),
                active=True, # Assume active if we can't check
                enabled=True,
                status="Géré par l'hôte (Logs only)",
                description=f"{config['desc']} (Mode Docker)"
            ))
            continue

        status = {}
        if config["type"] == "docker":
            status = get_container_status(config["target"])
        elif config["type"] == "systemd":
            status = get_systemd_status(config["target"])

        services.append(ServiceStatus(
            name=key,
            display_name=key.capitalize(),
            active=status["active"],
            enabled=status["enabled"],
            status=status["status"],
            description=config["desc"]
        ))

    # --- RESTORED: RQ Worker Status injection ---
    # In pure Docker mode, users expect to see "RQ Worker" status
    if not has_systemd:
        try:
             # Lazy import to avoid circular dep
             from src.api.routes.bot_control import redis_pool
             from rq import Worker
             from redis import Redis

             r = Redis(connection_pool=redis_pool)
             workers = Worker.all(connection=r)

             for idx, worker in enumerate(workers):
                 state = worker.get_state()
                 services.append(ServiceStatus(
                    name=f"rq_worker_{idx}",
                    display_name=f"Worker RQ {worker.name[-6:]}",
                    active=state in ["busy", "idle"],
                    enabled=True,
                    status=f"{state.upper()} (Jobs: {worker.successful_job_count})",
                    description="Processus de fond"
                 ))
        except Exception as e:
            logger.warning(f"Could not inject RQ worker status: {e}")

    return ServicesStatusResponse(
        services=services,
        mode="hybrid" if has_systemd else "docker"
    )

@router.post("/services/action")
async def execute_service_action_endpoint(
    request: ServiceActionRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """Execute action on service."""
    if request.service not in MANAGED_SERVICES:
        raise HTTPException(status_code=400, detail="Invalid service")

    config = MANAGED_SERVICES[request.service]

    # Block systemd actions in Docker mode
    if config["type"] == "systemd" and not is_systemd_available():
         raise HTTPException(status_code=501, detail="Action impossible sur ce service depuis le conteneur API (Géré par l'hôte)")

    success = False

    if config["type"] == "docker":
        success = manage_docker_container(config["target"], request.action)
    elif config["type"] == "systemd":
        success = execute_systemd_action(config["target"], request.action)

    if not success:
        raise HTTPException(status_code=500, detail="Action failed")

    return {"status": "success", "service": request.service, "action": request.action}

# --- RESTORED: Specific Workers Endpoint ---
@router.get("/workers/status")
async def get_workers_status(authenticated: bool = Depends(verify_api_key)):
    """Get granular status of RQ workers."""
    try:
        from src.api.routes.bot_control import redis_pool
        from rq import Worker
        from redis import Redis

        r = Redis(connection_pool=redis_pool)
        workers = Worker.all(connection=r)

        worker_info = []
        for worker in workers:
            current_job = worker.get_current_job()
            job_id = current_job.id if current_job else None

            worker_info.append({
                "name": worker.name,
                "state": worker.get_state(),
                "current_job": job_id,
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
