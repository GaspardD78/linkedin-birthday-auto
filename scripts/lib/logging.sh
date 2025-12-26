#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - LOGGING LIBRARY
# Centralized logging, colors, and dual-output configuration
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === COLORS & FORMATTING ===
# Guard against multiple sourcing or pre-existing readonly declarations

[[ -v BLUE ]] || readonly BLUE='\033[0;34m'
[[ -v GREEN ]] || readonly GREEN='\033[0;32m'
[[ -v YELLOW ]] || readonly YELLOW='\033[1;33m'
[[ -v RED ]] || readonly RED='\033[0;31m'
[[ -v CYAN ]] || readonly CYAN='\033[0;36m'
[[ -v MAGENTA ]] || readonly MAGENTA='\033[0;35m'
[[ -v NC ]] || readonly NC='\033[0m'
[[ -v BOLD ]] || readonly BOLD='\033[1m'
[[ -v DIM ]] || readonly DIM='\033[2m'
[[ -v UNDERLINE ]] || readonly UNDERLINE='\033[4m'

# === LOGGING DUAL-OUTPUT (SCREEN + FILE) ===

SETUP_LOG_FILE="${SETUP_LOG_FILE:-}"
LOGGING_INITIALIZED="${LOGGING_INITIALIZED:-false}"

# Initialiser le logging dual-output (exec tee)
setup_logging() {
    if [[ "$LOGGING_INITIALIZED" == "true" ]]; then
        return 0
    fi

    local log_dir="${1:-logs}"
    local timestamp=$(date +%Y%m%d_%H%M%S)

    # Créer le répertoire de logs si nécessaire
    mkdir -p "$log_dir"

    # Définir le fichier de log avec timestamp
    SETUP_LOG_FILE="${log_dir}/setup_install_${timestamp}.log"

    # Rediriger stdout et stderr vers tee (dual output)
    # Cela capture TOUT ce qui s'affiche à l'écran dans le fichier
    # Note: On utilise un pipe nommé ou une redirection process substitution
    exec > >(tee -a "$SETUP_LOG_FILE")
    exec 2>&1

    LOGGING_INITIALIZED=true

    # Enregistrer l'environnement
    echo "═══════════════════════════════════════════════════════════════" >> "$SETUP_LOG_FILE"
    echo "SETUP LOG - $(date '+%Y-%m-%d %H:%M:%S')" >> "$SETUP_LOG_FILE"
    echo "Host: $(hostname)" >> "$SETUP_LOG_FILE"
    echo "User: $(whoami)" >> "$SETUP_LOG_FILE"
    echo "Working Directory: $(pwd)" >> "$SETUP_LOG_FILE"
    echo "═══════════════════════════════════════════════════════════════" >> "$SETUP_LOG_FILE"
    echo "" >> "$SETUP_LOG_FILE"
}

# Fonction pour afficher le chemin du log
get_log_file() {
    echo "${SETUP_LOG_FILE:-Logging non initialisé}"
}

# === LOGGING FUNCTIONS ===

log_info()    { echo -e "${BLUE}ℹ [INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}✓ [OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}⚠ [WARN]${NC} $1"; }
log_error()   { echo -e "${RED}✗ [ERROR]${NC} $1"; }
log_debug()   { echo -e "${DIM}[DEBUG]${NC} $1"; }

log_step() {
    echo ""
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  🚀 $1${NC}"
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}
