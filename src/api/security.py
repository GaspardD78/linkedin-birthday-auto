"""
Security utilities for the API with persistent rate limiting using Redis.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

import redis
from fastapi import HTTPException, Security, Request
from fastapi.security import APIKeyHeader

from ..utils.logging import get_logger

logger = get_logger(__name__)

API_KEY_NAME = "X-API-Key"

# Header expected: X-API-Key: <your-key>
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# ✅ Rate Limiting: Max 10 tentatives par IP toutes les 15 minutes
RATE_LIMIT_WINDOW = timedelta(minutes=15)
MAX_ATTEMPTS = 10

# Redis connection for persistent rate limiting
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get or create Redis client for rate limiting."""
    global _redis_client
    if _redis_client is None:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        _redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
        # Verify connection on initialization
        try:
            _redis_client.ping()
            logger.info("redis_connected", host=redis_host, port=redis_port)
        except redis.ConnectionError as e:
            logger.error("redis_connection_failed", error=str(e))
            raise RuntimeError(f"Failed to connect to Redis at {redis_host}:{redis_port}") from e
    return _redis_client


def get_rate_limit_key(ip: str) -> str:
    """Generate Redis key for rate limiting an IP."""
    return f"rate_limit:failed_attempts:{ip}"


def get_failed_attempts(ip: str) -> int:
    """Get current failed attempt count for an IP from Redis."""
    try:
        client = get_redis_client()
        count = client.get(get_rate_limit_key(ip))
        return int(count) if count else 0
    except redis.RedisError as e:
        logger.warning("redis_error_getting_attempts", ip=ip, error=str(e))
        # Fallback: deny access if Redis fails (fail-secure)
        return MAX_ATTEMPTS


def increment_failed_attempts(ip: str) -> int:
    """Increment failed attempts counter for an IP in Redis."""
    try:
        client = get_redis_client()
        key = get_rate_limit_key(ip)
        # Increment and set expiration if first attempt
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, int(RATE_LIMIT_WINDOW.total_seconds()))
        result = pipe.execute()
        return result[0]  # Return incremented count
    except redis.RedisError as e:
        logger.warning("redis_error_incrementing_attempts", ip=ip, error=str(e))
        # Fallback: don't block (fail-open for availability)
        return MAX_ATTEMPTS - 1


def reset_failed_attempts(ip: str) -> None:
    """Reset failed attempts counter for an IP in Redis."""
    try:
        client = get_redis_client()
        client.delete(get_rate_limit_key(ip))
    except redis.RedisError as e:
        logger.warning("redis_error_resetting_attempts", ip=ip, error=str(e))


def get_api_key_from_env() -> str:
    """Retrieves API key from environment."""
    key = os.getenv("API_KEY")
    if not key:
        logger.critical("no_api_key_configured", msg="API_KEY not set in environment!")
        # HARDENING: Raise explicit error if key is missing
        raise RuntimeError("API_KEY environment variable is not set. Please run main.py to generate one.")

    # HARDENING: Explicitly reject the legacy default key
    if key == "internal_secret_key":
        logger.critical("insecure_default_key", msg="API_KEY is set to insecure default 'internal_secret_key'!")
        raise RuntimeError(
            "Security Violation: API_KEY is set to the insecure default 'internal_secret_key'. "
            "Please remove it from your environment/configuration and run main.py to generate a secure key."
        )

    return key


def verify_api_key(api_key: str = Security(api_key_header), request: Request = None) -> str:
    """
    Verifies the API Key with persistent rate limiting protection via Redis.

    Args:
        api_key: Key from header
        request: FastAPI request object (for IP tracking)

    Returns:
        The api_key if valid

    Raises:
        HTTPException: If invalid, missing, or rate limited
    """
    expected_key = get_api_key_from_env()

    # Extract client IP
    client_ip = request.client.host if request else "unknown"

    if not api_key:
        raise HTTPException(status_code=403, detail="Missing API Key")

    # ✅ Check rate limit BEFORE validation (CPU economy against brute force)
    failed_count = get_failed_attempts(client_ip)

    if failed_count >= MAX_ATTEMPTS:
        logger.warning(
            "rate_limit_exceeded",
            ip=client_ip,
            attempts=failed_count
        )
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {int(RATE_LIMIT_WINDOW.total_seconds() // 60)} minutes."
        )

    # Validate the key with timing-attack protection
    if not secrets.compare_digest(api_key, expected_key):
        # Record failed attempt in Redis (persistent)
        new_count = increment_failed_attempts(client_ip)
        logger.warning(
            "invalid_api_key_attempt",
            attempted_key=api_key[:4] + "***",
            ip=client_ip,
            total_attempts=new_count
        )
        raise HTTPException(status_code=403, detail="Invalid API Key")

    # ✅ Success: reset the counter for this IP
    reset_failed_attempts(client_ip)

    return api_key
