#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - ULTIMATE SETUP SCRIPT v10.0 "Bulletproof"       ║
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
HEADLESS_PASSWORD=""

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
        --headless=*)
            HEADLESS_PASSWORD="${arg#*=}"
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
    # Auto-yes if headless password is provided or --yes flag (implied by non-interactive check)
    if [[ -n "$HEADLESS_PASSWORD" ]] || [[ " $* " == *" -y "* ]] || [[ " $* " == *" --yes "* ]]; then return 0; fi

    read -p "$(echo -e "${BOLD}${prompt} (y/n) ${NC}")" -n 1 -r < /dev/tty
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then return 0; else return 1; fi
}

check_command() {
    command -v "$1" &> /dev/null
}

check_connectivity() {
    log INFO "Checking network connectivity..."
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
         log ERROR "No internet access (cannot ping 8.8.8.8)."
         log INFO "Please check your network cable or Wi-Fi connection."
         return 1
    fi
    log SUCCESS "Network connectivity OK."
}

fix_permissions() {
    log INFO "Applying preventive permission fixes..."

    # Create directories if missing
    mkdir -p data logs config

    # Check if data/linkedin.db is a directory (Docker error)
    if [ -d "data/linkedin.db" ]; then
        log WARN "data/linkedin.db detected as a DIRECTORY. Fixing..."
        mv "data/linkedin.db" "data/linkedin.db.bak_$(date +%s)"
    fi

    # Ensure it's a file if it doesn't exist
    if [ ! -e "data/linkedin.db" ]; then
        touch "data/linkedin.db"
    fi

    # Force 777 permissions (Critical for Pi4 Docker binding)
    chmod -R 777 data logs config
    log SUCCESS "Permissions fixed: data, logs, config set to 777."
}

# ═══════════════════════════════════════════════════════════════════════════
# 1. PHASE 1: INTELLIGENT INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔍 PHASE 1: Infrastructure Check"

# 1.1 Connectivity Check
check_connectivity

# 1.2 Essential Tools
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

# 1.3 Docker Group Check
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

# 1.4 Pre-flight Port Check
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

# 1.5 Swap Check (Pi 4 Requirement)
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

# 2.1 Smart .env Merging
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_TEMPLATE" ]; then
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        log SUCCESS "Created .env from template."

        # Auto-configure Local IP for fresh install
        LOCAL_IP=$(hostname -I | awk '{print $1}')
        sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000|g" "$ENV_FILE"
        sed -i "s|NEXT_PUBLIC_DASHBOARD_URL=.*|NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000|g" "$ENV_FILE"
    else
        log ERROR "Template $ENV_TEMPLATE not found!"
        exit 1
    fi
else
    log INFO "Analyzing .env for missing keys..."

    MISSING_KEYS_COUNT=0

    # 1. Merge from template (general update)
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ ^#.* ]] || [[ -z "$line" ]]; then continue; fi
        KEY=$(echo "$line" | cut -d'=' -f1 | xargs)
        if [[ -n "$KEY" ]] && ! grep -q "^${KEY}=" "$ENV_FILE"; then
            echo "" >> "$ENV_FILE"
            echo "# Added by setup.sh update" >> "$ENV_FILE"
            echo "$line" >> "$ENV_FILE"
            log INFO "Added missing key: $KEY"
            ((MISSING_KEYS_COUNT++))
        fi
    done < "$ENV_TEMPLATE"

    # 2. Force check specific critical keys with defaults if still missing
    # DASHBOARD_PORT default 3000
    if ! grep -q "^DASHBOARD_PORT=" "$ENV_FILE"; then
         echo "" >> "$ENV_FILE"
         echo "DASHBOARD_PORT=3000" >> "$ENV_FILE"
         log INFO "Added critical default: DASHBOARD_PORT=3000"
         ((MISSING_KEYS_COUNT++))
    fi

    if [ $MISSING_KEYS_COUNT -gt 0 ]; then
        log SUCCESS "Merged $MISSING_KEYS_COUNT new keys into $ENV_FILE"
    else
        log INFO ".env is up to date."
    fi
fi

# Generate Secure Keys if placeholder or missing
API_KEY=$(grep "^API_KEY=" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$API_KEY" == "CHANGEZ_MOI"* || "$API_KEY" == "internal_secret_key" || -z "$API_KEY" ]]; then
    NEW_KEY=$(openssl rand -hex 32)
    sed -i "s|^API_KEY=.*|API_KEY=$NEW_KEY|" "$ENV_FILE"
    sed -i "s|^BOT_API_KEY=.*|BOT_API_KEY=$NEW_KEY|" "$ENV_FILE"
    log SUCCESS "Generated secure API_KEY."
fi

JWT_SECRET=$(grep "^JWT_SECRET=" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$JWT_SECRET" == "CHANGEZ_MOI"* || -z "$JWT_SECRET" ]]; then
    NEW_JWT=$(openssl rand -hex 32)
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$NEW_JWT|" "$ENV_FILE"
    log SUCCESS "Generated secure JWT_SECRET."
fi

# 2.2 Robust Password Hashing
CURRENT_PASS=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)

if [[ "$CURRENT_PASS" != "\$2"* ]]; then
    log WARN "DASHBOARD_PASSWORD is not hashed."

    # Ensure bcrypt is available
    if ! python3 -c "import bcrypt" 2>/dev/null; then
        log INFO "Installing python3-bcrypt..."
        sudo apt-get install -y python3-bcrypt || pip3 install bcrypt || log WARN "Failed to install bcrypt via apt/pip. Will attempt fallback or fail."
    fi

    PASSWORD_TO_HASH=""
    if [[ -n "$HEADLESS_PASSWORD" ]]; then
        log INFO "Using password provided via --headless argument."
        PASSWORD_TO_HASH="$HEADLESS_PASSWORD"
    else
        log INFO "Please enter the password for the Dashboard."
        PASSWORD_TO_HASH=$(python3 -c "import getpass; print(getpass.getpass('Password: '))")
    fi

    if [[ -z "$PASSWORD_TO_HASH" ]]; then
        log ERROR "No password provided. Aborting security setup."
        exit 1
    fi

    export PASS_VAR="$PASSWORD_TO_HASH"
    HASHED_PASS=$(python3 -c "import bcrypt, os; print(bcrypt.hashpw(os.environ['PASS_VAR'].encode(), bcrypt.gensalt()).decode())" 2>/dev/null)
    unset PASS_VAR

    if [[ -n "$HASHED_PASS" ]]; then
        ESCAPED_HASH=$(echo "$HASHED_PASS" | sed 's/\$/$$/g')
        sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=$ESCAPED_HASH|" "$ENV_FILE"
        log SUCCESS "Password hashed and updated in .env"
    else
        log ERROR "Password hashing failed (missing bcrypt?)."
        log INFO "Try running: sudo apt install python3-bcrypt"
        exit 1
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# 3. PHASE 3: DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🚀 PHASE 3: Deployment"

# Run preventive permission fixes
fix_permissions

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
    $DOCKER_CMD -f "$COMPOSE_FILE" pull "$svc" || log WARN "Could not pull $svc (using local cache if available)"
done

log INFO "Starting Stack..."
$DOCKER_CMD -f "$COMPOSE_FILE" up -d --remove-orphans

# ═══════════════════════════════════════════════════════════════════════════
# 4. PHASE 4: VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🕵️ PHASE 4: Health Check"

wait_for_healthy() {
    local service=$1
    local max_retries=120
    local retry=0

    log INFO "Waiting for $service to be healthy (Timeout: 10 mins)..."

    # Progress bar style
    echo -n "Waiting: "

    while [ $retry -lt $max_retries ]; do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "starting")

        if [ "$STATUS" == "healthy" ]; then
            echo "" # New line after dots
            log SUCCESS "$service is healthy."
            return 0
        fi

        # Feedback visual
        echo -n "."
        sleep 5
        ((retry++))
    done

    echo "" # New line
    # Diagnostics on failure (Auto-Diagnostic)
    log ERROR "CRITICAL: $service failed to become healthy after $((max_retries * 5)) seconds."

    echo -e "${RED}🚨 DUMPING LOGS FOR DEBUGGING...${NC}"
    echo -e "${RED}--- Last 50 Log Lines for $service ---${NC}"
    docker logs --tail 50 "$service"
    echo -e "${RED}--------------------------------------${NC}"

    echo -e "${YELLOW}--- Resource Usage (Docker Stats) ---${NC}"
    docker stats --no-stream

    return 1
}

# Protected wait calls (won't exit immediately on return 1 due to if wrap or explicit check,
# but set -e is active so we need to be careful. The return 1 will trigger exit unless handled)
# We want it to exit if it fails, but AFTER the logs are printed.
# wait_for_healthy prints logs then returns 1.
# set -e will cause the script to exit immediately when wait_for_healthy returns 1.
# This is desired behavior.

wait_for_healthy "bot-api"
wait_for_healthy "dashboard"

log INFO "Initializing Database Schema..."
docker exec bot-api python -m src.scripts.init_db || log WARN "DB Init warning (check logs)"

log SUCCESS "---------------------------------------------------"
log SUCCESS "✅ DEPLOYMENT COMPLETE"
LOCAL_IP=$(hostname -I | awk '{print $1}')
log SUCCESS "Dashboard accessible at http://${LOCAL_IP:-localhost}:3000"
log SUCCESS "---------------------------------------------------"
exit 0
