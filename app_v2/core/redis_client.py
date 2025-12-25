"""
Redis client singleton for atomic operations in rate limiter.

This module provides a singleton Redis client instance for use throughout
the application. It handles connection lifecycle and provides utilities
for atomic operations required for quota enforcement.
"""

import logging
from typing import Optional
import redis.asyncio as redis
from app_v2.core.config import Settings

logger = logging.getLogger(__name__)

# Global Redis instance
_redis_client: Optional[redis.Redis] = None


async def get_redis_client(settings: Optional[Settings] = None) -> redis.Redis:
    """
    Get or create the Redis client singleton.

    Args:
        settings: Settings object (only needed for first initialization)

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        if settings is None:
            settings = Settings()

        # Connect to Redis
        # For production, use a proper Redis URL from settings
        try:
            _redis_client = await redis.from_url(
                "redis://localhost:6379/0",
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await _redis_client.ping()
            logger.info("✅ Redis client connected")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise

    return _redis_client


async def close_redis_client() -> None:
    """Close the Redis client connection."""
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("✅ Redis client closed")
