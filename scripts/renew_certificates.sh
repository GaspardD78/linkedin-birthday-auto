#!/bin/bash
# ==============================================================================
# LinkedIn Auto RPi4 - Renewal Script
# ==============================================================================
# Vérifie et renouvelle les certificats si nécessaire.
# À exécuter via CRON.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
CERT_ROOT="$PROJECT_ROOT/certbot"

# Logging simple
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

log "Vérification des certificats SSL..."

# Lancer le renouvellement
docker run --rm \
    --user 1000:1000 \
    -v "$CERT_ROOT/conf:/etc/letsencrypt" \
    -v "$CERT_ROOT/www:/var/www/certbot" \
    -v "$CERT_ROOT/logs:/var/log/letsencrypt" \
    certbot/certbot renew \
    --webroot \
    --webroot-path=/var/www/certbot \
    --non-interactive \
    --quiet

EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
    # Vérifier si un renouvellement a eu lieu (en regardant la date du fichier cert)
    # C'est approximatif, mais suffisant pour reload nginx
    # Une méthode plus robuste serait de parser la sortie de certbot, mais --quiet supprime la sortie

    # On reload Nginx systématiquement par sécurité si la commande réussit
    log "Reloading Nginx..."
    docker compose -f "$COMPOSE_FILE" exec nginx nginx -s reload
else
    log "Erreur lors du renouvellement (Code $EXIT_CODE)"
fi
