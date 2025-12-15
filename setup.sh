#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - ULTIMATE SETUP SCRIPT v9.0                      ║
# ║  Refactored & Hardened for Raspberry Pi 4                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# Strict Mode
set -e
set -o pipefail

# ═══════════════════════════════════════════════════════════════════════════
# 0. CORE FRAMEWORK & LOGGING
# ═══════════════════════════════════════════════════════════════════════════

# Configuration
LOG_FILE="logs/setup_$(date +%Y%m%d_%H%M%S).log"
ENV_FILE=".env"
ENV_TEMPLATE=".env.pi4.example"
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
mkdir -p logs

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Parsing Arguments
DEBUG_MODE=false
CLEAN_DEPLOY=false

for arg in "$@"; do
    case $arg in
        --debug)
            DEBUG_MODE=true
            set -x
            echo -e "${YELLOW}[DEBUG] Debug mode enabled.${NC}"
            ;;
        --clean|--force)
            CLEAN_DEPLOY=true
            ;;
    esac
done

# Dual Logging (Stdout + File)
log() {
    local level=$1
    local msg=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local color=$NC
    local icon=""

    case $level in
        INFO)    color=$CYAN; icon="ℹ️" ;;
        SUCCESS) color=$GREEN; icon="✅" ;;
        WARN)    color=$YELLOW; icon="⚠️" ;;
        ERROR)   color=$RED; icon="❌" ;;
    esac

    # Console Output
    echo -e "${color}[${timestamp}] ${icon} [${level}] ${msg}${NC}"

    # File Output (Strip colors)
    echo "[${timestamp}] [${level}] ${msg}" >> "$LOG_FILE"
}

# Error Handler
error_handler() {
    local line_no=$1
    local exit_code=$2
    if [ "$exit_code" -ne 0 ]; then
        echo ""
        log ERROR "Critical failure at line $line_no (Exit Code: $exit_code)"
        log ERROR "See full log at: $LOG_FILE"
    fi
}
trap 'error_handler ${LINENO} $?' EXIT

# Utilities
ask_confirmation() {
    local prompt=$1
    # Non-interactive fallback: assume YES if running blindly unless it's critical
    # But for safety, we default to prompts.
    if [[ " $* " == *" -y "* ]] || [[ " $* " == *" --yes "* ]]; then return 0; fi

    read -p "$(echo -e "${BOLD}${prompt} (y/n) ${NC}")" -n 1 -r < /dev/tty
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then return 0; else return 1; fi
}

check_command() {
    command -v "$1" &> /dev/null
}

# ═══════════════════════════════════════════════════════════════════════════
# 1. PHASE 1: INTELLIGENT INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔍 PHASE 1: Infrastructure Check"

# 1.1 Essential Tools
TOOLS=("git" "python3" "curl" "grep" "sed" "lsof")
MISSING_TOOLS=()

for tool in "${TOOLS[@]}"; do
    if ! check_command "$tool"; then
        MISSING_TOOLS+=("$tool")
    fi
done

if [ ${#MISSING_TOOLS[@]} -ne 0 ]; then
    log WARN "Missing tools: ${MISSING_TOOLS[*]}"
    log INFO "Installing missing tools..."
    sudo apt-get update -qq
    sudo apt-get install -y "${MISSING_TOOLS[@]}" || log ERROR "Failed to install tools."
fi

# 1.2 Docker Group Check
if check_command "docker"; then
    if ! groups "$USER" | grep -q "docker"; then
        log WARN "User $USER is not in the 'docker' group."
        sudo usermod -aG docker "$USER"
        log WARN "Added $USER to docker group. A REBOOT or 'newgrp docker' is required."
        log WARN "Please reboot your Pi and run this script again."
        exit 1
    else
        log SUCCESS "User is correctly in the docker group."
    fi
else
    log WARN "Docker not found. Installing..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    log WARN "Docker installed. Please reboot and re-run this script."
    exit 1
fi

# 1.3 Pre-flight Port Check
log INFO "Checking port availability..."
PORTS_TO_CHECK=(3000 8000 80 443)
PORT_CONFLICT=false

for port in "${PORTS_TO_CHECK[@]}"; do
    # Check if port is in use
    if sudo lsof -i :$port >/dev/null 2>&1; then
        # Check if it's Docker (com.docker.backend or similar is acceptable if we are restarting)
        PID=$(sudo lsof -t -i :$port | head -n1)
        PROCESS=$(ps -p $PID -o comm=)

        if [[ "$PROCESS" != "dockerd" && "$PROCESS" != "docker-proxy" ]]; then
            log WARN "Port $port is in use by non-Docker process: $PROCESS (PID $PID)."
            PORT_CONFLICT=true
        else
            log INFO "Port $port is used by Docker (Safe to restart)."
        fi
    else
        log INFO "Port $port is free."
    fi
done

if [ "$PORT_CONFLICT" = true ]; then
    if ! ask_confirmation "Some ports are occupied by other services. Continue?"; then
        log ERROR "Aborted by user due to port conflict."
        exit 1
    fi
fi

# 1.4 Swap Check (Pi 4 Requirement)
SWAP_TOTAL=$(free -m | awk '/^Swap:/{print $2}')
if [ "$SWAP_TOTAL" -lt 2000 ]; then
    log WARN "Swap < 2GB ($SWAP_TOTAL MB). Increasing swap..."
    if [ -f /etc/dphys-swapfile ]; then
        sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
        sudo dphys-swapfile setup && sudo dphys-swapfile swapon
    else
        log INFO "Creating manual swapfile..."
        sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        grep -q "/swapfile" /etc/fstab || echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab
    fi
    log SUCCESS "Swap configured."
fi

# ═══════════════════════════════════════════════════════════════════════════
# 2. PHASE 2: SECURITY & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔒 PHASE 2: Security & Environment"

# 2.1 Robust Database Initialization (CRITICAL)
# Ensure data/linkedin.db exists as a FILE, not a directory
mkdir -p data
DB_PATH="data/linkedin.db"

if [ -d "$DB_PATH" ]; then
    log WARN "$DB_PATH detected as a DIRECTORY (Docker mounting error)."
    BACKUP_NAME="${DB_PATH}_backup_$(date +%s)"
    mv "$DB_PATH" "$BACKUP_NAME"
    log INFO "Moved invalid directory to $BACKUP_NAME"
fi

if [ ! -f "$DB_PATH" ]; then
    touch "$DB_PATH"
    log INFO "Created empty database file: $DB_PATH"
fi

# Set permissions to 666 to avoid Docker permission issues
chmod 666 "$DB_PATH"
# SQLite requires write access to the directory for WAL/shm files
chmod 777 data
log SUCCESS "Database file secured (chmod 666) and data directory writable."

# 2.2 Improved .env Handling
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_TEMPLATE" ]; then
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        log SUCCESS "Created .env from template."

        # Auto-configure Local IP
        LOCAL_IP=$(hostname -I | awk '{print $1}')
        sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000|g" "$ENV_FILE"
        sed -i "s|NEXT_PUBLIC_DASHBOARD_URL=.*|NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000|g" "$ENV_FILE"
    else
        log ERROR "Template $ENV_TEMPLATE not found!"
        exit 1
    fi
fi

# Generate Secure Keys (Alphanumeric only)
API_KEY=$(grep "^API_KEY=" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$API_KEY" == "internal_secret_key" || -z "$API_KEY" ]]; then
    NEW_KEY=$(openssl rand -hex 32)
    sed -i "s|^API_KEY=.*|API_KEY=$NEW_KEY|" "$ENV_FILE"
    sed -i "s|^BOT_API_KEY=.*|BOT_API_KEY=$NEW_KEY|" "$ENV_FILE"
    log SUCCESS "Generated secure API_KEY."
fi

JWT_SECRET=$(grep "^JWT_SECRET=" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$JWT_SECRET" == *"CHANGEZ_MOI"* || -z "$JWT_SECRET" ]]; then
    NEW_JWT=$(openssl rand -hex 32)
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$NEW_JWT|" "$ENV_FILE"
    log SUCCESS "Generated secure JWT_SECRET."
fi

# 2.3 Python-based Password Hashing
# Check DASHBOARD_PASSWORD status
CURRENT_PASS=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)

if [[ "$CURRENT_PASS" != "\$2"* ]]; then
    log WARN "DASHBOARD_PASSWORD is not hashed."

    # Ensure bcrypt is available
    if ! python3 -c "import bcrypt" 2>/dev/null; then
        log INFO "Installing python3-bcrypt..."
        sudo apt-get install -y python3-bcrypt || pip3 install bcrypt
    fi

    # Interactive Hashing
    log INFO "Please enter the password for the Dashboard."
    HASHED_PASS=$(python3 -c "import bcrypt, getpass; print(bcrypt.hashpw(getpass.getpass('Password: ').encode(), bcrypt.gensalt()).decode())")

    if [[ -n "$HASHED_PASS" ]]; then
        # Escape $ for Docker Compose ($ -> $$)
        ESCAPED_HASH=$(echo "$HASHED_PASS" | sed 's/\$/$$/g')
        sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=$ESCAPED_HASH|" "$ENV_FILE"
        log SUCCESS "Password hashed and updated in .env"
    else
        log ERROR "Password hashing failed."
        exit 1
    fi
fi

# 2.4 Permissions
chmod 600 "$ENV_FILE"
mkdir -p logs config
chmod 777 logs config # Required for container writes
log SUCCESS "Fixed permissions."

# ═══════════════════════════════════════════════════════════════════════════
# 3. PHASE 3: DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🚀 PHASE 3: Deployment"

DOCKER_CMD="docker compose"
if ! docker compose version &>/dev/null; then
    if command -v docker-compose &>/dev/null; then
        DOCKER_CMD="docker-compose"
    fi
fi

if [ "$CLEAN_DEPLOY" = true ]; then
    log WARN "Cleaning up existing containers (--clean)..."
    $DOCKER_CMD -f "$COMPOSE_FILE" down --remove-orphans
fi

log INFO "Pulling images..."
SERVICES="redis-bot redis-dashboard api bot-worker dashboard"
for svc in $SERVICES; do
    $DOCKER_CMD -f "$COMPOSE_FILE" pull "$svc" || log WARN "Could not pull $svc (using local if available)"
done

log INFO "Starting Stack..."
$DOCKER_CMD -f "$COMPOSE_FILE" up -d --remove-orphans

# ═══════════════════════════════════════════════════════════════════════════
# 4. PHASE 4: VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🕵️ PHASE 4: Health Check"

wait_for_healthy() {
    local service=$1
    local retries=30
    log INFO "Waiting for $service..."
    while [ $retries -gt 0 ]; do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "starting")
        if [ "$STATUS" == "healthy" ]; then
            log SUCCESS "$service is healthy."
            return 0
        fi
        sleep 5
        retries=$((retries-1))
    done
    log ERROR "$service failed to become healthy."
    return 1
}

wait_for_healthy "bot-api"
wait_for_healthy "dashboard"

log INFO "Initializing Database Schema..."
docker exec bot-api python -m src.scripts.init_db || log WARN "DB Init warning (check logs)"

log SUCCESS "---------------------------------------------------"
log SUCCESS "✅ DEPLOYMENT COMPLETE"
log SUCCESS "Dashboard: http://${LOCAL_IP:-localhost}:3000"
log SUCCESS "API:       http://${LOCAL_IP:-localhost}:8000"
log SUCCESS "---------------------------------------------------"
exit 0
