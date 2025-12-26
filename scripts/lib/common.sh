#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - COMMON LIBRARY (v5.0 - SUPER ORCHESTRATEUR)
# UI immersive, spinners, progress bars, et utilitaires
# Expert DevOps avec obsession UX/DX
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Sourcing logging first to ensure colors and log functions are available
# if common.sh is sourced independently.
# Use a local variable to avoid overwriting SCRIPT_DIR from the parent script
_COMMON_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$_COMMON_SCRIPT_DIR/logging.sh" ]]; then
    source "$_COMMON_SCRIPT_DIR/logging.sh"
fi

# === BANNERS & UI ELEMENTS ===

# Bannière de bienvenue (Super Orchestrateur)
show_welcome_banner() {
    local version="${1:-5.0}"
    local project_name="${2:-LinkedIn Birthday Auto}"

    cat << "EOF"

╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║     █████╗ ██╗   ██╗████████╗ ██████╗       ██████╗  ██████╗ ████████╗  ║
║    ██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗      ██╔══██╗██╔═══██╗╚══██╔══╝  ║
║    ███████║██║   ██║   ██║   ██║   ██║█████╗██████╔╝██║   ██║   ██║     ║
║    ██╔══██║██║   ██║   ██║   ██║   ██║╚════╝██╔══██╗██║   ██║   ██║     ║
║    ██║  ██║╚██████╔╝   ██║   ╚██████╔╝      ██████╔╝╚██████╔╝   ██║     ║
║    ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝       ╚═════╝  ╚═════╝    ╚═╝     ║
║                                                                           ║
EOF

    echo -e "${BOLD}${BLUE}║           🎂 LINKEDIN BIRTHDAY AUTO - SUPER ORCHESTRATEUR 🎂          ║${NC}"
    echo -e "${BOLD}${BLUE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}  Version      : ${BOLD}${version}${NC}"
    echo -e "${CYAN}  Plateforme   : ${BOLD}Raspberry Pi 4 (ARM64)${NC}"
    echo -e "${CYAN}  Architecture : ${BOLD}Docker Compose Standalone${NC}"
    echo -e "${CYAN}  Date         : ${BOLD}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo ""
    echo -e "${GREEN}  ✓ Installation fiable et robuste${NC}"
    echo -e "${GREEN}  ✓ Configuration Cloud guidée (Headless)${NC}"
    echo -e "${GREEN}  ✓ Audit final complet${NC}"
    echo -e "${GREEN}  ✓ Logs centralisés${NC}"
    echo ""
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Bannière de fin (Résumé)
show_completion_banner() {
    local status="${1:-success}" # success | warning | error
    local message="${2:-Installation terminée}"

    echo ""
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"

    case "$status" in
        success)
            echo -e "${BOLD}${GREEN}  ✓ $message${NC}"
            ;;
        warning)
            echo -e "${BOLD}${YELLOW}  ⚠ $message${NC}"
            ;;
        error)
            echo -e "${BOLD}${RED}  ✗ $message${NC}"
            ;;
    esac

    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# === PROGRESS INDICATORS (Barres de progression améliorées) ===

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
    echo -e "\n${BOLD}${BLUE}┌─ 🔄 ${PROGRESS_PHASE} (0/${PROGRESS_TOTAL})${NC}"
}

# Avance à l'étape suivante avec description
# Usage: progress_step "Description de l'étape"
progress_step() {
    local description="$1"
    PROGRESS_CURRENT=$((PROGRESS_CURRENT + 1))

    # Générer la barre de progression avec émojis
    local bar_width=40
    local filled=$((PROGRESS_CURRENT * bar_width / PROGRESS_TOTAL))
    local empty=$((bar_width - filled))
    local percent=$((PROGRESS_CURRENT * 100 / PROGRESS_TOTAL))

    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+="░"; done

    echo -e "${BLUE}│${NC}"
    echo -e "${BLUE}│${NC} ${BOLD}${DIM}[${PROGRESS_CURRENT}/${PROGRESS_TOTAL}]${NC} ${description}"
    echo -e "${BLUE}│${NC} ${GREEN}${bar}${NC} ${BOLD}${percent}%${NC}"
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
        echo -e "${BOLD}${GREEN}└─ ✓ ${PROGRESS_PHASE} terminé avec succès${NC}\n"
    else
        echo -e "${BOLD}${YELLOW}└─ ⚠ ${PROGRESS_PHASE} incomplet (${PROGRESS_CURRENT}/${PROGRESS_TOTAL})${NC}\n"
    fi
}

# === SPINNERS (Indicateurs de chargement) ===

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
        echo -ne "\r${BLUE}│${NC} ${message} ${CYAN}${spinchars:$i:1}${NC} "
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

# Spinner simple pour les opérations courtes
# Usage: simple_spinner &lt;durée_secondes&gt; "message"
simple_spinner() {
    local duration="$1"
    local message="${2:-Chargement}"
    local spinchars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0
    local elapsed=0

    echo -ne "${CYAN}${message} ${NC}"
    while [[ $elapsed -lt $duration ]]; do
        i=$(( (i+1) % ${#spinchars} ))
        echo -ne "\r${CYAN}${message} ${spinchars:$i:1}${NC} "
        sleep 0.1
        elapsed=$((elapsed + 1))
    done
    echo -e "\r${CYAN}${message} ${GREEN}✓${NC}  "
}

# === BARRE DE PROGRESSION POUR TÂCHES LONGUES (ex: Docker Pull) ===

# Affiche une barre de progression animée
# Usage: show_progress_bar &lt;current&gt; &lt;total&gt; "message"
show_progress_bar() {
    local current="$1"
    local total="$2"
    local message="${3:-Progression}"
    local bar_width=50

    local filled=$((current * bar_width / total))
    local empty=$((bar_width - filled))
    local percent=$((current * 100 / total))

    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+="░"; done

    echo -ne "\r${BLUE}│${NC} ${message}: ${GREEN}${bar}${NC} ${BOLD}${percent}%${NC} (${current}/${total}) "

    if [[ $current -eq $total ]]; then
        echo -e "${GREEN}✓${NC}"
    fi
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

# === VÉRIFICATIONS RÉSEAU ===

# Vérifier la connectivité internet (plusieurs méthodes)
check_internet_connectivity() {
    log_info "Vérification de la connectivité internet..."

    local test_hosts=("1.1.1.1" "8.8.8.8" "google.com")
    local connected=false

    for host in "${test_hosts[@]}"; do
        if ping -c 1 -W 2 "$host" &> /dev/null; then
            connected=true
            log_success "✓ Connectivité internet OK (via $host)"
            return 0
        fi
    done

    if [[ "$connected" == "false" ]]; then
        log_error "Aucune connectivité internet détectée"
        log_error "Veuillez vérifier votre connexion réseau"
        return 1
    fi
}

# Vérifier la résolution DNS
check_dns_resolution() {
    log_info "Vérification de la résolution DNS..."

    if nslookup google.com &> /dev/null || dig google.com &> /dev/null || host google.com &> /dev/null; then
        log_success "✓ Résolution DNS fonctionnelle"
        return 0
    else
        log_error "Résolution DNS échouée"
        log_warn "DNS peut être mal configuré. Vérifiez /etc/resolv.conf"
        return 1
    fi
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
        [Yy]) return 0 ;;
        [Nn]) return 1 ;;
        "") [[ "$default" != "n" ]] && return 0 || return 1 ;;
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

# === PAUSE POUR LAISSER L'UTILISATEUR LIRE ===

# Pause avec message et délai
pause_with_message() {
    local message="${1:-Appuyez sur Entrée pour continuer}"
    local auto_continue_delay="${2:-0}" # 0 = pas d'auto-continue

    echo ""
    echo -e "${CYAN}${message}${NC}"

    if [[ $auto_continue_delay -gt 0 ]]; then
        echo -e "${DIM}(Auto-continue dans ${auto_continue_delay}s)${NC}"
        read -t "$auto_continue_delay" -p "" || true
    else
        read -p ""
    fi
}

# === KERNEL & SYSTEM CONFIG ===

configure_kernel_params() {
    local sysctl_file="/etc/sysctl.d/99-rpi4-docker.conf"
    log_info "Configuration des paramètres kernel pour RPi4..."

    if [[ -f "$sysctl_file" ]]; then
        if grep -q "vm.overcommit_memory" "$sysctl_file" && \
           grep -q "net.core.somaxconn" "$sysctl_file" && \
           grep -q "vm.swappiness" "$sysctl_file"; then
            log_info "✓ Paramètres kernel déjà configurés."
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
    log_success "✓ Paramètres kernel configurés (overcommit_memory=1, swappiness=10)."
}

configure_zram() {
    log_info "Configuration ZRAM (Swap compressé en RAM)..."
    if lsblk | grep -q "zram0"; then
        log_info "✓ ZRAM déjà configuré et actif"
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

    log_success "✓ ZRAM activé (1GB) et rendu persistant."
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
            log_info "✓ Docker déjà configuré (IPv4 + DNS fiables)."
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
        log_success "✓ Docker redémarré avec IPv4 + DNS fiables."
    fi
}

# === TERMINAL UI UTILS (Added for Dashboard UX) ===

# Detect if we have a robust TTY capable of cursor movement
has_smart_tty() {
    [[ -t 1 ]] && command -v tput >/dev/null 2>&1
}

# Get terminal dimensions
get_term_cols() {
    tput cols 2>/dev/null || echo 80
}

get_term_lines() {
    tput lines 2>/dev/null || echo 24
}

# Cursor controls
ui_cursor_hide() { has_smart_tty && tput civis; }
ui_cursor_show() { has_smart_tty && tput cnorm; }
ui_cursor_save() { has_smart_tty && tput sc; }
ui_cursor_restore() { has_smart_tty && tput rc; }
ui_line_clear() { has_smart_tty && tput el; }
ui_move_up() { has_smart_tty && tput cuu1; }
ui_move_up_n() { has_smart_tty && tput cuu "$1"; }

# Text truncation for clean columns
ui_truncate_text() {
    local text="$1"
    local max_len="$2"
    if [[ ${#text} -gt $max_len ]]; then
        echo "${text:0:$((max_len-1))}…"
    else
        printf "%-${max_len}s" "$text"
    fi
}

# Render a robust progress bar
# Usage: ui_render_progress_bar <current> <total> <width> <color>
ui_render_progress_bar() {
    local current=$1
    local total=$2
    local width=${3:-20}
    local color=${4:-$BLUE}

    local percent=0
    local filled=0

    if [[ $total -gt 0 ]]; then
        percent=$((current * 100 / total))
        filled=$((current * width / total))
    fi
    local empty=$((width - filled))

    # Use Unicode block characters if locale supports it, else ASCII
    local char_fill="█"
    local char_empty="░"
    if [[ "${LANG:-}" != *"UTF-8"* ]]; then
        char_fill="#"
        char_empty="-"
    fi

    local bar=""
    for ((i=0; i<filled; i++)); do bar+="${char_fill}"; done
    for ((i=0; i<empty; i++)); do bar+="${char_empty}"; done

    echo -ne "${color}${bar}${NC} ${percent}%"
}

# Format bytes to human readable
ui_format_bytes() {
    local bytes="${1:-0}"
    if [[ $bytes -lt 1024 ]]; then
        echo "${bytes} B"
    elif [[ $bytes -lt 1048576 ]]; then
        echo "$((bytes / 1024)) KB"
    else
        echo "$((bytes / 1048576)) MB"
    fi
}
