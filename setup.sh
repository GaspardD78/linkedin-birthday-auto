#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO RPi4 - SUPER ORCHESTRATEUR v5.1
# ═══════════════════════════════════════════════════════════════════════════════
# Expert DevOps avec Architecture Modulaire, UX Immersive & Robustesse Maximale
# Cible: Raspberry Pi 4 (4GB RAM, SD 32GB, ARM64)
# Domaine: gaspardanoukolivier.freeboxos.fr (192.168.1.145)
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === INITIALISATION ===

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROJECT_ROOT="$SCRIPT_DIR"
export PROJECT_ROOT

# Sourcing logging IMMEDIATELY (avant tout autre chose)
# Fixes Issue #13: Logging redirection cassée en cas d'erreur précoce
if [[ -f "$SCRIPT_DIR/scripts/lib/logging.sh" ]]; then
    source "$SCRIPT_DIR/scripts/lib/logging.sh"
    setup_logging "logs"
else
    # Fallback si logging.sh manquant
    echo "ERROR: scripts/lib/logging.sh missing" >&2
    exit 1
fi

# === VERROU DE FICHIER (ÉVITER EXÉCUTIONS MULTIPLES) ===
# Fixes Issue #9: Race condition & timeout
# Fixes Critical #2: Atomic directory locking (mkdir) to avoid race conditions

readonly LOCK_DIR="/tmp/linkedin-bot-setup.lock"

cleanup_lock() {
    if [[ -d "$LOCK_DIR" ]]; then
        # On ne supprime que si c'est notre PID
        if [[ -f "$LOCK_DIR/pid" ]] && [[ "$(cat "$LOCK_DIR/pid" 2>/dev/null)" == "$$" ]]; then
            rm -rf "$LOCK_DIR" 2>/dev/null || true
        fi
    fi
}

acquire_lock() {
    # Retry loop (30s timeout)
    local retries=30
    while [[ $retries -gt 0 ]]; do
        if mkdir "$LOCK_DIR" 2>/dev/null; then
            echo $$ > "$LOCK_DIR/pid"
            trap cleanup_lock EXIT
            return 0
        fi

        # Check if stale lock
        local lock_pid
        if [[ -f "$LOCK_DIR/pid" ]]; then
            lock_pid=$(cat "$LOCK_DIR/pid" 2>/dev/null)
            if [[ -n "$lock_pid" ]] && ! kill -0 "$lock_pid" 2>/dev/null; then
                log_warn "Verrou stérile détecté (PID $lock_pid mort). Nettoyage..."
                rm -rf "$LOCK_DIR"
                continue
            fi
        fi

        sleep 1
        ((retries--))
    done

    log_error "Impossible d'acquérir le verrou après 30s."
    log_warn "Si aucune instance ne tourne: sudo rm -rf $LOCK_DIR"
    exit 1
}

acquire_lock

# === DOCKER COMMAND STANDARDIZATION ===
# Fixes Issue #4: Commande Docker Incohérente

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    DOCKER_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_CMD="docker-compose"
else
    # Fallback (sera détecté comme erreur dans les prerequisites)
    DOCKER_CMD="docker compose"
fi
export DOCKER_CMD

# === OPTIONS DE LIGNE DE COMMANDE ===

# Initialiser les flags à false par défaut
CHECK_ONLY=false
DRY_RUN=false
SKIP_VERIFY="${SKIP_VERIFY:-false}"
# Fix Major #1: Initialization of CONFIGURE_SYSTEM_DNS
CONFIGURE_SYSTEM_DNS="${CONFIGURE_SYSTEM_DNS:-true}"
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
source "$SCRIPT_DIR/scripts/lib/common.sh" || { log_error "Failed to load common.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/installers.sh" || { log_error "Failed to load installers.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/security.sh" || { log_error "Failed to load security.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/docker.sh" || { log_error "Failed to load docker.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/checks.sh" || { log_error "Failed to load checks.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/state.sh" || { log_error "Failed to load state.sh"; exit 1; }
source "$SCRIPT_DIR/scripts/lib/audit.sh" || { log_error "Failed to load audit.sh"; exit 1; }

# Vérifier la disponibilité de Python3 (requis par state.sh)
if ! cmd_exists python3; then
    log_error "Python3 est requis pour le state management"
    exit 1
fi

# === AFFICHER LA BANNIÈRE DE BIENVENUE (NOUVEAU v5.0) ===

show_welcome_banner "5.1" "LinkedIn Birthday Auto"

log_info "📋 Fichier de log: ${BOLD}$(get_log_file)${NC}"
echo ""

# === VARIABLES DE CONFIGURATION ===

readonly COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
readonly ENV_FILE="$SCRIPT_DIR/.env"
readonly ENV_TEMPLATE="$SCRIPT_DIR/.env.pi4.example"
readonly NGINX_TEMPLATE_HTTPS="$SCRIPT_DIR/deployment/nginx/linkedin-bot-https.conf.template"
readonly NGINX_TEMPLATE_LAN="$SCRIPT_DIR/deployment/nginx/linkedin-bot-lan.conf.template"
readonly NGINX_TEMPLATE_ACME_BOOTSTRAP="$SCRIPT_DIR/deployment/nginx/linkedin-bot-acme-bootstrap.conf.template"
readonly NGINX_CONFIG="$SCRIPT_DIR/deployment/nginx/linkedin-bot.conf"
readonly DOMAIN_DEFAULT="gaspardanoukolivier.freeboxos.fr"
# LOCAL_IP will be determined dynamically in Phase 0

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

    cleanup_lock
    return $exit_code
}

trap setup_cleanup EXIT

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SETUP FLOW
# ═══════════════════════════════════════════════════════════════════════════════

# === PHASE 0: INITIALIZATION & NETWORK CHECKS (NOUVEAU v5.0) ===

log_step "PHASE 0: Vérifications Préliminaires"

# Détection de l'IP locale (Phase 0)
LOCAL_IP=$(
    hostname -I 2>/dev/null | awk '{print $1}' ||
    ip addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '^127\.' | head -1 ||
    echo "127.0.0.1"
)
log_info "IP Locale détectée: $LOCAL_IP"

# Vérification de l'espace disque disponible (CRITIQUE pour RPi4 SD card)
log_info "Vérification de l'espace disque..."
AVAILABLE_SPACE_GB=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
REQUIRED_SPACE_GB=5  # Minimum requis pour les images Docker

if [[ "$AVAILABLE_SPACE_GB" =~ ^[0-9]+$ ]] && [[ "$AVAILABLE_SPACE_GB" -lt "$REQUIRED_SPACE_GB" ]]; then
    log_error "Espace disque insuffisant: ${AVAILABLE_SPACE_GB}Go disponible (minimum ${REQUIRED_SPACE_GB}Go requis)"
    log_error "Les images Docker peuvent nécessiter jusqu'à 3-4 Go d'espace"
    log_warn "Solutions:"
    log_warn "  1. Libérer de l'espace: sudo apt clean && docker system prune -a"
    log_warn "  2. Utiliser un stockage externe (USB/SSD)"
    exit 1
else
    log_success "✓ Espace disque suffisant: ${AVAILABLE_SPACE_GB}Go disponible"
fi

# Détection architecture et optimisations RPi4
ARCH=$(uname -m)
if [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "armv7l" ]]; then
    log_info "Architecture ARM détectée ($ARCH) - Raspberry Pi"

    # Vérifier la RAM disponible
    TOTAL_RAM_MB=$(free -m | awk '/^Mem:/ {print $2}')
    AVAILABLE_RAM_MB=$(free -m | awk '/^Mem:/ {print $7}')

    log_info "RAM: ${TOTAL_RAM_MB}Mo total, ${AVAILABLE_RAM_MB}Mo disponible"

    # Avertissement si < 1Go disponible
    if [[ "$AVAILABLE_RAM_MB" -lt 1024 ]]; then
        log_warn "⚠️  Mémoire disponible faible (< 1Go)"
        log_warn "    Recommandation: Fermez les applications inutiles avant de continuer"
        if ! prompt_yes_no "Continuer malgré la RAM faible ?" "y"; then
            exit 1
        fi
    fi

    # Vérifier le type de stockage (SD card vs USB/SSD)
    ROOT_DEVICE=$(df "$SCRIPT_DIR" | awk 'NR==2 {print $1}')
    if [[ "$ROOT_DEVICE" == *"mmcblk"* ]]; then
        log_warn "⚠️  Installation sur carte SD détectée ($ROOT_DEVICE)"
        log_warn "    Les SD cards ont une durée de vie limitée avec Docker"
        log_warn "    Recommandation: Utilisez un SSD/USB externe via USB 3.0 pour la production"
        if ! prompt_yes_no "Continuer sur SD card ?" "y"; then
            exit 1
        fi
    elif [[ "$ROOT_DEVICE" == *"sd"* ]] || [[ "$ROOT_DEVICE" == *"nvme"* ]]; then
        log_success "✓ Stockage externe USB/SSD détecté ($ROOT_DEVICE)"
        log_info "  Excellente durabilité pour Docker en production"
    else
        log_info "Stockage détecté: $ROOT_DEVICE"
    fi
fi

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

# Ports: Redis(6379), API(8000), Dashboard(3000), Nginx(80,443)
for port in 6379 8000 3000 80 443; do
    if ! check_port_available $port; then
        log_warn "Port $port occupé. Si c'est par nos conteneurs, c'est OK."
        # On ne bloque pas strictement car docker compose restart gérera ça,
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

    # Vérifier si dhcpcd est actif
    if command -v dhcpcd >/dev/null 2>&1 && systemctl is-active --quiet dhcpcd; then
        # Détecter l'interface principale (eth0 ou wlan0)
        PRIMARY_INTERFACE=$(ip route show default | awk '/default/ {print $5}' | head -1)

        # Vérif configuration existante (idempotence)
        if grep -q "static domain_name_servers=8.8.8.8" /etc/dhcpcd.conf 2>/dev/null; then
            echo "✓ [OK] DNS déjà configuré (Google DNS)"
        else
            echo "🔧 Configuration DNS permanent pour interface: ${PRIMARY_INTERFACE:-auto}..."

            # Configuration adaptée pour WiFi (préserve DNS local pour .freeboxos.fr)
            if [[ "${PRIMARY_INTERFACE}" == wlan* ]]; then
                # Détecter le SSID WiFi pour feedback utilisateur
                WIFI_SSID=$(iwgetid -r 2>/dev/null || echo "inconnu")
                echo "ℹ [WiFi] Réseau détecté: ${WIFI_SSID} (interface: ${PRIMARY_INTERFACE})"
                echo "ℹ [WiFi] Configuration DNS hybride (local + publics)..."
                # Détecter le DNS de la box (généralement 192.168.1.254 pour Freebox)
                LOCAL_GATEWAY=$(ip route show default | awk '/default/ {print $3}' | head -1)
                sudo tee -a /etc/dhcpcd.conf > /dev/null << EOF
# DNS stable RPi4 WiFi - anti-timeout Docker pull (LinkedIn-bot)
# Préserve DNS local pour domaines .freeboxos.fr + fallback publics
interface ${PRIMARY_INTERFACE}
static domain_name_servers=${LOCAL_GATEWAY:-192.168.1.254} 8.8.8.8 1.1.1.1
EOF
            else
                # Configuration Ethernet standard
                sudo tee -a /etc/dhcpcd.conf > /dev/null << 'EOF'
# DNS stable RPi4 - anti-timeout Docker pull (LinkedIn-bot)
static domain_name_servers=8.8.8.8 8.8.4.4 1.1.1.1
EOF
            fi

            # Redémarrage dhcpcd en douceur (pas de coupure réseau brutale)
            echo "🔄 Rechargement configuration réseau..."
            sudo killall -HUP dhcpcd 2>/dev/null || sudo dhcpcd -n || echo "⚠️ Rechargement dhcpcd échoué"
            sleep 2
        fi
    else
        echo "ℹ [INFO] dhcpcd non détecté ou inactif. Modification ignorée."
    fi
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

#===============================================================================
# PHASE 1.6 : DNS Docker OPTIMISÉ (Local + fallback public)
#===============================================================================
log_step "PHASE 1.6: Optimisation DNS Docker (Freebox/Local + Publics)"

# 1. Détection DNS Local
detect_dns_local() {
    local dns=""
    # Méthode A: Gateway par défaut (Robust)
    if command -v ip >/dev/null; then
        dns=$(ip route show default | awk '/default/ {print $3}' | head -1)
    fi
    # Méthode B: resolv.conf (si A échoue ou vide)
    if [[ -z "$dns" ]] && [[ -f /etc/resolv.conf ]]; then
        dns=$(awk '/^nameserver/ {print $2; exit}' /etc/resolv.conf)
    fi
    # Méthode C: DHCP leases (Raspberry Pi specific)
    if [[ -z "$dns" ]]; then
         dns=$(grep -h 'routers=' /var/lib/dhcpcd/*.lease 2>/dev/null | head -1 | cut -d= -f2 | tr -d "'\"")
    fi

    # Validation format IP (Plus stricte - 0-255 range check)
    # Fix Major #8: Regex Validation Incohérente -> Python check is safer
    if [[ "$dns" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        # Check octet range using python since we have it
        if python3 -c "import sys; ip=sys.argv[1]; all(0<=int(x)<=255 for x in ip.split('.')) or sys.exit(1)" "$dns" 2>/dev/null; then
             echo "$dns"
        else
             echo ""
             return 1
        fi
    else
        echo ""
        return 1
    fi
}

DNS_LOCAL=$(detect_dns_local)
DOMAIN_TO_TEST="gaspardanoukolivier.freeboxos.fr"
DNS_VALIDATED=false
DNS_CONFIGURED_PHASE_1_6=false

if [[ -n "$DNS_LOCAL" ]]; then
    log_info "DNS Local candidat détecté: $DNS_LOCAL"
    # 2. Vérification de la résolution
    if command -v nslookup >/dev/null; then
        if nslookup "$DOMAIN_TO_TEST" "$DNS_LOCAL" >/dev/null 2>&1; then
             log_success "✓ DNS Local validé: $DNS_LOCAL résout $DOMAIN_TO_TEST"
             DNS_VALIDATED=true
        else
             log_warn "DNS Local $DNS_LOCAL ne résout pas $DOMAIN_TO_TEST. Fallback publics."
        fi
    else
        log_warn "nslookup absent, validation impossible. Utilisation prudente."
        DNS_VALIDATED=true
    fi
else
    log_warn "Aucun DNS local détecté. Utilisation des DNS publics uniquement."
fi

# 3. Création daemon.json Idempotent
DOCKER_DAEMON_FILE="/etc/docker/daemon.json"
if [[ "$DNS_VALIDATED" == "true" ]]; then
    # Validation stricte de DNS_LOCAL avant insertion dans JSON
    if [[ ! "$DNS_LOCAL" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        log_error "Format d'adresse IP invalide: $DNS_LOCAL. Fallback DNS publics uniquement."
        DNS_VALIDATED=false
    else
        # Validation supplémentaire: chaque octet 0-255
        if ! python3 -c "import sys; ip='$DNS_LOCAL'; parts=ip.split('.'); sys.exit(0 if len(parts)==4 and all(0<=int(p)<=255 for p in parts) else 1)" 2>/dev/null; then
            log_error "Adresse IP hors limites: $DNS_LOCAL. Fallback DNS publics uniquement."
            DNS_VALIDATED=false
        fi
    fi
fi

if [[ "$DNS_VALIDATED" == "true" ]]; then
    DNS_LIST="\"$DNS_LOCAL\", \"1.1.1.1\", \"8.8.8.8\""
    LOG_MSG="DNS Docker: $DNS_LOCAL (auto-détecté) + publics"
else
    DNS_LIST="\"1.1.1.1\", \"8.8.8.8\""
    LOG_MSG="DNS Docker: Publics uniquement (fallback)"
fi

# Vérification idempotence
SHOULD_WRITE=true
if [[ -f "$DOCKER_DAEMON_FILE" ]]; then
    CURRENT_CONTENT=$(sudo cat "$DOCKER_DAEMON_FILE")
    # Si le fichier contient déjà notre DNS local (si valide) ou juste les publics
    if [[ "$DNS_VALIDATED" == "true" ]] && [[ "$CURRENT_CONTENT" == *"$DNS_LOCAL"* ]]; then
        SHOULD_WRITE=false
    elif [[ "$DNS_VALIDATED" == "false" ]] && [[ "$CURRENT_CONTENT" == *"1.1.1.1"* ]]; then
        # On assume que si 1.1.1.1 est là, c'est bon pour le fallback
        SHOULD_WRITE=false
    fi
fi

if [[ "$SHOULD_WRITE" == "true" ]]; then
    log_info "Configuration de $DOCKER_DAEMON_FILE..."

    # Création du répertoire si nécessaire
    sudo mkdir -p /etc/docker

    # Fix Major #4: JSON Généré Manuellement -> Utiliser Python pour générer du JSON valide
    # Construction du JSON via Python en passant les DNS comme arguments séparés
    if [[ "$DNS_VALIDATED" == "true" ]]; then
        JSON_CONTENT=$(python3 -c "import json, sys; print(json.dumps({'dns': ['$DNS_LOCAL', '1.1.1.1', '8.8.8.8'], 'dns-opts': ['timeout:2', 'attempts:3']}, indent=2))")
    else
        JSON_CONTENT=$(python3 -c "import json; print(json.dumps({'dns': ['1.1.1.1', '8.8.8.8'], 'dns-opts': ['timeout:2', 'attempts:3']}, indent=2))")
    fi

    if [[ $? -eq 0 && -n "$JSON_CONTENT" ]]; then
        echo "$JSON_CONTENT" | sudo tee "$DOCKER_DAEMON_FILE" > /dev/null
    else
        log_error "Impossible de générer le JSON pour daemon.json."
        exit 1
    fi

    log_info "Rechargement de la configuration Docker..."
    # Utiliser reload au lieu de restart pour éviter de tuer les conteneurs
    if systemctl is-active --quiet docker; then
        # Vérifier qu'aucune opération critique n'est en cours
        if ! docker ps --quiet >/dev/null 2>&1 || [[ $(docker ps --quiet | wc -l) -eq 0 ]]; then
            sudo systemctl restart docker || log_warn "Redémarrage Docker échoué"
        else
            log_warn "Conteneurs actifs détectés - Le redémarrage sera fait au prochain démarrage du système"
            log_info "Vous pouvez redémarrer manuellement: sudo systemctl restart docker"
        fi
    else
        log_info "Docker non actif, configuration sera appliquée au prochain démarrage"
    fi
    DNS_CONFIGURED_PHASE_1_6=true
else
    log_info "Configuration DNS Docker déjà à jour. Skip."
    DNS_CONFIGURED_PHASE_1_6=true
fi

# 5. Test (si Docker dispo)
if command -v docker >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    if docker run --rm busybox nslookup "$DOMAIN_TO_TEST" >/dev/null 2>&1; then
        log_success "✓ TEST RÉUSSI: Résolution conteneur OK pour $DOMAIN_TO_TEST"
    else
        # Test fallback internet
        if docker run --rm busybox nslookup google.com >/dev/null 2>&1; then
             log_warn "⚠ Résolution locale échouée, mais internet OK."
        fi
    fi
fi
log_success "✓ $LOG_MSG"


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
if [[ "${DNS_CONFIGURED_PHASE_1_6:-false}" == "true" ]]; then
    log_info "DNS déjà configuré en Phase 1.6 (Optimisé Local). Saut du fix générique."
elif [[ -f "$SCRIPT_DIR/scripts/lib/docker_dns_fix.sh" ]]; then
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

# Optimisations RPi4 spécifiques (4Go RAM)
if [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "armv7l" ]]; then
    log_info "Application des optimisations RPi4..."

    # Limiter la mémoire par défaut des conteneurs (éviter OOM sur 4Go RAM)
    DOCKER_DAEMON_FILE="/etc/docker/daemon.json"
    if [[ -f "$DOCKER_DAEMON_FILE" ]]; then
        # Ajouter la limitation mémoire par défaut si pas déjà présente
        if ! grep -q "default-ulimits" "$DOCKER_DAEMON_FILE" 2>/dev/null; then
            log_info "  → Configuration des limites mémoire par conteneur (1Go max par défaut)..."
            # Backup du fichier actuel
            sudo cp "$DOCKER_DAEMON_FILE" "${DOCKER_DAEMON_FILE}.bak"

            # Merger avec les paramètres existants via Python (safe JSON merge)
            MERGED_JSON=$(python3 -c "
import json, sys
try:
    with open('$DOCKER_DAEMON_FILE', 'r') as f:
        config = json.load(f)
except:
    config = {}

# Ajouter les limites par défaut pour RPi4
config['default-ulimits'] = {
    'memlock': {'Hard': 1073741824, 'Name': 'memlock', 'Soft': 1073741824}
}

# Log driver optimisé pour SD card (moins d'écritures)
config['log-driver'] = 'json-file'
config['log-opts'] = {
    'max-size': '10m',
    'max-file': '3'
}

print(json.dumps(config, indent=2))
" 2>/dev/null)

            if [[ $? -eq 0 && -n "$MERGED_JSON" ]]; then
                echo "$MERGED_JSON" | sudo tee "$DOCKER_DAEMON_FILE" > /dev/null
                log_success "✓ Limites mémoire configurées (1Go par conteneur)"

                # Redémarrer Docker pour appliquer
                if systemctl is-active --quiet docker && [[ $(docker ps --quiet | wc -l) -eq 0 ]]; then
                    sudo systemctl restart docker
                    log_success "✓ Configuration Docker appliquée"
                else
                    log_info "  → Redémarrez Docker manuellement: sudo systemctl restart docker"
                fi
            else
                log_warn "Impossible de configurer les limites mémoire (fichier JSON invalide ?)"
            fi
        else
            log_info "  → Limites mémoire déjà configurées"
        fi
    fi
fi

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
    if [[ ! -f "$ENV_TEMPLATE" ]]; then
        log_error "Template .env manquant: $ENV_TEMPLATE"
        exit 1
    fi
    cp "$ENV_TEMPLATE" "$ENV_FILE" || {
        log_error "Impossible de copier le template"
        exit 1
    }
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
        # Fix Critical #1: Ne jamais exporter le mot de passe en variable d'environnement
        SETUP_PASSWORD_PLAINTEXT="$PASSWORD"
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
    if [[ -z "$NEW_JWT" ]]; then
        log_error "JWT généré vide"
        exit 1
    fi
    ESCAPED_JWT=$(escape_sed_string "$NEW_JWT")
    if [[ -z "$ESCAPED_JWT" ]]; then
        log_error "JWT échappé vide"
        exit 1
    fi
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${ESCAPED_JWT}|" "$ENV_FILE"
    log_success "✓ JWT_SECRET généré"
fi

# === PHASE 4.5: PRÉPARATION VOLUMES & PERMISSIONS ===

log_step "PHASE 4.5: Permissions & Volumes"

# Créer les répertoires nécessaires
mkdir -p data logs config certbot/conf certbot/www certbot/logs certbot/work deployment/nginx

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
        # Fixes Issue #26: Chown fail silently -> Now Explicit Error
        if ! sudo chown -R 1000:1000 data logs config certbot 2>/dev/null; then
             log_error "Impossible de changer le propriétaire vers 1000:1000"
             log_error "L'utilisateur 1000 (node/python) ne pourra pas écrire."
             log_error "Exécutez: sudo chown -R 1000:1000 data logs config certbot"
             exit 1
        fi
        sudo chmod -R 775 data logs config 2>/dev/null || {
            log_error "Impossible de modifier les permissions"
            return 1
        }
    else
        if ! chown -R 1000:1000 data logs config certbot 2>/dev/null; then
             log_warn "Impossible de changer le propriétaire vers 1000:1000"
        fi
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

# ══════════════════════════════════════════════════════════════════════════════
# STRATÉGIE "ZERO SELF-SIGNED" (v5.2)
# ══════════════════════════════════════════════════════════════════════════════
# 1. Mode Let's Encrypt: Utiliser config HTTP-only (ACME bootstrap) pour démarrer
#    Nginx SANS certificat SSL, puis obtenir le vrai certificat.
# 2. Mode "existing": Certificats déjà fournis, utiliser config HTTPS directement.
# 3. Mode "manual": Config HTTP-only, l'utilisateur configurera plus tard.
#
# AUCUN certificat auto-signé n'est généré. Si Let's Encrypt échoue,
# le script s'arrête avec une erreur claire.
# ══════════════════════════════════════════════════════════════════════════════

# Variable pour suivre si on doit passer en HTTPS après Let's Encrypt
PENDING_HTTPS_SWITCH=false

# Vérifier si des certificats valides existent déjà
EXISTING_CERT="$CERT_DIR/fullchain.pem"
VALID_CERT_EXISTS=false

if [[ -f "$EXISTING_CERT" ]]; then
    # Vérifier si le certificat existant est valide (non auto-signé et non expiré)
    subject=$(openssl x509 -noout -subject -in "$EXISTING_CERT" 2>/dev/null || echo "")
    issuer=$(openssl x509 -noout -issuer -in "$EXISTING_CERT" 2>/dev/null || echo "")

    if [[ -z "$subject" ]]; then
        log_warn "⚠️  Certificat existant détecté mais invalide (format incorrect)"
    else
        # Extract CN (Common Name) from subject and issuer for comparison
        subject_cn=$(echo "$subject" | sed 's/.*CN\s*=\s*//' | cut -d',' -f1 | tr -d ' ')
        issuer_cn=$(echo "$issuer" | sed 's/.*CN\s*=\s*//' | cut -d',' -f1 | tr -d ' ')

        # Check if it's a Let's Encrypt certificate (proper validation)
        if [[ "$issuer" =~ "Let's Encrypt" ]] || [[ "$issuer_cn" =~ ^(R3|R10|R11|E1|E2)$ ]]; then
            # Valid Let's Encrypt certificate
            if openssl x509 -checkend 604800 -noout -in "$EXISTING_CERT" 2>/dev/null; then
                log_success "✓ Certificat Let's Encrypt valide détecté (non expiré)"
                VALID_CERT_EXISTS=true
            else
                log_warn "⚠️  Certificat Let's Encrypt existant mais expiré ou proche de l'expiration"
                log_info "    Un nouveau certificat sera obtenu en Phase 6.5"
            fi
        elif [[ "$subject_cn" == "$issuer_cn" ]] || [[ "$subject" == "$issuer" ]]; then
            # Self-signed certificate
            log_warn "⚠️  Certificat AUTO-SIGNÉ détecté - sera ignoré"
            log_warn "    Issuer CN: $issuer_cn (même que le sujet)"
            log_warn "    Les certificats auto-signés causent des alertes de sécurité"
            log_info "    Un nouveau certificat Let's Encrypt sera obtenu en Phase 6.5"
            # Supprimer le certificat auto-signé pour forcer le mode ACME bootstrap
            rm -f "$EXISTING_CERT" "$CERT_DIR/privkey.pem" 2>/dev/null || true
        else
            # Certificate from another CA
            if openssl x509 -checkend 604800 -noout -in "$EXISTING_CERT" 2>/dev/null; then
                log_success "✓ Certificat valide détecté (émis par CA: $issuer_cn, non expiré)"
                VALID_CERT_EXISTS=true
            else
                log_warn "⚠️  Certificat existant mais expiré ou proche de l'expiration"
                log_info "    Un nouveau certificat sera obtenu en Phase 6.5"
            fi
        fi
    fi
fi

# Sélectionner le template nginx approprié selon le mode et l'état des certificats
case "$HTTPS_MODE" in
    "letsencrypt")
        if [[ "$VALID_CERT_EXISTS" == "true" ]]; then
            # Certificat valide existe déjà, utiliser config HTTPS directement
            NGINX_TEMPLATE="$NGINX_TEMPLATE_HTTPS"
            log_info "Utilisation du template Nginx: MODE HTTPS (certificat existant valide)"
        else
            # Pas de certificat valide, utiliser config ACME bootstrap (HTTP-only)
            NGINX_TEMPLATE="$NGINX_TEMPLATE_ACME_BOOTSTRAP"
            PENDING_HTTPS_SWITCH=true
            log_info "Utilisation du template Nginx: MODE ACME BOOTSTRAP (HTTP-only)"
            log_info "  → Le certificat Let's Encrypt sera obtenu en Phase 6.5"
            log_info "  → La config passera automatiquement en HTTPS après obtention"
        fi
        ;;
    "existing")
        if [[ "$VALID_CERT_EXISTS" == "true" ]]; then
            NGINX_TEMPLATE="$NGINX_TEMPLATE_HTTPS"
            log_info "Utilisation du template Nginx: MODE HTTPS (certificats importés)"
        else
            log_error "Mode 'existing' sélectionné mais aucun certificat valide trouvé"
            log_error "Veuillez importer des certificats valides dans: $CERT_DIR/"
            exit 1
        fi
        ;;
    "lan"|"manual")
        NGINX_TEMPLATE="$NGINX_TEMPLATE_LAN"
        log_info "Utilisation du template Nginx: MODE LAN/MANUEL (HTTP only)"
        ;;
    *)
        log_error "Mode HTTPS inconnu: $HTTPS_MODE"
        exit 1
        ;;
esac

# Créer le répertoire certbot/www pour les challenges ACME
mkdir -p "$SCRIPT_DIR/certbot/www"
chown -R 1000:1000 "$SCRIPT_DIR/certbot" 2>/dev/null || true

# Générer la configuration nginx
if [[ -f "$NGINX_TEMPLATE" ]]; then
    export DOMAIN
    if ! envsubst '${DOMAIN}' < "$NGINX_TEMPLATE" > "$NGINX_CONFIG"; then
        log_error "Impossible de générer config Nginx"
        exit 1
    fi
    chmod 644 "$NGINX_CONFIG"

    # Fix: Remove www subdomain for freeboxos.fr (not supported)
    if [[ "$DOMAIN" == *".freeboxos.fr" ]]; then
        sed -i "s/ www\.${DOMAIN}//g" "$NGINX_CONFIG"
        log_info "  → www subdomain removed (freeboxos.fr limitation)"
    fi

    log_success "✓ Configuration Nginx générée"
else
    log_error "Template Nginx introuvable: $NGINX_TEMPLATE"
    exit 1
fi

# Exporter la variable pour la Phase 6.5
export PENDING_HTTPS_SWITCH

# Vérifier que la configuration Nginx est valide avant de continuer
log_info "Validation de la configuration Nginx..."
if command -v nginx >/dev/null 2>&1; then
    # Si nginx est installé sur l'hôte, on peut tester la config localement
    if nginx -t -c "$NGINX_CONFIG" 2>/dev/null; then
        log_success "✓ Configuration Nginx valide (test local)"
    else
        log_warn "⚠️  Test local Nginx échoué, sera vérifié dans le conteneur après démarrage"
    fi
else
    log_info "  (nginx non installé sur l'hôte, validation dans le conteneur après démarrage)"
fi

# === PHASE 5.3: CONFIGURATION CRON RENOUVELLEMENT SSL ===

if [[ "$HTTPS_MODE" == "letsencrypt" ]]; then
    log_step "PHASE 5.3: Configuration Renouvellement SSL Automatique"

    if prompt_yes_no "Configurer le renouvellement automatique des certificats SSL (cron) ?" "y"; then
        # Vérifier si le cron job existe déjà
        CRON_JOB="0 3 * * * $PROJECT_ROOT/scripts/renew_certificates.sh >> /var/log/certbot-renew.log 2>&1"
        CRON_SIGNATURE="# LinkedIn Bot - SSL Auto-Renew"

        # Vérifier idempotence stricte via signature unique
        if crontab -l 2>/dev/null | grep -qF "$CRON_SIGNATURE"; then
            log_info "✓ Cron job SSL déjà configuré"
        else
            log_info "Ajout du cron job pour le renouvellement SSL..."

            # Créer le fichier de log si nécessaire
            sudo touch /var/log/certbot-renew.log 2>/dev/null || true
            sudo chown "$(whoami):$(whoami)" /var/log/certbot-renew.log 2>/dev/null || true

            # Ajouter au crontab avec signature
            (crontab -l 2>/dev/null || true; echo "$CRON_SIGNATURE"; echo "$CRON_JOB") | crontab -

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

log_step "PHASE 6: Déploiement Docker (Mode Agressif)"

# Demander pour le monitoring (DÉSACTIVÉ - Grafana retiré)
MONITORING_ENABLED="false"
setup_state_set_config "monitoring_enabled" "false"

# Initialiser la barre de progression pour la phase 6
# 6 étapes : Env, Config, Pull, Start, Check, Prune
progress_init "Déploiement Docker" 6

# Étape 1: Validation de l'environnement
progress_step "Validation de l'environnement"
if ! "$SCRIPT_DIR/scripts/validate_env.sh"; then
    log_warn "Environnement invalide, tentative de correction automatique..."
    if ! "$SCRIPT_DIR/scripts/validate_env.sh" --fix; then
        progress_fail "Environnement invalide (Fix échoué)"
        progress_end
        log_error "Validation de l'environnement échouée (.env / API_KEY)"
        exit 1
    fi
    log_success "Environnement corrigé automatiquement"
fi
progress_done "Environnement valide"

# Étape 2: Validation docker-compose
progress_step "Validation du fichier docker-compose"
if ! docker_compose_validate "$COMPOSE_FILE"; then
    progress_fail "Fichier docker-compose invalide"
    progress_end
    log_error "Docker-compose validation échouée"
    exit 1
fi
progress_done "Configuration valide"

# Étape 3: Pull des images Docker (optimisé v5.0)
progress_step "Téléchargement des images Docker"

if ! docker_pull_with_retry "$COMPOSE_FILE"; then
    progress_fail "Impossible de télécharger les images"
    progress_end
    log_error "Pull images échoué"
    exit 1
fi

# Vérifier l'espace disque après pull (critique pour RPi4 avec USB limité)
SPACE_AFTER=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
if [[ "$SPACE_AFTER" =~ ^[0-9]+$ ]] && [[ "$SPACE_AFTER" -lt 2 ]]; then
    progress_fail "Espace disque critique après pull: ${SPACE_AFTER}GB"
    progress_end
    log_error "Moins de 2GB disponible. Libérez de l'espace avant de continuer."
    log_info "Commandes utiles: docker system prune -a"
    exit 1
fi
log_info "Espace disque restant: ${SPACE_AFTER}GB"
progress_done "Images téléchargées"

# Étape 4: Démarrage des conteneurs (Force Recreate)
progress_step "Démarrage des conteneurs (--force-recreate)"

# Get list of startable services (exclude failed pulls)
STARTABLE_SERVICES=$(docker_get_startable_services "$COMPOSE_FILE")

if [[ -z "$STARTABLE_SERVICES" ]]; then
    progress_fail "Aucun service démarrable"
    progress_end
    log_error "Aucun service ne peut être démarré (toutes les images ont échoué)"
    exit 1
fi

# Count services
STARTABLE_COUNT=$(echo "$STARTABLE_SERVICES" | wc -w)
TOTAL_SERVICES=$(docker compose -f "$COMPOSE_FILE" config --services 2>/dev/null | wc -l)

if [[ $STARTABLE_COUNT -lt $TOTAL_SERVICES ]]; then
    SKIPPED_COUNT=$((TOTAL_SERVICES - STARTABLE_COUNT))
    log_warn "  ⚠ $SKIPPED_COUNT service(s) ignoré(s) (images manquantes)"
fi

# Start only services with available images
# USING DOCKER_CMD (Consistent)
if ! $DOCKER_CMD -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans $STARTABLE_SERVICES >/dev/null 2>&1; then
    progress_fail "Échec du démarrage"
    progress_end
    log_error "Démarrage des conteneurs échoué"
    exit 1
fi
progress_done "Conteneurs démarrés ($STARTABLE_COUNT/$TOTAL_SERVICES)"

# Étape 5: Vérification post-démarrage
progress_step "Vérification des conteneurs"
sleep 5 # Délai accru pour stabilisation
RUNNING_CONTAINERS=$($DOCKER_CMD -f "$COMPOSE_FILE" ps --status running --quiet 2>/dev/null | wc -l)
TOTAL_CONTAINERS=$($DOCKER_CMD -f "$COMPOSE_FILE" ps --quiet 2>/dev/null | wc -l)

# Raspberry Pi 4 specific: Check for failed critical services
if [[ "$(uname -m)" == "aarch64" ]] || [[ "$(uname -m)" == "armv7l" ]]; then
    CRITICAL_SERVICES=("nginx" "api" "dashboard")
    for svc in "${CRITICAL_SERVICES[@]}"; do
        if ! $DOCKER_CMD -f "$COMPOSE_FILE" ps "$svc" 2>/dev/null | grep -q "Up"; then
            log_warn "⚠️  Service critique $svc non démarré (ARM64/Pi4)"
            log_info "    Tentative de redémarrage..."
            $DOCKER_CMD -f "$COMPOSE_FILE" restart "$svc" 2>/dev/null || true
            sleep 3
        fi
    done
    RUNNING_CONTAINERS=$($DOCKER_CMD -f "$COMPOSE_FILE" ps --status running --quiet 2>/dev/null | wc -l)
fi

progress_done "${RUNNING_CONTAINERS}/${TOTAL_CONTAINERS} conteneurs actifs"

# Vérification spéciale: Nginx doit être prêt avant la phase Let's Encrypt
log_info "Vérification que Nginx est prêt pour ACME challenge..."
NGINX_READY=false
for i in {1..10}; do
    if $DOCKER_CMD -f "$COMPOSE_FILE" exec -T nginx nginx -t 2>/dev/null; then
        NGINX_READY=true
        log_success "✓ Nginx opérationnel et configuration valide"
        break
    fi
    log_warn "  Tentative $i/10: Nginx pas encore prêt, attente 2s..."
    sleep 2
done

if [[ "$NGINX_READY" != "true" ]]; then
    log_warn "⚠️  Nginx pas complètement prêt, mais on continue..."
    log_info "Les logs Nginx: $DOCKER_CMD -f $COMPOSE_FILE logs nginx --tail=20"
fi

# Étape 6: Nettoyage final
progress_step "Nettoyage images obsolètes"
docker image prune -f >/dev/null 2>&1 || true
progress_done "Espace disque optimisé"

progress_end

# === PHASE 6.5: POST-PROVISIONING SSL (Let's Encrypt automatique) ===

if [[ "$HTTPS_MODE" == "letsencrypt" ]]; then
    log_step "PHASE 6.5: Obtention des Certificats Let's Encrypt"

    LETSENCRYPT_SCRIPT="./scripts/setup_letsencrypt.sh"

    # Vérifier que le script existe et est exécutable
    if [[ ! -f "$LETSENCRYPT_SCRIPT" ]]; then
        log_error "Script Let's Encrypt introuvable: $LETSENCRYPT_SCRIPT"
        log_error "Impossible de continuer sans certificat SSL valide."
        exit 1
    fi

    if [[ ! -x "$LETSENCRYPT_SCRIPT" ]]; then
        log_warn "Script Let's Encrypt non exécutable, correction..."
        chmod +x "$LETSENCRYPT_SCRIPT" || {
            log_error "Impossible de rendre le script exécutable"
            exit 1
        }
    fi

    # Exécuter le script pour obtenir le certificat
    log_info "Tentative d'obtention du certificat Let's Encrypt..."
    log_info "Cette opération peut prendre jusqu'à 2 minutes..."

    if "$LETSENCRYPT_SCRIPT"; then
        log_success "✓ Certificat Let's Encrypt obtenu avec succès"

        # ══════════════════════════════════════════════════════════════════
        # VÉRIFICATION STRICTE: Le certificat DOIT être émis par Let's Encrypt
        # ══════════════════════════════════════════════════════════════════
        FINAL_CERT="$CERT_DIR/fullchain.pem"
        if [[ -f "$FINAL_CERT" ]]; then
            final_subject=$(openssl x509 -noout -subject -in "$FINAL_CERT" 2>/dev/null || echo "")
            final_issuer=$(openssl x509 -noout -issuer -in "$FINAL_CERT" 2>/dev/null || echo "")

            # Extract CN (Common Name) for precise validation
            cert_cn=$(echo "$final_subject" | sed 's/.*CN\s*=\s*//' | cut -d',' -f1 | tr -d ' ')
            cert_issuer_cn=$(echo "$final_issuer" | sed 's/.*CN\s*=\s*//' | cut -d',' -f1 | tr -d ' ')
            cert_expiry=$(openssl x509 -noout -enddate -in "$FINAL_CERT" 2>/dev/null | cut -d'=' -f2)

            # CRITICAL FIX: Properly validate Let's Encrypt certificate
            # Check if issuer is Let's Encrypt (not self-signed)
            if [[ "$final_issuer" =~ "Let's Encrypt" ]] || [[ "$cert_issuer_cn" =~ ^(R3|R10|R11|E1|E2)$ ]]; then
                # Valid Let's Encrypt certificate
                log_success "✓ Certificat Let's Encrypt valide obtenu"
                log_info "  Domaine: $cert_cn"
                log_info "  Émetteur: $cert_issuer_cn (Let's Encrypt)"
                log_info "  Expiration: $cert_expiry"
            elif [[ "$cert_cn" == "$cert_issuer_cn" ]] || [[ "$final_subject" == "$final_issuer" ]]; then
                # Self-signed certificate detected
                log_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                log_error "❌ ERREUR CRITIQUE: Le certificat obtenu est AUTO-SIGNÉ"
                log_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                log_error "Subject CN: $cert_cn"
                log_error "Issuer CN:  $cert_issuer_cn"
                log_error ""
                log_error "Ce n'est PAS un certificat Let's Encrypt valide."
                log_error "Le setup ne peut pas continuer avec un certificat auto-signé."
                log_error ""
                log_error "🔧 SOLUTIONS:"
                log_error "   1. Vérifiez que le DNS pointe vers ce serveur"
                log_error "   2. Vérifiez que le port 80 est accessible depuis Internet"
                log_error "   3. Relancez: $LETSENCRYPT_SCRIPT --force"
                log_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                exit 1
            else
                # Certificate from unknown CA
                log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                log_warn "⚠️  AVERTISSEMENT: Certificat d'une CA inconnue"
                log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                log_warn "Domaine: $cert_cn"
                log_warn "Émetteur: $cert_issuer_cn"
                log_warn "Expiration: $cert_expiry"
                log_warn ""
                log_warn "Attendu: Certificat émis par Let's Encrypt (CN=R3, R10, R11, E1, ou E2)"
                log_warn "Le certificat sera utilisé mais pourrait ne pas être optimal."
                log_warn "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            fi
        fi

        # ══════════════════════════════════════════════════════════════════
        # BASCULER VERS HTTPS (si on était en mode ACME bootstrap)
        # ══════════════════════════════════════════════════════════════════
        if [[ "${PENDING_HTTPS_SWITCH:-false}" == "true" ]]; then
            log_info "Basculement de la configuration Nginx vers HTTPS..."

            # Générer la configuration HTTPS finale
            export DOMAIN
            if envsubst '${DOMAIN}' < "$NGINX_TEMPLATE_HTTPS" > "$NGINX_CONFIG"; then
                # Fix: Remove www subdomain for freeboxos.fr (not supported)
                if [[ "$DOMAIN" == *".freeboxos.fr" ]]; then
                    sed -i "s/ www\.${DOMAIN}//g" "$NGINX_CONFIG"
                    log_info "  → www subdomain removed (freeboxos.fr limitation)"
                fi
                log_success "✓ Configuration Nginx HTTPS générée"
            else
                log_error "Impossible de générer la config HTTPS"
                exit 1
            fi
        fi

        # Recharger Nginx pour appliquer les nouveaux certificats
        log_info "Rechargement de la configuration Nginx..."
        if $DOCKER_CMD -f "$COMPOSE_FILE" exec -T nginx nginx -t 2>/dev/null; then
            if $DOCKER_CMD -f "$COMPOSE_FILE" exec -T nginx nginx -s reload 2>/dev/null; then
                log_success "✓ Nginx rechargé - HTTPS production actif"
            else
                log_warn "Reload échoué, tentative de restart..."
                $DOCKER_CMD -f "$COMPOSE_FILE" restart nginx
            fi
        else
            log_error "Configuration Nginx invalide après génération HTTPS"
            log_info "Vérifiez les logs: $DOCKER_CMD -f $COMPOSE_FILE logs nginx"
            exit 1
        fi

        log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_success "✅ CERTIFICAT SSL VALIDE INSTALLÉ"
        log_success "   Votre site est accessible en HTTPS sécurisé"
        log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    else
        # ══════════════════════════════════════════════════════════════════
        # ÉCHEC DE LET'S ENCRYPT - ARRÊT DU SETUP (pas de fallback auto-signé)
        # ══════════════════════════════════════════════════════════════════
        log_error ""
        log_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_error "❌ ÉCHEC CRITIQUE: Impossible d'obtenir un certificat Let's Encrypt"
        log_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        log_error "Le setup ne peut pas continuer sans un certificat SSL valide."
        log_error "Les certificats auto-signés NE sont PAS acceptables pour la production."
        echo ""
        log_warn "📋 CAUSES PROBABLES:"
        log_warn "   1. DNS NON PROPAGÉ"
        log_warn "      → Domaine ${DOMAIN} ne pointe pas vers cette machine"
        log_warn "      → Solution: Vérifier configuration DNS, attendre propagation (24-48h)"
        log_warn "      → Test: nslookup ${DOMAIN} 8.8.8.8"
        echo ""
        log_warn "   2. PORT 80 NON ACCESSIBLE"
        log_warn "      → Le port 80 doit être ouvert et accessible depuis Internet"
        log_warn "      → Vérifiez: NAT/Redirection de port sur votre box/routeur"
        log_warn "      → Test externe: https://www.yougetsignal.com/tools/open-ports/"
        echo ""
        log_warn "   3. RATE LIMIT LET'S ENCRYPT"
        log_warn "      → Limite: 5 échecs/heure, 50 certificats/semaine par domaine"
        log_warn "      → Solution: Attendre 1 heure avant nouvelle tentative"
        echo ""
        log_warn "🔧 APRÈS CORRECTION:"
        log_warn "   Relancez: ${BOLD}${CYAN}$LETSENCRYPT_SCRIPT --force${NC}"
        log_warn "   Ou relancez le setup complet: ${BOLD}${CYAN}./setup.sh${NC}"
        echo ""
        log_warn "📚 DOCUMENTATION:"
        log_warn "   • Troubleshooting: docs/RASPBERRY_PI_TROUBLESHOOTING.md"
        log_warn "   • Logs Certbot: certbot/logs/letsencrypt.log"
        log_error "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""

        # NE PAS générer de certificat auto-signé - arrêter le setup
        exit 1
    fi
fi

# === PHASE 7: VALIDATION (Utilise les nouvelles fonctions de audit.sh) ===

log_step "PHASE 7: Validation du Déploiement"

# Attendre que les services soient opérationnels (NOUVEAU - utilise wait_for_api_endpoint)
if ! wait_for_api_endpoint "API" "http://localhost:8000/health" 90; then
    log_error "API ne démarre pas"
    $DOCKER_CMD -f "$COMPOSE_FILE" logs api --tail=50
    exit 1
fi

if ! wait_for_api_endpoint "Dashboard" "http://localhost:3000/api/system/health" 90; then
    log_error "Dashboard ne démarre pas"
    $DOCKER_CMD -f "$COMPOSE_FILE" logs dashboard --tail=50
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

# Fixes Issue #16: Check properly if function exists or load it
if declare -f run_full_audit &>/dev/null; then
    if ! run_full_audit "$ENV_FILE" "$COMPOSE_FILE" "data" "$DOMAIN"; then
        log_error "⚠️ L'audit final a détecté des problèmes. Consultez les détails ci-dessus."
        log_error "Le déploiement a réussi, mais certains problèmes de sécurité ou de santé nécessitent attention."
    else
        log_success "✓ Audit final réussi - Tous les contrôles de sécurité OK"
    fi
else
    log_warn "Audit final non disponible (fonction manquante dans audit.sh)"
fi

# === RAPPORT FINAL ===

log_step "DÉPLOIEMENT TERMINÉ AVEC SUCCÈS"

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
  ├─ Conteneurs       : $($DOCKER_CMD -f "$COMPOSE_FILE" ps --quiet 2>/dev/null | wc -l)
  ├─ HTTPS mode       : ${HTTPS_MODE}
  └─ Sauvegardes      : $([ "$BACKUP_CONFIGURED" == "true" ] && echo "${GREEN}Activées (gdrive)${NC}" || echo "${YELLOW}Non configurées${NC}")

  ${BOLD}🔧 Commandes utiles${NC}
  ├─ Logs              : $DOCKER_CMD -f $COMPOSE_FILE logs -f
  ├─ Statut            : $DOCKER_CMD -f $COMPOSE_FILE ps
  ├─ Redémarrer        : $DOCKER_CMD -f $COMPOSE_FILE restart
  ├─ Arrêter           : $DOCKER_CMD -f $COMPOSE_FILE down
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

# Nettoyage des variables sensibles
unset SETUP_PASSWORD_PLAINTEXT
unset PASSWORD
unset PASSWORD_CONFIRM

# Bannière de fin (NOUVEAU v5.0)
show_completion_banner "success" "Installation terminée avec succès 🎉"

exit 0
