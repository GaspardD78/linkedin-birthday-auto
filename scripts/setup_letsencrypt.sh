#!/bin/bash
# ==============================================================================
# LinkedIn Auto RPi4 - Bootstrap SSL (Let's Encrypt)
# ==============================================================================
# Stratégie "Zero Self-Signed":
# 1. Tente d'obtenir un certificat Let's Encrypt via mode "Bootstrap"
# 2. Configure Nginx en HTTPS propre si succès
# 3. Fallback sur auto-signé UNIQUEMENT en cas d'échec critique
# ==============================================================================

set -euo pipefail

# --- Arguments ---
FORCE_RENEW=false

for arg in "$@"; do
    case $arg in
        --force)
            FORCE_RENEW=true
            shift
            ;;
    esac
done

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"
NGINX_TEMPLATE="$PROJECT_ROOT/deployment/nginx/linkedin-bot-https.conf.template"
NGINX_CONF="$PROJECT_ROOT/deployment/nginx/linkedin-bot.conf"
CERT_ROOT="$PROJECT_ROOT/certbot"
WEBROOT="$CERT_ROOT/www"

# --- Couleurs ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Fonctions de Logging ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Pré-requis ---
if [[ ! -f "$ENV_FILE" ]]; then
    log_error ".env introuvable"
    exit 1
fi

DOMAIN=$(grep "^DOMAIN=" "$ENV_FILE" | cut -d'=' -f2)
EMAIL=$(grep "^LETSENCRYPT_EMAIL=" "$ENV_FILE" | cut -d'=' -f2 || echo "")

if [[ -z "$DOMAIN" ]]; then
    log_error "DOMAIN non défini dans .env"
    exit 1
fi

# Intelligence Domaine: Pas de www pour freeboxos.fr
DOMAINS_ARG="-d $DOMAIN"
if [[ "$DOMAIN" != *".freeboxos.fr" ]]; then
    DOMAINS_ARG="$DOMAINS_ARG -d www.$DOMAIN"
    log_info "Domaine standard détecté: inclusion de www.$DOMAIN"
else
    log_info "Sous-domaine Freebox détecté: exclusion de www (non supporté)"
fi

# Permissions (UID 1000)
log_info "Application des permissions (UID 1000)..."
mkdir -p "$CERT_ROOT/conf" "$CERT_ROOT/www" "$CERT_ROOT/logs"
chown -R 1000:1000 "$CERT_ROOT"

# --- Fonctions Clés ---

generate_final_nginx_config() {
    log_info "Génération de la configuration Nginx finale (HTTPS)..."
    export DOMAIN
    if command -v envsubst >/dev/null; then
        envsubst '${DOMAIN}' < "$NGINX_TEMPLATE" > "$NGINX_CONF"
    else
        sed "s/\${DOMAIN}/$DOMAIN/g" "$NGINX_TEMPLATE" > "$NGINX_CONF"
    fi
    log_success "Configuration HTTPS générée"
}

generate_self_signed_fallback() {
    log_warn "⚠️  Génération de certificats de SECOURS (Auto-signés)..."
    local cert_dir="$CERT_ROOT/conf/live/$DOMAIN"
    mkdir -p "$cert_dir"

    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -keyout "$cert_dir/privkey.pem" \
        -out "$cert_dir/fullchain.pem" \
        -subj "/CN=$DOMAIN/O=Fallback Self-Signed/C=FR" 2>/dev/null

    chmod 644 "$cert_dir/fullchain.pem"
    chmod 600 "$cert_dir/privkey.pem"
    chown -R 1000:1000 "$cert_dir"

    log_warn "Certificats auto-signés générés. Connexion HTTPS non sécurisée (alerte navigateur)."
}

reload_nginx() {
    log_info "Rechargement de Nginx..."
    if docker compose -f "$COMPOSE_FILE" exec nginx nginx -s reload; then
        log_success "Nginx rechargé avec succès"
    else
        log_warn "Échec du reload Nginx, tentative de restart..."
        docker compose -f "$COMPOSE_FILE" restart nginx
    fi
}

check_existing_certs() {
    if [[ "$FORCE_RENEW" == "true" ]]; then
        log_warn "Force renew activé : Ignorer certificats existants."
        return 1
    fi

    if [[ -f "$CERT_ROOT/conf/live/$DOMAIN/fullchain.pem" ]]; then
        # Vérifier validité (expiré dans moins de 30 jours ?)
        if openssl x509 -checkend 2592000 -noout -in "$CERT_ROOT/conf/live/$DOMAIN/fullchain.pem" >/dev/null 2>&1; then
            return 0 # Valide
        else
            log_warn "Certificats existants mais expirés ou bientôt expirés."
            return 1 # Invalide/Expiré
        fi
    fi
    return 1 # Pas de certs
}

# --- Main Logic ---

# Nettoyage forcé si demandé
if [[ "$FORCE_RENEW" == "true" ]]; then
    log_warn "⚠️  SUPPRESSION des certificats existants (--force)..."
    rm -rf "$CERT_ROOT/conf/live/$DOMAIN" 2>/dev/null || true
    rm -rf "$CERT_ROOT/conf/archive/$DOMAIN" 2>/dev/null || true
    rm -rf "$CERT_ROOT/conf/renewal/$DOMAIN.conf" 2>/dev/null || true
    rm -rf "$CERT_ROOT/conf/live/$DOMAIN-0001" 2>/dev/null || true
fi

log_info "🔍 Analyse de l'état SSL pour $DOMAIN..."

if check_existing_certs; then
    log_success "Certificats valides détectés. Pas d'action requise."
    generate_final_nginx_config
    reload_nginx
    exit 0
else
    log_info "Pas de certificats valides (ou forcé). Tentative d'obtention (Let's Encrypt)..."
fi

# Demander email si manquant ou défaut
if [[ -z "$EMAIL" ]] || [[ "$EMAIL" == "votre.email@example.com" ]]; then
    echo -e "${YELLOW}Email requis pour Let's Encrypt (notifications expiration):${NC}"
    read -r -p "Email: " EMAIL_INPUT
    if [[ -n "$EMAIL_INPUT" ]]; then
        EMAIL="$EMAIL_INPUT"
        # Sauvegarder dans .env si possible
        if grep -q "^LETSENCRYPT_EMAIL=" "$ENV_FILE"; then
            sed -i "s|^LETSENCRYPT_EMAIL=.*|LETSENCRYPT_EMAIL=$EMAIL|" "$ENV_FILE"
        else
            echo "LETSENCRYPT_EMAIL=$EMAIL" >> "$ENV_FILE"
        fi
    else
        log_error "Email obligatoire. Abandon."
        exit 1
    fi
fi

# Tentative Certbot
log_info "Lancement de Certbot (Webroot Mode)..."

# Nettoyage préventif en cas de corruption précédente
rm -rf "$CERT_ROOT/conf/live/$DOMAIN-0001" 2>/dev/null || true

docker run --rm \
    --user 1000:1000 \
    -v "$CERT_ROOT/conf:/etc/letsencrypt" \
    -v "$CERT_ROOT/www:/var/www/certbot" \
    -v "$CERT_ROOT/logs:/var/log/letsencrypt" \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --non-interactive \
    $DOMAINS_ARG

CERTBOT_EXIT=$?

if [[ $CERTBOT_EXIT -eq 0 ]]; then
    log_success "🎉 Certificat Let's Encrypt obtenu avec succès !"
    generate_final_nginx_config
    reload_nginx
else
    log_error "❌ Échec de Let's Encrypt (Code $CERTBOT_EXIT)"

    # Fallback Logic
    log_info "Activation du mode DÉGRADÉ (Self-Signed)..."
    generate_self_signed_fallback
    generate_final_nginx_config
    reload_nginx

    log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_warn "  ÉCHEC SSL - MODE DÉGRADÉ ACTIVÉ"
    log_warn "  Votre site est accessible mais affichera une alerte."
    log_warn "  Vérifiez: Port 80, DNS, et Logs."
    log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1 # On sort en erreur pour informer setup.sh, mais le service tourne
fi
