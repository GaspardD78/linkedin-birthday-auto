#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - ULTIMATE SETUP SCRIPT v8.0                      ║
# ║  Unified Installer: Infrastructure, Security, Deployment & Deep Audit    ║
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

# Debug Mode
DEBUG_MODE=false
for arg in "$@"; do
    if [[ "$arg" == "--debug" ]]; then
        DEBUG_MODE=true
        set -x
        echo -e "${YELLOW}[DEBUG] Debug mode enabled. Output will be verbose.${NC}"
    fi
done

# Dual Logging (Stdout + File)
# We use a custom log function instead of global redirection to preserve interactive prompts
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
        DEBUG)   [ "$DEBUG_MODE" = false ] && return; color=$BLUE; icon="🐛" ;;
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
        if [ "$DEBUG_MODE" = false ]; then
            echo -e "${YELLOW}Tip: Run with './setup.sh --debug' for more details.${NC}"
        fi
    fi
}
trap 'error_handler ${LINENO} $?' EXIT

# Utilities
ask_confirmation() {
    local prompt=$1
    if [[ " $* " == *" -y "* ]] || [[ " $* " == *" --yes "* ]]; then return 0; fi

    # Read from /dev/tty to bypass any potential redirection issues
    read -p "$(echo -e "${BOLD}${prompt} (y/n) ${NC}")" -n 1 -r < /dev/tty
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then return 0; else return 1; fi
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

# ═══════════════════════════════════════════════════════════════════════════
# 1. PHASE 1: INTELLIGENT INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔍 PHASE 1: Infrastructure Check"

# 1.1 Essential Tools
TOOLS=("git" "jq" "curl" "python3")
MISSING_TOOLS=()

for tool in "${TOOLS[@]}"; do
    if ! check_command "$tool"; then
        MISSING_TOOLS+=("$tool")
    fi
done

if [ ${#MISSING_TOOLS[@]} -ne 0 ]; then
    log WARN "Missing tools: ${MISSING_TOOLS[*]}"
    if ask_confirmation "Install missing tools?"; then
        sudo apt-get update -qq
        sudo apt-get install -y "${MISSING_TOOLS[@]}" || log ERROR "Failed to install tools."
    else
        log ERROR "Cannot proceed without essential tools."
        exit 1
    fi
fi

# 1.2 Docker Check
if ! check_command "docker"; then
    log WARN "Docker not found."
    if ask_confirmation "Install Docker (official script)?"; then
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker $USER
        log WARN "Docker installed. You may need to relogin/reboot for group permissions."
    else
        log ERROR "Docker is required."
        exit 1
    fi
fi

# 1.3 Hardware (Swap Check for Pi 4)
SWAP_TOTAL=$(free -m | awk '/^Swap:/{print $2}')
SWAP_TOTAL=${SWAP_TOTAL:-0}
if [ "$SWAP_TOTAL" -lt 2000 ]; then
    log WARN "Detected Swap < 2GB ($SWAP_TOTAL MB). Low memory may crash Docker builds."
    if ask_confirmation "Increase Swap to 2GB (Recommended for Pi 4)?"; then
        log INFO "Configuring Swap..."
        if [ -f /etc/dphys-swapfile ]; then
            sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
            sudo dphys-swapfile setup
            sudo dphys-swapfile swapon
            log SUCCESS "Swap increased via dphys-swapfile."
        else
            log INFO "Creating manual swapfile..."
            sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
            sudo chmod 600 /swapfile
            sudo mkswap /swapfile
            sudo swapon /swapfile
            grep -q "/swapfile" /etc/fstab || echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab
            log SUCCESS "Swap increased via /swapfile."
        fi
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# 2. PHASE 2: SECURITY & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔒 PHASE 2: Security & Environment"

# 2.1 Environment File
if [ ! -f "$ENV_FILE" ]; then
    log WARN "$ENV_FILE not found."
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    log SUCCESS "Created .env from template."

    # Auto-set IP
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000|g" "$ENV_FILE"
    sed -i "s|NEXT_PUBLIC_DASHBOARD_URL=.*|NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000|g" "$ENV_FILE"
    log INFO "Configured local IP: $LOCAL_IP"
fi

# 2.2 Permissions
chmod 600 "$ENV_FILE"
mkdir -p data logs config
chmod 777 data logs config # 777 needed for Docker mounts on Pi without UID matching hell
log SUCCESS "Permissions fixed (600 for .env, 777 for data/logs)."

# 2.3 Password Hardening
CURRENT_PASS=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$CURRENT_PASS" != "\$2"* ]]; then # Bcrypt starts with $2
    log WARN "DASHBOARD_PASSWORD appears to be plain text."
    if ask_confirmation "Hash password with Bcrypt (Recommended)?"; then
        read -s -p "Enter new Dashboard Password: " PASS_INPUT
        echo ""

        HASHED_PASS=""

        # Method A: Local Node
        if check_command "node" && [ -f "dashboard/scripts/hash_password.js" ]; then
             log INFO "Using local Node.js for hashing..."
             # Check if bcryptjs exists, else install locally in temp
             if [ ! -d "dashboard/node_modules/bcryptjs" ]; then
                 log INFO "Installing bcryptjs locally..."
                 (cd dashboard && npm install bcryptjs --no-save --silent)
             fi
             HASHED_PASS=$(node dashboard/scripts/hash_password.js "$PASS_INPUT" --quiet)
        fi

        # Method B: Docker Fallback
        if [ -z "$HASHED_PASS" ]; then
             log INFO "Using Docker (node:20-slim) for hashing..."
             # We assume dashboard/scripts is mounted to /scripts
             HASHED_PASS=$(docker run --rm -v "$(pwd)/dashboard/scripts:/scripts" node:20-slim \
                 sh -c "npm install bcryptjs --prefix /scripts --silent >/dev/null 2>&1 && node /scripts/hash_password.js '$PASS_INPUT' --quiet")
        fi

        if [[ "$HASHED_PASS" == "\$2"* ]]; then
             # Escape $ for Docker Compose ($ -> $$)
             ESCAPED_HASH=$(echo "$HASHED_PASS" | sed 's/\$/$$/g')
             sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=$ESCAPED_PASS|" "$ENV_FILE"
             log SUCCESS "Password hashed and updated in .env"
        else
             log ERROR "Failed to hash password. Please do it manually."
        fi
    fi
fi

# 2.4 API Keys
API_KEY=$(grep "^API_KEY=" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$API_KEY" == "internal_secret_key" || -z "$API_KEY" ]]; then
    NEW_KEY=$(openssl rand -hex 32)
    sed -i "s|^API_KEY=.*|API_KEY=$NEW_KEY|" "$ENV_FILE"
    sed -i "s|^BOT_API_KEY=.*|BOT_API_KEY=$NEW_KEY|" "$ENV_FILE"
    log SUCCESS "Generated secure API Keys."
fi

# 2.5 Nginx Proposal
if ask_confirmation "Do you want to configure Nginx/HTTPS (Certbot)?"; then
    log INFO "Invoking security script for Nginx setup..."
    if [ -f "scripts/fix_security_issues.py" ]; then
        sudo python3 scripts/fix_security_issues.py --nginx-only
    else
        log ERROR "scripts/fix_security_issues.py not found. Skipping Nginx setup."
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# 3. PHASE 3: DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🚀 PHASE 3: Deployment"

DOCKER_CMD="docker compose"
if ! docker compose version &>/dev/null; then
    if command -v docker-compose &>/dev/null; then
        DOCKER_CMD="docker-compose"
    else
        log ERROR "docker compose plugin not found."
        exit 1
    fi
fi

log INFO "Pulling images (Sequential for stability)..."
SERVICES=$($DOCKER_CMD -f "$COMPOSE_FILE" config --services 2>/dev/null || echo "redis-bot redis-dashboard api bot-worker dashboard")

for svc in $SERVICES; do
    log INFO "Pulling $svc..."
    $DOCKER_CMD -f "$COMPOSE_FILE" pull "$svc" || log WARN "Failed to pull $svc (might be local build)"
done

log INFO "Starting services..."
$DOCKER_CMD -f "$COMPOSE_FILE" up -d --remove-orphans

# ═══════════════════════════════════════════════════════════════════════════
# 4. PHASE 4: DEEP SERVICE AUDIT
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🕵️ PHASE 4: Deep Service Audit"

analyze_logs() {
    local service=$1
    echo "---------------------------------------------------"
    echo "🔎 Analyzing logs for: $service"

    # Check if container exists/running
    if ! docker ps -q -f name="$service" &>/dev/null; then
        echo -e "${RED}Container $service is NOT running!${NC}"
        return
    fi

    # Fetch logs
    local logs=$(docker logs --tail 50 "$service" 2>&1)

    # Grep for errors
    if echo "$logs" | grep -E "ERROR|CRITICAL|Exception|Traceback" &>/dev/null; then
        echo -e "${RED}❌ ERRORS DETECTED:${NC}"
        echo "$logs" | grep -E --color=always "ERROR|CRITICAL|Exception|Traceback"
    elif echo "$logs" | grep "WARN" &>/dev/null; then
        echo -e "${YELLOW}⚠️ WARNINGS DETECTED:${NC}"
        echo "$logs" | grep --color=always "WARN"
    else
        echo -e "${GREEN}✅ No critical errors found in last 50 lines.${NC}"
    fi
}

wait_for_healthy() {
    local service=$1
    local max_retries=30
    log INFO "Waiting for $service to be healthy..."

    for i in $(seq 1 $max_retries); do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "starting")
        if [ "$STATUS" == "healthy" ]; then
            log SUCCESS "$service is healthy."
            return 0
        fi
        sleep 5
        echo -n "."
    done
    echo ""
    log ERROR "$service timed out waiting for health."
    return 1
}

# 4.1 Wait & Check API
wait_for_healthy "bot-api" || analyze_logs "bot-api"

# 4.2 DB Init (Post-Start)
log INFO "Initializing Database..."
if docker exec bot-api python -m src.scripts.init_db; then
    log SUCCESS "Database Initialized."
else
    log ERROR "Database Initialization Failed."
    analyze_logs "bot-api"
fi

# 4.3 Wait & Check Dashboard
wait_for_healthy "dashboard" || analyze_logs "dashboard"

# 4.4 Final Log Analysis
SERVICES_TO_CHECK=("bot-api" "bot-worker" "dashboard" "redis-bot")
for svc in "${SERVICES_TO_CHECK[@]}"; do
    analyze_logs "$svc"
done

# 4.5 Endpoint Verification
log INFO "Verifying Endpoints..."
HTTP_API=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
if [ "$HTTP_API" == "200" ]; then
    log SUCCESS "API (Port 8000): 200 OK"
else
    log ERROR "API (Port 8000): $HTTP_API"
fi

HTTP_DASH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "000")
if [[ "$HTTP_DASH" =~ ^(200|307|308)$ ]]; then
    log SUCCESS "Dashboard (Port 3000): $HTTP_DASH OK"
else
    log WARN "Dashboard (Port 3000): $HTTP_DASH (Check logs)"
fi

log INFO "Installation Complete. Log saved to $LOG_FILE"
exit 0
