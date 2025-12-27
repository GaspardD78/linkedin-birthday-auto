"""
FastAPI middleware for logging and metrics.

This module provides:
- Request/response logging with correlation IDs
- Automatic Prometheus metrics tracking
- Performance monitoring
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
from typing import Callable

from app_v2.core.logging import set_request_id, clear_request_id, get_logger
from app_v2.core.metrics import (
    track_request_metrics,
    http_requests_in_progress,
)

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests with correlation IDs.

    Features:
    - Generates unique request ID for each request
    - Logs request details (method, path, client IP)
    - Logs response details (status code, duration)
    - Adds request ID to response headers
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response."""
        # Generate and set request ID
        request_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(request_id)

        # Get client info
        client_host = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Log request start
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "client_ip": client_host,
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=path).inc()

        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

            # Track metrics
            track_request_metrics(
                method=method,
                endpoint=path,
                status_code=response.status_code,
                duration=duration,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Log error
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                },
                exc_info=True,
            )

            # Track error metrics
            track_request_metrics(
                method=method,
                endpoint=path,
                status_code=500,
                duration=duration,
            )

            raise

        finally:
            # Decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=path).dec()

            # Clear request ID from context
            clear_request_id()


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware for metrics only.

    Use this if you don't need logging (faster).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track metrics."""
        method = request.method
        path = request.url.path

        # Track in-progress
        http_requests_in_progress.labels(method=method, endpoint=path).inc()

        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Track metrics
            track_request_metrics(
                method=method,
                endpoint=path,
                status_code=response.status_code,
                duration=duration,
            )

            return response

        except Exception:
            duration = time.time() - start_time
            track_request_metrics(
                method=method,
                endpoint=path,
                status_code=500,
                duration=duration,
            )
            raise

        finally:
            http_requests_in_progress.labels(method=method, endpoint=path).dec()
