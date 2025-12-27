# ==============================================================================
# Dockerfile pour APP_V2 - LinkedIn Birthday Auto (FastAPI)
# Multi-arch: AMD64 + ARM64 (Raspberry Pi 4 compatible)
# ==============================================================================
FROM python:3.11-slim-bookworm as base

# Arguments de build
ARG APP_VERSION=v2
ARG TARGETPLATFORM

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Optimisation Mémoire Python (CRITIQUE pour RPi 4)
    MALLOC_ARENA_MAX=2 \
    PYTHONHASHSEED=0 \
    # App configuration
    APP_VERSION=${APP_VERSION}

WORKDIR /app

# ==============================================================================
# Installation des dépendances système
# ==============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libffi-dev \
    libssl-dev \
    # Cleanup agressif
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# ==============================================================================
# Installation des dépendances Python
# ==============================================================================
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Cleanup: Supprimer les caches pip résiduels
    rm -rf /root/.cache/pip

# ==============================================================================
# Copie du code source APP_V2
# ==============================================================================
COPY app_v2/ /app/app_v2/

# ==============================================================================
# Configuration utilisateur non-root (UID/GID 1000)
# ==============================================================================
RUN groupadd -g 1000 appgroup 2>/dev/null || true && \
    useradd -u 1000 -g 1000 -m -s /bin/bash appuser 2>/dev/null || true && \
    mkdir -p /app/logs /app/data /app/config && \
    chown -R 1000:1000 /app && \
    echo "Using UID/GID 1000 for user appuser"

USER appuser

# ==============================================================================
# Healthcheck
# ==============================================================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; import sys; r = urllib.request.urlopen('http://localhost:8000/health'); sys.exit(0 if r.code == 200 else 1)" || exit 1

# ==============================================================================
# Exposition du port
# ==============================================================================
EXPOSE 8000

# ==============================================================================
# Point d'entrée
# ==============================================================================
# IMPORTANT: WORKDIR must be /app (not /app/app_v2) because imports use "app_v2.*"
# If WORKDIR is /app/app_v2, Python will look for /app/app_v2/app_v2 which doesn't exist
WORKDIR /app
CMD ["uvicorn", "app_v2.main:app", "--host", "0.0.0.0", "--port", "8000"]
