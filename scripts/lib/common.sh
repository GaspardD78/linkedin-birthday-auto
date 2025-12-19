#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - COMMON LIBRARY (v4.0)
# Logging, utility functions, and user interaction
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === COLORS & FORMATTING ===

readonly BLUE='\033[0;34m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'
readonly BOLD='\033[1m'
readonly DIM='\033[2m'

# === LOGGING FUNCTIONS ===

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

log_step() {
    echo -e "\n${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
    sleep 2
}

# === PROGRESS INDICATORS ===

# Variables globales pour le suivi de progression
PROGRESS_CURRENT=0
PROGRESS_TOTAL=0
PROGRESS_PHASE=""

# Initialise une nouvelle séquence de progression
# Usage: progress_init "Phase Name" 5
progress_init() {
    PROGRESS_PHASE="$1"
    PROGRESS_TOTAL="$2"
    PROGRESS_CURRENT=0
    echo -e "\n${BOLD}${BLUE}┌─ ${PROGRESS_PHASE} (0/${PROGRESS_TOTAL})${NC}"
}

# Avance à l'étape suivante avec description
# Usage: progress_step "Description de l'étape"
progress_step() {
    local description="$1"
    PROGRESS_CURRENT=$((PROGRESS_CURRENT + 1))

    # Générer la barre de progression
    local bar_width=30
    local filled=$((PROGRESS_CURRENT * bar_width / PROGRESS_TOTAL))
    local empty=$((bar_width - filled))
    local percent=$((PROGRESS_CURRENT * 100 / PROGRESS_TOTAL))

    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+="░"; done

    echo -e "${BLUE}│${NC} ${DIM}[${PROGRESS_CURRENT}/${PROGRESS_TOTAL}]${NC} ${description}"
    echo -e "${BLUE}│${NC} ${GREEN}${bar}${NC} ${percent}%"
}

# Marque l'étape actuelle comme terminée avec succès
# Usage: progress_done "Message optionnel"
progress_done() {
    local message="${1:-Terminé}"
    echo -e "${BLUE}│${NC}   ${GREEN}✓${NC} ${message}"
}

# Marque l'étape actuelle comme échouée
# Usage: progress_fail "Message d'erreur"
progress_fail() {
    local message="${1:-Échec}"
    echo -e "${BLUE}│${NC}   ${RED}✗${NC} ${message}"
}

# Termine la séquence de progression
# Usage: progress_end
progress_end() {
    if [[ $PROGRESS_CURRENT -eq $PROGRESS_TOTAL ]]; then
        echo -e "${BOLD}${GREEN}└─ ${PROGRESS_PHASE} terminé avec succès ✓${NC}\n"
    else
        echo -e "${BOLD}${YELLOW}└─ ${PROGRESS_PHASE} incomplet (${PROGRESS_CURRENT}/${PROGRESS_TOTAL})${NC}\n"
    fi
}

# Affiche un spinner pendant une opération
# Usage: run_with_spinner "message" command args...
run_with_spinner() {
    local message="$1"
    shift
    local spinchars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local pid
    local i=0

    # Démarrer la commande en arrière-plan
    "$@" &
    pid=$!

    # Afficher le spinner
    echo -ne "${BLUE}│${NC} ${message} "
    while kill -0 $pid 2>/dev/null; do
        i=$(( (i+1) % ${#spinchars} ))
        echo -ne "\r${BLUE}│${NC} ${message} ${YELLOW}${spinchars:$i:1}${NC} "
        sleep 0.1
    done

    # Vérifier le code de retour
    wait $pid
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        echo -e "\r${BLUE}│${NC} ${message} ${GREEN}✓${NC}  "
    else
        echo -e "\r${BLUE}│${NC} ${message} ${RED}✗${NC}  "
    fi

    return $exit_code
}

# === UTILITY FUNCTIONS ===

cmd_exists() {
    command -v "$1" &> /dev/null
}

check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        log_warn "Privilèges sudo requis."
        sudo true || { log_error "Sudo refusé."; exit 1; }
    fi
}

get_total_memory_gb() {
    local ram_kb swap_kb total_kb
    ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    swap_kb=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
    total_kb=$((ram_kb + swap_kb))
    echo $((total_kb / 1024 / 1024))
}

# === BACKUP & FILE OPERATIONS ===

backup_file() {
    local file="$1"
    local description="${2:-backup}"
    local backup_dir=".setup_backups"

    if [[ ! -f "$file" ]]; then
        log_warn "Fichier à sauvegarder n'existe pas: $file"
        return 0
    fi

    mkdir -p "$backup_dir"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${backup_dir}/${file##*/}.${timestamp}.bak"

    cp "$file" "$backup_file"
    log_info "✓ Backup: $file -> $backup_file"
    echo "$backup_file"
}

cleanup_temp_files() {
    # Nettoyer les fichiers temporaires de setup
    rm -f /tmp/setup_* 2>/dev/null || true
}

# === USER INTERACTION ===

prompt_yes_no() {
    local question="$1"
    local default="${2:-}"
    local timeout=30
    local reply

    if [[ "$default" == "y" ]]; then
        echo -ne "${YELLOW}${question} [Y/n] : ${NC}"
    elif [[ "$default" == "n" ]]; then
        echo -ne "${YELLOW}${question} [y/N] : ${NC}"
    else
        echo -ne "${YELLOW}${question} [y/n] : ${NC}"
    fi

    # Vérifier si stdin est un TTY (mode interactif)
    if [[ ! -t 0 ]]; then
        # Non-interactif: utiliser la valeur par défaut ou "n"
        reply="${default:-n}"
        log_warn "Mode non-interactif, utilisation de la réponse par défaut: $reply" >&2
    else
        # Mode interactif: lire avec timeout
        read -r -t "$timeout" reply || reply="$default"
    fi

    if [[ -z "$reply" && -z "$default" ]]; then
        log_error "Pas de réponse (timeout ${timeout}s)"
        return 1
    fi

    case "$reply" in
        [Yy]|"") [[ "$default" != "n" ]] && return 0 || return 1 ;;
        [Nn]|"") [[ "$default" == "n" ]] && return 0 || return 1 ;;
        *) log_error "Réponse invalide. Veuillez répondre par 'y' ou 'n'"; return 2 ;;
    esac
}

prompt_menu() {
    local title="$1"
    shift
    local options=("$@")
    local choice
    local timeout=30

    echo -e "\n${BOLD}${BLUE}${title}${NC}\n" >&2

    local i=1
    for option in "${options[@]}"; do
        echo "  ${BOLD}${i})${NC} ${option}" >&2
        i=$((i + 1))
    done

    # Vérifier si stdin est un TTY (mode interactif)
    if [[ ! -t 0 ]]; then
        # Non-interactif: utiliser le premier choix par défaut
        log_warn "Mode non-interactif détecté, utilisation de la première option" >&2
        echo "1"
        return 0
    fi

    echo -ne "\n${YELLOW}Votre choix [1-$#] (timeout ${timeout}s) : ${NC}" >&2

    # Lire l'entrée avec timeout
    if ! read -r -t "$timeout" choice; then
        # Timeout: utiliser le premier choix par défaut
        log_warn "Timeout (${timeout}s), utilisation de la première option" >&2
        echo "1"
        return 0
    fi

    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [[ "$choice" -lt 1 ]] || [[ "$choice" -gt $# ]]; then
        log_error "Choix invalide. Veuillez entrer un nombre entre 1 et $#" >&2
        return 2
    fi

    echo "$choice"
    return 0
}

# === KERNEL & SYSTEM CONFIG ===

configure_kernel_params() {
    local sysctl_file="/etc/sysctl.d/99-rpi4-docker.conf"
    log_info "Configuration des paramètres kernel pour RPi4..."

    if [[ -f "$sysctl_file" ]]; then
        if grep -q "vm.overcommit_memory" "$sysctl_file" && \
           grep -q "net.core.somaxconn" "$sysctl_file" && \
           grep -q "vm.swappiness" "$sysctl_file"; then
            log_info "Paramètres kernel déjà configurés."
            return 0
        fi
    fi

    check_sudo
    sudo tee "$sysctl_file" > /dev/null <<'EOF'
# Configuration kernel optimisée pour LinkedIn Bot sur Raspberry Pi 4
vm.overcommit_memory = 1
net.core.somaxconn = 1024
vm.swappiness = 10
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 5
EOF
    sudo sysctl -p "$sysctl_file" > /dev/null 2>&1
    log_success "Paramètres kernel configurés (overcommit_memory=1, swappiness=10)."
}

configure_zram() {
    log_info "Configuration ZRAM (Swap compressé en RAM)..."
    if lsblk | grep -q "zram0"; then
        log_info "ZRAM déjà configuré et actif"
        return 0
    fi
    if ! modprobe zram 2>/dev/null; then
        log_warn "Module ZRAM non disponible. Skip."
        return 0
    fi

    check_sudo
    local ZRAM_SIZE="1G"
    sudo modprobe zram num_devices=1
    echo lz4 | sudo tee /sys/block/zram0/comp_algorithm > /dev/null
    echo "$ZRAM_SIZE" | sudo tee /sys/block/zram0/disksize > /dev/null
    sudo mkswap /dev/zram0
    sudo swapon -p 10 /dev/zram0

    if ! grep -q "zram" /etc/modules 2>/dev/null; then
        echo "zram" | sudo tee -a /etc/modules > /dev/null
    fi

    local ZRAM_SERVICE="/etc/systemd/system/zram-swap.service"
    if [[ ! -f "$ZRAM_SERVICE" ]]; then
        sudo tee "$ZRAM_SERVICE" > /dev/null <<'EOF'
[Unit]
Description=ZRAM Compressed Swap
After=local-fs.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'modprobe zram num_devices=1 && echo lz4 > /sys/block/zram0/comp_algorithm && echo 1G > /sys/block/zram0/disksize && mkswap /dev/zram0 && swapon -p 10 /dev/zram0'
ExecStop=/bin/sh -c 'swapoff /dev/zram0 && rmmod zram'

[Install]
WantedBy=multi-user.target
EOF
        sudo systemctl daemon-reload
        sudo systemctl enable zram-swap.service
    fi

    log_success "ZRAM activé (1GB) et rendu persistant."
}

configure_docker_ipv4() {
    local daemon_json="/etc/docker/daemon.json"
    local needs_restart=false
    local target_config='{
  "ipv6": false,
  "ip6tables": false,
  "dns": ["1.1.1.1", "8.8.8.8", "8.8.4.4"],
  "dns-opts": ["timeout:2", "attempts:3"],
  "registry-mirrors": []
}'

    if [[ -f "$daemon_json" ]]; then
        if grep -q '"ip6tables": false' "$daemon_json" 2>/dev/null && \
           grep -q '"dns"' "$daemon_json" 2>/dev/null; then
            log_info "Docker déjà configuré (IPv4 + DNS fiables)."
            return 0
        fi
    fi

    log_info "Configuration de Docker (IPv4 + DNS fiables Cloudflare/Google)..."
    check_sudo

    if [[ ! -f "$daemon_json" ]]; then
        echo "$target_config" | sudo tee "$daemon_json" > /dev/null
        needs_restart=true
    else
        local temp_file=$(mktemp)
        if command -v jq &> /dev/null; then
            sudo jq '. + {"ipv6": false, "ip6tables": false, "dns": ["1.1.1.1", "8.8.8.8", "8.8.4.4"], "dns-opts": ["timeout:2", "attempts:3"]}' "$daemon_json" > "$temp_file"
            sudo mv "$temp_file" "$daemon_json"
        else
            log_warn "jq non disponible, remplacement complet de daemon.json"
            echo "$target_config" | sudo tee "$daemon_json" > /dev/null
        fi
        needs_restart=true
    fi

    if [[ "$needs_restart" == "true" ]]; then
        log_info "Redémarrage du daemon Docker..."
        sudo systemctl restart docker
        sleep 3
        log_success "Docker redémarré avec IPv4 + DNS fiables."
    fi
}
