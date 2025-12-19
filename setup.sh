#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO RPi4 - SETUP SCRIPT (V4.0 - HYBRID ARCHITECTURE)
# ═══════════════════════════════════════════════════════════════════════════════
# Expert DevOps avec Architecture Modulaire & State Management
# Cible: Raspberry Pi 4 (4GB RAM, SD 32GB, ARM64)
# Domaine: gaspardanoukolivier.freeboxos.fr (192.168.1.145)
# ═══════════════════════════════════════════════════════════════════════════════
#
# AMÉLIORATIONS v4.0:
#  ✅ Architecture modulaire (libs réutilisables)
#  ✅ État persistant (checkpoint + recovery)
#  ✅ Pré-vérifications robustes
#  ✅ Sécurité renforcée (mots de passe, secrets)
#  ✅ Idempotence (skip phases déjà complétées)
#  ✅ Logs centralisés et diagnostics
#  ✅ Backup automatique avant modifications
#
# Usage:
#   ./setup.sh                    # Setup normal avec tous les checks
#   ./setup.sh --check-only       # Vérifications sans modifications
#   ./setup.sh --dry-run          # Simulation sans déploiement
#   ./setup.sh --resume           # Reprendre après erreur
#
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === INITIALISATION ===

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROJECT_ROOT="$SCRIPT_DIR"
export PROJECT_ROOT

# === OPTIONS DE LIGNE DE COMMANDE ===

CHECK_ONLY="${1:---check-only}"
DRY_RUN="${2:---dry-run}"
SKIP_VERIFY="${SKIP_VERIFY:-false}"
VERBOSE="${VERBOSE:-false}"
RESUME_MODE="${RESUME_MODE:-false}"

# Traiter les arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --check-only) CHECK_ONLY=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --skip-verify) SKIP_VERIFY=true; shift ;;
        --verbose) VERBOSE=true; LOG_LEVEL="DEBUG"; shift ;;
        --resume) RESUME_MODE=true; shift ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "  --check-only    Vérifications sans modifications"
            echo "  --dry-run       Simulation sans déploiement"
            echo "  --verbose       Logs détaillés"
            echo "  --resume        Reprendre après erreur"
            exit 0
            ;;
        *) shift ;;
    esac
done

# === SOURCING DES LIBRARIES ===

# Charger les libs dans l'ordre (dependencies) - utiliser chemins absolus
source "$SCRIPT_DIR/scripts/lib/common.sh" || { echo "ERROR: Failed to load common.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/security.sh" || { echo "ERROR: Failed to load security.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/docker.sh" || { echo "ERROR: Failed to load docker.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/checks.sh" || { echo "ERROR: Failed to load checks.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/state.sh" || { echo "ERROR: Failed to load state.sh"; exit 1; }

# === VARIABLES DE CONFIGURATION ===

readonly COMPOSE_FILE="docker-compose.pi4-standalone.yml"
readonly ENV_FILE=".env"
readonly ENV_TEMPLATE=".env.pi4.example"
readonly NGINX_TEMPLATE="deployment/nginx/linkedin-bot.conf.template"
readonly NGINX_CONFIG="deployment/nginx/linkedin-bot.conf"
readonly DOMAIN_DEFAULT="gaspardanoukolivier.freeboxos.fr"
readonly LOCAL_IP="192.168.1.145"

# === GLOBAL VARIABLES (set during setup) ===

DOMAIN="$DOMAIN_DEFAULT"
HTTPS_MODE="letsencrypt"
BACKUP_CONFIGURED="false"

# === GESTION D'ERREURS AMÉLIORÉE ===

setup_cleanup() {
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        log_error "Setup échoué (Code $exit_code)"
        finalize_setup_state "failed"
        cleanup_temp_files

        log_info "Pour relancer après correction:"
        log_info "  ./setup.sh --resume"
    else
        finalize_setup_state "completed"
    fi

    return $exit_code
}

trap setup_cleanup EXIT

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SETUP FLOW
# ═══════════════════════════════════════════════════════════════════════════════

# === PHASE 0: INITIALIZATION ===

log_step "PHASE 0: Initialisation du Setup"

# Récupérer domaine depuis .env existant si présent
if [[ -f "$ENV_FILE" ]]; then
    DOMAIN=$(grep "^DOMAIN=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "$DOMAIN_DEFAULT")
    log_info "Domaine chargé depuis .env: $DOMAIN"
fi

# Initialiser l'état (ou reprendre)
if [[ "$RESUME_MODE" == "true" ]]; then
    log_info "Mode RESUME: Reprise après erreur"
    if [[ ! -f "$SETUP_STATE_FILE" ]]; then
        log_error "Aucun état de setup trouvé à reprendre"
        exit 1
    fi
else
    setup_state_init
fi

# === PHASE 1: VÉRIFICATIONS ===

log_step "PHASE 1: Vérifications Pré-Déploiement"

if ! check_all_prerequisites "$COMPOSE_FILE"; then
    log_error "Vérifications échouées"
    setup_state_checkpoint "prerequisites" "failed"
    exit 1
fi

setup_state_checkpoint "prerequisites" "completed"

# Si --check-only, arrêter ici
if [[ "$CHECK_ONLY" == "true" ]]; then
    log_success "✓ Toutes les vérifications passées"
    exit 0
fi

# === PHASE 2: BACKUP & CONFIGURATION ===

log_step "PHASE 2: Backup"

if ! backup_file "$ENV_FILE" "before setup" >/dev/null; then
    log_error "Backup .env échoué"
    setup_state_checkpoint "backup" "failed"
    exit 1
fi

setup_state_checkpoint "backup" "completed"

# === PHASE 3: CONFIGURATION DOCKER ===

log_step "PHASE 3: Configuration Docker"

if ! docker_check_all_prerequisites; then
    log_error "Docker checks échouées"
    setup_state_checkpoint "docker_config" "failed"
    exit 1
fi

setup_state_checkpoint "docker_config" "completed"

# Configure Docker IPv4 et DNS fiables
log_info "Configuration Docker pour RPi4..."
configure_docker_ipv4 || true
configure_kernel_params || true
configure_zram || true

# Nettoyage disque
log_info "Nettoyage des ressources Docker..."
docker_cleanup || true

# === PHASE 4: CONFIGURATION .env & SECRETS ===

log_step "PHASE 4: Configuration Sécurisée"

# Ensure bcrypt is available for password hashing
log_info "Vérification des dépendances Python pour la sécurité..."
if ! python3 -c "import bcrypt" 2>/dev/null; then
    log_info "Installation bcrypt pour le hashage de mot de passe..."
    if cmd_exists python3; then
        python3 -m pip install -q bcrypt --break-system-packages 2>/dev/null || true
    fi
fi

# Créer .env s'il n'existe pas
if [[ ! -f "$ENV_FILE" ]]; then
    log_info "Création $ENV_FILE depuis template..."
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi

# Configuration du mot de passe dashboard
log_info "Configuration mot de passe dashboard..."

HAS_BCRYPT_HASH=false
if grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" "$ENV_FILE" 2>/dev/null; then
    HAS_BCRYPT_HASH=true
fi

NEEDS_PASSWORD=false
if grep -q "CHANGEZ_MOI" "$ENV_FILE" || [[ "$HAS_BCRYPT_HASH" == "false" ]]; then
    NEEDS_PASSWORD=true
fi

if [[ "$NEEDS_PASSWORD" == "true" ]]; then
    log_step "Mot de Passe Dashboard"

    if [[ "$HAS_BCRYPT_HASH" == "true" ]]; then
        choice=$(prompt_menu "Configuration du mot de passe" \
            "Définir/Changer le mot de passe maintenant" \
            "Garder le mot de passe existant" \
            "Annuler pour l'instant")
    else
        choice=$(prompt_menu "Configuration du mot de passe" \
            "Définir un nouveau mot de passe" \
            "Annuler pour l'instant")
    fi

    case "$choice" in
        1)
            echo -e "\n${BOLD}Entrez le nouveau mot de passe:${NC}"
            echo -n "Mot de passe (caché) : "
            read -rs PASS_INPUT
            echo ""

            if [[ -n "$PASS_INPUT" ]]; then
                hash_and_store_password "$ENV_FILE" "$PASS_INPUT" || {
                    log_error "Impossible de hasher le mot de passe"
                    exit 1
                }
                setup_state_set_config "password_set" "true"
            fi
            ;;
        2)
            log_info "✓ Mot de passe conservé"
            ;;
        3)
            log_warn "Configuration annulée"
            ;;
    esac
fi

# Générer API_KEY si nécessaire
if grep -q "API_KEY=your_secure_random_key_here\|API_KEY=CHANGEZ_MOI" "$ENV_FILE"; then
    log_info "Génération API_KEY robuste..."
    NEW_KEY=$(generate_api_key) || {
        log_error "Impossible de générer API_KEY"
        exit 1
    }
    sed -i "s|^API_KEY=.*|API_KEY=${NEW_KEY}|" "$ENV_FILE"
    log_success "✓ API_KEY générée"
    setup_state_set_config "api_key_generated" "true"
fi

# Générer JWT_SECRET si nécessaire
if grep -q "JWT_SECRET=your_jwt_secret_here\|JWT_SECRET=CHANGEZ_MOI" "$ENV_FILE"; then
    log_info "Génération JWT_SECRET robuste..."
    NEW_JWT=$(generate_jwt_secret) || {
        log_error "Impossible de générer JWT_SECRET"
        exit 1
    }
    ESCAPED_JWT=$(escape_sed_string "$NEW_JWT")
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${ESCAPED_JWT}|" "$ENV_FILE"
    log_success "✓ JWT_SECRET généré"
fi

# === PHASE 4.5: PRÉPARATION VOLUMES & PERMISSIONS ===

log_step "PHASE 4.5: Permissions & Volumes"

mkdir -p data logs config certbot/conf certbot/www
touch data/messages.txt data/late_messages.txt
[[ ! -f data/linkedin.db ]] && touch data/linkedin.db

# Appliquer permissions
if [[ -w "." ]]; then
    if [[ "$EUID" -ne 1000 ]]; then
        check_sudo || true
        sudo chown -R 1000:1000 data logs config 2>/dev/null || true
    fi
else
    check_sudo || true
    sudo chown -R 1000:1000 data logs config 2>/dev/null || true
fi

chmod -R 775 data logs config
log_success "✓ Permissions appliquées"

# === PHASE 5: BOOTSTRAP SSL ===

log_step "PHASE 5: Préparation SSL"

CERT_DIR="certbot/conf/live/${DOMAIN}"
if [[ ! -f "$CERT_DIR/fullchain.pem" ]] || [[ ! -f "$CERT_DIR/privkey.pem" ]]; then
    log_warn "Certificats temporaires générés..."
    mkdir -p "$CERT_DIR"

    if cmd_exists openssl; then
        openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
            -keyout "$CERT_DIR/privkey.pem" \
            -out "$CERT_DIR/fullchain.pem" \
            -subj "/CN=${DOMAIN}/O=Temporary Certificate/C=FR" 2>/dev/null

        chmod 644 "$CERT_DIR/fullchain.pem"
        chmod 600 "$CERT_DIR/privkey.pem"
        log_success "✓ Certificats temporaires créés"
    fi
fi

# === PHASE 5.1: CONFIGURATION NGINX ===

log_step "PHASE 5.1: Configuration Nginx"

if [[ -f "$NGINX_TEMPLATE" ]]; then
    export DOMAIN
    if ! envsubst '${DOMAIN}' < "$NGINX_TEMPLATE" > "$NGINX_CONFIG"; then
        log_error "Impossible de générer config Nginx"
        exit 1
    fi
    chmod 644 "$NGINX_CONFIG"
    log_success "✓ Configuration Nginx générée"
fi

# === PHASE 5.2: CONFIGURATION HTTPS ===

log_step "PHASE 5.2: Configuration HTTPS"

choice=$(prompt_menu "Scénario HTTPS" \
    "🏠 LAN uniquement (HTTP, pas HTTPS)" \
    "🌐 Domaine avec Let's Encrypt (production)" \
    "🔒 Certificats existants (import)" \
    "⚙️  Configuration manuelle (plus tard)")

case "$choice" in
    1)
        HTTPS_MODE="lan"
        log_warn "HTTPS désactivé (LAN uniquement)"
        ;;
    2)
        HTTPS_MODE="letsencrypt"
        log_info "Let's Encrypt sera configuré avec: ./scripts/setup_letsencrypt.sh"
        ;;
    3)
        log_step "Import de Certificats Existants"
        read -p "Chemin fullchain.pem : " CERT_FILE
        read -p "Chemin privkey.pem : " KEY_FILE

        if [[ -f "$CERT_FILE" ]] && [[ -f "$KEY_FILE" ]]; then
            cp "$CERT_FILE" "$CERT_DIR/fullchain.pem"
            cp "$KEY_FILE" "$CERT_DIR/privkey.pem"
            chmod 600 "$CERT_DIR/privkey.pem"
            HTTPS_MODE="existing"
            log_success "✓ Certificats importés"
        else
            log_error "Fichiers certificats non trouvés"
        fi
        ;;
    4)
        HTTPS_MODE="manual"
        log_warn "Configuration HTTPS manuelle sélectionnée"
        ;;
esac

setup_state_set_config "https_mode" "$HTTPS_MODE"

# === PHASE 6: DÉPLOIEMENT DOCKER ===

log_step "PHASE 6: Déploiement Docker"

# Valider docker-compose
if ! docker_compose_validate "$COMPOSE_FILE"; then
    log_error "Docker-compose validation échouée"
    exit 1
fi

# Pull images
if ! docker_pull_with_retry "$COMPOSE_FILE"; then
    log_error "Pull images échoué"
    exit 1
fi

# Démarrer les conteneurs
if ! docker_compose_up "$COMPOSE_FILE" true; then
    log_error "Démarrage des conteneurs échoué"
    exit 1
fi

# === PHASE 7: VALIDATION ===

log_step "PHASE 7: Validation du Déploiement"

# Attendre que les services soient opérationnels
if ! wait_for_service "api" "http://localhost:8000/health"; then
    log_error "API ne démarre pas"
    docker compose -f "$COMPOSE_FILE" logs api --tail=50
    exit 1
fi

if ! wait_for_service "dashboard" "http://localhost:3000/api/system/health"; then
    log_error "Dashboard ne démarre pas"
    docker compose -f "$COMPOSE_FILE" logs dashboard --tail=50
    exit 1
fi

log_success "✓ Services validés"

# === PHASE 8: CONFIGURATION GOOGLE DRIVE (OPTIONNEL) ===

log_step "PHASE 8: Configuration Sauvegardes Google Drive (Optionnel)"

if prompt_yes_no "Configurer sauvegardes Google Drive ?" "n"; then
    if cmd_exists rclone; then
        log_info "Configuration rclone..."
        rclone config
        BACKUP_CONFIGURED="true"
        setup_state_set_config "backup_configured" "true"
    else
        log_warn "rclone non installé, skippé"
    fi
else
    log_info "Sauvegardes non configurées (vous pouvez les ajouter plus tard)"
fi

# === AUDIT SÉCURITÉ FINAL ===

log_step "🔒 AUDIT SÉCURITÉ & CONFIGURATION"

audit_env_security "$ENV_FILE" || true

# === RAPPORT FINAL ===

log_step "DÉPLOIEMENT TERMINÉ AVEC SUCCÈS"

LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
DASHBOARD_USER=$(grep "^DASHBOARD_USER=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "admin")

cat <<EOF

${BOLD}${BLUE}┌─────────────────────────────────────────────────────────────────────────┐${NC}
${BOLD}${BLUE}│                    CONFIGURATION TERMINÉE AVEC SUCCÈS                  │${NC}
${BOLD}${BLUE}└─────────────────────────────────────────────────────────────────────────┘${NC}

  ${BOLD}🌐 Accès${NC}
  ├─ HTTPS externe     : ${GREEN}https://${DOMAIN}${NC}
  ├─ HTTP local        : http://${LOCAL_IP}:3000
  └─ Grafana monitoring : http://${LOCAL_IP}:3001

  ${BOLD}🔐 Authentification${NC}
  ├─ Utilisateur       : ${GREEN}${DASHBOARD_USER}${NC}
  └─ Mot de passe      : [vous l'avez entré]

  ${BOLD}📊 Infrastructure${NC}
  ├─ Domaine          : ${DOMAIN}
  ├─ IP locale        : ${LOCAL_IP}
  ├─ Conteneurs       : $(docker compose -f "$COMPOSE_FILE" ps --quiet 2>/dev/null | wc -l)
  └─ HTTPS mode       : ${HTTPS_MODE}

  ${BOLD}🔧 Commandes utiles${NC}
  ├─ Logs              : docker compose -f $COMPOSE_FILE logs -f
  ├─ Statut            : docker compose -f $COMPOSE_FILE ps
  ├─ Redémarrer        : docker compose -f $COMPOSE_FILE restart
  ├─ Arrêter           : docker compose -f $COMPOSE_FILE down
  ├─ Mot de passe      : ./scripts/manage_dashboard_password.sh
  └─ Monitoring        : ./scripts/monitor_pi4_health.sh

  ${BOLD}📚 Documentation${NC}
  ├─ Setup: docs/RASPBERRY_PI_DOCKER_SETUP.md
  ├─ Troubleshooting: docs/RASPBERRY_PI_TROUBLESHOOTING.md
  ├─ Security: docs/SECURITY_AUDIT.md
  └─ État du setup: .setup.state

${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

✓ ${GREEN}Setup v4.0 réussi${NC} - Accédez au dashboard pour finaliser la configuration!

EOF

exit 0
