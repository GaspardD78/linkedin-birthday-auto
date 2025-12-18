"""
Security utilities for the API with rate limiting.
"""

import os
import secrets
from collections import defaultdict
from datetime import datetime, timedelta

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
failed_attempts = defaultdict(list)  # {ip: [timestamp1, timestamp2, ...]}


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
    Verifies the API Key with rate limiting protection.

    Args:
        api_key: Key from header
        request: FastAPI request object (for IP tracking)

    Returns:
        The api_key if valid

    Raises:
        HTTPException: If invalid, missing, or rate limited
    """
    expected_key = get_api_key_from_env()

    # Extraire l'IP du client
    client_ip = request.client.host if request else "unknown"

    if not api_key:
        raise HTTPException(status_code=403, detail="Missing API Key")

    # ✅ Vérifier rate limit AVANT la validation (économie CPU contre brute force)
    now = datetime.now()

    # Nettoyer les anciennes tentatives (> 15 min)
    if client_ip in failed_attempts:
        failed_attempts[client_ip] = [
            ts for ts in failed_attempts[client_ip]
            if now - ts < RATE_LIMIT_WINDOW
        ]

    # Vérifier si trop de tentatives échouées
    if len(failed_attempts[client_ip]) >= MAX_ATTEMPTS:
        logger.warning(
            "rate_limit_exceeded",
            ip=client_ip,
            attempts=len(failed_attempts[client_ip])
        )
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {RATE_LIMIT_WINDOW.seconds // 60} minutes."
        )

    # Validation de la clé avec timing-attack protection
    if not secrets.compare_digest(api_key, expected_key):
        # Enregistrer tentative échouée
        failed_attempts[client_ip].append(now)
        logger.warning(
            "invalid_api_key_attempt",
            attempted_key=api_key[:4] + "***",
            ip=client_ip,
            total_attempts=len(failed_attempts[client_ip])
        )
        raise HTTPException(status_code=403, detail="Invalid API Key")

    # ✅ Succès : réinitialiser le compteur pour cette IP
    if client_ip in failed_attempts:
        failed_attempts[client_ip] = []

    return api_key
