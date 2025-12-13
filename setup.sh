#!/bin/bash

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - Script Maître de Déploiement & Maintenance v6.0 ║
# ║  Déploiement étape par étape avec hardening sécurité intégré             ║
# ║                                                                          ║
# ║  Optimisé pour Raspberry Pi 4 - Images pré-construites via GHCR         ║
# ╚══════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
LINK_COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
ENV_TEMPLATE=".env.pi4.example"
LOG_FILE="setup_$(date +%Y%m%d_%H%M%S).log"
DEBUG_MODE="${DEBUG:-false}"
SCRIPT_VERSION="6.0"

# Options CLI
UNATTENDED_MODE=false
SKIP_PHASE2=false
QUICK_MODE=false
RESUME_MODE=false
FORCE_REINSTALL=false

# Timeouts optimisés pour RPI4 (plus lent qu'un PC)
TIMEOUT_REDIS=90
TIMEOUT_API=240
TIMEOUT_WORKER=180
TIMEOUT_DASHBOARD=240

# Seuils RPI4
RPI4_MIN_RAM_MB=3500       # Minimum 3.5GB RAM
RPI4_WARN_TEMP=70          # Avertissement température (°C)
RPI4_CRITICAL_TEMP=80      # Température critique (°C)
RPI4_MIN_DISK_GB=3         # Minimum 3GB disque

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Caractères pour spinner
SPINNER_CHARS='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

# ═══════════════════════════════════════════════════════════════════════════
# AIDE ET PARSING ARGUMENTS CLI
# ═══════════════════════════════════════════════════════════════════════════
show_help() {
    cat << EOF
${BOLD}LinkedIn Birthday Bot - Script Maître v${SCRIPT_VERSION}${NC}
Optimisé pour Raspberry Pi 4

${BOLD}Usage:${NC}
  ./setup.sh [OPTIONS]

${BOLD}Options:${NC}
  -h, --help          Affiche cette aide
  -u, --unattended    Mode non-interactif (installation automatique)
  -q, --quick         Mode rapide (skip les explications)
  -s, --skip-phase2   Sauter la phase 2 (sécurisation avancée)
  -r, --resume        Reprendre une installation interrompue
  -f, --force         Forcer la réinstallation (supprime les containers existants)
  -d, --debug         Activer le mode debug (logs détaillés)

${BOLD}Exemples:${NC}
  ./setup.sh                    # Installation interactive
  ./setup.sh -u -s              # Installation automatique basique
  ./setup.sh -u -q              # Installation rapide complète
  DEBUG=true ./setup.sh         # Installation avec debug

${BOLD}Variables d'environnement:${NC}
  DEBUG=true          Active le mode debug
  DASHBOARD_USER      Définit l'utilisateur dashboard
  DASHBOARD_PASSWORD  Définit le mot de passe dashboard

${BOLD}Documentation:${NC}
  Voir DOCS_INDEX.md à la racine.

EOF
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                ;;
            -u|--unattended)
                UNATTENDED_MODE=true
                shift
                ;;
            -q|--quick)
                QUICK_MODE=true
                shift
                ;;
            -s|--skip-phase2)
                SKIP_PHASE2=true
                shift
                ;;
            -r|--resume)
                RESUME_MODE=true
                shift
                ;;
            -f|--force)
                FORCE_REINSTALL=true
                shift
                ;;
            -d|--debug)
                DEBUG_MODE=true
                shift
                ;;
            *)
                log_error "Option inconnue: $1"
                echo "Utilisez --help pour voir les options disponibles"
                exit 1
                ;;
        esac
    done
}

# ═══════════════════════════════════════════════════════════════════════════
# SYSTÈME DE LOGGING DEBUG
# ═══════════════════════════════════════════════════════════════════════════
log_init() {
    echo "═══════════════════════════════════════════════════════════════" > "$LOG_FILE"
    echo "LinkedIn Birthday Bot - Setup Log v${SCRIPT_VERSION}" >> "$LOG_FILE"
    echo "Date: $(date)" >> "$LOG_FILE"
    echo "User: $(whoami)" >> "$LOG_FILE"
    echo "PWD: $(pwd)" >> "$LOG_FILE"
    echo "Args: UNATTENDED=$UNATTENDED_MODE QUICK=$QUICK_MODE SKIP_PHASE2=$SKIP_PHASE2" >> "$LOG_FILE"
    echo "═══════════════════════════════════════════════════════════════" >> "$LOG_FILE"
}

log_debug() {
    local msg="[DEBUG $(date +%H:%M:%S)] $1"
    echo "$msg" >> "$LOG_FILE"
    [[ "$DEBUG_MODE" == "true" ]] && echo -e "${DIM}$msg${NC}"
}

log_info() {
    local msg="[INFO  $(date +%H:%M:%S)] $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${CYAN}ℹ${NC}  $1"
}

log_success() {
    local msg="[OK    $(date +%H:%M:%S)] $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    local msg="[WARN  $(date +%H:%M:%S)] $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${YELLOW}⚠️${NC}  $1"
}

log_error() {
    local msg="[ERROR $(date +%H:%M:%S)] $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${RED}❌${NC} $1"
}

log_step() {
    local step_num="$1"
    local step_name="$2"
    echo "" >> "$LOG_FILE"
    echo "═══ ÉTAPE $step_num: $step_name ═══" >> "$LOG_FILE"
    echo ""
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  ÉTAPE $step_num : $step_name${NC}"
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════

# Spinner animé pour les opérations longues
SPINNER_PID=""

start_spinner() {
    local message="${1:-Chargement...}"
    if [[ "$UNATTENDED_MODE" == "true" ]]; then
        echo -e "${CYAN}⏳${NC} $message"
        return
    fi

    (
        local i=0
        while true; do
            printf "\r${CYAN}${SPINNER_CHARS:i++%${#SPINNER_CHARS}:1}${NC} $message"
            sleep 0.1
        done
    ) &
    SPINNER_PID=$!
    disown $SPINNER_PID 2>/dev/null
}

stop_spinner() {
    local status="${1:-success}"
    local message="${2:-}"

    if [[ -n "$SPINNER_PID" ]]; then
        kill $SPINNER_PID 2>/dev/null || true
        wait $SPINNER_PID 2>/dev/null || true
        SPINNER_PID=""
    fi

    # Effacer la ligne du spinner
    printf "\r\033[K"

    if [[ -n "$message" ]]; then
        if [[ "$status" == "success" ]]; then
            log_success "$message"
        elif [[ "$status" == "error" ]]; then
            log_error "$message"
        else
            log_info "$message"
        fi
    fi
}

# Barre de progression (compatible tous terminaux)
show_progress() {
    local current=$1
    local total=$2
    local width=30
    local percent=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))

    # Utiliser des caractères ASCII simples pour compatibilité
    printf "["
    for ((i=0; i<filled; i++)); do printf "#"; done
    for ((i=0; i<empty; i++)); do printf "-"; done
    printf "] %3d%%" "$percent"
}

# Compte à rebours visuel
countdown() {
    local seconds=$1
    local message="${2:-Attente}"

    if [[ "$UNATTENDED_MODE" == "true" || "$QUICK_MODE" == "true" ]]; then
        sleep "$seconds"
        return
    fi

    for ((i=seconds; i>0; i--)); do
        printf "\r${CYAN}⏳${NC} $message (%ds)" "$i"
        sleep 1
    done
    printf "\r\033[K"
}

print_banner() {
    [[ "$QUICK_MODE" == "true" ]] && return

    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   🚀 LinkedIn Birthday Bot - Script Maître v6.0                         ║
║                                                                          ║
║   • Déploiement étape par étape                                         ║
║   • Hardening sécurité intégré                                          ║
║   • Optimisé pour Raspberry Pi 4                                        ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

ask_continue() {
    local prompt="${1:-Continuer ?}"

    # Mode non-interactif : toujours oui
    if [[ "$UNATTENDED_MODE" == "true" ]]; then
        log_debug "Mode non-interactif: auto-accept '$prompt'"
        return 0
    fi

    echo -e -n "${CYAN}❓${NC} $prompt [O/n] "
    read -r response
    [[ -z "$response" || "$response" =~ ^[OoYy]$ ]]
}

# Demande avec valeur par défaut (supporte mode unattended)
ask_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"

    # En mode unattended, utiliser la valeur par défaut ou env var
    if [[ "$UNATTENDED_MODE" == "true" ]]; then
        local env_value="${!var_name:-}"
        if [[ -n "$env_value" ]]; then
            echo "$env_value"
        else
            echo "$default"
        fi
        return
    fi

    echo -e -n "${CYAN}❓${NC} $prompt [$default]: "
    read -r response
    echo "${response:-$default}"
}

generate_secure_key() {
    python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || \
    openssl rand -hex 32 2>/dev/null || \
    head -c 32 /dev/urandom | xxd -p | tr -d '\n'
}

validate_key() {
    local key="$1"
    local name="$2"

    # Vérifier si la clé est vide
    if [[ -z "$key" ]]; then
        log_error "$name est vide"
        return 1
    fi

    # Liste des valeurs interdites (préfixes)
    local forbidden_prefixes=("internal_secret_key" "CHANGE_ME" "CHANGEZ_MOI" "changeme")
    # Valeurs exactes interdites
    local forbidden_exact=("secret" "password" "admin" "test" "demo")

    for bad in "${forbidden_prefixes[@]}"; do
        if [[ "$key" == "$bad"* ]]; then
            log_error "$name contient une valeur non sécurisée: '$bad...'"
            return 1
        fi
    done

    for bad in "${forbidden_exact[@]}"; do
        if [[ "$key" == "$bad" ]]; then
            log_error "$name est une valeur par défaut non sécurisée: '$bad'"
            return 1
        fi
    done

    # Vérifier longueur minimum (32 caractères = 64 hex)
    if [[ ${#key} -lt 32 ]]; then
        log_error "$name est trop court (${#key} chars, minimum 32)"
        return 1
    fi

    log_debug "$name validé (${#key} chars)"
    return 0
}

# ═══════════════════════════════════════════════════════════════════════════
# FONCTIONS DE VÉRIFICATION RPI4
# ═══════════════════════════════════════════════════════════════════════════

# Vérifie si on est sur un Raspberry Pi
is_raspberry_pi() {
    [[ -f /proc/device-tree/model ]] && grep -qi "raspberry" /proc/device-tree/model 2>/dev/null
}

# Récupère la température CPU du RPI4
get_cpu_temp() {
    if [[ -f /sys/class/thermal/thermal_zone0/temp ]]; then
        local temp_raw=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo "0")
        echo $((temp_raw / 1000))
    else
        echo "0"
    fi
}

# Vérifie la température et avertit si trop élevée
check_cpu_temp() {
    local temp=$(get_cpu_temp)

    if [[ "$temp" -eq 0 ]]; then
        log_debug "Impossible de lire la température CPU"
        return 0
    fi

    log_debug "Température CPU: ${temp}°C"

    if [[ "$temp" -ge "$RPI4_CRITICAL_TEMP" ]]; then
        log_error "CRITIQUE: CPU à ${temp}°C - Risque de throttling!"
        log_warning "Le RPI4 va réduire sa performance pour éviter la surchauffe"
        log_info "Conseil: Vérifiez le refroidissement (ventilateur, dissipateur)"

        if ! ask_continue "Continuer malgré la température critique ?"; then
            exit 1
        fi
        return 1
    elif [[ "$temp" -ge "$RPI4_WARN_TEMP" ]]; then
        log_warning "CPU chaud: ${temp}°C - Performance peut être réduite"
        return 0
    else
        log_debug "Température CPU OK: ${temp}°C"
        return 0
    fi
}

# Vérifie la mémoire disponible
check_memory() {
    local total_mb=$(free -m | awk '/^Mem:/{print $2}')
    local available_mb=$(free -m | awk '/^Mem:/{print $7}')
    local swap_mb=$(free -m | awk '/^Swap:/{print $2}')

    log_debug "RAM: ${total_mb}MB total, ${available_mb}MB disponible, ${swap_mb}MB swap"

    if [[ "$total_mb" -lt "$RPI4_MIN_RAM_MB" ]]; then
        log_warning "RAM totale faible: ${total_mb}MB (recommandé: ≥4GB)"
    fi

    # Vérifier si swap est configuré
    if [[ "$swap_mb" -lt 1000 ]]; then
        log_warning "Swap faible ou absent (${swap_mb}MB)"
        log_info "Conseil: Activez au moins 1GB de swap pour la stabilité"

        if is_raspberry_pi && [[ ! -f /etc/dphys-swapfile ]]; then
            log_info "Pour activer le swap sur RPI4:"
            log_info "  sudo dphys-swapfile swapoff"
            log_info "  sudo nano /etc/dphys-swapfile  # CONF_SWAPSIZE=2048"
            log_info "  sudo dphys-swapfile setup && sudo dphys-swapfile swapon"
        fi
    fi

    # Vérifier si assez de mémoire pour l'installation
    if [[ "$available_mb" -lt 500 ]]; then
        log_error "Mémoire disponible insuffisante: ${available_mb}MB"
        log_info "Fermez d'autres applications ou augmentez le swap"
        return 1
    fi

    return 0
}

# Configure automatiquement le swap si nécessaire (avec permission)
setup_swap_if_needed() {
    local swap_mb=$(free -m | awk '/^Swap:/{print $2}')

    if [[ "$swap_mb" -ge 1000 ]]; then
        return 0  # Swap déjà configuré
    fi

    if ! is_raspberry_pi; then
        return 0  # Pas un RPI, ne pas toucher au swap
    fi

    if [[ "$UNATTENDED_MODE" == "true" ]]; then
        log_info "Mode unattended: configuration swap ignorée"
        return 0
    fi

    if ask_continue "Configurer automatiquement 2GB de swap ? (recommandé)"; then
        log_info "Configuration du swap..."

        if [[ -f /etc/dphys-swapfile ]]; then
            sudo dphys-swapfile swapoff 2>/dev/null || true
            sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
            sudo dphys-swapfile setup
            sudo dphys-swapfile swapon
            log_success "Swap configuré (2GB)"
        else
            log_warning "dphys-swapfile non trouvé, swap manuel requis"
        fi
    fi
}

# Vérifie si le système est surchargé
check_system_load() {
    local load_1min=$(cat /proc/loadavg | awk '{print $1}')
    local cpus=$(nproc)
    local load_threshold=$(echo "$cpus * 2" | bc 2>/dev/null || echo "4")

    log_debug "Load average: $load_1min (CPUs: $cpus)"

    # Comparer en entier (bash ne gère pas les floats)
    local load_int=${load_1min%.*}
    if [[ "$load_int" -gt "$load_threshold" ]]; then
        log_warning "Système très chargé (load: $load_1min)"
        log_info "L'installation sera plus lente, patientez..."
        return 1
    fi

    return 0
}

# Retry avec backoff exponentiel
retry_with_backoff() {
    local max_attempts=${1:-4}
    local base_delay=${2:-2}
    local cmd="${@:3}"
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        log_debug "Tentative $attempt/$max_attempts: $cmd"

        if eval "$cmd"; then
            return 0
        fi

        if [[ $attempt -lt $max_attempts ]]; then
            local delay=$((base_delay * (2 ** (attempt - 1))))
            log_warning "Échec, nouvelle tentative dans ${delay}s..."
            countdown "$delay" "Attente avant retry"
        fi

        ((attempt++))
    done

    log_error "Échec après $max_attempts tentatives"
    return 1
}

wait_container_healthy() {
    local container="$1"
    local timeout="${2:-120}"
    local start_time=$(date +%s)

    log_debug "Attente de $container (timeout: ${timeout}s)"

    # Utiliser le spinner pour l'attente
    start_spinner "Démarrage de $container..."

    while true; do
        local elapsed=$(($(date +%s) - start_time))

        if [[ $elapsed -ge $timeout ]]; then
            stop_spinner "error" "Timeout: $container non healthy après ${timeout}s"
            log_debug "Logs de $container:"
            docker logs "$container" --tail 30 2>&1 | tee -a "$LOG_FILE"
            return 1
        fi

        local status=$(docker inspect "$container" --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
        local health=$(docker inspect "$container" --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' 2>/dev/null || echo "unknown")

        log_debug "$container: status=$status health=$health (${elapsed}s)"

        case "$health" in
            "healthy")
                stop_spinner "success" "$container est healthy (${elapsed}s)"
                return 0
                ;;
            "no_healthcheck")
                if [[ "$status" == "running" ]]; then
                    stop_spinner "success" "$container est running (pas de healthcheck)"
                    return 0
                fi
                ;;
            "unhealthy")
                stop_spinner "error" "$container est unhealthy!"
                log_debug "Derniers logs:"
                docker logs "$container" --tail 20 2>&1 | tee -a "$LOG_FILE"
                return 1
                ;;
        esac

        if [[ "$status" == "exited" || "$status" == "dead" ]]; then
            stop_spinner "error" "$container a crashé (status: $status)"
            log_debug "Logs de crash:"
            docker logs "$container" --tail 50 2>&1 | tee -a "$LOG_FILE"
            return 1
        fi

        sleep 3
    done
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 0 : INITIALISATION
# ═══════════════════════════════════════════════════════════════════════════
step_0_init() {
    log_step "0" "INITIALISATION"

    log_info "Fichier de log: $LOG_FILE"
    log_info "Mode debug: $DEBUG_MODE"

    # Afficher les modes actifs
    [[ "$UNATTENDED_MODE" == "true" ]] && log_info "Mode: Non-interactif (unattended)"
    [[ "$QUICK_MODE" == "true" ]] && log_info "Mode: Rapide (quick)"
    [[ "$SKIP_PHASE2" == "true" ]] && log_info "Mode: Phase 2 ignorée"

    # Création du symlink pour docker-compose
    if [[ -f "$COMPOSE_FILE" ]]; then
        if [[ ! -L "$LINK_COMPOSE_FILE" || "$(readlink "$LINK_COMPOSE_FILE")" != "$COMPOSE_FILE" ]]; then
             log_info "Création du lien symbolique $LINK_COMPOSE_FILE -> $COMPOSE_FILE"
             ln -sf "$COMPOSE_FILE" "$LINK_COMPOSE_FILE"
        fi
    else
        log_error "Fichier principal $COMPOSE_FILE introuvable !"
        exit 1
    fi

    # Détection plateforme
    if is_raspberry_pi; then
        local model=$(tr -d '\0' < /proc/device-tree/model)
        log_success "Plateforme: $model"

        # Vérifications spécifiques RPI4
        echo ""
        log_info "Vérifications Raspberry Pi..."

        # Température CPU
        local temp=$(get_cpu_temp)
        if [[ "$temp" -gt 0 ]]; then
            if [[ "$temp" -ge "$RPI4_WARN_TEMP" ]]; then
                log_warning "Température CPU: ${temp}°C (élevée)"
            else
                log_success "Température CPU: ${temp}°C"
            fi
        fi

        # Vérifier le throttling actuel
        if command -v vcgencmd &>/dev/null; then
            local throttled=$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2)
            if [[ "$throttled" != "0x0" && -n "$throttled" ]]; then
                log_warning "Throttling détecté: $throttled"
                log_info "Le RPI4 a réduit ses performances (température/alimentation)"
            else
                log_debug "Pas de throttling actif"
            fi
        fi

        check_cpu_temp
    else
        log_info "Plateforme: $(uname -m) / $(uname -s)"
    fi

    # RAM
    if command -v free &>/dev/null; then
        local ram_total=$(free -m | awk '/^Mem:/{print $2}')
        local ram_avail=$(free -m | awk '/^Mem:/{print $7}')
        local swap=$(free -m | awk '/^Swap:/{print $2}')

        log_info "RAM: ${ram_total}MB total, ${ram_avail}MB disponible"
        log_info "Swap: ${swap}MB"
        log_debug "RAM détail: $(free -m | head -2)"

        # Vérifier et configurer le swap si nécessaire
        check_memory || true
        setup_swap_if_needed
    fi

    # Disque
    local disk=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')
    log_info "Disque disponible: ${disk}GB"

    if [[ "$disk" -lt "$RPI4_MIN_DISK_GB" ]]; then
        log_warning "Espace disque faible (<${RPI4_MIN_DISK_GB}GB)"
        log_info "Conseil: Nettoyez avec 'docker system prune -a'"
    fi

    # Vérifier la charge système
    check_system_load || true

    # Détection d'une installation précédente
    check_existing_installation
}

# Vérifie s'il y a déjà une installation
check_existing_installation() {
    echo ""
    log_info "Vérification d'une installation existante..."

    local existing_containers=0
    local running_containers=0

    # Compter les containers existants
    for container in redis-bot redis-dashboard bot-api bot-worker dashboard; do
        if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${container}$"; then
            ((existing_containers++))
            if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${container}$"; then
                ((running_containers++))
            fi
        fi
    done

    if [[ $existing_containers -gt 0 ]]; then
        log_info "Installation précédente détectée:"
        log_info "  • $existing_containers containers existants"
        log_info "  • $running_containers containers en cours d'exécution"

        if [[ $running_containers -eq 5 ]]; then
            log_success "Tous les services sont déjà en cours d'exécution!"

            if [[ "$FORCE_REINSTALL" == "true" ]]; then
                log_warning "Mode --force: réinstallation forcée"
            elif [[ "$RESUME_MODE" == "true" ]]; then
                log_info "Mode --resume: vérification de l'état..."
                return 0
            else
                if ! ask_continue "L'installation semble complète. Réinstaller ?"; then
                    log_info "Utilisez les commandes suivantes:"
                    echo "  • Status:  docker compose ps"
                    echo "  • Logs:    docker compose logs -f"
                    echo "  • Stop:    docker compose down"
                    exit 0
                fi
            fi
        fi

        # Afficher l'état des services
        if [[ "$QUICK_MODE" != "true" ]]; then
            echo ""
            docker compose -f "$COMPOSE_FILE" ps 2>/dev/null || true
            echo ""
        fi
    else
        log_info "Aucune installation précédente détectée"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 1 : VÉRIFICATION PRÉREQUIS
# ═══════════════════════════════════════════════════════════════════════════
step_1_prerequisites() {
    log_step "1" "VÉRIFICATION DES PRÉREQUIS"

    local errors=0

    # Docker
    log_info "Vérification Docker..."
    if docker --version &>/dev/null; then
        local docker_ver=$(docker --version)
        log_success "Docker: $docker_ver"
        log_debug "Docker info: $(docker info 2>/dev/null | grep -E 'Server Version|Storage Driver' | head -2)"
    else
        log_error "Docker n'est pas installé!"
        log_info "Installation: curl -fsSL https://get.docker.com | sh"
        ((errors++))
    fi

    # Permissions Docker
    log_info "Vérification permissions Docker..."
    if docker ps &>/dev/null; then
        log_success "Permissions Docker OK"
    else
        log_error "Pas de permissions Docker pour $(whoami)"
        log_info "Exécutez: sudo usermod -aG docker $(whoami) && newgrp docker"
        ((errors++))
    fi

    # Docker Compose V2
    log_info "Vérification Docker Compose..."
    if docker compose version &>/dev/null; then
        local compose_ver=$(docker compose version --short)
        log_success "Docker Compose: $compose_ver"
    else
        log_error "Docker Compose V2 manquant!"
        log_info "Installation: sudo apt install docker-compose-plugin"
        ((errors++))
    fi

    # Fichier compose
    log_info "Vérification fichier compose..."
    if [[ -f "$COMPOSE_FILE" ]]; then
        log_success "Fichier compose: $COMPOSE_FILE"
        log_debug "Services définis: $(grep -E '^\s+\w+:$' "$COMPOSE_FILE" | head -10)"
    else
        log_error "Fichier $COMPOSE_FILE introuvable!"
        ((errors++))
    fi

    # Template .env
    log_info "Vérification template .env..."
    if [[ -f "$ENV_TEMPLATE" ]]; then
        log_success "Template: $ENV_TEMPLATE"
    else
        log_error "Template $ENV_TEMPLATE introuvable!"
        ((errors++))
    fi

    if [[ $errors -gt 0 ]]; then
        log_error "$errors erreur(s) de prérequis - Installation impossible"
        exit 1
    fi

    log_success "Tous les prérequis sont satisfaits"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 2 : CONFIGURATION SÉCURISÉE
# ═══════════════════════════════════════════════════════════════════════════
step_2_security_config() {
    log_step "2" "CONFIGURATION SÉCURISÉE (HARDENING)"

    # Création .env si absent
    if [[ ! -f "$ENV_FILE" ]]; then
        log_info "Création du fichier .env depuis le template..."
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        log_success "Fichier .env créé"
    else
        log_info "Fichier .env existant détecté"
        log_debug "Contenu .env (sans secrets): $(grep -E '^[A-Z_]+=' "$ENV_FILE" | grep -v -E 'PASSWORD|SECRET|KEY' | head -10)"
    fi

    # ─────────────────────────────────────────────────────────────────────
    # HARDENING: API_KEY
    # ─────────────────────────────────────────────────────────────────────
    log_info "Vérification API_KEY..."

    local current_api_key=$(grep -E "^API_KEY=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
    log_debug "API_KEY actuelle: ${current_api_key:0:10}..."

    if ! validate_key "$current_api_key" "API_KEY" 2>/dev/null; then
        log_warning "API_KEY invalide ou non sécurisée - Génération automatique"

        local new_api_key=$(generate_secure_key)
        log_debug "Nouvelle API_KEY générée: ${new_api_key:0:10}..."

        if grep -q "^API_KEY=" "$ENV_FILE"; then
            sed -i "s/^API_KEY=.*/API_KEY=$new_api_key/" "$ENV_FILE"
        else
            echo "API_KEY=$new_api_key" >> "$ENV_FILE"
        fi

        log_success "API_KEY sécurisée générée et enregistrée"
    else
        log_success "API_KEY valide"
    fi

    # ─────────────────────────────────────────────────────────────────────
    # HARDENING: JWT_SECRET
    # ─────────────────────────────────────────────────────────────────────
    log_info "Vérification JWT_SECRET..."

    local current_jwt=$(grep -E "^JWT_SECRET=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
    log_debug "JWT_SECRET actuel: ${current_jwt:0:10}..."

    if ! validate_key "$current_jwt" "JWT_SECRET" 2>/dev/null; then
        log_warning "JWT_SECRET invalide - Génération automatique"

        local new_jwt=$(generate_secure_key)

        if grep -q "^JWT_SECRET=" "$ENV_FILE"; then
            sed -i "s/^JWT_SECRET=.*/JWT_SECRET=$new_jwt/" "$ENV_FILE"
        else
            echo "JWT_SECRET=$new_jwt" >> "$ENV_FILE"
        fi

        log_success "JWT_SECRET sécurisé généré"
    else
        log_success "JWT_SECRET valide"
    fi

    # ─────────────────────────────────────────────────────────────────────
    # HARDENING: DASHBOARD CREDENTIALS
    # ─────────────────────────────────────────────────────────────────────
    log_info "Vérification credentials dashboard..."

    local dash_user=$(grep -E "^DASHBOARD_USER=" "$ENV_FILE" | cut -d'=' -f2-)
    local dash_pass=$(grep -E "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')

    if [[ -z "$dash_user" || "$dash_user" == "admin" ]]; then
        log_warning "DASHBOARD_USER non défini ou par défaut"
        echo -e -n "${CYAN}❓${NC} Nom d'utilisateur dashboard [admin]: "
        read -r new_user
        new_user="${new_user:-admin}"

        if grep -q "^DASHBOARD_USER=" "$ENV_FILE"; then
            sed -i "s/^DASHBOARD_USER=.*/DASHBOARD_USER=$new_user/" "$ENV_FILE"
        else
            echo "DASHBOARD_USER=$new_user" >> "$ENV_FILE"
        fi
        log_success "DASHBOARD_USER configuré: $new_user"
    fi

    if [[ -z "$dash_pass" || "$dash_pass" == "CHANGEZ_MOI"* || ${#dash_pass} -lt 8 ]]; then
        log_warning "DASHBOARD_PASSWORD non sécurisé"
        echo -e -n "${CYAN}❓${NC} Mot de passe dashboard (min 8 chars): "
        read -rs new_pass
        echo ""

        if [[ ${#new_pass} -lt 8 ]]; then
            log_error "Mot de passe trop court!"
            exit 1
        fi

        if grep -q "^DASHBOARD_PASSWORD=" "$ENV_FILE"; then
            sed -i "s/^DASHBOARD_PASSWORD=.*/DASHBOARD_PASSWORD=$new_pass/" "$ENV_FILE"
        else
            echo "DASHBOARD_PASSWORD=$new_pass" >> "$ENV_FILE"
        fi
        log_success "DASHBOARD_PASSWORD configuré"
    else
        log_success "DASHBOARD_PASSWORD valide"
    fi

    # Permissions sécurisées
    chmod 600 "$ENV_FILE"
    log_debug "Permissions .env: $(ls -la "$ENV_FILE")"

    log_success "Configuration sécurisée terminée"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 3 : PRÉPARATION DOSSIERS
# ═══════════════════════════════════════════════════════════════════════════
step_3_prepare_dirs() {
    log_step "3" "PRÉPARATION DES DOSSIERS"

    local dirs=("data" "logs" "config")

    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_success "Dossier créé: $dir/"
        else
            log_info "Dossier existant: $dir/"
        fi

        # Permissions pour Docker (UID 1000)
        chmod 755 "$dir" 2>/dev/null || true
        log_debug "Permissions $dir: $(ls -ld "$dir")"
    done

    # Config par défaut si manquant
    if [[ ! -f "config/config.yaml" ]]; then
        if [[ -f "config/config.yaml.example" ]]; then
            cp "config/config.yaml.example" "config/config.yaml"
            log_success "config.yaml copié depuis example"
        else
            log_warning "config/config.yaml absent - sera créé par le bot"
        fi
    else
        log_success "config/config.yaml présent"
    fi

    # Fichiers messages si manquants (pour éviter erreurs de montage)
    if [[ ! -f "messages.txt" ]]; then
        touch messages.txt
        log_success "messages.txt initialisé"
    fi
    if [[ ! -f "late_messages.txt" ]]; then
        touch late_messages.txt
        log_success "late_messages.txt initialisé"
    fi

    # Permissions 666 sur ces fichiers pour être sûr que le bot (UID 1000) peut écrire
    chmod 666 messages.txt late_messages.txt 2>/dev/null || true

    log_success "Dossiers préparés"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 4 : PULL DES IMAGES GHCR
# ═══════════════════════════════════════════════════════════════════════════
step_4_pull_images() {
    log_step "4" "TÉLÉCHARGEMENT DES IMAGES (GHCR)"

    log_info "Pull des images pré-construites depuis GitHub Container Registry..."
    log_debug "Compose file: $COMPOSE_FILE"

    # Vérifier la température avant le pull (opération intensive)
    if is_raspberry_pi; then
        check_cpu_temp || log_warning "Température élevée - le téléchargement peut être plus lent"
    fi

    # Arrêt des containers existants
    if [[ "$FORCE_REINSTALL" == "true" ]] || docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null | grep -q .; then
        log_info "Arrêt des containers existants..."
        start_spinner "Arrêt des services..."
        docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>&1 >> "$LOG_FILE" || true
        stop_spinner "success" "Services arrêtés"
    fi

    # Liste des images à télécharger
    local images=(
        "redis:7-alpine"
        "ghcr.io/gaspardd78/linkedin-birthday-auto-bot:latest"
        "ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest"
    )

    log_info "Téléchargement de ${#images[@]} images (peut prendre 5-15 minutes sur RPI4)..."

    local failed=0
    local img_num=0

    # Image 1: Redis
    img_num=1
    log_info "[$img_num/3] Téléchargement de redis:7-alpine..."
    if docker pull redis:7-alpine; then
        echo "redis:7-alpine téléchargé avec succès" >> "$LOG_FILE"
        log_success "[$img_num/3] redis:7-alpine téléchargé"
    else
        echo "Échec du téléchargement de redis:7-alpine" >> "$LOG_FILE"
        log_error "[$img_num/3] Échec redis:7-alpine"
        failed=$((failed + 1))
    fi

    # Image 2: Bot
    img_num=2
    log_info "[$img_num/3] Téléchargement de linkedin-birthday-auto-bot..."
    if docker pull ghcr.io/gaspardd78/linkedin-birthday-auto-bot:latest; then
        echo "linkedin-birthday-auto-bot téléchargé avec succès" >> "$LOG_FILE"
        log_success "[$img_num/3] linkedin-birthday-auto-bot téléchargé"
    else
        echo "Échec du téléchargement de linkedin-birthday-auto-bot" >> "$LOG_FILE"
        log_error "[$img_num/3] Échec linkedin-birthday-auto-bot"
        failed=$((failed + 1))
    fi

    # Image 3: Dashboard
    img_num=3
    log_info "[$img_num/3] Téléchargement de linkedin-birthday-auto-dashboard..."
    if docker pull ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest; then
        echo "linkedin-birthday-auto-dashboard téléchargé avec succès" >> "$LOG_FILE"
        log_success "[$img_num/3] linkedin-birthday-auto-dashboard téléchargé"
    else
        echo "Échec du téléchargement de linkedin-birthday-auto-dashboard" >> "$LOG_FILE"
        log_error "[$img_num/3] Échec linkedin-birthday-auto-dashboard"
        failed=$((failed + 1))
    fi

    echo ""

    if [[ $failed -gt 0 ]]; then
        log_error "$failed image(s) n'ont pas pu être téléchargées"
        log_info "Vérifiez votre connexion internet et réessayez"
        log_info "Conseil: docker compose pull"
        exit 1
    fi

    log_success "Toutes les images téléchargées avec succès"

    # Afficher la taille des images
    if [[ "$DEBUG_MODE" == "true" ]]; then
        log_debug "Images Docker présentes:"
        docker images --format "  {{.Repository}}:{{.Tag}} ({{.Size}})" | grep -E "linkedin|redis" | tee -a "$LOG_FILE" || true
    fi

    # Nettoyage des vieilles images si l'espace est limité
    local disk=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')
    if [[ "$disk" -lt 5 ]]; then
        log_info "Nettoyage des images inutilisées pour libérer de l'espace..."
        docker image prune -f >> "$LOG_FILE" 2>&1 || true
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 5 : DÉMARRAGE SÉQUENTIEL
# ═══════════════════════════════════════════════════════════════════════════
step_5_start_services() {
    log_step "5" "DÉMARRAGE SÉQUENTIEL DES SERVICES"

    # Vérifier la température avant le démarrage
    if is_raspberry_pi; then
        local temp=$(get_cpu_temp)
        if [[ "$temp" -ge "$RPI4_WARN_TEMP" ]]; then
            log_warning "CPU à ${temp}°C - Pause de 30s pour refroidissement..."
            countdown 30 "Refroidissement du CPU"
        fi
    fi

    local services_started=0
    local total_services=5

    # ─────────────────────────────────────────────────────────────────────
    # 5.1 Redis Bot
    # ─────────────────────────────────────────────────────────────────────
    echo ""
    show_progress 1 $total_services
    echo -e " ${BOLD}Redis Bot${NC}"

    log_info "5.1 Démarrage redis-bot..."
    if ! docker compose -f "$COMPOSE_FILE" up -d redis-bot 2> >(tee -a "$LOG_FILE" >&2); then
        log_error "Échec de la commande docker compose up redis-bot"
        exit 1
    fi

    if wait_container_healthy "redis-bot" "$TIMEOUT_REDIS"; then
        ((services_started++))
    else
        log_error "redis-bot n'a pas démarré correctement"
        show_troubleshooting "redis-bot"
        exit 1
    fi

    # ─────────────────────────────────────────────────────────────────────
    # 5.2 Redis Dashboard
    # ─────────────────────────────────────────────────────────────────────
    show_progress 2 $total_services
    echo -e " ${BOLD}Redis Dashboard${NC}"

    log_info "5.2 Démarrage redis-dashboard..."
    if ! docker compose -f "$COMPOSE_FILE" up -d redis-dashboard 2> >(tee -a "$LOG_FILE" >&2); then
        log_error "Échec de la commande docker compose up redis-dashboard"
        exit 1
    fi

    if wait_container_healthy "redis-dashboard" "$TIMEOUT_REDIS"; then
        ((services_started++))
    else
        log_error "redis-dashboard n'a pas démarré correctement"
        show_troubleshooting "redis-dashboard"
        exit 1
    fi

    # ─────────────────────────────────────────────────────────────────────
    # 5.3 Bot API
    # ─────────────────────────────────────────────────────────────────────
    show_progress 3 $total_services
    echo -e " ${BOLD}Bot API${NC}"

    log_info "5.3 Démarrage bot-api..."
    log_debug "Vérification API_KEY avant démarrage..."

    # Vérification critique avant démarrage
    source "$ENV_FILE" 2>/dev/null || true
    if [[ "${API_KEY:-}" == "internal_secret_key" ]]; then
        log_error "CRITIQUE: API_KEY est toujours 'internal_secret_key'!"
        log_error "Le bot refusera de démarrer pour des raisons de sécurité."
        log_info "Exécutez: sed -i \"s/API_KEY=.*/API_KEY=\$(openssl rand -hex 32)/\" .env"
        exit 1
    fi

    if ! docker compose -f "$COMPOSE_FILE" up -d api 2> >(tee -a "$LOG_FILE" >&2); then
        log_error "Échec de la commande docker compose up api"
        show_troubleshooting "bot-api"
        exit 1
    fi

    if wait_container_healthy "bot-api" "$TIMEOUT_API"; then
        ((services_started++))
    else
        log_error "bot-api n'a pas démarré correctement"
        show_troubleshooting "bot-api"
        exit 1
    fi

    # ─────────────────────────────────────────────────────────────────────
    # 5.4 Bot Worker
    # ─────────────────────────────────────────────────────────────────────
    show_progress 4 $total_services
    echo -e " ${BOLD}Bot Worker${NC}"

    log_info "5.4 Démarrage bot-worker..."
    if ! docker compose -f "$COMPOSE_FILE" up -d bot-worker 2> >(tee -a "$LOG_FILE" >&2); then
        log_error "Échec de la commande docker compose up bot-worker"
        show_troubleshooting "bot-worker"
        exit 1
    fi

    if wait_container_healthy "bot-worker" "$TIMEOUT_WORKER"; then
        ((services_started++))
    else
        log_warning "bot-worker pas encore healthy (peut être normal au premier démarrage)"
        ((services_started++))  # Compter quand même car peut être OK
    fi

    # ─────────────────────────────────────────────────────────────────────
    # 5.5 Dashboard
    # ─────────────────────────────────────────────────────────────────────
    show_progress 5 $total_services
    echo -e " ${BOLD}Dashboard${NC}"

    log_info "5.5 Démarrage dashboard..."
    if ! docker compose -f "$COMPOSE_FILE" up -d dashboard 2> >(tee -a "$LOG_FILE" >&2); then
        log_error "Échec de la commande docker compose up dashboard"
        show_troubleshooting "dashboard"
        exit 1
    fi

    if wait_container_healthy "dashboard" "$TIMEOUT_DASHBOARD"; then
        ((services_started++))
    else
        log_warning "dashboard pas encore healthy - vérifiez les logs"
    fi

    # Résumé
    echo ""
    if [[ $services_started -ge 4 ]]; then
        log_success "Services démarrés: $services_started/$total_services"
    else
        log_warning "Seulement $services_started/$total_services services démarrés"
    fi

    # Afficher la température finale
    if is_raspberry_pi; then
        local final_temp=$(get_cpu_temp)
        log_info "Température CPU finale: ${final_temp}°C"
    fi
}

# Affiche les conseils de dépannage pour un container
show_troubleshooting() {
    local container="$1"

    echo ""
    echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}${BOLD}  ÉCHEC: $container${NC}"
    echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # État du container
    local status=$(docker inspect "$container" --format='{{.State.Status}}' 2>/dev/null || echo "introuvable")
    local exit_code=$(docker inspect "$container" --format='{{.State.ExitCode}}' 2>/dev/null || echo "N/A")
    local health=$(docker inspect "$container" --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}N/A{{end}}' 2>/dev/null || echo "N/A")
    local started=$(docker inspect "$container" --format='{{.State.StartedAt}}' 2>/dev/null | cut -d'T' -f1,2 | tr 'T' ' ' || echo "N/A")
    local error_msg=$(docker inspect "$container" --format='{{.State.Error}}' 2>/dev/null || echo "")

    log_info "État du container:"
    echo "    • Status:     $status"
    echo "    • Exit code:  $exit_code"
    echo "    • Health:     $health"
    echo "    • Démarré:    $started"
    [[ -n "$error_msg" ]] && echo -e "    • Erreur:     ${RED}$error_msg${NC}"

    # Ressources utilisées
    echo ""
    log_info "Ressources système:"
    local mem_total=$(free -m | awk '/^Mem:/{print $2}')
    local mem_used=$(free -m | awk '/^Mem:/{print $3}')
    local mem_avail=$(free -m | awk '/^Mem:/{print $7}')
    local swap_used=$(free -m | awk '/^Swap:/{print $3}')
    echo "    • RAM:  ${mem_used}/${mem_total}MB utilisé (${mem_avail}MB disponible)"
    echo "    • Swap: ${swap_used}MB utilisé"

    # Conseils spécifiques par container
    echo ""
    log_info "Causes possibles:"
    case "$container" in
        "redis-bot"|"redis-dashboard")
            echo "    1. Mémoire insuffisante"
            echo "    2. Port déjà utilisé"
            echo "    3. Volume corrompu"
            echo ""
            log_info "Solutions:"
            echo "    • Libérer de la mémoire: docker system prune"
            echo "    • Vérifier les ports: netstat -tlnp | grep 6379"
            echo "    • Reset volume: docker volume rm linkedin-bot-redis-data"
            ;;
        "bot-api")
            echo "    1. API_KEY invalide ou manquante dans .env"
            echo "    2. Redis non accessible"
            echo "    3. Port 8000 déjà utilisé"
            echo ""
            log_info "Vérifications:"
            # Vérifier API_KEY
            local api_key_len=0
            if [[ -f "$ENV_FILE" ]]; then
                local api_key=$(grep -E "^API_KEY=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
                api_key_len=${#api_key}
            fi
            if [[ $api_key_len -lt 32 ]]; then
                echo -e "    ${RED}✗${NC} API_KEY trop courte: ${api_key_len} chars (min 32)"
            else
                echo -e "    ${GREEN}✓${NC} API_KEY OK: ${api_key_len} chars"
            fi
            # Vérifier Redis
            if docker exec redis-bot redis-cli ping 2>/dev/null | grep -q PONG; then
                echo -e "    ${GREEN}✓${NC} Redis accessible"
            else
                echo -e "    ${RED}✗${NC} Redis non accessible"
            fi
            ;;
        "bot-worker")
            echo "    1. Mémoire insuffisante pour Playwright (~1.8GB requis)"
            echo "    2. Swap insuffisant"
            echo "    3. Redis non accessible"
            echo ""
            log_info "Vérifications:"
            if [[ $mem_avail -lt 500 ]]; then
                echo -e "    ${RED}✗${NC} Mémoire très faible: ${mem_avail}MB"
            elif [[ $mem_avail -lt 1000 ]]; then
                echo -e "    ${YELLOW}~${NC} Mémoire limite: ${mem_avail}MB (1GB+ recommandé)"
            else
                echo -e "    ${GREEN}✓${NC} Mémoire OK: ${mem_avail}MB"
            fi
            local swap_total=$(free -m | awk '/^Swap:/{print $2}')
            if [[ $swap_total -lt 1000 ]]; then
                echo -e "    ${RED}✗${NC} Swap insuffisant: ${swap_total}MB (2GB recommandé)"
            else
                echo -e "    ${GREEN}✓${NC} Swap OK: ${swap_total}MB"
            fi
            ;;
        "dashboard")
            echo "    1. JWT_SECRET manquant ou invalide"
            echo "    2. DASHBOARD_PASSWORD manquant"
            echo "    3. Bot API non accessible"
            echo ""
            log_info "Vérifications:"
            # Vérifier JWT_SECRET
            if [[ -f "$ENV_FILE" ]]; then
                local jwt=$(grep -E "^JWT_SECRET=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
                if [[ ${#jwt} -ge 32 ]]; then
                    echo -e "    ${GREEN}✓${NC} JWT_SECRET OK"
                else
                    echo -e "    ${RED}✗${NC} JWT_SECRET manquant ou trop court"
                fi
                local dash_pass=$(grep -E "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2-)
                if [[ -n "$dash_pass" ]]; then
                    echo -e "    ${GREEN}✓${NC} DASHBOARD_PASSWORD défini"
                else
                    echo -e "    ${RED}✗${NC} DASHBOARD_PASSWORD manquant"
                fi
            fi
            # Vérifier API
            if docker exec bot-api curl -sf http://localhost:8000/health &>/dev/null; then
                echo -e "    ${GREEN}✓${NC} Bot API accessible"
            else
                echo -e "    ${RED}✗${NC} Bot API non accessible"
            fi
            ;;
    esac

    # Afficher les logs du container
    echo ""
    echo -e "${YELLOW}━━━ Derniers logs de $container ━━━${NC}"
    docker logs "$container" --tail 30 2>&1 | while IFS= read -r line; do
        # Colorier les erreurs
        if echo "$line" | grep -qiE "error|exception|fatal|failed|critical"; then
            echo -e "  ${RED}$line${NC}"
        elif echo "$line" | grep -qiE "warning|warn"; then
            echo -e "  ${YELLOW}$line${NC}"
        else
            echo "  $line"
        fi
    done
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Commandes utiles
    echo ""
    log_info "Commandes utiles:"
    echo "    • Logs complets: docker logs $container"
    echo "    • Redémarrer:    docker restart $container"
    echo "    • Shell:         docker exec -it $container /bin/sh"
    echo "    • Inspecter:     docker inspect $container"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 6 : VALIDATION FINALE
# ═══════════════════════════════════════════════════════════════════════════
step_6_validate() {
    log_step "6" "VALIDATION FINALE"

    echo ""
    log_info "État des containers:"
    docker compose -f "$COMPOSE_FILE" ps 2>&1 | tee -a "$LOG_FILE"

    echo ""
    log_info "Test de connectivité API..."

    # Test health endpoint
    local api_health=$(docker exec bot-api curl -sf http://localhost:8000/health 2>/dev/null || echo "FAIL")
    log_debug "API /health response: $api_health"

    if [[ "$api_health" != "FAIL" ]]; then
        log_success "API health check OK"
    else
        log_warning "API health check échoué - l'API peut encore démarrer"
    fi

    # Récupérer l'IP locale
    local local_ip=$(hostname -I | awk '{print $1}')
    local dashboard_port=$(grep -E "DASHBOARD_PORT=" "$ENV_FILE" | cut -d'=' -f2 || echo "3000")
    dashboard_port="${dashboard_port:-3000}"

    echo ""
    echo -e "${GREEN}${BOLD}"
    cat << EOF
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║                    ✅ INSTALLATION TERMINÉE                              ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    echo -e "📍 ${BOLD}Dashboard:${NC}      http://${local_ip}:${dashboard_port}"
    echo -e "📄 ${BOLD}Logs setup:${NC}     $LOG_FILE"
    echo -e "🔐 ${BOLD}Credentials:${NC}    Voir fichier .env"
    echo ""
    echo -e "${BOLD}Commandes utiles:${NC}"
    echo "  • Logs temps réel:   docker compose logs -f"
    echo "  • Status:            docker compose ps"
    echo "  • Redémarrer:        docker compose restart"
    echo "  • Arrêter:           docker compose down"
    echo ""

    log_success "Installation de base complète!"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 7 : HASHAGE BCRYPT DU MOT DE PASSE
# ═══════════════════════════════════════════════════════════════════════════
step_7_bcrypt_password() {
    log_step "7" "HASHAGE BCRYPT DU MOT DE PASSE"

    cat << 'EOF'
🔐 POURQUOI C'EST IMPORTANT ?
   Le mot de passe en clair dans .env peut être lu par quiconque accède au fichier.
   Avec bcrypt, le mot de passe est hashé de façon irréversible.

EOF

    # Vérifier si le mot de passe est déjà hashé
    local current_pass=$(grep -E "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')

    if [[ "$current_pass" =~ ^\$2[aby]\$ ]]; then
        log_success "Mot de passe déjà hashé avec bcrypt"
        return 0
    fi

    # Vérifier si Node.js est disponible
    if ! command -v node &>/dev/null; then
        log_warning "Node.js non disponible - hashage bcrypt ignoré"
        log_info "Pour hasher plus tard: cd dashboard && npm install bcryptjs && node scripts/hash_password.js"
        return 0
    fi

    # Vérifier si bcryptjs est installé
    if [[ ! -d "dashboard/node_modules/bcryptjs" ]]; then
        log_info "Installation de bcryptjs..."
        (cd dashboard && npm install bcryptjs --silent 2>/dev/null) || {
            log_warning "Impossible d'installer bcryptjs"
            return 0
        }
    fi

    # Vérifier si le script de hashage existe
    if [[ ! -f "dashboard/scripts/hash_password.js" ]]; then
        log_warning "Script hash_password.js non trouvé"
        return 0
    fi

    log_info "Hashage du mot de passe avec bcrypt..."

    # Générer le hash
    local password_hash
    password_hash=$(cd dashboard && node scripts/hash_password.js "$current_pass" --quiet 2>/dev/null) || {
        log_warning "Échec du hashage bcrypt"
        return 0
    }

    if [[ -z "$password_hash" || ! "$password_hash" =~ ^\$2 ]]; then
        log_warning "Hash invalide généré"
        return 0
    fi

    # Backup et mise à jour
    cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

    # Échapper le hash pour Docker Compose ($ -> $$)
    local escaped_hash="${password_hash//$/\$\$}"

    sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD='$escaped_hash'|" "$ENV_FILE"

    log_success "Mot de passe hashé avec bcrypt"
    log_debug "Hash: ${password_hash:0:20}..."

    # Redémarrer le dashboard pour appliquer
    log_info "Redémarrage du dashboard..."
    docker compose -f "$COMPOSE_FILE" restart dashboard 2>&1 | tee -a "$LOG_FILE" || true
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 8 : PROTECTION CORS
# ═══════════════════════════════════════════════════════════════════════════
step_8_cors_protection() {
    log_step "8" "PROTECTION CORS"

    cat << 'EOF'
🛡️ POURQUOI C'EST IMPORTANT ?
   CORS empêche des sites malveillants d'accéder à votre API.
   Sans CORS, n'importe quel site pourrait faire des requêtes à votre bot.

EOF

    # Vérifier si ALLOWED_ORIGINS est déjà configuré
    if grep -q "^ALLOWED_ORIGINS=" "$ENV_FILE" 2>/dev/null; then
        local current_origins=$(grep "^ALLOWED_ORIGINS=" "$ENV_FILE" | cut -d'=' -f2-)
        if [[ -n "$current_origins" && "$current_origins" != "http://localhost:3000" ]]; then
            log_success "CORS déjà configuré: $current_origins"
            return 0
        fi
    fi

    # Récupérer l'IP locale
    local local_ip=$(hostname -I | awk '{print $1}')
    local dashboard_port=$(grep -E "^DASHBOARD_PORT=" "$ENV_FILE" | cut -d'=' -f2 || echo "3000")
    dashboard_port="${dashboard_port:-3000}"

    echo -e -n "${CYAN}❓${NC} Domaine pour CORS (ex: https://monbot.com) [http://${local_ip}:${dashboard_port}]: "
    read -r cors_domain
    cors_domain="${cors_domain:-http://${local_ip}:${dashboard_port}}"

    # Mettre à jour .env
    if grep -q "^ALLOWED_ORIGINS=" "$ENV_FILE"; then
        sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=$cors_domain|" "$ENV_FILE"
    else
        echo "ALLOWED_ORIGINS=$cors_domain" >> "$ENV_FILE"
    fi

    log_success "CORS configuré: $cors_domain"

    # Redémarrer l'API
    log_info "Redémarrage de l'API..."
    docker compose -f "$COMPOSE_FILE" restart api 2>&1 | tee -a "$LOG_FILE" || true
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 9 : ANTI-INDEXATION
# ═══════════════════════════════════════════════════════════════════════════
step_9_anti_indexation() {
    log_step "9" "ANTI-INDEXATION GOOGLE"

    cat << 'EOF'
🚫 POURQUOI C'EST IMPORTANT ?
   Sans protection, Google peut indexer votre dashboard.
   N'importe qui pourrait trouver votre bot en cherchant sur Google.

EOF

    # Créer robots.txt si absent
    local robots_file="dashboard/public/robots.txt"

    if [[ -f "$robots_file" ]] && grep -q "Disallow: /" "$robots_file"; then
        log_success "robots.txt déjà configuré"
    else
        mkdir -p "dashboard/public"
        cat > "$robots_file" << 'ROBOTS'
# LinkedIn Birthday Bot - Anti-indexation
User-agent: *
Disallow: /
Disallow: /api/
Disallow: /login
Disallow: /dashboard

# Block all known bots
User-agent: Googlebot
Disallow: /

User-agent: Bingbot
Disallow: /

User-agent: Slurp
Disallow: /

User-agent: DuckDuckBot
Disallow: /

User-agent: Baiduspider
Disallow: /

User-agent: YandexBot
Disallow: /
ROBOTS
        log_success "robots.txt créé"
    fi

    # Vérifier les headers X-Robots-Tag dans next.config.js
    if [[ -f "dashboard/next.config.js" ]]; then
        if grep -q "X-Robots-Tag" "dashboard/next.config.js"; then
            log_success "Headers X-Robots-Tag déjà configurés dans Next.js"
        else
            log_info "Ajout recommandé: headers X-Robots-Tag dans next.config.js"
        fi
    fi

    log_success "Anti-indexation configurée"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 10 : HTTPS AVEC LET'S ENCRYPT (OPTIONNEL)
# ═══════════════════════════════════════════════════════════════════════════
step_10_https_letsencrypt() {
    log_step "10" "HTTPS AVEC LET'S ENCRYPT"

    cat << 'EOF'
🔐 POURQUOI C'EST IMPORTANT ?
   Sans HTTPS, vos mots de passe circulent en CLAIR sur Internet.
   HTTPS chiffre toutes les communications.

⚠️  PRÉREQUIS :
   • Nom de domaine pointant vers votre IP publique
   • Ports 80 et 443 ouverts sur votre box/routeur
   • Accès root/sudo

EOF

    if ! ask_continue "Configurer HTTPS avec Let's Encrypt ?"; then
        log_info "Configuration HTTPS ignorée"
        return 0
    fi

    # Vérifier si Nginx est installé
    if ! command -v nginx &>/dev/null; then
        log_info "Installation de Nginx..."
        sudo apt update && sudo apt install -y nginx || {
            log_error "Impossible d'installer Nginx"
            return 1
        }
    fi
    log_success "Nginx installé"

    # Vérifier si Certbot est installé
    if ! command -v certbot &>/dev/null; then
        log_info "Installation de Certbot..."
        sudo apt install -y certbot python3-certbot-nginx || {
            log_error "Impossible d'installer Certbot"
            return 1
        }
    fi
    log_success "Certbot installé"

    # Demander le nom de domaine
    echo -e -n "${CYAN}❓${NC} Votre nom de domaine (ex: bot.exemple.com): "
    read -r domain_name

    if [[ -z "$domain_name" ]]; then
        log_error "Nom de domaine requis"
        return 1
    fi

    # Créer la configuration Nginx
    log_info "Configuration de Nginx pour $domain_name..."

    local nginx_conf="/etc/nginx/sites-available/linkedin-bot"
    sudo tee "$nginx_conf" > /dev/null << NGINX
# LinkedIn Birthday Bot - Nginx Configuration
# Generated by setup.sh

server {
    listen 80;
    server_name $domain_name;

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}

server {
    listen 443 ssl http2;
    server_name $domain_name;

    # SSL will be configured by Certbot

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Robots-Tag "noindex, nofollow" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Dashboard (Next.js)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

    # Activer le site
    sudo ln -sf "$nginx_conf" /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

    # Tester la configuration
    if ! sudo nginx -t; then
        log_error "Configuration Nginx invalide"
        return 1
    fi

    sudo systemctl reload nginx
    log_success "Nginx configuré"

    # Obtenir le certificat SSL
    log_info "Obtention du certificat SSL (Let's Encrypt)..."
    log_info "Assurez-vous que le port 80 est accessible depuis Internet"

    if sudo certbot --nginx -d "$domain_name" --non-interactive --agree-tos --register-unsafely-without-email; then
        log_success "Certificat SSL installé!"
        log_info "Accès sécurisé: https://$domain_name"

        # Mettre à jour ALLOWED_ORIGINS
        sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://$domain_name|" "$ENV_FILE"
        docker compose -f "$COMPOSE_FILE" restart api 2>&1 | tee -a "$LOG_FILE" || true
    else
        log_error "Échec de l'obtention du certificat"
        log_info "Vérifiez que:"
        log_info "  1. Le domaine $domain_name pointe vers votre IP"
        log_info "  2. Le port 80 est ouvert sur votre box"
        log_info "  3. Réessayez: sudo certbot --nginx -d $domain_name"
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 11 : BACKUP GOOGLE DRIVE (OPTIONNEL)
# ═══════════════════════════════════════════════════════════════════════════
step_11_gdrive_backup() {
    log_step "11" "BACKUP AUTOMATIQUE GOOGLE DRIVE"

    cat << 'EOF'
💾 POURQUOI C'EST IMPORTANT ?
   Sans backup, si votre serveur plante, vous perdez TOUT.
   Le backup Google Drive sauvegarde automatiquement chaque nuit.

⚠️  PRÉREQUIS :
   • Compte Google
   • Possibilité d'ouvrir un navigateur (ou configuration headless)

EOF

    if ! ask_continue "Configurer le backup Google Drive ?"; then
        log_info "Configuration backup ignorée"
        return 0
    fi

    # Vérifier si rclone est installé
    if ! command -v rclone &>/dev/null; then
        log_info "Installation de rclone..."
        curl https://rclone.org/install.sh | sudo bash || {
            log_error "Impossible d'installer rclone"
            return 1
        }
    fi
    log_success "rclone installé"

    # Vérifier si Google Drive est déjà configuré
    if rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
        log_success "Google Drive déjà configuré dans rclone"

        if ask_continue "Tester la connexion Google Drive ?"; then
            if rclone lsd gdrive: &>/dev/null; then
                log_success "Connexion Google Drive OK"
            else
                log_warning "Connexion échouée - reconfigurez avec: rclone config"
            fi
        fi
    else
        log_info "Configuration de Google Drive..."
        cat << 'INSTRUCTIONS'

📱 INSTRUCTIONS RCLONE :
   1. Tapez: gdrive (comme nom)
   2. Tapez: drive (comme storage)
   3. Appuyez Entrée pour client_id et client_secret (vide)
   4. Tapez: 1 pour scope (Full access)
   5. Appuyez Entrée pour service_account_file (vide)
   6. Tapez: n pour advanced config
   7. Tapez: y pour auto authenticate (si navigateur disponible)
   8. Autorisez dans le navigateur
   9. Tapez: n pour team drive
   10. Tapez: y pour confirmer

INSTRUCTIONS

        if ask_continue "Lancer la configuration rclone maintenant ?"; then
            rclone config

            if rclone listremotes | grep -q "gdrive:"; then
                log_success "Google Drive configuré!"
            else
                log_warning "Configuration incomplète"
                return 1
            fi
        fi
    fi

    # Vérifier le script de backup
    local backup_script="scripts/backup_to_gdrive.sh"

    if [[ ! -f "$backup_script" ]]; then
        log_info "Création du script de backup..."
        mkdir -p scripts
        cat > "$backup_script" << 'BACKUP'
#!/bin/bash
# Backup LinkedIn Bot vers Google Drive

set -e

BACKUP_DIR="LinkedInBot_Backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${DATE}"

echo "[$(date)] Démarrage du backup..."

# Créer le dossier distant si nécessaire
rclone mkdir "gdrive:${BACKUP_DIR}" 2>/dev/null || true

# Backup des données
rclone copy ./data "gdrive:${BACKUP_DIR}/${BACKUP_NAME}/data" --progress
rclone copy ./config "gdrive:${BACKUP_DIR}/${BACKUP_NAME}/config" --progress
rclone copy ./.env "gdrive:${BACKUP_DIR}/${BACKUP_NAME}/" --progress 2>/dev/null || true

# Nettoyer les backups > 30 jours
rclone delete "gdrive:${BACKUP_DIR}" --min-age 30d 2>/dev/null || true

echo "[$(date)] Backup terminé: ${BACKUP_NAME}"
BACKUP
        chmod +x "$backup_script"
        log_success "Script de backup créé"
    fi

    # Tester le backup
    if ask_continue "Tester le backup maintenant ?"; then
        log_info "Exécution du backup de test..."
        if bash "$backup_script"; then
            log_success "Backup de test réussi!"
        else
            log_warning "Backup échoué - vérifiez la configuration rclone"
        fi
    fi

    # Configurer le cron
    log_info "Configuration du backup automatique (cron)..."

    local cron_line="0 3 * * * $(pwd)/$backup_script >> /var/log/linkedin-bot-backup.log 2>&1"

    if crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"; then
        log_success "Backup automatique déjà configuré"
    else
        if ask_continue "Activer le backup automatique quotidien (3h du matin) ?"; then
            (crontab -l 2>/dev/null; echo "$cron_line") | crontab -
            log_success "Backup automatique configuré"
            log_info "Logs: /var/log/linkedin-bot-backup.log"
        fi
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE FINALE : RÉSUMÉ SÉCURITÉ
# ═══════════════════════════════════════════════════════════════════════════
step_final_security_summary() {
    log_step "✓" "RÉSUMÉ DE SÉCURITÉ"

    echo ""
    log_info "Vérification de la configuration sécurité..."
    echo ""

    local score=0
    local max_score=6

    # 1. API_KEY
    local api_key=$(grep -E "^API_KEY=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
    if [[ ${#api_key} -ge 32 && "$api_key" != "internal_secret_key"* ]]; then
        echo -e "  ${GREEN}✓${NC} API_KEY sécurisée"
        ((score++))
    else
        echo -e "  ${RED}✗${NC} API_KEY non sécurisée"
    fi

    # 2. JWT_SECRET
    local jwt=$(grep -E "^JWT_SECRET=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
    if [[ ${#jwt} -ge 32 ]]; then
        echo -e "  ${GREEN}✓${NC} JWT_SECRET sécurisé"
        ((score++))
    else
        echo -e "  ${RED}✗${NC} JWT_SECRET non sécurisé"
    fi

    # 3. Password hashé
    local pass=$(grep -E "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
    if [[ "$pass" =~ ^\$2 ]]; then
        echo -e "  ${GREEN}✓${NC} Mot de passe hashé (bcrypt)"
        ((score++))
    else
        echo -e "  ${YELLOW}~${NC} Mot de passe en clair"
    fi

    # 4. CORS
    local cors=$(grep -E "^ALLOWED_ORIGINS=" "$ENV_FILE" | cut -d'=' -f2-)
    if [[ -n "$cors" && "$cors" != "http://localhost:3000" ]]; then
        echo -e "  ${GREEN}✓${NC} CORS configuré: $cors"
        ((score++))
    else
        echo -e "  ${YELLOW}~${NC} CORS par défaut (localhost)"
    fi

    # 5. robots.txt
    if [[ -f "dashboard/public/robots.txt" ]] && grep -q "Disallow: /" "dashboard/public/robots.txt"; then
        echo -e "  ${GREEN}✓${NC} Anti-indexation (robots.txt)"
        ((score++))
    else
        echo -e "  ${YELLOW}~${NC} Anti-indexation non configurée"
    fi

    # 6. HTTPS
    if command -v certbot &>/dev/null && sudo certbot certificates 2>/dev/null | grep -q "Certificate Name:"; then
        echo -e "  ${GREEN}✓${NC} HTTPS (Let's Encrypt)"
        ((score++))
    else
        echo -e "  ${YELLOW}~${NC} HTTPS non configuré"
    fi

    echo ""
    echo -e "${BOLD}Score sécurité: ${score}/${max_score}${NC}"

    if [[ $score -ge 5 ]]; then
        echo -e "${GREEN}🔒 Excellent! Configuration très sécurisée.${NC}"
    elif [[ $score -ge 3 ]]; then
        echo -e "${YELLOW}🔓 Correct. Quelques améliorations possibles.${NC}"
    else
        echo -e "${RED}⚠️  Attention! Configuration à améliorer.${NC}"
    fi

    echo ""
    log_success "Consultez $LOG_FILE pour les détails complets."
}

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
main() {
    # Parser les arguments CLI
    parse_args "$@"

    print_banner
    log_init

    # Afficher info version et mode
    log_info "LinkedIn Birthday Bot - Setup v${SCRIPT_VERSION}"
    log_info "Optimisé pour Raspberry Pi 4"

    if [[ "$DEBUG_MODE" != "true" ]]; then
        log_info "Pour activer le mode debug: DEBUG=true ./setup.sh"
    fi
    echo ""

    # Résumé des options en mode non-interactif
    if [[ "$UNATTENDED_MODE" == "true" ]]; then
        log_info "Mode non-interactif activé"
        [[ "$SKIP_PHASE2" == "true" ]] && log_info "Phase 2 sera ignorée"
        [[ "$QUICK_MODE" == "true" ]] && log_info "Mode rapide activé"
    fi

    if ! ask_continue "Démarrer l'installation ?"; then
        log_info "Installation annulée par l'utilisateur"
        exit 0
    fi

    # ─────────────────────────────────────────────────────────────────────
    # PHASE 1: Installation de base
    # ─────────────────────────────────────────────────────────────────────
    local phase1_start=$(date +%s)

    step_0_init
    step_1_prerequisites
    step_2_security_config
    step_3_prepare_dirs

    if ! ask_continue "Télécharger les images et démarrer les services ?"; then
        log_info "Déploiement annulé - Configuration sauvegardée"
        log_info "Pour reprendre: ./setup.sh --resume"
        exit 0
    fi

    step_4_pull_images
    step_5_start_services
    step_6_validate

    local phase1_end=$(date +%s)
    local phase1_duration=$((phase1_end - phase1_start))
    log_info "Phase 1 terminée en ${phase1_duration}s"

    # ─────────────────────────────────────────────────────────────────────
    # PHASE 2: Sécurisation avancée (optionnel)
    # ─────────────────────────────────────────────────────────────────────
    if [[ "$SKIP_PHASE2" == "true" ]]; then
        log_info "Phase 2 ignorée (--skip-phase2)"
    else
        echo ""
        echo -e "${MAGENTA}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${MAGENTA}${BOLD}  PHASE 2 : SÉCURISATION AVANCÉE (Optionnel)${NC}"
        echo -e "${MAGENTA}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        if [[ "$QUICK_MODE" != "true" ]]; then
            cat << 'EOF'
La sécurisation avancée comprend :
  • Hashage bcrypt du mot de passe
  • Protection CORS
  • Anti-indexation Google
  • HTTPS avec Let's Encrypt
  • Backup automatique Google Drive

EOF
        fi

        if ask_continue "Continuer avec la sécurisation avancée ?"; then
            step_7_bcrypt_password
            step_8_cors_protection
            step_9_anti_indexation

            if ask_continue "Configurer HTTPS (nécessite un nom de domaine) ?"; then
                step_10_https_letsencrypt
            fi

            if ask_continue "Configurer le backup Google Drive ?"; then
                step_11_gdrive_backup
            fi

            step_final_security_summary
        else
            log_info "Sécurisation avancée ignorée"
            log_info "Pour la configurer plus tard: ./scripts/setup_security.sh"
        fi
    fi

    # ─────────────────────────────────────────────────────────────────────
    # FIN
    # ─────────────────────────────────────────────────────────────────────
    local total_duration=$(($(date +%s) - phase1_start))

    echo ""
    echo -e "${GREEN}${BOLD}"
    cat << EOF
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║                    🎉 INSTALLATION COMPLÈTE                              ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    local local_ip=$(hostname -I | awk '{print $1}')
    local dashboard_port=$(grep -E "^DASHBOARD_PORT=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "3000")

    echo -e "📍 ${BOLD}Dashboard:${NC}      http://${local_ip}:${dashboard_port:-3000}"
    echo -e "📄 ${BOLD}Logs setup:${NC}     $LOG_FILE"
    echo -e "🔐 ${BOLD}Credentials:${NC}    Fichier .env"
    echo -e "⏱️  ${BOLD}Durée totale:${NC}   ${total_duration}s"
    echo ""
    echo -e "${BOLD}Commandes utiles:${NC}"
    echo "  • Logs:        docker compose logs -f"
    echo "  • Status:      docker compose ps"
    echo "  • Redémarrer:  docker compose restart"
    echo "  • Arrêter:     docker compose down"
    echo ""

    # Afficher la température finale sur RPI4
    if is_raspberry_pi; then
        local final_temp=$(get_cpu_temp)
        if [[ "$final_temp" -gt 0 ]]; then
            echo -e "🌡️  ${BOLD}Température CPU:${NC} ${final_temp}°C"
            echo ""
        fi
    fi

    log_success "Installation terminée avec succès!"
}

# ═══════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ═══════════════════════════════════════════════════════════════════════════

# Gestion du signal CTRL+C
trap 'stop_spinner; echo ""; log_warning "Installation interrompue"; exit 130' INT TERM

# Lancer le script
main "$@"
