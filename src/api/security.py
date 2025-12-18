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
    """
    Retrieves and validates API key from environment.
    Implements strict validation to prevent default/weak keys at runtime.
    """
    key = os.getenv("API_KEY", "").strip()

    # List of dangerous/default values that are NEVER acceptable
    DANGEROUS_KEYS = [
        "internal_secret_key",
        "CHANGEZ_MOI_PAR_CLE_FORTE_GENERER_AVEC_COMMANDE_CI_DESSUS",
        "your_secure_random_key_here",
        "CHANGEZ_MOI",
        "changez_moi",
        "placeholder",
        "default",
        "test",
        "demo",
        "",  # Empty string
    ]

    # CRITICAL: Reject if not set
    if not key:
        error_msg = (
            "🛑 CRITICAL: API_KEY environment variable is REQUIRED and NOT SET.\n"
            "   This prevents unauthorized API access.\n"
            "   Please set a strong API_KEY (min 32 characters):\n"
            "   \n"
            "   python -c \"import secrets; print(secrets.token_hex(32))\"\n"
            "   \n"
            "   Then update your .env file and restart the application."
        )
        logger.critical("api_key_missing", msg=error_msg)
        raise RuntimeError(error_msg)

    # CRITICAL: Reject if matches dangerous patterns
    key_lower = key.lower()
    if key_lower in DANGEROUS_KEYS or key in DANGEROUS_KEYS:
        error_msg = (
            f"🛑 CRITICAL: API_KEY is set to a dangerous/default value: '{key[:10]}...'\n"
            "   This is a SECURITY VIOLATION. The API will not start.\n"
            "   \n"
            "   Generate a strong API_KEY:\n"
            "   python -c \"import secrets; print(secrets.token_hex(32))\"\n"
            "   \n"
            "   Update .env and restart."
        )
        logger.critical("insecure_default_key", msg=error_msg)
        raise RuntimeError(error_msg)

    # CRITICAL: Enforce minimum length (security requirement)
    MIN_KEY_LENGTH = 32
    if len(key) < MIN_KEY_LENGTH:
        error_msg = (
            f"🛑 CRITICAL: API_KEY is too short ({len(key)} chars, min {MIN_KEY_LENGTH} required).\n"
            "   This is a SECURITY VIOLATION. The API will not start.\n"
            "   \n"
            "   Generate a strong API_KEY:\n"
            "   python -c \"import secrets; print(secrets.token_hex(32))\"\n"
            "   \n"
            "   Update .env and restart."
        )
        logger.critical("weak_api_key_length", msg=error_msg)
        raise RuntimeError(error_msg)

    logger.info("api_key_validation_passed", key_length=len(key))
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
