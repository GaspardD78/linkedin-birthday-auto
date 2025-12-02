"""
Security utilities for the API.
"""

import os
import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Header expected: X-API-Key: <your-key>
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key_from_env() -> str:
    """Retrieves API key from environment."""
    key = os.getenv("API_KEY")
    if not key:
        logger.critical("no_api_key_configured", msg="API_KEY not set in environment!")
        # HARDENING: Raise explicit error if key is missing, no default fallback
        raise RuntimeError("API_KEY environment variable is not set. Please run main.py to generate one.")
    return key


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verifies the API Key.

    Args:
        api_key: Key from header

    Returns:
        The api_key if valid

    Raises:
        HTTPException: If invalid or missing
    """
    expected_key = get_api_key_from_env()

    if not api_key:
        raise HTTPException(status_code=403, detail="Missing API Key")

    if not secrets.compare_digest(api_key, expected_key):
        logger.warning("invalid_api_key_attempt", attempted_key=api_key[:4] + "***")
        raise HTTPException(status_code=403, detail="Invalid API Key")

    return api_key
