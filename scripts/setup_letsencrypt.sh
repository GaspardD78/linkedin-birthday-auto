#!/bin/bash
# ==============================================================================
# LinkedIn Auto RPi4 - Let's Encrypt Setup Script
# ==============================================================================
# Ce script automatise l'obtention de certificats SSL Let's Encrypt
# pour remplacer les certificats auto-signés générés par setup.sh
#
# Prérequis:
# - Docker Compose en cours d'exécution (setup.sh déjà lancé)
# - Domaine DNS pointant vers l'IP publique de votre Raspberry Pi
# - Port 80 accessible depuis Internet (vérifier configuration box/firewall)
#
# Usage:
#   ./scripts/setup_letsencrypt.sh
#   ./scripts/setup_letsencrypt.sh --staging  # Test avec serveur staging
# ==============================================================================

set -euo pipefail

# --- Couleurs ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# --- Configuration ---
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
ENV_FILE=".env"

# --- Logging ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${BLUE}  $1${NC}"; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"; }

# --- Vérification environnement ---
if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Fichier $ENV_FILE introuvable."
    log_info "Lancez d'abord ./setup.sh pour initialiser l'environnement."
    exit 1
fi

# Vérification des permissions de lecture sur .env
if [[ ! -r "$ENV_FILE" ]]; then
    log_error "Permissions insuffisantes pour lire $ENV_FILE"
    log_info "Le fichier .env appartient probablement à root."
    log_info "Solutions possibles:"
    log_info "  1. Relancez ce script avec sudo: sudo ./scripts/setup_letsencrypt.sh"
    log_info "  2. Ou corrigez les permissions: sudo chown \$USER:$USER $ENV_FILE && chmod 600 $ENV_FILE"
    log_info "  3. Ou utilisez le script de maintenance: sudo ./scripts/fix_permissions.sh"
    exit 1
fi

# Lecture du domaine depuis .env
if ! grep -q "^DOMAIN=" "$ENV_FILE" 2>/dev/null; then
    log_error "Variable DOMAIN non trouvée dans $ENV_FILE"
    exit 1
fi

DOMAIN=$(grep "^DOMAIN=" "$ENV_FILE" | cut -d'=' -f2)
log_info "Domaine configuré: $DOMAIN"

# Vérification mode staging
STAGING_ARG=""
if [[ "${1:-}" == "--staging" ]]; then
    STAGING_ARG="--staging"
    log_warn "Mode STAGING activé (certificats de test)"
    log_info "Retirez --staging pour obtenir de vrais certificats"
fi

# ==============================================================================
# VÉRIFICATIONS PRÉALABLES
# ==============================================================================
log_step "Vérifications Préalables"

# 1. Docker Compose en cours
if ! docker compose -f "$COMPOSE_FILE" ps nginx | grep -q "Up"; then
    log_error "Le conteneur Nginx n'est pas en cours d'exécution."
    log_info "Lancez: docker compose -f $COMPOSE_FILE up -d"
    exit 1
fi
log_success "Conteneur Nginx actif"

# 2. Vérification DNS
log_info "Vérification de la résolution DNS pour $DOMAIN..."
if ! host "$DOMAIN" >/dev/null 2>&1; then
    log_error "Le domaine $DOMAIN ne résout pas vers une IP."
    log_info "Vérifiez votre configuration DNS avant de continuer."
    exit 1
fi

RESOLVED_IP=$(host "$DOMAIN" | grep "has address" | awk '{print $4}' | head -1)
log_success "DNS OK: $DOMAIN → $RESOLVED_IP"

# 3. Vérification accessibilité HTTP
log_info "Vérification de l'accessibilité HTTP (port 80)..."
HTTP_TEST=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN/.well-known/acme-challenge/test" 2>/dev/null || echo "000")

if [[ "$HTTP_TEST" == "000" ]]; then
    log_warn "Impossible de joindre http://$DOMAIN"
    log_warn "Vérifiez:"
    log_warn "  - Port 80 ouvert sur votre box/firewall"
    log_warn "  - Redirection de port configurée vers le Raspberry Pi"
    echo -e "${YELLOW}Continuer quand même ? [y/N]${NC}"
    read -r REPLY
    if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    log_success "Port 80 accessible (HTTP $HTTP_TEST)"
fi

# ==============================================================================
# OBTENTION DU CERTIFICAT
# ==============================================================================
log_step "Obtention du Certificat Let's Encrypt"

# Email pour Let's Encrypt (notifications d'expiration)
echo -e "${BOLD}Entrez votre email pour les notifications Let's Encrypt:${NC}"
read -r EMAIL

if [[ -z "$EMAIL" ]]; then
    log_error "Email requis pour Let's Encrypt"
    exit 1
fi

log_info "Lancement de Certbot..."
log_info "  Domaine: $DOMAIN"
log_info "  Email: $EMAIL"
log_info "  Mode: ${STAGING_ARG:-PRODUCTION}"

# Exécution de Certbot via Docker
# - Mode webroot: utilise le dossier partagé ./certbot/www
# - Pas besoin d'arrêter Nginx
docker run --rm \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    $STAGING_ARG \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

if [[ $? -eq 0 ]]; then
    log_success "Certificat obtenu avec succès!"

    # ==============================================================================
    # RECHARGEMENT NGINX
    # ==============================================================================
    log_info "Rechargement de la configuration Nginx..."
    docker compose -f "$COMPOSE_FILE" exec nginx nginx -s reload

    if [[ $? -eq 0 ]]; then
        log_success "Nginx rechargé avec les nouveaux certificats"
    else
        log_warn "Erreur lors du rechargement Nginx"
        log_info "Redémarrez le conteneur: docker compose -f $COMPOSE_FILE restart nginx"
    fi

    # ==============================================================================
    # RENOUVELLEMENT AUTOMATIQUE
    # ==============================================================================
    log_step "Configuration du Renouvellement Automatique"

    log_info "Les certificats Let's Encrypt expirent après 90 jours."
    log_info "Pour renouveler automatiquement, ajoutez cette tâche cron:"
    echo ""
    echo -e "${GREEN}0 3 * * * cd $(pwd) && docker run --rm -v \$(pwd)/certbot/conf:/etc/letsencrypt -v \$(pwd)/certbot/www:/var/www/certbot certbot/certbot renew --webroot --webroot-path=/var/www/certbot && docker compose -f $COMPOSE_FILE exec nginx nginx -s reload${NC}"
    echo ""
    log_info "Pour éditer votre crontab: crontab -e"

    # ==============================================================================
    # RÉSUMÉ
    # ==============================================================================
    log_step "Configuration Terminée"

    echo -e "
${BOLD}Certificat SSL Installé :${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Domaine       : $DOMAIN
✅ Certificats   : certbot/conf/live/$DOMAIN/
✅ Expiration    : $(date -d "+90 days" +"%d %B %Y")
✅ HTTPS actif   : https://$DOMAIN

${BOLD}Prochaines Étapes :${NC}
━━━━━━━━━━━━━━━━━
1. Testez l'accès HTTPS : https://$DOMAIN
2. Configurez le renouvellement automatique (voir ci-dessus)
3. Vérifiez le certificat : https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN

${GREEN}🎉 Votre application est maintenant sécurisée avec HTTPS !${NC}
"

else
    log_error "Échec de l'obtention du certificat"
    log_info "Vérifiez les logs ci-dessus pour plus de détails."
    log_info ""
    log_info "Problèmes courants:"
    log_info "  - Port 80 non accessible depuis Internet"
    log_info "  - DNS ne pointe pas vers la bonne IP"
    log_info "  - Firewall bloque les connexions entrantes"
    exit 1
fi
