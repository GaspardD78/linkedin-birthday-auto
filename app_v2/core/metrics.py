"""
Prometheus metrics module for application monitoring.

This module provides:
- HTTP request metrics (count, latency, status codes)
- Business metrics (birthday messages, profile visits)
- System metrics (database, Redis, errors)
- Custom metrics for specific operations
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from typing import Optional
import time
from functools import wraps
from app_v2.core.logging import get_logger

logger = get_logger(__name__)

# Create a custom registry (optional, can use default)
registry = CollectorRegistry()

# ============================================================================
# HTTP Metrics
# ============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed",
    ["method", "endpoint"],
    registry=registry,
)

# ============================================================================
# Business Metrics - Birthday Campaign
# ============================================================================

birthday_messages_sent_total = Counter(
    "birthday_messages_sent_total",
    "Total birthday messages sent",
    ["status"],  # success, failed
    registry=registry,
)

birthday_campaign_duration_seconds = Histogram(
    "birthday_campaign_duration_seconds",
    "Duration of birthday campaign execution",
    buckets=[1, 5, 10, 30, 60, 120, 300],
    registry=registry,
)

birthday_contacts_checked_total = Counter(
    "birthday_contacts_checked_total",
    "Total contacts checked for birthdays",
    registry=registry,
)

# ============================================================================
# Business Metrics - Sourcing Campaign
# ============================================================================

profiles_visited_total = Counter(
    "profiles_visited_total",
    "Total profiles visited",
    ["status"],  # success, failed, skipped
    registry=registry,
)

sourcing_campaign_duration_seconds = Histogram(
    "sourcing_campaign_duration_seconds",
    "Duration of sourcing campaign execution",
    buckets=[10, 30, 60, 300, 600, 1800, 3600],
    registry=registry,
)

profiles_queue_size = Gauge(
    "profiles_queue_size",
    "Number of profiles in queue to visit",
    registry=registry,
)

# ============================================================================
# Database Metrics
# ============================================================================

database_connections_active = Gauge(
    "database_connections_active",
    "Number of active database connections",
    registry=registry,
)

database_query_duration_seconds = Histogram(
    "database_query_duration_seconds",
    "Database query execution time",
    ["operation"],  # select, insert, update, delete
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    registry=registry,
)

database_errors_total = Counter(
    "database_errors_total",
    "Total database errors",
    ["operation"],
    registry=registry,
)

# ============================================================================
# Redis Metrics
# ============================================================================

redis_operations_total = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],  # get/set/incr, success/failed
    registry=registry,
)

redis_operation_duration_seconds = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
    registry=registry,
)

redis_connection_errors_total = Counter(
    "redis_connection_errors_total",
    "Total Redis connection errors",
    registry=registry,
)

# ============================================================================
# Rate Limiter Metrics
# ============================================================================

rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total rate limit hits",
    ["endpoint", "result"],  # allowed, denied
    registry=registry,
)

rate_limit_quota_remaining = Gauge(
    "rate_limit_quota_remaining",
    "Remaining quota for rate limited operations",
    ["operation"],
    registry=registry,
)

# ============================================================================
# Circuit Breaker Metrics
# ============================================================================

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service"],
    registry=registry,
)

circuit_breaker_failures_total = Counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["service"],
    registry=registry,
)

# ============================================================================
# Application Info
# ============================================================================

app_info = Info(
    "app_info",
    "Application information",
    registry=registry,
)

app_info.info({
    "version": "2.0.0",
    "name": "linkedin-automation-api-v2",
    "environment": "production",
})

# ============================================================================
# System Metrics
# ============================================================================

errors_total = Counter(
    "errors_total",
    "Total application errors",
    ["error_type", "endpoint"],
    registry=registry,
)

background_tasks_active = Gauge(
    "background_tasks_active",
    "Number of active background tasks",
    ["task_type"],
    registry=registry,
)

# ============================================================================
# Helper Functions
# ============================================================================


def track_request_metrics(method: str, endpoint: str, status_code: int, duration: float):
    """
    Track HTTP request metrics.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        status_code: HTTP status code
        duration: Request duration in seconds
    """
    http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def track_birthday_message(success: bool):
    """
    Track birthday message sent.

    Args:
        success: True if message sent successfully, False otherwise
    """
    status = "success" if success else "failed"
    birthday_messages_sent_total.labels(status=status).inc()


def track_profile_visit(status: str):
    """
    Track profile visit.

    Args:
        status: Visit status (success, failed, skipped)
    """
    profiles_visited_total.labels(status=status).inc()


def track_database_error(operation: str):
    """
    Track database error.

    Args:
        operation: Database operation type (select, insert, etc.)
    """
    database_errors_total.labels(operation=operation).inc()
    errors_total.labels(error_type="database", endpoint="n/a").inc()


def track_redis_operation(operation: str, success: bool, duration: Optional[float] = None):
    """
    Track Redis operation.

    Args:
        operation: Operation type (get, set, incr, etc.)
        success: True if operation succeeded
        duration: Operation duration in seconds (optional)
    """
    status = "success" if success else "failed"
    redis_operations_total.labels(operation=operation, status=status).inc()

    if duration is not None:
        redis_operation_duration_seconds.labels(operation=operation).observe(duration)

    if not success:
        redis_connection_errors_total.inc()


def track_rate_limit(endpoint: str, allowed: bool):
    """
    Track rate limit check.

    Args:
        endpoint: API endpoint
        allowed: True if request was allowed, False if denied
    """
    result = "allowed" if allowed else "denied"
    rate_limit_hits_total.labels(endpoint=endpoint, result=result).inc()


def set_circuit_breaker_state(service: str, state: str):
    """
    Set circuit breaker state.

    Args:
        service: Service name (e.g., "redis", "database")
        state: State (closed, open, half_open)
    """
    state_map = {"closed": 0, "open": 1, "half_open": 2}
    circuit_breaker_state.labels(service=service).set(state_map.get(state, 0))


def track_error(error_type: str, endpoint: str = "n/a"):
    """
    Track application error.

    Args:
        error_type: Type of error (validation, auth, internal, etc.)
        endpoint: API endpoint where error occurred
    """
    errors_total.labels(error_type=error_type, endpoint=endpoint).inc()


# ============================================================================
# Decorators
# ============================================================================


def track_duration(metric: Histogram, **labels):
    """
    Decorator to track operation duration.

    Args:
        metric: Prometheus Histogram metric
        **labels: Labels to apply to the metric

    Example:
        @track_duration(birthday_campaign_duration_seconds)
        async def run_campaign():
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        return wrapper
    return decorator


def get_metrics() -> bytes:
    """
    Get Prometheus metrics in text format.

    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(registry)


def get_metrics_content_type() -> str:
    """
    Get content type for Prometheus metrics.

    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST
