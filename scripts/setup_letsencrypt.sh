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

# Fixes Issue #23: Validation DOMAIN
DOMAIN=$(grep "^DOMAIN=" "$ENV_FILE" | cut -d'=' -f2)
# Regex basique pour nom de domaine (alphanum, tirets, points)
if [[ ! "$DOMAIN" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    log_error "Domaine invalide ou manquant: '$DOMAIN'"
    exit 1
fi

# --- Fonctions Diagnostic ---
check_port_accessible() {
    local port=$1
    local timeout=5

    log_info "Vérification port $port (accès Internet)..."

    # Méthode 1: Essayer d'accéder en local
    if timeout $timeout bash -c "echo > /dev/tcp/127.0.0.1/$port" 2>/dev/null; then
        log_success "Port $port accessible localement"
        return 0
    fi

    log_warn "Port $port non accessible localement (peut être bloqué par Docker)"
    return 1
}

check_domain_dns() {
    local domain=$1

    log_info "Vérification résolution DNS pour $domain..."

    # Essayer avec nslookup ou dig
    if command -v nslookup >/dev/null; then
        if nslookup "$domain" 1.1.1.1 >/dev/null 2>&1; then
            local resolved_ip=$(nslookup "$domain" 1.1.1.1 2>/dev/null | grep -A1 "Name:" | tail -1 | awk '{print $NF}')
            if [[ -n "$resolved_ip" ]]; then
                log_success "Domaine résout à: $resolved_ip"
                return 0
            fi
        fi
    elif command -v dig >/dev/null; then
        if dig +short "$domain" @1.1.1.1 | grep -qE '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'; then
            local resolved_ip=$(dig +short "$domain" @1.1.1.1 | head -1)
            log_success "Domaine résout à: $resolved_ip"
            return 0
        fi
    fi

    log_warn "Domaine $domain ne résout pas (DNS non propagé?)"
    return 1
}

verify_certificate_validity() {
    local cert_file=$1

    if [[ ! -f "$cert_file" ]]; then
        return 1
    fi

    # Vérifier que c'est un certificat valide (pas auto-signé)
    local subject=$(openssl x509 -noout -subject -in "$cert_file" 2>/dev/null || echo "")
    local issuer=$(openssl x509 -noout -issuer -in "$cert_file" 2>/dev/null || echo "")

    # Si subject == issuer, c'est auto-signé (mauvais!)
    if [[ "$subject" == "$issuer" ]] && [[ -n "$subject" ]]; then
        log_warn "Certificat auto-signé détecté (sujet = émetteur)"
        return 1
    fi

    # Vérifier expiration
    if openssl x509 -checkend 0 -noout -in "$cert_file" >/dev/null 2>&1; then
        log_success "Certificat valide et non expiré"
        return 0
    else
        log_warn "Certificat expiré"
        return 1
    fi
}

EMAIL=$(grep "^LETSENCRYPT_EMAIL=" "$ENV_FILE" | cut -d'=' -f2 || echo "")

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

# ══════════════════════════════════════════════════════════════════════════════
# STRATÉGIE "ZERO SELF-SIGNED" (v5.2)
# ══════════════════════════════════════════════════════════════════════════════
# La fonction generate_self_signed_fallback a été SUPPRIMÉE.
# Les certificats auto-signés ne sont JAMAIS acceptables pour la production.
# Si Let's Encrypt échoue, le script retourne une erreur et setup.sh s'arrête.
# ══════════════════════════════════════════════════════════════════════════════

reload_nginx() {
    log_info "Rechargement de Nginx..."
    # Standardize on command available
    local DOCKER_CMD="docker compose"
    if ! command -v docker compose >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1; then
        DOCKER_CMD="docker-compose"
    fi

    if $DOCKER_CMD -f "$COMPOSE_FILE" exec -T nginx nginx -s reload; then
        log_success "Nginx rechargé avec succès"
    else
        log_warn "Échec du reload Nginx, tentative de restart..."
        $DOCKER_CMD -f "$COMPOSE_FILE" restart nginx
    fi
}

check_existing_certs() {
    if [[ "$FORCE_RENEW" == "true" ]]; then
        log_warn "Force renew activé : Ignorer certificats existants."
        return 1
    fi

    if [[ -f "$CERT_ROOT/conf/live/$DOMAIN/fullchain.pem" ]]; then
        # Vérifier validité: doit être émis par une CA connue ET expiration > 30 jours
        if verify_certificate_validity "$CERT_ROOT/conf/live/$DOMAIN/fullchain.pem"; then
            if openssl x509 -checkend 2592000 -noout -in "$CERT_ROOT/conf/live/$DOMAIN/fullchain.pem" >/dev/null 2>&1; then
                log_success "Certificats valides et non proches de l'expiration"
                return 0 # Valide
            else
                log_warn "Certificats existants mais expirés ou bientôt expirés."
                return 1 # Invalide/Expiré
            fi
        else
            log_error "Certificats existants mais auto-signés ou invalides!"
            return 1
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

# --- PRE-CERTBOT DIAGNOSTIC (NOUVEAU) ---
log_info ""
log_info "╔════════════════════════════════════════════════════════════╗"
log_info "║  DIAGNOSTIC PRÉ-CERTBOT (Vérifications requis pour succès)  ║"
log_info "╚════════════════════════════════════════════════════════════╝"
log_info ""

DIAGNOSTIC_PASSED=true

# 1. Vérifier port 80
if ! check_port_accessible 80; then
    log_warn "⚠️  Port 80 non accessible - May cause Let's Encrypt to fail"
    DIAGNOSTIC_PASSED=false
fi

# 2. Vérifier DNS
if ! check_domain_dns "$DOMAIN"; then
    log_error "❌ DNS non résolu - Let's Encrypt ÉCHOUERA"
    log_error "   Assurez-vous que: $DOMAIN pointe vers cette machine"
    log_error "   Peut prendre 24-48h après configuration DNS"
    DIAGNOSTIC_PASSED=false
fi

log_info ""
if [[ "$DIAGNOSTIC_PASSED" != "true" ]]; then
    log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_warn "⚠️  DIAGNOSTICS ÉCHOUÉS - Probables causes d'échec Let's Encrypt"
    log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_warn ""
    log_warn "Continuant quand même... (peut échouer)"
    log_warn ""
fi

# Vérifier que l'email est configuré
# Note: L'email devrait être configuré par setup.sh Phase 4.9
# Si exécuté manuellement, demander l'email
if [[ -z "$EMAIL" ]] || [[ "$EMAIL" == "votre.email@example.com" ]]; then
    # Vérifier si on est en mode interactif (terminal attaché)
    if [[ -t 0 ]]; then
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
    else
        log_error "Email Let's Encrypt non configuré dans .env"
        log_error "Configurez LETSENCRYPT_EMAIL dans le fichier .env avant de relancer."
        log_error "Exemple: LETSENCRYPT_EMAIL=votre.email@example.com"
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

    # Vérifier que le certificat obtenu n'est PAS auto-signé
    if verify_certificate_validity "$CERT_ROOT/conf/live/$DOMAIN/fullchain.pem"; then
        log_success "✓ Certificat vérifié (émis par Let's Encrypt, non auto-signé)"
        generate_final_nginx_config
        reload_nginx
        log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_success "✓ CERTIFICAT VALIDE INSTALLÉ"
        log_success "  Site HTTPS sécurisé ✓"
        log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        exit 0
    else
        log_error "Certificat obtenu mais invalide (auto-signé?)"
        CERTBOT_EXIT=1
    fi
fi

if [[ $CERTBOT_EXIT -ne 0 ]]; then
    log_error "❌ Échec de Let's Encrypt (Code $CERTBOT_EXIT)"
    log_error ""
    log_error "╔════════════════════════════════════════════════════════════╗"
    log_error "║        CAUSES PROBABLES & SOLUTIONS                        ║"
    log_error "╚════════════════════════════════════════════════════════════╝"
    log_error ""
    log_error "1️⃣  DNS NON PROPAGÉ:"
    log_error "   • Le domaine '$DOMAIN' ne pointe pas vers cette machine"
    log_error "   • Solution: Vérifiez votre configuration DNS"
    log_error "   • Attendre 24-48h après DNS change pour propagation complète"
    log_error "   • Test: nslookup $DOMAIN 8.8.8.8"
    log_error ""
    log_error "2️⃣  PORT 80 BLOQUÉ:"
    log_error "   • Let's Encrypt a besoin du port 80 en HTTP"
    log_error "   • FAI peut bloquer (box Freebox, Orange, etc.)"
    log_error "   • Solution: Ouvrir port 80 en UPnP ou configuration manuelle"
    log_error "   • Test: curl http://$(hostname -I | awk '{print $1}'):80"
    log_error ""
    log_error "3️⃣  RATE LIMIT LET'S ENCRYPT:"
    log_error "   • Trop de tentatives échouées (5/heure, 50/semaine)"
    log_error "   • Solution: Attendre avant nouvelle tentative"
    log_error ""
    log_error "4️⃣  CERTBOT CONTAINER INACCESSIBLE:"
    log_error "   • Docker ou image certbot manquante"
    log_error "   • Solution: docker pull certbot/certbot"
    log_error ""
    log_error "📋 LOGS DÉTAILLÉS:"
    log_error "   cat $CERT_ROOT/logs/letsencrypt.log"
    log_error ""

    # ══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE "ZERO SELF-SIGNED" (v5.2)
    # ══════════════════════════════════════════════════════════════════════════
    # PAS de fallback auto-signé. Le script échoue proprement.
    # setup.sh gère l'affichage du message d'erreur complet.
    # ══════════════════════════════════════════════════════════════════════════

    log_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_error "❌ AUCUN CERTIFICAT GÉNÉRÉ"
    log_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_error ""
    log_error "Les certificats auto-signés ne sont PLUS générés."
    log_error "Un certificat Let's Encrypt valide est REQUIS."
    log_error ""
    log_error "🔧 POUR CORRIGER:"
    log_error "  1. Résolvez le problème détecté ci-dessus"
    log_error "  2. Relancez: $0 --force"
    log_error ""

    exit 1
fi
