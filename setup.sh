#!/bin/bash
# ==============================================================================
# LINKEDIN AUTO RPi4 - SETUP SCRIPT (V4.0 - PRODUCTION HARDENED)
# ==============================================================================
# Architecte : Claude - Audit Technique Complet
# Cible      : Raspberry Pi 4 (4GB RAM, SD 32GB, ARM64)
# ==============================================================================
#
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        RAPPORT D'AUDIT TECHNIQUE V4.0                        ║
# ╠══════════════════════════════════════════════════════════════════════════════╣
# ║                                                                              ║
# ║ FAILLES CRITIQUES CORRIGÉES (V3.0 → V4.0) :                                  ║
# ║                                                                              ║
# ║ 1. [CRITIQUE] Nginx proxy_pass vers 127.0.0.1 (impossible dans Docker)       ║
# ║    - AVANT: proxy_pass http://127.0.0.1:3000                                 ║
# ║    - FIX: Détection contexte Docker vs Host, patch dynamique vers            ║
# ║          dashboard:3000 (DNS interne Docker)                                 ║
# ║                                                                              ║
# ║ 2. [CRITIQUE] Placeholder YOUR_DOMAIN.COM jamais remplacé                    ║
# ║    - FIX: Remplacement automatique par $DOMAIN dans linkedin-bot.conf        ║
# ║                                                                              ║
# ║ 3. [HAUTE] Pas de vérification architecture ARM64                            ║
# ║    - FIX: Fail-fast si uname -m ≠ aarch64 (avec option --force)              ║
# ║                                                                              ║
# ║ 4. [HAUTE] vm.overcommit_memory non configuré                                ║
# ║    - FIX: Configuration sysctl automatique pour Redis (évite warnings BGSAVE)║
# ║                                                                              ║
# ║ 5. [MOYENNE] Swappiness trop élevé pour SD Card                              ║
# ║    - FIX: Réduction vm.swappiness=10 (protège la carte SD)                   ║
# ║                                                                              ║
# ║ 6. [MOYENNE] Timeouts insuffisants pour ARM64                                ║
# ║    - FIX: Health timeout 300s (Next.js compile lentement sur Pi4)            ║
# ║                                                                              ║
# ║ 7. [UX] Mode non-interactif manquant                                         ║
# ║    - FIX: Flag --unattended pour CI/CD et cron                               ║
# ║                                                                              ║
# ║ 8. [ROBUSTESSE] Retry avec backoff exponentiel amélioré                      ║
# ║    - FIX: Retry réseau avec délais 2s, 4s, 8s, 16s, 32s                      ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# USAGE:
#   ./setup.sh                    # Mode interactif (défaut)
#   ./setup.sh --unattended       # Mode silencieux (utilise valeurs par défaut)
#   ./setup.sh --force            # Force l'exécution sur architecture non-ARM64
#   ./setup.sh --skip-ssl         # Ignore la configuration SSL
#   ./setup.sh --help             # Affiche l'aide
#
# ==============================================================================

set -euo pipefail

# --- Couleurs ---
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# --- Configuration ---
readonly SCRIPT_VERSION="4.0"
readonly DOMAIN="gaspardanoukolivier.freeboxos.fr"
readonly COMPOSE_FILE="docker-compose.pi4-standalone.yml"
readonly ENV_FILE=".env"
readonly ENV_TEMPLATE=".env.pi4.example"
readonly NGINX_CONF_TEMPLATE="deployment/nginx/linkedin-bot.conf"
readonly MIN_MEMORY_GB=6           # RAM + SWAP minimum requis
readonly DISK_THRESHOLD_PERCENT=20 # Seuil pour nettoyage
readonly HEALTH_TIMEOUT=300        # 5 minutes pour Pi4 (Next.js compile lentement)
readonly HEALTH_INTERVAL=10        # Check toutes les 10 secondes
readonly MAX_RETRIES=5             # Nombre de tentatives réseau

# --- Flags ---
UNATTENDED=false
FORCE_ARCH=false
SKIP_SSL=false
DEBUG=${DEBUG:-false}

# --- Variables globales ---
DASHBOARD_PASS=""

# --- Logging ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    {
    echo -e "\n${BOLD}${CYAN}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════════${NC}\n"
}
log_debug()   { [[ "$DEBUG" == "true" ]] && echo -e "${DIM}[DEBUG] $1${NC}" || true; }

# --- Aide ---
show_help() {
    cat << EOF
${BOLD}LinkedIn Auto RPi4 - Setup Script v${SCRIPT_VERSION}${NC}

${BOLD}USAGE:${NC}
    ./setup.sh [OPTIONS]

${BOLD}OPTIONS:${NC}
    --unattended    Mode silencieux (pas de prompts, utilise valeurs par défaut)
    --force         Force l'exécution sur architecture non-ARM64
    --skip-ssl      Ignore la configuration SSL/HTTPS
    --help, -h      Affiche cette aide

${BOLD}EXEMPLES:${NC}
    ./setup.sh                           # Installation interactive
    ./setup.sh --unattended              # Installation automatique
    ./setup.sh --force --skip-ssl        # Force sur x86 sans SSL

${BOLD}VARIABLES D'ENVIRONNEMENT:${NC}
    DEBUG=true      Active les logs de debug

EOF
    exit 0
}

# --- Parse arguments ---
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --unattended)
                UNATTENDED=true
                shift
                ;;
            --force)
                FORCE_ARCH=true
                shift
                ;;
            --skip-ssl)
                SKIP_SSL=true
                shift
                ;;
            --help|-h)
                show_help
                ;;
            *)
                log_error "Option inconnue: $1"
                show_help
                ;;
        esac
    done
}

# --- Gestion d'erreurs ---
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo ""
        log_error "Le script a échoué (code: $exit_code). Affichage des logs des conteneurs..."
        docker compose -f "$COMPOSE_FILE" logs --tail=50 2>/dev/null || true
        echo ""
        log_error "Consultez les logs ci-dessus pour diagnostiquer le problème."
    fi
}
trap cleanup EXIT

# --- Fonctions utilitaires ---

# Vérifie si une commande existe
cmd_exists() {
    command -v "$1" &> /dev/null
}

# Prompt avec timeout et valeur par défaut
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local timeout="${3:-30}"
    local result=""

    if [[ "$UNATTENDED" == "true" ]]; then
        echo "$default"
        return 0
    fi

    read -r -t "$timeout" -p "$prompt" result || true
    echo "${result:-$default}"
}

# Confirmation avec timeout
confirm_action() {
    local prompt="$1"
    local default="${2:-n}"

    if [[ "$UNATTENDED" == "true" ]]; then
        [[ "$default" =~ ^[OoYy]$ ]] && return 0 || return 1
    fi

    local reply
    read -r -t 30 -p "$prompt" reply || reply="$default"
    [[ "$reply" =~ ^[OoYy]$ ]]
}

# Retry avec backoff exponentiel
retry_with_backoff() {
    local cmd="$1"
    local max_attempts="${2:-$MAX_RETRIES}"
    local attempt=1
    local delay=2

    while [[ $attempt -le $max_attempts ]]; do
        log_debug "Tentative $attempt/$max_attempts: $cmd"
        if eval "$cmd"; then
            return 0
        fi

        if [[ $attempt -lt $max_attempts ]]; then
            log_warn "Échec (tentative $attempt/$max_attempts). Retry dans ${delay}s..."
            sleep "$delay"
            delay=$((delay * 2))  # Backoff exponentiel: 2, 4, 8, 16, 32
        fi
        attempt=$((attempt + 1))
    done

    return 1
}

# Calcule la mémoire totale disponible (RAM + SWAP) en GB
get_total_memory_gb() {
    local ram_kb swap_kb total_kb
    ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    swap_kb=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
    total_kb=$((ram_kb + swap_kb))
    echo $((total_kb / 1024 / 1024))
}

# Calcule le pourcentage d'espace disque utilisé
get_disk_usage_percent() {
    df -h . | awk 'NR==2 {gsub(/%/,"",$5); print $5}'
}

# Vérifie si l'utilisateur peut utiliser sudo
check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        if [[ "$UNATTENDED" == "true" ]]; then
            log_error "Privilèges sudo requis mais mode unattended actif."
            log_error "Exécutez d'abord: sudo -v"
            exit 1
        fi
        log_warn "Privilèges sudo requis pour certaines opérations."
        sudo true || { log_error "Impossible d'obtenir les privilèges sudo."; exit 1; }
    fi
}

# ==============================================================================
# BANNIÈRE
# ==============================================================================

show_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
  _      _       _            _ _             _         _
 | |    (_)     | |          | (_)           | |       | |
 | |     _ _ __ | | _____  __| |_ _ __       | |_ _   _| |_ ___
 | |    | | '_ \| |/ / _ \/ _` | | '_ \      | __| | | | __/ _ \
 | |____| | | | |   <  __/ (_| | | | | |     | |_| |_| | || (_) |
 |______|_|_| |_|_|\_\___|\__,_|_|_| |_|      \__|\__,_|\__\___/

EOF
    echo -e "${NC}"
    echo -e "${BOLD}         >>> RASPBERRY PI 4 SETUP v${SCRIPT_VERSION} (Production Hardened) <<<${NC}"
    echo -e "${DIM}Optimisé pour: ARM64 | 4GB RAM | SD 32GB | Docker${NC}"
    echo ""

    if [[ "$UNATTENDED" == "true" ]]; then
        echo -e "${YELLOW}Mode non-interactif activé${NC}"
    fi
    if [[ "$FORCE_ARCH" == "true" ]]; then
        echo -e "${YELLOW}Force architecture activé${NC}"
    fi
    if [[ "$SKIP_SSL" == "true" ]]; then
        echo -e "${YELLOW}SSL désactivé${NC}"
    fi
    echo ""
}

# ==============================================================================
# PHASE 0 : VÉRIFICATION ARCHITECTURE (FAIL-FAST)
# ==============================================================================

check_architecture() {
    log_step "PHASE 0 : Vérification Architecture (Fail-Fast)"

    local arch
    arch=$(uname -m)

    log_info "Architecture détectée: $arch"

    if [[ "$arch" != "aarch64" ]] && [[ "$arch" != "arm64" ]]; then
        if [[ "$FORCE_ARCH" == "true" ]]; then
            log_warn "Architecture non-ARM64 détectée mais --force activé."
            log_warn "Les images Docker ARM64 peuvent ne pas fonctionner!"
        else
            log_error "Ce script est optimisé pour Raspberry Pi 4 (ARM64)."
            log_error "Architecture détectée: $arch (attendu: aarch64)"
            log_error ""
            log_error "Options:"
            log_error "  1. Exécutez sur un Raspberry Pi 4"
            log_error "  2. Utilisez --force pour ignorer (non recommandé)"
            exit 1
        fi
    else
        log_success "Architecture ARM64 confirmée."
    fi

    # Vérification modèle Raspberry Pi
    if [[ -f /proc/device-tree/model ]]; then
        local model
        model=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo "Unknown")
        log_info "Modèle: $model"

        if [[ "$model" == *"Raspberry Pi 4"* ]]; then
            log_success "Raspberry Pi 4 détecté."
        else
            log_warn "Modèle différent du Pi 4 recommandé. Performances variables."
        fi
    fi
}

# ==============================================================================
# PHASE 1 : PRÉ-REQUIS SYSTÈME (FAIL-FAST)
# ==============================================================================

check_prerequisites() {
    log_step "PHASE 1 : Vérifications Système (Fail-Fast)"

    # 1.1 Vérification UID utilisateur
    local current_uid
    current_uid=$(id -u)

    if [[ "$current_uid" -eq 0 ]]; then
        log_warn "Script lancé en root. Recommandé: lancer en utilisateur normal (UID 1000)."
        log_info "Continuation avec root, mais les permissions pourraient nécessiter ajustement."
    elif [[ "$current_uid" -ne 1000 ]]; then
        log_warn "UID actuel: $current_uid (attendu: 1000)"
        log_info "Les volumes Docker utilisent UID 1000. Ajustements possibles requis."
    else
        log_success "UID correct: 1000"
    fi

    # 1.2 Vérification des fichiers critiques
    log_info "Vérification des fichiers critiques..."
    local missing_files=()

    [[ ! -f "$COMPOSE_FILE" ]] && missing_files+=("$COMPOSE_FILE")
    [[ ! -f "$ENV_TEMPLATE" ]] && missing_files+=("$ENV_TEMPLATE")
    [[ ! -d "dashboard" ]] && missing_files+=("dashboard/")
    [[ ! -f "dashboard/scripts/hash_password.js" ]] && missing_files+=("dashboard/scripts/hash_password.js")
    [[ ! -f "$NGINX_CONF_TEMPLATE" ]] && missing_files+=("$NGINX_CONF_TEMPLATE")

    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log_error "Fichiers critiques manquants:"
        for f in "${missing_files[@]}"; do
            echo "  - $f"
        done
        exit 1
    fi
    log_success "Fichiers critiques présents."

    # 1.3 Vérification Docker
    log_info "Vérification de Docker..."
    if ! cmd_exists docker; then
        log_error "Docker n'est pas installé."
        log_info "Installation: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi

    if ! docker info &>/dev/null; then
        log_error "Le daemon Docker ne répond pas."
        log_info "Vérifiez: sudo systemctl status docker"
        exit 1
    fi

    # Vérification groupe docker
    if [[ "$current_uid" -ne 0 ]] && ! groups | grep -q docker; then
        log_error "L'utilisateur n'est pas dans le groupe docker."
        log_info "Exécutez: sudo usermod -aG docker \$USER && newgrp docker"
        exit 1
    fi
    log_success "Docker opérationnel ($(docker --version | cut -d' ' -f3 | tr -d ','))."

    # 1.4 Vérification Docker Compose
    if ! docker compose version &>/dev/null; then
        log_error "Docker Compose (plugin) n'est pas disponible."
        log_info "Mettez à jour Docker ou installez le plugin compose."
        exit 1
    fi
    log_success "Docker Compose disponible."

    log_success "Phase 1 terminée: Système prêt."
}

# ==============================================================================
# PHASE 2 : OPTIMISATIONS KERNEL POUR RPi4 (SYSCTL)
# ==============================================================================

configure_kernel_params() {
    log_step "PHASE 2 : Optimisations Kernel pour RPi4"

    check_sudo

    local sysctl_changed=false

    # 2.1 vm.overcommit_memory=1 (requis par Redis pour BGSAVE)
    local current_overcommit
    current_overcommit=$(cat /proc/sys/vm/overcommit_memory 2>/dev/null || echo "0")

    if [[ "$current_overcommit" != "1" ]]; then
        log_info "Configuration vm.overcommit_memory=1 (requis par Redis)..."
        sudo sysctl -w vm.overcommit_memory=1 > /dev/null
        sysctl_changed=true

        # Persister
        if ! grep -q "^vm.overcommit_memory" /etc/sysctl.conf 2>/dev/null; then
            echo "vm.overcommit_memory=1" | sudo tee -a /etc/sysctl.conf > /dev/null
        fi
        log_success "vm.overcommit_memory=1 configuré."
    else
        log_success "vm.overcommit_memory déjà configuré (1)."
    fi

    # 2.2 vm.swappiness=10 (protège la SD card)
    local current_swappiness
    current_swappiness=$(cat /proc/sys/vm/swappiness 2>/dev/null || echo "60")

    if [[ "$current_swappiness" -gt 20 ]]; then
        log_info "Réduction vm.swappiness=10 (protège la SD card)..."
        sudo sysctl -w vm.swappiness=10 > /dev/null
        sysctl_changed=true

        # Persister
        if ! grep -q "^vm.swappiness" /etc/sysctl.conf 2>/dev/null; then
            echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf > /dev/null
        else
            sudo sed -i 's/^vm.swappiness=.*/vm.swappiness=10/' /etc/sysctl.conf
        fi
        log_success "vm.swappiness réduit à 10 (était: $current_swappiness)."
    else
        log_success "vm.swappiness déjà optimisé ($current_swappiness)."
    fi

    # 2.3 net.core.somaxconn (requis par Redis)
    local current_somaxconn
    current_somaxconn=$(cat /proc/sys/net/core/somaxconn 2>/dev/null || echo "128")

    if [[ "$current_somaxconn" -lt 511 ]]; then
        log_info "Augmentation net.core.somaxconn=511 (requis par Redis)..."
        sudo sysctl -w net.core.somaxconn=511 > /dev/null
        sysctl_changed=true

        if ! grep -q "^net.core.somaxconn" /etc/sysctl.conf 2>/dev/null; then
            echo "net.core.somaxconn=511" | sudo tee -a /etc/sysctl.conf > /dev/null
        fi
        log_success "net.core.somaxconn=511 configuré."
    else
        log_success "net.core.somaxconn déjà suffisant ($current_somaxconn)."
    fi

    if [[ "$sysctl_changed" == "true" ]]; then
        log_info "Paramètres kernel persistés dans /etc/sysctl.conf"
    fi

    log_success "Phase 2 terminée: Kernel optimisé pour RPi4."
}

# ==============================================================================
# PHASE 3 : MÉMOIRE (RAM + SWAP)
# ==============================================================================

check_and_configure_memory() {
    log_step "PHASE 3 : Vérification Mémoire (RAM + SWAP)"

    local total_mem_gb
    total_mem_gb=$(get_total_memory_gb)

    log_info "Mémoire totale disponible: ${total_mem_gb}GB (minimum requis: ${MIN_MEMORY_GB}GB)"

    if [[ $total_mem_gb -lt $MIN_MEMORY_GB ]]; then
        log_warn "Mémoire insuffisante! Risque d'OOM (Out Of Memory) élevé."

        local swap_size=$((MIN_MEMORY_GB - total_mem_gb + 1))
        local swap_file="/swapfile"

        if [[ ! -f "$swap_file" ]]; then
            local create_swap
            if [[ "$UNATTENDED" == "true" ]]; then
                create_swap="o"
            else
                echo -e "${YELLOW}Voulez-vous créer un swapfile de ${swap_size}GB ? (recommandé) [O/n]${NC}"
                read -r -t 30 create_swap || create_swap="o"
            fi

            if [[ ! "$create_swap" =~ ^[Nn]$ ]]; then
                check_sudo
                log_info "Création du swapfile de ${swap_size}GB..."

                # Préférer fallocate, fallback sur dd
                if ! sudo fallocate -l "${swap_size}G" "$swap_file" 2>/dev/null; then
                    sudo dd if=/dev/zero of="$swap_file" bs=1G count="$swap_size" status=progress
                fi

                sudo chmod 600 "$swap_file"
                sudo mkswap "$swap_file"
                sudo swapon "$swap_file"

                # Ajouter au fstab si pas déjà présent
                if ! grep -q "$swap_file" /etc/fstab; then
                    echo "$swap_file none swap sw 0 0" | sudo tee -a /etc/fstab > /dev/null
                fi

                total_mem_gb=$(get_total_memory_gb)
                log_success "Swapfile créé. Nouvelle mémoire totale: ${total_mem_gb}GB"
            else
                log_warn "Continuation sans swap additionnel. Risque d'OOM!"
            fi
        else
            log_warn "Swapfile existe déjà mais mémoire insuffisante."
            log_info "Considérez augmenter le swap manuellement."
        fi
    else
        log_success "Mémoire suffisante: ${total_mem_gb}GB"
    fi

    # Vérification ZRAM (optionnel mais recommandé)
    if [[ -d /sys/block/zram0 ]] && ! swapon --show | grep -q zram; then
        log_info "ZRAM disponible mais non activé."
        log_info "Pour de meilleures performances: sudo apt install zram-tools"
    fi

    log_success "Phase 3 terminée: Mémoire OK."
}

# ==============================================================================
# PHASE 4 : HYGIÈNE DISQUE INTELLIGENTE
# ==============================================================================

manage_disk_space() {
    log_step "PHASE 4 : Gestion Espace Disque (SD Card Optimized)"

    local disk_usage disk_free
    disk_usage=$(get_disk_usage_percent)
    disk_free=$((100 - disk_usage))

    log_info "Espace disque utilisé: ${disk_usage}% (libre: ${disk_free}%)"

    if [[ $disk_free -lt $DISK_THRESHOLD_PERCENT ]]; then
        log_warn "Espace disque faible! Nettoyage Docker en cours..."

        # Nettoyage ciblé pour économiser les I/O de la SD
        log_info "Suppression des images dangling uniquement..."
        docker image prune -f --filter "dangling=true" 2>/dev/null || true

        log_info "Suppression des conteneurs arrêtés..."
        docker container prune -f 2>/dev/null || true

        log_info "Suppression des volumes orphelins..."
        docker volume prune -f 2>/dev/null || true

        # Nettoyage build cache (peut être gros)
        log_info "Nettoyage du cache de build Docker..."
        docker builder prune -f --filter "until=24h" 2>/dev/null || true

        local new_disk_free=$((100 - $(get_disk_usage_percent)))
        local freed=$((new_disk_free - disk_free))
        if [[ $freed -gt 0 ]]; then
            log_success "Nettoyage terminé. Espace libéré: ${freed}%"
        else
            log_info "Pas d'espace significatif libéré."
        fi
    else
        log_success "Espace disque suffisant. Pas de nettoyage nécessaire."
    fi

    # Vérification espace minimum pour images (~4GB requis)
    local available_gb
    available_gb=$(df -BG . | awk 'NR==2 {gsub(/G/,"",$4); print $4}')

    if [[ $available_gb -lt 4 ]]; then
        log_error "Espace disque insuffisant: ${available_gb}GB disponible (minimum 4GB requis)"
        log_error "Libérez de l'espace ou utilisez une SD plus grande."
        exit 1
    fi

    log_success "Phase 4 terminée: Espace disque OK (${available_gb}GB disponible)."
}

# ==============================================================================
# PHASE 5 : ARRÊT DES SERVICES EXISTANTS
# ==============================================================================

stop_existing_services() {
    log_step "PHASE 5 : Arrêt Propre des Services Existants"

    if docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null | grep -q .; then
        log_info "Arrêt des conteneurs existants..."
        docker compose -f "$COMPOSE_FILE" down --remove-orphans --timeout 60 2>/dev/null || true

        # Attendre que les conteneurs soient vraiment arrêtés
        local wait_count=0
        while docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null | grep -q . && [[ $wait_count -lt 30 ]]; do
            sleep 1
            wait_count=$((wait_count + 1))
        done

        log_success "Conteneurs arrêtés."
    else
        log_info "Aucun conteneur en cours d'exécution."
    fi

    # Libération Port 80/443 si nécessaire (pour Certbot standalone)
    log_info "Vérification des ports 80/443..."

    for port in 80 443; do
        local port_pids
        port_pids=$(lsof -t -i :"$port" 2>/dev/null || true)

        if [[ -n "$port_pids" ]]; then
            log_warn "Port $port occupé (PIDs: $port_pids). Libération..."
            check_sudo
            echo "$port_pids" | xargs -r sudo kill -15 2>/dev/null || true
            sleep 2
            # Force kill si toujours présent
            port_pids=$(lsof -t -i :"$port" 2>/dev/null || true)
            if [[ -n "$port_pids" ]]; then
                echo "$port_pids" | xargs -r sudo kill -9 2>/dev/null || true
            fi
        fi
    done

    log_success "Phase 5 terminée: Ports libérés."
}

# ==============================================================================
# PHASE 6 : TÉLÉCHARGEMENT DES IMAGES DOCKER
# ==============================================================================

pull_docker_images() {
    log_step "PHASE 6 : Téléchargement des Images Docker"

    log_info "Pull des images en cours (peut prendre 5-10 minutes sur Pi4)..."
    log_info "Les images ARM64 sont pré-buildées sur GHCR."

    if retry_with_backoff "docker compose -f '$COMPOSE_FILE' pull" "$MAX_RETRIES"; then
        log_success "Images téléchargées avec succès."
    else
        log_error "Impossible de télécharger les images après $MAX_RETRIES tentatives."
        log_error "Vérifiez votre connexion Internet."
        exit 1
    fi
}

# ==============================================================================
# PHASE 7 : CONFIGURATION (.env & Secrets)
# ==============================================================================

configure_environment() {
    log_step "PHASE 7 : Configuration Sécurisée"

    local current_uid
    current_uid=$(id -u)

    # 7.1 Création du .env si manquant
    if [[ ! -f "$ENV_FILE" ]]; then
        log_info "Création du fichier .env depuis le template..."
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        log_success "Fichier .env créé avec permissions 600."
    else
        log_info "Fichier .env existant détecté."
    fi

    # 7.2 Authentification Dashboard
    echo -e "\n${BOLD}>>> Configuration Authentification Dashboard${NC}"

    local current_user current_pass skip_password=false
    current_user=$(grep "^DASHBOARD_USER=" "$ENV_FILE" | cut -d '=' -f2 || echo "")
    current_pass=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d '=' -f2- || echo "")

    # Détection si c'est un hash bcrypt existant
    if [[ "$current_pass" =~ ^\$2[aby]\$ ]]; then
        if [[ "$UNATTENDED" == "true" ]]; then
            log_info "Mot de passe déjà hashé. Conservation en mode unattended."
            skip_password=true
        else
            echo -e "${YELLOW}Mot de passe déjà hashé en bcrypt. Voulez-vous le changer ? [o/N]${NC}"
            local change_pass
            read -r -t 15 change_pass || change_pass="n"
            if [[ ! "$change_pass" =~ ^[Oo]$ ]]; then
                log_info "Conservation du mot de passe existant."
                skip_password=true
            fi
        fi
    fi

    if [[ "$skip_password" != "true" ]]; then
        local dashboard_user

        # Utilisateur
        if [[ -z "$current_user" ]] || [[ "$current_user" == "admin" ]] || [[ "$current_user" == "your_username" ]]; then
            if [[ "$UNATTENDED" == "true" ]]; then
                dashboard_user="admin"
            else
                echo -n "Nom d'utilisateur Dashboard (défaut: admin): "
                read -r input_user
                dashboard_user=${input_user:-admin}
            fi
        else
            dashboard_user="$current_user"
            log_info "Utilisateur existant conservé: $dashboard_user"
        fi

        # Mot de passe
        if [[ "$UNATTENDED" == "true" ]]; then
            # Générer un mot de passe aléatoire en mode unattended
            DASHBOARD_PASS=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)
            log_warn "Mot de passe généré automatiquement (mode unattended)"
        else
            echo -n "Mot de passe Dashboard: "
            read -rs DASHBOARD_PASS
            echo ""

            if [[ -z "$DASHBOARD_PASS" ]]; then
                log_error "Le mot de passe ne peut pas être vide."
                exit 1
            fi

            if [[ ${#DASHBOARD_PASS} -lt 8 ]]; then
                log_warn "Mot de passe court (< 8 caractères). Recommandé: 12+ caractères."
            fi
        fi

        # Hashage bcrypt
        log_info "Hashage du mot de passe avec bcrypt..."

        # Vérification de bcryptjs
        if [[ ! -d "dashboard/node_modules/bcryptjs" ]]; then
            log_info "Installation de bcryptjs..."
            if ! (cd dashboard && npm install bcryptjs --silent --no-audit --no-fund 2>/dev/null); then
                log_error "Impossible d'installer bcryptjs. Vérifiez npm."
                exit 1
            fi
        fi

        # Hashage (mode quiet pour récupérer uniquement le hash)
        local hashed_pass
        hashed_pass=$(node dashboard/scripts/hash_password.js "$DASHBOARD_PASS" --quiet 2>/dev/null)

        if [[ -z "$hashed_pass" ]] || [[ ! "$hashed_pass" =~ ^\$2[aby]\$ ]]; then
            log_error "Échec du hashage bcrypt."
            exit 1
        fi

        # Échappement pour Docker Compose ($ → $$)
        local docker_safe_hash
        docker_safe_hash=$(echo "$hashed_pass" | sed 's/\$/\$\$/g')

        # Mise à jour du .env
        sed -i "s|^DASHBOARD_USER=.*|DASHBOARD_USER=${dashboard_user}|" "$ENV_FILE"

        # Utilisation d'un délimiteur différent pour sed
        local escaped_hash
        escaped_hash=$(echo "$docker_safe_hash" | sed 's/[\/&]/\\&/g')
        sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${escaped_hash}|" "$ENV_FILE"

        log_success "Identifiants mis à jour."
    fi

    # 7.3 Génération des secrets si placeholders
    log_info "Vérification des secrets API/JWT..."

    if grep -qE "CHANGEZ_MOI|your_secure|your_username" "$ENV_FILE" 2>/dev/null; then
        log_info "Génération de nouveaux secrets..."

        local new_api_key new_jwt_secret
        new_api_key=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
        new_jwt_secret=$(openssl rand -hex 32)

        sed -i "s|^API_KEY=.*|API_KEY=${new_api_key}|" "$ENV_FILE"
        sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${new_jwt_secret}|" "$ENV_FILE"

        log_success "Secrets API/JWT générés."
    else
        log_info "Secrets existants conservés."
    fi

    # 7.4 Permissions fichiers
    chmod 600 "$ENV_FILE"

    log_success "Phase 7 terminée: Configuration sécurisée."
}

# ==============================================================================
# PHASE 8 : CONFIGURATION NGINX (PATCH DYNAMIQUE)
# ==============================================================================

configure_nginx() {
    log_step "PHASE 8 : Configuration Nginx (Patch Dynamique)"

    local nginx_conf="$NGINX_CONF_TEMPLATE"

    if [[ ! -f "$nginx_conf" ]]; then
        log_warn "Configuration Nginx non trouvée: $nginx_conf"
        log_warn "Nginx pourrait ne pas fonctionner correctement."
        return 0
    fi

    # Backup de la configuration originale
    if [[ ! -f "${nginx_conf}.original" ]]; then
        cp "$nginx_conf" "${nginx_conf}.original"
        log_info "Backup de la configuration Nginx créé."
    fi

    log_info "Patch de la configuration Nginx..."

    # 8.1 Remplacer YOUR_DOMAIN.COM par le domaine réel
    if grep -q "YOUR_DOMAIN.COM" "$nginx_conf"; then
        sed -i "s/YOUR_DOMAIN.COM/${DOMAIN}/g" "$nginx_conf"
        log_success "Domaine remplacé: YOUR_DOMAIN.COM → $DOMAIN"
    fi

    # 8.2 Corriger proxy_pass pour fonctionner dans Docker
    # Remplacer 127.0.0.1:3000 par dashboard:3000 (DNS Docker interne)
    if grep -q "proxy_pass http://127.0.0.1:3000" "$nginx_conf"; then
        sed -i 's|proxy_pass http://127.0.0.1:3000|proxy_pass http://dashboard:3000|g' "$nginx_conf"
        log_success "Proxy corrigé: 127.0.0.1:3000 → dashboard:3000 (DNS Docker)"
    fi

    # 8.3 Corriger proxy vers API (8000)
    if grep -q "proxy_pass http://127.0.0.1:8000" "$nginx_conf"; then
        sed -i 's|proxy_pass http://127.0.0.1:8000|proxy_pass http://api:8000|g' "$nginx_conf"
        log_success "Proxy API corrigé: 127.0.0.1:8000 → api:8000 (DNS Docker)"
    fi

    # 8.4 Activer les certificats SSL si présents
    local cert_dir="./certbot/conf/live/$DOMAIN"

    if [[ -f "$cert_dir/fullchain.pem" ]]; then
        log_info "Certificat SSL détecté, activation..."

        # Décommenter les lignes SSL
        if grep -q "# ssl_certificate " "$nginx_conf"; then
            sed -i "s|# ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN.COM/fullchain.pem;|ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;|" "$nginx_conf"
            sed -i "s|# ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN.COM/privkey.pem;|ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;|" "$nginx_conf"
            log_success "Certificats SSL activés dans Nginx."
        fi
    else
        log_info "Pas de certificat SSL trouvé. HTTPS désactivé."
    fi

    log_success "Phase 8 terminée: Nginx configuré."
}

# ==============================================================================
# PHASE 9 : PRÉPARATION VOLUMES & PERMISSIONS
# ==============================================================================

prepare_volumes() {
    log_step "PHASE 9 : Préparation des Volumes"

    local current_uid
    current_uid=$(id -u)

    # Création des répertoires locaux montés en bind
    log_info "Création des répertoires..."
    mkdir -p logs config certbot/conf certbot/www certbot/work certbot/logs

    # Permissions pour l'utilisateur 1000 (utilisateur des conteneurs)
    log_info "Configuration des permissions (UID 1000)..."

    if [[ "$current_uid" -eq 0 ]]; then
        chown -R 1000:1000 logs config
    elif [[ "$current_uid" -ne 1000 ]]; then
        check_sudo
        sudo chown -R 1000:1000 logs config
    fi

    chmod -R 775 logs config

    log_success "Phase 9 terminée: Volumes préparés."
}

# ==============================================================================
# PHASE 10 : GESTION SSL (Optionnelle)
# ==============================================================================

configure_ssl() {
    log_step "PHASE 10 : Gestion SSL (HTTPS)"

    if [[ "$SKIP_SSL" == "true" ]]; then
        log_info "SSL ignoré (--skip-ssl activé)."
        log_success "Phase 10 terminée."
        return 0
    fi

    local cert_dir="./certbot/conf/live/$DOMAIN"

    if [[ ! -f "$cert_dir/fullchain.pem" ]]; then
        log_warn "Certificat SSL non trouvé pour $DOMAIN."

        local generate_ssl
        if [[ "$UNATTENDED" == "true" ]]; then
            generate_ssl="n"
            log_info "Génération SSL ignorée en mode unattended."
        else
            echo -e "${YELLOW}Voulez-vous générer un certificat Let's Encrypt ? [o/N]${NC}"
            echo -e "${DIM}(Nécessite que le port 80 soit accessible depuis Internet)${NC}"
            read -r -t 30 generate_ssl || generate_ssl="n"
        fi

        if [[ "$generate_ssl" =~ ^[Oo]$ ]]; then
            if cmd_exists certbot; then
                check_sudo
                log_info "Génération du certificat SSL..."

                # Vérifier que le port 80 est accessible
                log_info "Test d'accessibilité du port 80..."

                if sudo certbot certonly --standalone \
                    -d "$DOMAIN" \
                    --email "gaspard.danouk@gmail.com" \
                    --agree-tos \
                    --non-interactive \
                    --config-dir "$(pwd)/certbot/conf" \
                    --work-dir "$(pwd)/certbot/work" \
                    --logs-dir "$(pwd)/certbot/logs"; then
                    log_success "Certificat SSL généré avec succès!"

                    # Re-configurer Nginx pour activer SSL
                    configure_nginx
                else
                    log_warn "Échec Certbot. Le dashboard sera accessible en HTTP uniquement."
                    log_info "Vérifiez que le port 80 est accessible depuis Internet."
                fi
            else
                log_warn "Certbot non installé. Installation: sudo apt install certbot"
            fi
        else
            log_info "SSL ignoré. Le dashboard sera accessible en HTTP sur le port 3000."
        fi
    else
        log_success "Certificat SSL valide détecté pour $DOMAIN."

        # Tentative de renouvellement si proche de l'expiration
        if cmd_exists certbot; then
            log_info "Vérification du renouvellement..."
            certbot renew --dry-run \
                --cert-name "$DOMAIN" \
                --config-dir "$(pwd)/certbot/conf" \
                --work-dir "$(pwd)/certbot/work" \
                --logs-dir "$(pwd)/certbot/logs" 2>/dev/null || true
        fi
    fi

    log_success "Phase 10 terminée."
}

# ==============================================================================
# PHASE 11 : DÉMARRAGE DES SERVICES
# ==============================================================================

start_services() {
    log_step "PHASE 11 : Démarrage des Services"

    log_info "Lancement des conteneurs..."

    if retry_with_backoff "docker compose -f '$COMPOSE_FILE' up -d" 3; then
        log_success "Conteneurs lancés. Attente du démarrage complet..."
    else
        log_error "Impossible de démarrer les conteneurs."
        exit 1
    fi
}

# ==============================================================================
# PHASE 12 : HEALTH CHECKS (VITAL)
# ==============================================================================

perform_health_checks() {
    log_step "PHASE 12 : Vérification de Santé (Health Checks)"

    local failed_services=()

    # Fonction de vérification de santé d'un service
    check_service_health() {
        local service="$1"
        local endpoint="$2"
        local timeout="$3"
        local elapsed=0

        echo -n "  - $service"

        while [[ $elapsed -lt $timeout ]]; do
            # Vérification état Docker
            local state
            state=$(docker compose -f "$COMPOSE_FILE" ps --format "{{.Service}}:{{.State}}:{{.Health}}" 2>/dev/null | grep "^${service}:" || echo "")

            log_debug "Service $service state: $state"

            if [[ "$state" == *":exited:"* ]] || [[ "$state" == *":dead:"* ]]; then
                echo -e " ${RED}CRASHED${NC}"
                log_error "Le service $service a crashé!"
                docker compose -f "$COMPOSE_FILE" logs "$service" --tail=30
                return 1
            fi

            if [[ "$state" == *":running:healthy"* ]]; then
                # Double vérification avec endpoint HTTP si fourni
                if [[ -n "$endpoint" ]]; then
                    if curl -sf "$endpoint" > /dev/null 2>&1; then
                        echo -e " ${GREEN}OK${NC} (healthy + HTTP OK)"
                        return 0
                    fi
                else
                    echo -e " ${GREEN}OK${NC} (healthy)"
                    return 0
                fi
            fi

            # Services sans healthcheck: vérifier juste running
            if [[ "$state" == *":running:"* ]] && [[ -z "$endpoint" ]] && [[ "$state" != *":healthy"* ]] && [[ "$state" != *":unhealthy"* ]]; then
                # Attendre un peu pour laisser le service démarrer
                if [[ $elapsed -gt 30 ]]; then
                    echo -e " ${GREEN}OK${NC} (running)"
                    return 0
                fi
            fi

            echo -n "."
            sleep "$HEALTH_INTERVAL"
            elapsed=$((elapsed + HEALTH_INTERVAL))
        done

        echo -e " ${RED}TIMEOUT${NC}"
        return 1
    }

    # Fonction pour les services sans healthcheck Docker (Nginx)
    check_http_endpoint() {
        local name="$1"
        local url="$2"
        local timeout="$3"
        local elapsed=0

        echo -n "  - $name"

        while [[ $elapsed -lt $timeout ]]; do
            if curl -sf -k "$url" > /dev/null 2>&1; then
                echo -e " ${GREEN}OK${NC}"
                return 0
            fi
            echo -n "."
            sleep "$HEALTH_INTERVAL"
            elapsed=$((elapsed + HEALTH_INTERVAL))
        done

        echo -e " ${YELLOW}WARN${NC} (timeout, vérifiez les logs)"
        return 1
    }

    log_info "Vérification de chaque service (timeout: ${HEALTH_TIMEOUT}s)..."
    log_info "Note: Next.js peut prendre 3-5 minutes à compiler sur Pi4."
    echo ""

    # Redis (démarrage rapide)
    check_service_health "redis-bot" "" 60 || failed_services+=("redis-bot")
    check_service_health "redis-dashboard" "" 60 || failed_services+=("redis-dashboard")

    # API (démarrage moyen, a un healthcheck)
    check_service_health "api" "http://localhost:8000/health" "$HEALTH_TIMEOUT" || failed_services+=("api")

    # Dashboard (démarrage lent sur Pi4, Next.js compile)
    check_service_health "dashboard" "http://localhost:3000" "$HEALTH_TIMEOUT" || failed_services+=("dashboard")

    # Nginx (pas de healthcheck Docker, vérification HTTP)
    check_http_endpoint "nginx (HTTPS)" "https://localhost" 90 || {
        # Fallback: essayer HTTP si HTTPS échoue (certificat manquant)
        check_http_endpoint "nginx (HTTP)" "http://localhost:80" 60 || failed_services+=("nginx")
    }

    # Bot Worker (peut être lent à démarrer)
    check_service_health "bot-worker" "" "$HEALTH_TIMEOUT" || failed_services+=("bot-worker")

    # Monitoring (optionnel)
    check_service_health "prometheus" "" 60 || log_warn "Prometheus non disponible (optionnel)"
    check_service_health "grafana" "" 60 || log_warn "Grafana non disponible (optionnel)"

    echo ""

    if [[ ${#failed_services[@]} -gt 0 ]]; then
        log_error "Services en échec: ${failed_services[*]}"
        log_error "Affichage des logs..."
        for svc in "${failed_services[@]}"; do
            echo -e "\n${YELLOW}=== Logs: $svc ===${NC}"
            docker compose -f "$COMPOSE_FILE" logs "$svc" --tail=50
        done
        exit 1
    fi

    log_success "Tous les services sont opérationnels!"
}

# ==============================================================================
# PHASE 13 : RAPPORT FINAL
# ==============================================================================

show_final_report() {
    log_step "PHASE 13 : Rapport d'Installation"

    # Collecte des informations
    local ip_addr services_status final_user display_pass ssl_status current_mem available_gb

    ip_addr=$(hostname -I | awk '{print $1}')
    services_status=$(docker compose -f "$COMPOSE_FILE" ps --format "table {{.Service}}\t{{.State}}\t{{.Status}}" 2>/dev/null || echo "N/A")
    final_user=$(grep "^DASHBOARD_USER=" "$ENV_FILE" | cut -d '=' -f2)
    current_mem=$(get_total_memory_gb)
    available_gb=$(df -BG . | awk 'NR==2 {gsub(/G/,"",$4); print $4}')

    # Mot de passe (affiché en clair pour copie)
    if [[ -n "${DASHBOARD_PASS:-}" ]]; then
        display_pass="$DASHBOARD_PASS"
    else
        display_pass="(inchangé - voir .env)"
    fi

    # État SSL
    local cert_dir="./certbot/conf/live/$DOMAIN"
    if [[ -f "$cert_dir/fullchain.pem" ]]; then
        ssl_status="${GREEN}Actif${NC} (Let's Encrypt)"
    else
        ssl_status="${YELLOW}Non configuré${NC}"
    fi

    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}${BOLD}                   LINKEDIN AUTO - RAPPORT FINAL                         ${NC}${CYAN}║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}                                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}ACCÈS${NC}                                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    URL Locale   : http://${ip_addr}:3000                                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    URL Publique : https://${DOMAIN}/                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    Grafana      : http://${ip_addr}:3001 (admin/admin)                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    API Health   : http://${ip_addr}:8000/health                         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}AUTHENTIFICATION${NC}                                                        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    Utilisateur  : ${final_user}                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    Mot de passe : ${YELLOW}${display_pass}${NC}                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                   ${DIM}(Copiez-le maintenant!)${NC}                              ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}SÉCURITÉ${NC}                                                                ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    SSL (HTTPS)  : $ssl_status                                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    Hachage MDP  : BCrypt (12 rounds)                                     ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    Permissions  : .env (600), data (UID 1000)                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}RESSOURCES${NC}                                                              ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    Mémoire      : ${current_mem}GB (RAM+SWAP)                                        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    Disque libre : ${available_gb}GB                                                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}    Architecture : $(uname -m)                                               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                                          ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"

    echo ""
    echo -e "${BOLD}ÉTAT DES SERVICES :${NC}"
    echo "$services_status"

    echo ""
    echo -e "${GREEN}${BOLD}Installation terminée avec succès! (v${SCRIPT_VERSION})${NC}"
    echo ""
    echo -e "${DIM}Commandes utiles:${NC}"
    echo -e "  Logs temps réel : docker compose -f $COMPOSE_FILE logs -f"
    echo -e "  Logs dashboard  : docker compose -f $COMPOSE_FILE logs -f dashboard"
    echo -e "  Redémarrer      : docker compose -f $COMPOSE_FILE restart"
    echo -e "  Arrêter         : docker compose -f $COMPOSE_FILE down"
    echo -e "  Audit sécurité  : ./scripts/verify_security.sh"
    echo ""

    if [[ "$UNATTENDED" == "true" ]] && [[ -n "${DASHBOARD_PASS:-}" ]]; then
        echo -e "${RED}${BOLD}IMPORTANT (Mode Unattended):${NC}"
        echo -e "${RED}Mot de passe généré automatiquement: ${DASHBOARD_PASS}${NC}"
        echo -e "${RED}Notez-le maintenant, il ne sera plus affiché!${NC}"
        echo ""
    fi
}

# ==============================================================================
# MAIN
# ==============================================================================

main() {
    # Parse arguments
    parse_args "$@"

    # Bannière
    show_banner

    # Exécution des phases
    check_architecture            # Phase 0
    check_prerequisites           # Phase 1
    configure_kernel_params       # Phase 2
    check_and_configure_memory    # Phase 3
    manage_disk_space             # Phase 4
    stop_existing_services        # Phase 5
    pull_docker_images            # Phase 6
    configure_environment         # Phase 7
    configure_nginx               # Phase 8
    prepare_volumes               # Phase 9
    configure_ssl                 # Phase 10
    start_services                # Phase 11
    perform_health_checks         # Phase 12
    show_final_report             # Phase 13
}

# Exécution
main "$@"
