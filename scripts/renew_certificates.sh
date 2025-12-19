#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - SSL CERTIFICATE RENEWAL SCRIPT
# Automatise le renouvellement des certificats Let's Encrypt via certbot
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   ./scripts/renew_certificates.sh              # Renouvellement automatique
#   ./scripts/renew_certificates.sh --force      # Forcer le renouvellement
#   ./scripts/renew_certificates.sh --dry-run    # Test sans modifications
#
# Cron (recommandé - tous les jours à 3h du matin):
#   0 3 * * * /path/to/linkedin-birthday-auto/scripts/renew_certificates.sh >> /var/log/certbot-renew.log 2>&1
#
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === CONFIGURATION ===

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

CERTBOT_CONF_DIR="$PROJECT_ROOT/certbot/conf"
CERTBOT_WWW_DIR="$PROJECT_ROOT/certbot/www"
NGINX_CONTAINER="nginx-proxy"
COMPOSE_FILE="docker-compose.yml"

# Charger les variables d'environnement si .env existe
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

DOMAIN="${DOMAIN:-gaspardanoukolivier.freeboxos.fr}"
LOG_FILE="${LOG_FILE:-/var/log/certbot-renew.log}"

# === COULEURS POUR LES LOGS ===

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# === FONCTIONS DE LOGGING ===

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} [INFO] $*"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} [SUCCESS] $*"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} [WARN] $*"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} [ERROR] $*" >&2
}

# === ARGUMENTS ===

FORCE_RENEW=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)
            FORCE_RENEW=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force      Force le renouvellement même si pas nécessaire"
            echo "  --dry-run    Test sans modifications réelles"
            echo "  --help       Affiche cette aide"
            exit 0
            ;;
        *)
            log_error "Option inconnue: $1"
            exit 1
            ;;
    esac
done

# === VÉRIFICATIONS PRÉALABLES ===

log_info "🔒 Début du processus de renouvellement SSL"
log_info "Domaine: $DOMAIN"

# Vérifier que Docker est installé
if ! command -v docker &>/dev/null; then
    log_error "Docker n'est pas installé"
    exit 1
fi

# Vérifier que le conteneur nginx existe
if ! docker ps -a --format '{{.Names}}' | grep -q "^${NGINX_CONTAINER}$"; then
    log_error "Le conteneur nginx '$NGINX_CONTAINER' n'existe pas"
    exit 1
fi

# Vérifier que les répertoires certbot existent
mkdir -p "$CERTBOT_CONF_DIR" "$CERTBOT_WWW_DIR"

# === VÉRIFIER L'EXPIRATION DES CERTIFICATS ===

CERT_FILE="$CERTBOT_CONF_DIR/live/$DOMAIN/fullchain.pem"

if [[ -f "$CERT_FILE" ]]; then
    # Calculer le nombre de jours avant expiration
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$EXPIRY_DATE" +%s 2>/dev/null)
    CURRENT_EPOCH=$(date +%s)
    DAYS_LEFT=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

    log_info "Certificat actuel expire dans $DAYS_LEFT jours (le $(date -d "$EXPIRY_DATE" '+%Y-%m-%d' 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$EXPIRY_DATE" '+%Y-%m-%d' 2>/dev/null))"

    # Renouveler si < 30 jours ou si --force
    if [[ $DAYS_LEFT -gt 30 ]] && [[ "$FORCE_RENEW" == "false" ]]; then
        log_success "✓ Certificat valide pour encore $DAYS_LEFT jours - pas besoin de renouveler"
        exit 0
    fi

    if [[ "$FORCE_RENEW" == "true" ]]; then
        log_warn "Renouvellement forcé demandé (--force)"
    else
        log_warn "⚠️  Certificat expire dans $DAYS_LEFT jours - renouvellement nécessaire"
    fi
else
    log_warn "⚠️  Aucun certificat trouvé - première génération"
fi

# === RENOUVELLEMENT AVEC CERTBOT ===

log_info "Lancement de certbot pour le renouvellement..."

CERTBOT_ARGS=(
    "certonly"
    "--webroot"
    "--webroot-path=/var/www/certbot"
    "--email=${CERTBOT_EMAIL:-admin@${DOMAIN}}"
    "--agree-tos"
    "--no-eff-email"
    "-d" "$DOMAIN"
)

if [[ "$FORCE_RENEW" == "true" ]]; then
    CERTBOT_ARGS+=("--force-renewal")
fi

if [[ "$DRY_RUN" == "true" ]]; then
    CERTBOT_ARGS+=("--dry-run")
    log_info "Mode DRY-RUN activé"
fi

# Lancer certbot dans un conteneur éphémère
if docker run --rm \
    -v "$CERTBOT_CONF_DIR:/etc/letsencrypt" \
    -v "$CERTBOT_WWW_DIR:/var/www/certbot" \
    certbot/certbot:latest \
    "${CERTBOT_ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"; then

    log_success "✓ Certbot a terminé avec succès"
else
    log_error "❌ Échec du renouvellement certbot"
    exit 1
fi

# === RELOAD NGINX (PAS RESTART) ===

if [[ "$DRY_RUN" == "false" ]]; then
    log_info "Rechargement de la configuration Nginx..."

    # Vérifier que nginx est running
    if docker ps --format '{{.Names}}' | grep -q "^${NGINX_CONTAINER}$"; then
        # Tester la configuration avant de reload
        if docker exec "$NGINX_CONTAINER" nginx -t >/dev/null 2>&1; then
            # Reload nginx (pas restart pour éviter downtime)
            if docker exec "$NGINX_CONTAINER" nginx -s reload; then
                log_success "✓ Nginx rechargé avec succès"
            else
                log_error "❌ Échec du rechargement Nginx"
                exit 1
            fi
        else
            log_error "❌ Configuration Nginx invalide - reload annulé"
            docker exec "$NGINX_CONTAINER" nginx -t
            exit 1
        fi
    else
        log_warn "⚠️  Le conteneur Nginx n'est pas en cours d'exécution"
        log_info "Redémarrage du conteneur Nginx..."
        docker compose -f "$COMPOSE_FILE" restart nginx
    fi
fi

# === VÉRIFICATION POST-RENOUVELLEMENT ===

if [[ "$DRY_RUN" == "false" ]] && [[ -f "$CERT_FILE" ]]; then
    NEW_EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
    NEW_EXPIRY_EPOCH=$(date -d "$NEW_EXPIRY_DATE" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$NEW_EXPIRY_DATE" +%s 2>/dev/null)
    NEW_DAYS_LEFT=$(( ($NEW_EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

    log_success "✓ Nouveau certificat valide pour $NEW_DAYS_LEFT jours"
    log_info "Expire le: $(date -d "$NEW_EXPIRY_DATE" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$NEW_EXPIRY_DATE" '+%Y-%m-%d %H:%M:%S' 2>/dev/null)"
fi

# === RAPPORT FINAL ===

log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_success "✓ Renouvellement SSL terminé avec succès"
log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit 0
