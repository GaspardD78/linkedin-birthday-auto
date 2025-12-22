#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO RPi4 - SUPER ORCHESTRATEUR v5.0
# ═══════════════════════════════════════════════════════════════════════════════
# Expert DevOps avec Architecture Modulaire, UX Immersive & Robustesse Maximale
# Cible: Raspberry Pi 4 (4GB RAM, SD 32GB, ARM64)
# Domaine: gaspardanoukolivier.freeboxos.fr (192.168.1.145)
# ═══════════════════════════════════════════════════════════════════════════════
#
# NOUVEAUTÉS v5.0 (SUPER ORCHESTRATEUR):
#  ✅ Logging dual-output centralisé (screen + fichier timestampé)
#  ✅ Bannière de bienvenue ASCII immersive
#  ✅ Vérification connectivité internet avant de commencer
#  ✅ Configuration Google Drive (rclone) guidée pour headless (Cheat Sheet visuel)
#  ✅ Attente active des conteneurs "healthy" avec tests endpoints
#  ✅ Barres de progression et spinners améliorés
#  ✅ Affichage intelligent des mots de passe (en clair si généré, masqué sinon)
#  ✅ Audit final complet avec Deep Dive
#  ✅ Intégration scripts d'optimisation (kernel, ZRAM) si présents
#
# Usage:
#   ./setup.sh                    # Setup normal avec tous les checks
#   ./setup.sh --check-only       # Vérifications sans modifications
#   ./setup.sh --dry-run          # Simulation sans déploiement
#   ./setup.sh --resume           # Reprendre après erreur
#   ./setup.sh --verbose          # Logs détaillés
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
            echo -e "${_RED}[ERROR]${_NC} Option inconnue: $1"
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
source "$SCRIPT_DIR/scripts/lib/audit.sh" || { echo "ERROR: Failed to load audit.sh"; exit 1; }

# Vérifier la disponibilité de Python3 (requis par state.sh)
if ! cmd_exists python3; then
    log_error "Python3 est requis pour le state management"
    exit 1
fi

# === INITIALISER LE LOGGING DUAL-OUTPUT (NOUVEAU v5.0) ===

setup_logging "logs"

# === AFFICHER LA BANNIÈRE DE BIENVENUE (NOUVEAU v5.0) ===

show_welcome_banner "5.0" "LinkedIn Birthday Auto"

log_info "📋 Fichier de log: ${BOLD}$(get_log_file)${NC}"
echo ""

# === VARIABLES DE CONFIGURATION ===

readonly COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
readonly ENV_FILE="$SCRIPT_DIR/.env"
readonly ENV_TEMPLATE="$SCRIPT_DIR/.env.pi4.example"
readonly NGINX_TEMPLATE_HTTPS="$SCRIPT_DIR/deployment/nginx/linkedin-bot-https.conf.template"
readonly NGINX_TEMPLATE_LAN="$SCRIPT_DIR/deployment/nginx/linkedin-bot-lan.conf.template"
readonly NGINX_CONFIG="$SCRIPT_DIR/deployment/nginx/linkedin-bot.conf"
readonly DOMAIN_DEFAULT="gaspardanoukolivier.freeboxos.fr"
LOCAL_IP="192.168.1.145"  # Not readonly - will be determined dynamically later

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

# === PHASE 0: INITIALIZATION & NETWORK CHECKS (NOUVEAU v5.0) ===

log_step "PHASE 0: Vérifications Préliminaires"

# Vérifier la connectivité internet (NOUVEAU)
if ! check_internet_connectivity; then
    log_error "Connectivité internet requise pour continuer"
    exit 1
fi

# Vérifier DNS (NOUVEAU)
check_dns_resolution || log_warn "DNS potentiellement problématique, mais on continue..."

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

# Vérification des ports critiques (NOUVEAU)
log_info "Vérification des ports..."
check_port_available() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        if lsof -i :$port -t >/dev/null 2>&1; then
            echo "❌ Port $port est déjà utilisé!"
            return 1
        fi
    elif command -v nc >/dev/null 2>&1; then
         if nc -z localhost $port 2>/dev/null; then
            echo "❌ Port $port est déjà utilisé!"
            return 1
         fi
    fi
    return 0
}

# Ports: Redis(6379), API(8000), Dashboard(3000), Nginx(80,443)
for port in 6379 8000 3000 80 443; do
    if ! check_port_available $port; then
        log_warn "Port $port occupé. Si c'est par nos conteneurs, c'est OK."
        # On ne bloque pas strictement car docker-compose restart gérera ça,
        # mais c'est une bonne info pour le debug
    fi
done

# Si --check-only, arrêter ici
if [[ "$CHECK_ONLY" == "true" ]]; then
    log_success "✓ Toutes les vérifications passées"
    exit 0
fi

#===============================================================================
# PHASE 1.5 : Configuration DNS Stable (Anti-timeout Docker pull)
#===============================================================================
echo "══════════════════════════════════════════════════════════════"
echo "  PHASE 1.5 : DNS Stable RPi4 (Google/Cloudflare)"
echo "══════════════════════════════════════════════════════════════"

# Paramétrage via variable d'environnement (Task 4.2)
CONFIGURE_SYSTEM_DNS="${CONFIGURE_SYSTEM_DNS:-true}"

if [ "${CONFIGURE_SYSTEM_DNS}" = "true" ]; then

    # Install dnsutils si manquant (pour nslookup)
    if ! command -v nslookup >/dev/null 2>&1; then
        echo "ℹ [INFO] Installation dnsutils..."
        sudo apt update -qq && sudo apt install dnsutils -y </dev/null
    fi

    # Vérif configuration existante (idempotence)
    if grep -q "static domain_name_servers=8.8.8.8" /etc/dhcpcd.conf 2>/dev/null; then
        echo "✓ [OK] DNS déjà configuré (Google DNS)"
    else
        echo "🔧 Configuration DNS permanent..."
        sudo tee -a /etc/dhcpcd.conf > /dev/null << 'EOF'
# DNS stable RPi4 - anti-timeout Docker pull (LinkedIn-bot)
static domain_name_servers=8.8.8.8 8.8.4.4 1.1.1.1
EOF
    fi

    # Redémarrage dhcpcd (pas systemctl !)
    echo "🔄 Redémarrage réseau dhcpcd..."
    sudo dhcpcd -n || echo "⚠️ Redémarrage dhcpcd échoué (ignorer si non présent)"
    sleep 3

    # Test DNS fonctionnel
    if nslookup google.com >/dev/null 2>&1; then
        echo "✓ [OK] DNS opérationnel : google.com"
    else
        echo "⚠ [WARN] DNS Google non accessible"
    fi

else
    echo "⚠️  CONFIGURE_SYSTEM_DNS=false; Configuration DNS système ignorée."
fi

echo "✅ PHASE DNS TERMINÉE"

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

# Configure Docker IPv4 et DNS fiables (NOUVEAU - Approche robuste)
log_info "Configuration Docker pour RPi4..."

# Sourcer le module DNS Fix (production-ready)
if [[ -f "$SCRIPT_DIR/scripts/lib/docker_dns_fix.sh" ]]; then
    source "$SCRIPT_DIR/scripts/lib/docker_dns_fix.sh"

    # Appliquer le fix DNS si nécessaire (avec diagnostic automatique)
    log_info "Diagnostic et correction DNS Docker..."
    if fix_docker_dns; then
        log_success "✓ DNS Docker configuré avec succès"
    else
        log_warn "⚠️  Fix DNS échoué, tentative avec méthode legacy..."
        # Fallback sur l'ancienne méthode si le nouveau module échoue
        configure_docker_ipv4 || log_warn "Configuration DNS partiellement échouée"
    fi
else
    # Fallback si le nouveau module n'existe pas
    log_warn "Module docker_dns_fix.sh non trouvé, utilisation méthode legacy"
    configure_docker_ipv4 || true
fi

# Optimisations système (kernel, ZRAM)
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

# PHASE 3 : Configuration Sécurisée Dashboard
configure_dashboard_password() {
    log_info ">>> 🔐 Configuration Mot de Passe Dashboard"

    # ==============================================================================
    # IDEMPOTENCE ROBUSTE (Correctif v5.2 - Production Ready)
    # Validation stricte du hash Bcrypt et gestion complète des cas .env
    # ==============================================================================

    if [[ -f "$ENV_FILE" ]]; then
        local current_pwd=""
        current_pwd=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"'\' | tr -d '\r' | xargs)
        local default_value="CHANGEZ_MOI_PAR_MOT_DE_PASSE_FORT"

        # Validation robuste acceptant le format standard ($2a$...) et le format échappé Docker ($$2a$$...)
        if [[ -n "$current_pwd" && "$current_pwd" != "$default_value" && "$current_pwd" =~ ^(\$\$|[\$])2[aby](\$\$|[\$]).{50,}$ ]]; then
            log_success "✅ Mot de passe déjà configuré (hash Bcrypt valide détecté)"
            return 0
        fi

        if [[ -z "$current_pwd" || "$current_pwd" == "$default_value" ]]; then
            log_warn "⚠️  Valeur par défaut ou vide détectée dans .env. Reconfiguration requise."
        else
            log_warn "⚠️  Mot de passe non hashé ou invalide. Hashage forcé enclenché..."
        fi
    fi

    local PASSWORD
    local PASSWORD_CONFIRM

    # Double validation mot de passe
    while true; do
        echo ""
        read -s -r -p "🔑 Mot de passe dashboard (≥8 car.) : " PASSWORD
        echo ""
        read -s -r -p "🔑 Confirmez le mot de passe       : " PASSWORD_CONFIRM
        echo ""

        if [[ "$PASSWORD" == "$PASSWORD_CONFIRM" ]] && [[ ${#PASSWORD} -ge 8 ]]; then
            break
        fi

        log_warn "❌ Non concordant ou trop court (<8). Réessayez."
    done

    # Hachage via lib security.sh (Architecture CI/CD Robuste)
    # Utilise l'image 'pi-security-hash' pré-buildée
    if hash_and_store_password "$ENV_FILE" "$PASSWORD"; then
        export SETUP_PASSWORD_PLAINTEXT="$PASSWORD"
        setup_state_set_config "password_set" "true"
        log_success "✅ Dashboard sécurisé !"
    else
        log_error "💥 ÉCHEC CRITIQUE du hachage. Setup abandonné."
        exit 1
    fi
}
configure_dashboard_password

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

choice=$(prompt_menu "Scénario HTTPS (RPi4 - Exposition HTTPS)" \
    "🌐 Domaine avec Let's Encrypt (production - recommandé)" \
    "🔒 Certificats existants (import)" \
    "⚙️  Configuration manuelle (plus tard)")

case "$choice" in
    1)
        HTTPS_MODE="letsencrypt"
        log_info "Let's Encrypt sera configuré avec: ./scripts/setup_letsencrypt.sh"
        ;;
    2)
        log_step "Import de Certificats Existants"

        # Fonction de validation certificat PEM
        validate_certificate() {
            local cert_file="$1"
            local cert_type="${2:-certificate}"

            if [[ ! -f "$cert_file" ]]; then
                log_error "Fichier non trouvé: $cert_file"
                return 1
            fi

            # Vérifier que c'est un fichier PEM valide
            if ! openssl x509 -in "$cert_file" -noout &>/dev/null && \
               ! openssl pkey -in "$cert_file" -noout &>/dev/null; then
                log_error "Fichier invalide (format PEM attendu): $cert_file"
                return 1
            fi

            log_success "✓ $cert_type valide (PEM)"
            return 0
        }

        cert_valid=false
        key_valid=false

        # Boucle de saisie avec validation
        while [[ "$cert_valid" != "true" ]]; do
            read -p "Chemin fullchain.pem : " CERT_FILE
            if validate_certificate "$CERT_FILE" "Certificat"; then
                cert_valid="true"
            else
                if ! prompt_yes_no "Réessayer ?" "y"; then
                    exit 1
                fi
            fi
        done

        while [[ "$key_valid" != "true" ]]; do
            read -p "Chemin privkey.pem : " KEY_FILE
            if validate_certificate "$KEY_FILE" "Clé privée"; then
                key_valid="true"
            else
                if ! prompt_yes_no "Réessayer ?" "y"; then
                    exit 1
                fi
            fi
        done

        cp "$CERT_FILE" "$CERT_DIR/fullchain.pem"
        cp "$KEY_FILE" "$CERT_DIR/privkey.pem"
        chmod 600 "$CERT_DIR/privkey.pem"
        HTTPS_MODE="existing"
        log_success "✓ Certificats importés avec succès"
        ;;
    3)
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

# Demander pour le monitoring (DÉSACTIVÉ - Grafana retiré)
MONITORING_ENABLED="false"
setup_state_set_config "monitoring_enabled" "false"

# Initialiser la barre de progression pour la phase 6
progress_init "Déploiement Docker" 4

# Étape 1: Validation docker-compose
progress_step "Validation du fichier docker-compose"
if ! docker_compose_validate "$COMPOSE_FILE"; then
    progress_fail "Fichier docker-compose invalide"
    progress_end
    log_error "Docker-compose validation échouée"
    exit 1
fi
progress_done "Configuration valide"

# Étape 2: Pull des images Docker
progress_step "Téléchargement des images Docker"
if ! docker_pull_with_retry "$COMPOSE_FILE"; then
    progress_fail "Impossible de télécharger les images"
    progress_end
    log_error "Pull images échoué"
    exit 1
fi
progress_done "Images téléchargées"

# Étape 3: Démarrage des conteneurs
progress_step "Démarrage des conteneurs"
if ! docker_compose_up "$COMPOSE_FILE" "true" "$MONITORING_ENABLED"; then
    progress_fail "Échec du démarrage"
    progress_end
    log_error "Démarrage des conteneurs échoué"
    exit 1
fi
progress_done "Conteneurs démarrés"

# Étape 4: Vérification post-démarrage
progress_step "Vérification des conteneurs"
sleep 3
RUNNING_CONTAINERS=$(docker compose -f "$COMPOSE_FILE" ps --status running --quiet 2>/dev/null | wc -l)
TOTAL_CONTAINERS=$(docker compose -f "$COMPOSE_FILE" ps --quiet 2>/dev/null | wc -l)
progress_done "${RUNNING_CONTAINERS}/${TOTAL_CONTAINERS} conteneurs actifs"

progress_end

# === PHASE 6.5: POST-PROVISIONING SSL (Let's Encrypt automatique) ===

if [[ "$HTTPS_MODE" == "letsencrypt" ]]; then
    log_step "PHASE 6.5: Obtention des Certificats Let's Encrypt"

    LETSENCRYPT_SCRIPT="./scripts/setup_letsencrypt.sh"

    # Vérifier que le script existe et est exécutable
    if [[ ! -f "$LETSENCRYPT_SCRIPT" ]]; then
        log_error "Script Let's Encrypt introuvable: $LETSENCRYPT_SCRIPT"
        log_warn "⚠️  Certificats temporaires actifs - Exécutez manuellement plus tard:"
        log_warn "     chmod +x $LETSENCRYPT_SCRIPT && $LETSENCRYPT_SCRIPT"
    elif [[ ! -x "$LETSENCRYPT_SCRIPT" ]]; then
        log_warn "Script Let's Encrypt non exécutable, correction..."
        chmod +x "$LETSENCRYPT_SCRIPT" || {
            log_error "Impossible de rendre le script exécutable"
            log_warn "⚠️  Certificats temporaires actifs - Correction manuelle requise:"
            log_warn "     sudo chmod +x $LETSENCRYPT_SCRIPT && $LETSENCRYPT_SCRIPT"
        }
    fi

    # Exécuter le script si disponible et exécutable (fail-safe)
    if [[ -x "$LETSENCRYPT_SCRIPT" ]]; then
        log_info "Tentative d'obtention du certificat Let's Encrypt..."
        log_info "Cette opération peut prendre jusqu'à 2 minutes..."

        # Exécuter avec capture du code de retour (ne pas planter le setup si échec)
        if "$LETSENCRYPT_SCRIPT"; then
            log_success "✓ Certificat Let's Encrypt obtenu avec succès"

            # Recharger Nginx pour appliquer les nouveaux certificats (sans coupure)
            log_info "Rechargement de la configuration Nginx..."
            if docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload 2>/dev/null; then
                log_success "✓ Nginx rechargé - Certificat SSL production actif"
            else
                log_warn "⚠️  Impossible de recharger Nginx automatiquement"
                log_info "Rechargez manuellement avec: docker compose -f $COMPOSE_FILE restart nginx"
            fi
        else
            # Échec de l'obtention du certificat
            log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            log_warn "⚠️  ${YELLOW}${BOLD}AVERTISSEMENT:${NC}${YELLOW} Échec de l'obtention du certificat Let's Encrypt${NC}"
            log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            log_warn "🔒 Votre serveur reste accessible via ${BOLD}certificats auto-signés temporaires${NC}"
            log_warn "   (navigateurs afficheront un avertissement de sécurité)"
            echo ""
            log_warn "📋 Causes possibles:"
            log_warn "   • Port 80 bloqué ou inaccessible depuis internet"
            log_warn "   • Domaine ${DOMAIN} ne pointe pas vers cette machine"
            log_warn "   • Rate limit Let's Encrypt atteint (5 échecs/heure, 50 certs/semaine)"
            log_warn "   • Serveur DNS non propagé (peut prendre jusqu'à 48h)"
            echo ""
            log_warn "🔧 Pour réessayer manuellement:"
            log_warn "   ${BOLD}${CYAN}$LETSENCRYPT_SCRIPT${NC}"
            echo ""
            log_warn "📚 Documentation troubleshooting:"
            log_warn "   docs/RASPBERRY_PI_TROUBLESHOOTING.md (section SSL)"
            log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""

            # Attendre 2 secondes pour que l'utilisateur voie le message
            sleep 2
        fi
    fi
fi

# === PHASE 7: VALIDATION (Utilise les nouvelles fonctions de audit.sh) ===

log_step "PHASE 7: Validation du Déploiement"

# Attendre que les services soient opérationnels (NOUVEAU - utilise wait_for_api_endpoint)
if ! wait_for_api_endpoint "API" "http://localhost:8000/health" 90; then
    log_error "API ne démarre pas"
    docker compose -f "$COMPOSE_FILE" logs api --tail=50
    exit 1
fi

if ! wait_for_api_endpoint "Dashboard" "http://localhost:3000/api/system/health" 90; then
    log_error "Dashboard ne démarre pas"
    docker compose -f "$COMPOSE_FILE" logs dashboard --tail=50
    exit 1
fi

log_success "✓ Services validés"

# === PHASE 8: CONFIGURATION GOOGLE DRIVE (OPTIONNEL) - NOUVEAU GUIDE VISUEL ===

log_step "PHASE 8: Configuration Sauvegardes Google Drive (Optionnel)"

if prompt_yes_no "Configurer sauvegardes Google Drive ?" "n"; then
    # Vérifier ou installer rclone
    if ! cmd_exists rclone; then
        log_warn "rclone n'est pas installé"
        if prompt_yes_no "Installer rclone maintenant ?" "y"; then
            log_info "Installation de rclone..."
            if install_rclone; then
                log_success "✓ rclone installé avec succès"
            else
                log_error "Impossible d'installer rclone"
                log_info "Installation manuelle: https://rclone.org/install/"
                prompt_yes_no "Continuer sans sauvegardes ?" "y" && BACKUP_CONFIGURED="false"
            fi
        else
            log_warn "rclone non installé. Les sauvegardes Google Drive seront désactivées."
            BACKUP_CONFIGURED="false"
        fi
    fi

    # Configurer rclone si installé (NOUVEAU - GUIDE VISUEL HEADLESS)
    if cmd_exists rclone; then
        log_step "Configuration rclone Google Drive (Headless)"

        # AFFICHER LE CHEAT SHEET VISUEL (CRITIQUE POUR RPi4 SANS ÉCRAN)
        cat <<'EOF'

╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   📚 GUIDE VISUEL - CONFIGURATION RCLONE GOOGLE DRIVE (HEADLESS)         ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

⚠️  IMPORTANT: Raspberry Pi 4 sans écran - Configuration en ligne de commande

┌─ Étapes à suivre EXACTEMENT ─────────────────────────────────────────────┐

  1️⃣  New remote? → Tapez: n

  2️⃣  Name → Tapez EXACTEMENT: gdrive
      (Ce nom est utilisé par les scripts de sauvegarde)

  3️⃣  Storage → Cherchez "Google Drive" dans la liste
      - Option 18 (peut varier selon version) OU tapez: drive

  4️⃣  client_id → Laissez vide (Entrée)

  5️⃣  client_secret → Laissez vide (Entrée)

  6️⃣  Scope → Tapez: 1 (Full access to all files)

  7️⃣  service_account_file → Laissez vide (Entrée)

  8️⃣  Edit advanced config → Tapez: n

  9️⃣  Use web browser to automatically authenticate → Tapez: n ❌ CRUCIAL!
      (Répondre "y" planterait sur un serveur sans écran)

  🔟  AUTHENTIFICATION (Mode Headless):
      ┌────────────────────────────────────────────────────────────────────┐
      │ rclone va afficher une COMMANDE comme:                             │
      │                                                                     │
      │   rclone authorize "drive" "eyJzY29wZSI6ImRyaXZlIn0"              │
      │                                                                     │
      │ 📋 COPIEZ cette commande                                           │
      │ 💻 LANCEZ-LA sur votre PC/Mac (avec rclone installé)              │
      │ 🌐 Un navigateur s'ouvrira pour vous authentifier                 │
      │ ✅ Autorisez l'accès à Google Drive                               │
      │ 📝 Copiez le TOKEN résultat (config_token: {...})                 │
      │ 📥 COLLEZ le token dans ce terminal du RPi                        │
      └────────────────────────────────────────────────────────────────────┘

  1️⃣1️⃣  Configure as team drive → Tapez: n

  1️⃣2️⃣  Keep this "gdrive" remote → Tapez: y

  1️⃣3️⃣  Quit config → Tapez: q

└───────────────────────────────────────────────────────────────────────────┘

📚 Documentation complète: https://rclone.org/drive/

EOF

        echo ""
        log_warn "⏸️  Prenez le temps de LIRE le guide ci-dessus avant de continuer"
        pause_with_message "Appuyez sur Entrée quand vous êtes prêt à lancer 'rclone config'" 0

        # Lancer rclone config
        if rclone config; then
            # Vérifier que la configuration est valide
            if rclone listremotes | grep -q "gdrive"; then
                BACKUP_CONFIGURED="true"
                setup_state_set_config "backup_configured" "true"
                log_success "✓ Configuration rclone réussie - Remote 'gdrive' détecté"

                # Tester l'accès
                log_info "Test de l'accès à Google Drive..."
                if rclone lsd gdrive: >/dev/null 2>&1; then
                    log_success "✓ Connexion à Google Drive fonctionnelle"
                else
                    log_warn "⚠️  Connexion à Google Drive non testable (vérifiez manuellement avec: rclone lsd gdrive:)"
                fi
            else
                log_warn "⚠️  Remote 'gdrive' non détecté après configuration"
                log_info "Remotes disponibles: $(rclone listremotes | tr '\n' ', ' | sed 's/,$//')"
                log_warn "Les scripts de sauvegarde attendent un remote nommé 'gdrive'"
                BACKUP_CONFIGURED="false"
            fi
        else
            log_warn "Configuration rclone annulée"
            BACKUP_CONFIGURED="false"
        fi
    else
        BACKUP_CONFIGURED="false"
        log_warn "rclone non disponible, sauvegardes désactivées"
    fi
else
    log_info "Sauvegardes Google Drive non configurées (vous pouvez les ajouter plus tard)"
    BACKUP_CONFIGURED="false"
fi

# === AUDIT COMPLET FINAL (SÉCURITÉ, SERVICES, BDD, ROUTES) - NOUVEAU v5.0 ===

if declare -f run_full_audit &>/dev/null; then
    run_full_audit "$ENV_FILE" "$COMPOSE_FILE" "data" "$DOMAIN" || true
else
    log_warn "Audit final non disponible (fonction manquante)"
fi

# === RAPPORT FINAL ===

log_step "DÉPLOIEMENT TERMINÉ AVEC SUCCÈS"

# Meilleure détection de l'IP locale (compatible Linux/macOS)
LOCAL_IP=$(
    hostname -I 2>/dev/null | awk '{print $1}' ||
    ip addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '^127\.' | head -1 ||
    echo "127.0.0.1"
)
DASHBOARD_USER=$(grep "^DASHBOARD_USER=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "admin")
DASHBOARD_HASH=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "[non configuré]")

# Préparer l'affichage du mot de passe/hash (NOUVEAU - Affichage intelligent)
if [[ -n "${SETUP_PASSWORD_PLAINTEXT:-}" ]]; then
    # Afficher le mot de passe en clair UNIQUEMENT s'il vient d'être généré
    PASSWORD_DISPLAY="${BOLD}${RED}${SETUP_PASSWORD_PLAINTEXT}${NC}"
    HASH_DISPLAY="${GREEN}${DASHBOARD_HASH}${NC}"
    PASSWORD_NOTE="${BOLD}${GREEN}✓ Mot de passe défini lors de ce setup${NC}"
else
    # Sinon, afficher "Masqué" (sécurité)
    PASSWORD_DISPLAY="${YELLOW}[Masqué - déjà configuré]${NC}"
    HASH_DISPLAY="${YELLOW}[voir .env]${NC}"
    PASSWORD_NOTE=""
fi

cat <<EOF

${BOLD}${BLUE}┌─────────────────────────────────────────────────────────────────────────┐${NC}
${BOLD}${BLUE}│                    CONFIGURATION TERMINÉE AVEC SUCCÈS                  │${NC}
${BOLD}${BLUE}└─────────────────────────────────────────────────────────────────────────┘${NC}

  ${BOLD}🌐 Accès${NC}
  ├─ HTTPS externe     : ${GREEN}https://${DOMAIN}${NC}
  ├─ HTTP local        : http://${LOCAL_IP}:3000
  └─ API              : http://${LOCAL_IP}:8000

  ${BOLD}🔐 Authentification Dashboard${NC}
  ├─ Utilisateur       : ${GREEN}${DASHBOARD_USER}${NC}
  ├─ Mot de passe      : ${PASSWORD_DISPLAY}
  ├─ Hash (bcrypt)     : ${HASH_DISPLAY}
  └─ ${PASSWORD_NOTE}

  ${BOLD}📊 Infrastructure${NC}
  ├─ Domaine          : ${DOMAIN}
  ├─ IP locale        : ${LOCAL_IP}
  ├─ Conteneurs       : $(docker compose -f "$COMPOSE_FILE" ps --quiet 2>/dev/null | wc -l)
  ├─ HTTPS mode       : ${HTTPS_MODE}
  └─ Sauvegardes      : $([ "$BACKUP_CONFIGURED" == "true" ] && echo "${GREEN}Activées (gdrive)${NC}" || echo "${YELLOW}Non configurées${NC}")

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
  ├─ Passwords: docs/PASSWORD_MANAGEMENT_GUIDE.md
  ├─ Security: docs/SECURITY_AUDIT.md
  └─ État du setup: .setup.state

  ${BOLD}📋 Logs de cette installation${NC}
  └─ Fichier: ${CYAN}$(get_log_file)${NC}

  ${BOLD}🆘 En cas de problème de login${NC}
  ├─ Vérifiez le .env: grep DASHBOARD_PASSWORD .env
  ├─ Réinitialiser: ./scripts/manage_dashboard_password.sh
  └─ Consultez: docs/PASSWORD_MANAGEMENT_GUIDE.md

${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

✓ ${GREEN}Setup v5.0 (Super Orchestrateur) réussi${NC} - Accédez au dashboard!

EOF

# Afficher un rappel final avec les infos de connexion (UNIQUEMENT si mot de passe généré)
if [[ -n "${SETUP_PASSWORD_PLAINTEXT:-}" ]]; then
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}📝 IDENTIFIANTS DE CONNEXION DASHBOARD${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  URL                : ${GREEN}https://${DOMAIN}${NC}"
    echo -e "  Utilisateur        : ${BOLD}${DASHBOARD_USER}${NC}"
    echo -e "  Mot de passe       : ${BOLD}${RED}${SETUP_PASSWORD_PLAINTEXT}${NC}"
    echo ""
    echo -e "${YELLOW}💾 Conseils:${NC}"
    echo -e "  - Sauvegardez ces identifiants dans un gestionnaire de mots de passe"
    echo -e "  - La connexion est sécurisée par HTTPS"
    echo -e "  - Pour changer le mot de passe plus tard: ./scripts/manage_dashboard_password.sh"
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
fi

# Bannière de fin (NOUVEAU v5.0)
show_completion_banner "success" "Installation terminée avec succès 🎉"

exit 0
