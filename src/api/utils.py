"""
Utilitaires communs pour les routes API
Utilisé par: stream_routes.py, autres modules
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types d'événements streamés"""
    MESSAGE_SENT = "message_sent"
    PROFILE_VISITED = "profile_visited"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    ERROR = "error"
    STATUS_UPDATE = "status_update"


def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """
    Formate un événement pour Server-Sent Events (SSE/streaming)

    Args:
        event_type: Type d'événement (string)
        data: Données de l'événement (dict)

    Returns:
        String formatée SSE: "data: {...}\n\n"
    """
    payload = {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }
    return f"data: {json.dumps(payload)}\n\n"


def format_sse_comment(message: str) -> str:
    """Formate un commentaire SSE (pour keepalive)"""
    return f": {message}\n"


def retry_on_error(max_attempts: int = 3, backoff_factor: float = 2.0):
    """
    Décorateur pour retry avec backoff exponentiel

    Usage:
        @retry_on_error(max_attempts=5, backoff_factor=2)
        async def my_function():
            ...
    """
    from functools import wraps
    import asyncio

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            attempt = 0
            last_error = None

            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    attempt += 1

                    if attempt < max_attempts:
                        wait_time = backoff_factor ** (attempt - 1)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt}/{max_attempts}), "
                            f"retrying in {wait_time}s: {str(e)}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {str(e)}"
                        )

            raise last_error

        return async_wrapper
    return decorator


async def check_redis_connection(redis_client) -> bool:
    """Vérifie la disponibilité de Redis"""
    try:
        redis_client.ping()
        logger.info("✅ Redis connection verified")
        return True
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False


def build_error_response(error_code: str, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """Construit une réponse d'erreur standardisée"""
    return {
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {}
        }
    }


def build_success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """Construit une réponse de succès standardisée"""
    return {
        "success": True,
        "message": message or "Operation successful",
        "data": data
    }
