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

# === VERROU DE FICHIER (ÉVITER EXÉCUTIONS MULTIPLES) ===

readonly LOCK_FILE="/tmp/linkedin-bot-setup.lock"
readonly LOCK_FD=200

# Couleurs pour les messages (avant le sourcing de common.sh)
readonly _RED='\033[0;31m'
readonly _YELLOW='\033[1;33m'
readonly _NC='\033[0m'

# Fonction de nettoyage du verrou
cleanup_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        rm -f "$LOCK_FILE" 2>/dev/null || true
    fi
}

# Acquérir le verrou exclusif
acquire_lock() {
    # Si le fichier de verrou existe mais n'est pas accessible, le supprimer
    if [[ -f "$LOCK_FILE" ]] && ! [[ -w "$LOCK_FILE" ]]; then
        rm -f "$LOCK_FILE" 2>/dev/null || true
    fi

    exec 200>"$LOCK_FILE" 2>/dev/null || {
        echo -e "\n${_RED}[ERROR]${_NC} Impossible d'accéder au verrou $LOCK_FILE"
        echo -e "${_YELLOW}[INFO]${_NC} Essayez de nettoyer le verrou:"
        echo -e "  sudo rm -f $LOCK_FILE"
        exit 1
    }

    if ! flock -n 200; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "unknown")

        echo -e "\n${_RED}[ERROR]${_NC} Une autre instance de setup.sh est déjà en cours d'exécution (PID: $lock_pid)"
        echo -e "${_YELLOW}[INFO]${_NC} Si vous êtes certain qu'aucun setup n'est actif, supprimez le verrou:"
        echo -e "  rm -f $LOCK_FILE"
        exit 1
    fi

    # Écrire le PID dans le fichier de verrou
    echo $$ >&200

    # Nettoyer le verrou à la sortie
    trap cleanup_lock EXIT
}

# Acquérir le verrou avant de continuer
acquire_lock

# === OPTIONS DE LIGNE DE COMMANDE ===

# Initialiser les flags à false par défaut
CHECK_ONLY=false
DRY_RUN=false
SKIP_VERIFY="${SKIP_VERIFY:-false}"
VERBOSE="${VERBOSE:-false}"
RESUME_MODE=false
LOG_LEVEL="${LOG_LEVEL:-INFO}"

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
        *)
            log_error "Option inconnue: $1"
            echo "Utilisez --help pour voir les options disponibles"
            exit 1
            ;;
    esac
done

# === SOURCING DES LIBRARIES ===

# Charger les libs dans l'ordre (dependencies) - utiliser chemins absolus
source "$SCRIPT_DIR/scripts/lib/common.sh" || { echo "ERROR: Failed to load common.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/installers.sh" || { echo "ERROR: Failed to load installers.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/security.sh" || { echo "ERROR: Failed to load security.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/docker.sh" || { echo "ERROR: Failed to load docker.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/checks.sh" || { echo "ERROR: Failed to load checks.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/state.sh" || { echo "ERROR: Failed to load state.sh"; exit 1; }

# === VARIABLES DE CONFIGURATION ===

readonly COMPOSE_FILE="docker-compose.yml"
readonly ENV_FILE=".env"
readonly ENV_TEMPLATE=".env.pi4.example"
readonly NGINX_TEMPLATE_HTTPS="deployment/nginx/linkedin-bot-https.conf.template"
readonly NGINX_TEMPLATE_LAN="deployment/nginx/linkedin-bot-lan.conf.template"
readonly NGINX_CONFIG="deployment/nginx/linkedin-bot.conf"
readonly DOMAIN_DEFAULT="gaspardanoukolivier.freeboxos.fr"
readonly LOCAL_IP="192.168.1.145"

# === GLOBAL VARIABLES (set during setup) ===

DOMAIN="$DOMAIN_DEFAULT"
HTTPS_MODE="letsencrypt"
BACKUP_CONFIGURED="false"
MONITORING_ENABLED="false"

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

if ! ensure_prerequisites "$COMPOSE_FILE"; then
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

# Note: Le hashage de mot de passe utilise désormais le conteneur Docker du dashboard
# Aucune dépendance Python (bcrypt) n'est requise sur l'hôte
log_info "Le hashage de mot de passe utilisera le conteneur Docker (bcryptjs)"

# Créer .env s'il n'existe pas
if [[ ! -f "$ENV_FILE" ]]; then
    log_info "Création $ENV_FILE depuis template..."
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi

# Configuration du mot de passe dashboard
log_info "Configuration mot de passe dashboard..."

# Détecter si un hash bcrypt existe (supporte $ simple et $$ doublé)
# Formats bcrypt: $2a$, $2b$, $2x$, $2y$ ou $$2a$$, $$2b$$, $$2x$$, $$2y$$
HAS_BCRYPT_HASH=false
if grep -qE "^DASHBOARD_PASSWORD=\\\$\\\$?2[abxy]\\\$\\\$?" "$ENV_FILE" 2>/dev/null; then
    HAS_BCRYPT_HASH=true
    log_info "✓ Hash bcrypt détecté dans .env"
fi

# Vérifier si le mot de passe doit être configuré
NEEDS_PASSWORD=false
CURRENT_PASSWORD=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2)

if [[ -z "$CURRENT_PASSWORD" ]] || \
   grep -q "CHANGEZ_MOI" "$ENV_FILE" 2>/dev/null || \
   [[ "$CURRENT_PASSWORD" == "CHANGEZ_MOI_PAR_MOT_DE_PASSE_FORT" ]] || \
   [[ "$HAS_BCRYPT_HASH" == "false" ]]; then
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

# Créer les répertoires nécessaires
mkdir -p data logs config certbot/conf certbot/www deployment/nginx

# Créer les fichiers de base s'ils n'existent pas
touch data/messages.txt data/late_messages.txt 2>/dev/null || true
[[ ! -f data/linkedin.db ]] && touch data/linkedin.db 2>/dev/null || true

# Appliquer permissions de manière robuste
log_info "Configuration des permissions pour Docker (UID 1000)..."

# Vérifier si nous avons besoin de sudo
NEED_SUDO=false
if [[ ! -w data ]] || [[ ! -w logs ]] || [[ ! -w config ]]; then
    NEED_SUDO=true
fi

# Fonction pour appliquer les permissions
apply_permissions() {
    local use_sudo="$1"

    if [[ "$use_sudo" == "true" ]]; then
        check_sudo
        sudo chown -R 1000:1000 data logs config certbot 2>/dev/null || {
            log_warn "Impossible de changer le propriétaire (ignoré si vous êtes déjà UID 1000)"
        }
        sudo chmod -R 775 data logs config 2>/dev/null || {
            log_error "Impossible de modifier les permissions"
            return 1
        }
    else
        chown -R 1000:1000 data logs config certbot 2>/dev/null || {
            log_warn "Impossible de changer le propriétaire (ignoré si vous êtes déjà UID 1000)"
        }
        chmod -R 775 data logs config 2>/dev/null || {
            log_error "Impossible de modifier les permissions"
            return 1
        }
    fi

    return 0
}

# Appliquer les permissions
if ! apply_permissions "$NEED_SUDO"; then
    log_error "Échec de la configuration des permissions"
    exit 1
fi

# Vérifier que les permissions sont correctes
if [[ ! -w data ]] || [[ ! -w logs ]] || [[ ! -w config ]]; then
    log_warn "Les permissions ne sont pas optimales mais on continue..."
else
    log_success "✓ Permissions appliquées (UID 1000, mode 775)"
fi

# === PHASE 5: CONFIGURATION HTTPS (REORDERED BEFORE NGINX) ===

log_step "PHASE 5: Configuration HTTPS"

CERT_DIR="certbot/conf/live/${DOMAIN}"
mkdir -p "$CERT_DIR"

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
            exit 1
        fi
        ;;
    4)
        HTTPS_MODE="manual"
        log_warn "Configuration HTTPS manuelle sélectionnée"
        ;;
esac

setup_state_set_config "https_mode" "$HTTPS_MODE"

# === PHASE 5.1: BOOTSTRAP SSL & CONFIGURATION NGINX ===

log_step "PHASE 5.1: Préparation SSL et Configuration Nginx"

# Créer certificats temporaires si nécessaire (pour tous les modes sauf manual)
if [[ "$HTTPS_MODE" != "manual" ]]; then
    if [[ ! -f "$CERT_DIR/fullchain.pem" ]] || [[ ! -f "$CERT_DIR/privkey.pem" ]]; then
        log_info "Génération de certificats temporaires..."

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
fi

# Sélectionner le template nginx approprié
if [[ "$HTTPS_MODE" == "lan" ]]; then
    NGINX_TEMPLATE="$NGINX_TEMPLATE_LAN"
    log_info "Utilisation du template Nginx: MODE LAN (HTTP only)"
else
    NGINX_TEMPLATE="$NGINX_TEMPLATE_HTTPS"
    log_info "Utilisation du template Nginx: MODE HTTPS"
fi

# Générer la configuration nginx
if [[ -f "$NGINX_TEMPLATE" ]]; then
    export DOMAIN
    if ! envsubst '${DOMAIN}' < "$NGINX_TEMPLATE" > "$NGINX_CONFIG"; then
        log_error "Impossible de générer config Nginx"
        exit 1
    fi
    chmod 644 "$NGINX_CONFIG"
    log_success "✓ Configuration Nginx générée (${HTTPS_MODE})"
else
    log_error "Template Nginx introuvable: $NGINX_TEMPLATE"
    exit 1
fi

# === PHASE 5.3: CONFIGURATION CRON RENOUVELLEMENT SSL ===

if [[ "$HTTPS_MODE" == "letsencrypt" ]]; then
    log_step "PHASE 5.3: Configuration Renouvellement SSL Automatique"

    if prompt_yes_no "Configurer le renouvellement automatique des certificats SSL (cron) ?" "y"; then
        # Vérifier si le cron job existe déjà
        CRON_JOB="0 3 * * * $PROJECT_ROOT/scripts/renew_certificates.sh >> /var/log/certbot-renew.log 2>&1"

        if crontab -l 2>/dev/null | grep -qF "renew_certificates.sh"; then
            log_info "✓ Cron job SSL déjà configuré"
        else
            log_info "Ajout du cron job pour le renouvellement SSL..."

            # Créer le fichier de log si nécessaire
            sudo touch /var/log/certbot-renew.log 2>/dev/null || true
            sudo chown "$(whoami):$(whoami)" /var/log/certbot-renew.log 2>/dev/null || true

            # Ajouter au crontab
            (crontab -l 2>/dev/null || true; echo "$CRON_JOB") | crontab -

            log_success "✓ Cron job configuré (tous les jours à 3h du matin)"
            log_info "Le renouvellement automatique vérifiera si les certificats expirent dans < 30 jours"
        fi
    else
        log_warn "Renouvellement automatique non configuré"
        log_info "Vous pouvez le configurer manuellement plus tard avec:"
        log_info "  crontab -e"
        log_info "  Ajouter: 0 3 * * * $PROJECT_ROOT/scripts/renew_certificates.sh >> /var/log/certbot-renew.log 2>&1"
    fi
fi

# === PHASE 6: DÉPLOIEMENT DOCKER ===

log_step "PHASE 6: Déploiement Docker"

# Demander pour le monitoring
if prompt_yes_no "Activer le monitoring complet (Grafana/Prometheus) ? [Mémoire +500MB]" "n"; then
    MONITORING_ENABLED="true"
    setup_state_set_config "monitoring_enabled" "true"
else
    MONITORING_ENABLED="false"
    setup_state_set_config "monitoring_enabled" "false"
fi

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
if ! docker_compose_up "$COMPOSE_FILE" "true" "$MONITORING_ENABLED"; then
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
