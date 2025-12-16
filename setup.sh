#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - ULTIMATE SETUP SCRIPT v13.2 "Crystal Clear"     ║
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

# Global Variables for Report
TEMP_CLEAR_PASS=""
TEMP_HASH_PASS=""
DASHBOARD_USER=""
LOCAL_IP=""
DOMAIN_NAME=""

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
         return 1
    fi
    log SUCCESS "Network connectivity OK."
}

fix_permissions() {
    log INFO "Applying preventive permission fixes..."
    mkdir -p data logs config

    # Reclaim ownership from Docker (root) to current user for initial setup
    sudo chown -R $USER:$USER data logs config

    if [ -d "data/linkedin.db" ]; then
        log WARN "data/linkedin.db detected as a DIRECTORY. Fixing..."
        mv "data/linkedin.db" "data/linkedin.db.bak_$(date +%s)" || true
    fi
    if [ ! -e "data/linkedin.db" ]; then touch "data/linkedin.db"; fi

    # Apply secure permissions for container users (UID 1000)
    # Using 1000:1000 as defined in Dockerfiles (appuser/node)
    log INFO "Setting ownership to UID 1000:1000 (Container User)..."
    sudo chown -R 1000:1000 data logs config

    # Ensure group write access if host user is part of group 1000,
    # but strictly chmod 777 is not needed if ownership is correct.
    # However, to avoid 'Permission denied' on host if mapped, we keep it readable.
    sudo chmod -R 775 data logs config

    log SUCCESS "Permissions fixed: data, logs, config owned by 1000:1000."
}

# ═══════════════════════════════════════════════════════════════════════════
# 1. PHASE 1: INFRASTRUCTURE & CREDENTIALS
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔍 PHASE 1: Infrastructure Check"

check_connectivity

# ZRAM vs Swap Check (Optimized for Pi 4)
SWAP_TOTAL=$(free -m | awk '/Swap/ {print $2}')
# CORRECTION: Revert to 2000MB threshold to catch default 100MB Swap and ensure enough memory
if [ "$SWAP_TOTAL" -lt 2000 ]; then
    log WARN "Insufficient Swap detected: ${SWAP_TOTAL}MB (Recommended: 2048MB+ or ZRAM)."

    if check_command "zramctl"; then
        log SUCCESS "ZRAM detected, this is optimal for Raspberry Pi 4."
    else
        log INFO "Checking for ZRAM support..."
        if ask_confirmation "Install optimized ZRAM (Recommended for Pi4) instead of slow SwapFile?"; then
             sudo apt-get update && sudo apt-get install -y zram-tools
             # Default config is usually fine (50% RAM), reload service
             sudo systemctl restart zramswap || true
             log SUCCESS "ZRAM installed and active."
        else
            # Fallback to legacy dphys-swapfile
             log WARN "Falling back to standard SwapFile (slower)."
             # Only ask if swap is truly low (e.g. < 2GB)
             if [ "$SWAP_TOTAL" -lt 2000 ]; then
                 if ask_confirmation "Increase SwapFile to 2GB?"; then
                     sudo dphys-swapfile swapoff || true
                     sudo sed -i 's/^#*CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
                     sudo dphys-swapfile setup
                     sudo dphys-swapfile swapon
                     log SUCCESS "SwapFile updated to 2048MB."
                 fi
             fi
        fi
    fi
else
    log SUCCESS "Swap/ZRAM Config OK: ${SWAP_TOTAL}MB"
fi

# Tools Check
TOOLS=("git" "python3" "curl" "grep" "sed" "lsof")
MISSING_TOOLS=()
for tool in "${TOOLS[@]}"; do
    if ! check_command "$tool"; then MISSING_TOOLS+=("$tool"); fi
done
if [ ${#MISSING_TOOLS[@]} -ne 0 ]; then
    log WARN "Installing missing tools: ${MISSING_TOOLS[*]}"
    sudo apt-get update -qq && sudo apt-get install -y "${MISSING_TOOLS[@]}"
fi

# Docker Check
if ! check_command "docker"; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    log WARN "Docker installed. Reboot required."
    exit 1
fi

# Password Management
reset_password() {
    log INFO "🔑 PHASE 1.5: Credential Management (Systematic Reset)"

    if ! python3 -c "import bcrypt" 2>/dev/null; then
        sudo apt-get install -y python3-bcrypt || pip3 install bcrypt || true
    fi

    if [[ -n "$HEADLESS_PASSWORD" ]]; then
        TEMP_CLEAR_PASS="$HEADLESS_PASSWORD"
        log INFO "Using headless password."
    else
        echo -e "${YELLOW}Enter new dashboard password (leave empty to generate random):${NC}"
        # Use simple read to allow empty input
        read -s -p "Password: " USER_PASS
        echo ""
        if [[ -z "$USER_PASS" ]]; then
            TEMP_CLEAR_PASS=$(openssl rand -base64 12)
            log INFO "Generated random password."
        else
            TEMP_CLEAR_PASS="$USER_PASS"
        fi
    fi

    export PASS_VAR="$TEMP_CLEAR_PASS"
    TEMP_HASH_PASS=$(python3 -c "import bcrypt, os; print(bcrypt.hashpw(os.environ['PASS_VAR'].encode(), bcrypt.gensalt()).decode())" 2>/dev/null)
    unset PASS_VAR

    if [[ -n "$TEMP_HASH_PASS" ]]; then
        # Escape $ for Docker Compose
        ESCAPED_HASH=$(echo "$TEMP_HASH_PASS" | sed 's/\$/$$/g')
        # Smart Update .env
        if grep -q "^DASHBOARD_PASSWORD=" "$ENV_FILE"; then
            sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=$ESCAPED_HASH|" "$ENV_FILE"
        else
            echo "DASHBOARD_PASSWORD=$ESCAPED_HASH" >> "$ENV_FILE"
        fi
        log SUCCESS "Password updated in .env"
    else
        log ERROR "Failed to hash password."
        exit 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# 2. PHASE 2: CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔒 PHASE 2: Configuration"

if [ ! -f "$ENV_FILE" ]; then
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000|g" "$ENV_FILE"
    sed -i "s|NEXT_PUBLIC_DASHBOARD_URL=.*|NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000|g" "$ENV_FILE"
    log SUCCESS "Created .env from template."
else
    # Smart Merge (Append missing keys)
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ ^#.* ]] || [[ -z "$line" ]]; then continue; fi
        KEY=$(echo "$line" | cut -d'=' -f1 | xargs)
        if [[ -n "$KEY" ]] && ! grep -q "^${KEY}=" "$ENV_FILE"; then
            echo "$line" >> "$ENV_FILE"
            log INFO "Added missing key: $KEY"
        fi
    done < "$ENV_TEMPLATE"

    # Ensure Critical Defaults
    if ! grep -q "^DASHBOARD_PORT=" "$ENV_FILE"; then
         echo "DASHBOARD_PORT=3000" >> "$ENV_FILE"
    fi
fi

# Run Password Reset
reset_password

# Retrieve User
DASHBOARD_USER=$(grep "^DASHBOARD_USER=" "$ENV_FILE" | cut -d'=' -f2)
[ -z "$DASHBOARD_USER" ] && DASHBOARD_USER="admin"

# Generate other secrets if missing
for KEY in API_KEY JWT_SECRET; do
    VAL=$(grep "^$KEY=" "$ENV_FILE" | cut -d'=' -f2)
    if [[ -z "$VAL" || "$VAL" == "CHANGEZ_MOI"* ]]; then
        NEW_VAL=$(openssl rand -hex 32)
        sed -i "s|^$KEY=.*|$KEY=$NEW_VAL|" "$ENV_FILE"
        if [ "$KEY" == "API_KEY" ]; then
            sed -i "s|^BOT_API_KEY=.*|BOT_API_KEY=$NEW_VAL|" "$ENV_FILE"
        fi
        log SUCCESS "Generated secure $KEY."
    fi
done

# ═══════════════════════════════════════════════════════════════════════════
# 2.5 HTTPS & REVERSE PROXY CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🌐 PHASE 2.5: HTTPS Configuration"

ENABLE_HTTPS=false

# Check if ports 80/443 are free
PORTS_HTTP=(80 443)
HTTP_PORTS_BUSY=false
for p in "${PORTS_HTTP[@]}"; do
    if sudo lsof -i :$p >/dev/null 2>&1; then
        PID=$(sudo lsof -t -i :$p | head -n1)
        PROCESS=$(ps -p $PID -o comm=)
        if [[ "$PROCESS" != "dockerd" && "$PROCESS" != "docker-proxy" ]]; then
            log WARN "Port $p occupied by $PROCESS. HTTPS setup might fail."
            HTTP_PORTS_BUSY=true
        fi
    fi
done

if [ "$HTTP_PORTS_BUSY" = false ]; then
    if ask_confirmation "Voulez-vous activer l'accès externe via HTTPS (Reverse Proxy Nginx) ?"; then
        ENABLE_HTTPS=true

        # Get Domain
        read -p "$(echo -e "${BOLD}Domaine (Default: gaspardanoukolivier.freeboxos.fr): ${NC}")" INPUT_DOMAIN
        DOMAIN_NAME=${INPUT_DOMAIN:-"gaspardanoukolivier.freeboxos.fr"}

        # Get Email for Certbot
        read -p "$(echo -e "${BOLD}Email pour Let's Encrypt: ${NC}")" EMAIL_ADDR

        if [[ -z "$EMAIL_ADDR" ]]; then
            log ERROR "Email requise pour SSL. Abort HTTPS setup."
            ENABLE_HTTPS=false
        else
            log INFO "Setting up HTTPS for $DOMAIN_NAME..."
            mkdir -p certbot/conf certbot/www

            # Update Nginx Config with Domain
            NGINX_CONF="deployment/nginx/linkedin-bot.conf"
            if [ -f "$NGINX_CONF" ]; then
                # Use sed to replace placeholder or update existing
                sed -i "s/server_name .*/server_name $DOMAIN_NAME;/g" "$NGINX_CONF"
                log SUCCESS "Updated Nginx config with domain $DOMAIN_NAME"
            else
                log ERROR "Nginx config not found at $NGINX_CONF"
                exit 1
            fi

            # Check for existing certs
            if ! sudo test -d "certbot/conf/live/$DOMAIN_NAME"; then
                log INFO "Generating SSL Certificates via Certbot (Standalone)..."

                # AUTO-FIX: Check if nginx-proxy container is holding port 80
                NGINX_CONTAINER="nginx-proxy"
                NGINX_WAS_RUNNING=false
                if docker ps --format '{{.Names}}' | grep -q "^$NGINX_CONTAINER$"; then
                     log WARN "Stopping $NGINX_CONTAINER to free Port 80 for Certbot..."
                     docker stop "$NGINX_CONTAINER" || true
                     NGINX_WAS_RUNNING=true
                     sleep 3 # Wait for socket release
                fi

                # Check port 80 again
                if sudo lsof -i :80 >/dev/null 2>&1; then
                     log ERROR "Port 80 still busy (System process?). Cannot proceed with Certbot."
                     log ERROR "Use: sudo lsof -i :80 to find the culprit."
                     ENABLE_HTTPS=false
                else
                    if [ "$ENABLE_HTTPS" = true ]; then
                        docker run --rm -p 80:80 \
                            -v "$PWD/certbot/conf:/etc/letsencrypt" \
                            -v "$PWD/certbot/www:/var/www/certbot" \
                            certbot/certbot certonly \
                            --standalone \
                            --email "$EMAIL_ADDR" \
                            --agree-tos \
                            --no-eff-email \
                            -d "$DOMAIN_NAME" \
                            --non-interactive || log ERROR "Certbot failed. Check DNS or Port 80."

                        if sudo test -d "certbot/conf/live/$DOMAIN_NAME"; then
                            log SUCCESS "Certificates generated successfully!"
                        else
                            log WARN "Certificate generation failed. Nginx might fail to start."
                        fi
                    fi
                fi

                # Restart Nginx if we stopped it (will be handled by docker compose up later anyway, but good practice)
                # if [ "$NGINX_WAS_RUNNING" = true ]; then docker start "$NGINX_CONTAINER" || true; fi
            else
                log INFO "Existing certificates found for $DOMAIN_NAME. Skipping generation."
            fi
        fi
    fi
else
    log WARN "Ports 80/443 busy. Skipping HTTPS setup."
fi


# ═══════════════════════════════════════════════════════════════════════════
# 3. PHASE 3: DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🚀 PHASE 3: Deployment"

fix_permissions

DOCKER_CMD="docker compose"
if ! docker compose version &>/dev/null; then DOCKER_CMD="docker-compose"; fi

if [ "$CLEAN_DEPLOY" = true ]; then
    log WARN "Cleaning up existing containers..."
    $DOCKER_CMD -f "$COMPOSE_FILE" down --remove-orphans
fi

log INFO "Pulling images..."
SERVICES="redis-bot redis-dashboard api bot-worker dashboard nginx"
for svc in $SERVICES; do
    $DOCKER_CMD -f "$COMPOSE_FILE" pull "$svc" || log WARN "Could not pull $svc"
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
    echo -n "Waiting: "

    while [ $retry -lt $max_retries ]; do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "starting")
        if [ "$STATUS" == "healthy" ]; then
            echo ""
            log SUCCESS "$service is healthy."
            return 0
        fi
        echo -n "."
        sleep 5
        ((retry++))
    done

    echo ""
    log ERROR "CRITICAL: $service failed to become healthy."
    return 1
}

# We allow wait_for_healthy to fail without exiting immediately to run diagnostics
set +e
wait_for_healthy "bot-api"
API_EXIT=$?
wait_for_healthy "dashboard"
DASH_EXIT=$?
set -e

# DB Init
docker exec bot-api python -m src.scripts.init_db || log WARN "DB Init warning"

# ═══════════════════════════════════════════════════════════════════════════
# 5. PHASE 5: DIAGNOSTIC REPORT
# ═══════════════════════════════════════════════════════════════════════════

audit_services() {
    log INFO "🕵️ PHASE 5: Deep Health Audit"

    # Audit Targets
    TARGETS=("dashboard" "bot-api" "bot-worker" "redis-bot" "nginx-proxy")
    declare -A SERVICE_STATUS
    declare -A SERVICE_ERRORS

    for svc in "${TARGETS[@]}"; do
        # 1. Status Check
        RAW_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$svc" 2>/dev/null || echo "running") # nginx doesn't have healthcheck by default

        # 2. Log Mining (Last 100 lines)
        LOGS=$(docker logs --tail 100 "$svc" 2>&1)
        ERROR_COUNT=$(echo "$LOGS" | grep -c -iE "Error|Exception|Traceback|Connection refused" || true)
        ERRORS=$(echo "$LOGS" | grep -iE "Error|Exception|Traceback|Connection refused" | tail -n 5 || true)

        if [[ "$RAW_STATUS" == "healthy" || "$RAW_STATUS" == "running" ]] && [[ "$ERROR_COUNT" -eq 0 ]]; then
            SERVICE_STATUS[$svc]="${GREEN}OK${NC}"
        elif [[ "$RAW_STATUS" == "healthy" || "$RAW_STATUS" == "running" ]]; then
             SERVICE_STATUS[$svc]="${YELLOW}WARNING (${ERROR_COUNT} log errors)${NC}"
             SERVICE_ERRORS[$svc]="$ERRORS"
        else
             SERVICE_STATUS[$svc]="${RED}CRITICAL (${RAW_STATUS})${NC}"
             SERVICE_ERRORS[$svc]="$ERRORS"
        fi
    done

    LOCAL_IP=$(hostname -I | awk '{print $1}')

    # Display "Crystal Clear" Box
    echo -e "\n"
    echo -e "╔════════════════════════════════════════════════════════════════════╗"
    echo -e "║                 🚀 RAPPORT D'INSTALLATION v13.2                    ║"
    echo -e "╚════════════════════════════════════════════════════════════════════╝"
    echo -e ""
    echo -e "${BOLD}1. ACCÈS DASHBOARD${NC}"
    echo -e "──────────────────"
    echo -e "🌐 Local    : http://${LOCAL_IP:-localhost}:${DASHBOARD_PORT:-3000}"
    if [ "$ENABLE_HTTPS" = true ]; then
    echo -e "🔒 HTTPS    : https://${DOMAIN_NAME}"
    fi
    echo -e "👤 User     : ${DASHBOARD_USER}"
    echo -e "🔑 Pass     : ${TEMP_CLEAR_PASS}      <-- (En clair)"
    echo -e "🔒 Hash     : ${TEMP_HASH_PASS}      <-- (Stocké dans .env)"
    echo -e ""
    echo -e "${BOLD}2. ÉTAT DES SERVICES${NC}"
    echo -e "────────────────────"
    echo -e "🟢 Dashboard  : ${SERVICE_STATUS[dashboard]}"
    echo -e "🟢 API        : ${SERVICE_STATUS[bot-api]}"
    echo -e "🟢 Bot Worker : ${SERVICE_STATUS[bot-worker]}"
    echo -e "🟢 Redis      : ${SERVICE_STATUS[redis-bot]}"
    echo -e "🟢 Nginx      : ${SERVICE_STATUS[nginx-proxy]}"
    echo -e ""

    # Security Status Check
    SEC_HTTPS="❌ Désactivé"
    if [ "$ENABLE_HTTPS" = true ] && [ -d "certbot/conf/live/$DOMAIN_NAME" ]; then
        SEC_HTTPS="✅ Activé ($DOMAIN_NAME)"
    fi

    SEC_PERMS="✅ Correctes (UID 1000)"
    if [ "$(stat -c '%u' data)" != "1000" ]; then
        SEC_PERMS="⚠️  Incorrectes (Check owner)"
    fi

    SEC_ENV="✅ Sécurisé (600)"
    ENV_PERM=$(stat -c '%a' .env 2>/dev/null || echo "Unknown")
    if [[ "$ENV_PERM" != "600" && "$ENV_PERM" != "640" ]]; then
         SEC_ENV="⚠️  Permissions .env: $ENV_PERM (Rec: 600)"
    fi

    echo -e "${BOLD}3. ÉTAT SÉCURITÉ${NC}"
    echo -e "────────────────"
    echo -e "🔒 HTTPS    : ${SEC_HTTPS}"
    echo -e "👤 Droits   : ${SEC_PERMS}"
    echo -e "🔑 Secrets  : ${SEC_ENV}"
    echo -e ""

    echo -e "${BOLD}4. DÉTAILS DEBUG (Si erreurs détectées)${NC}"
    echo -e "───────────────────────────────────────"
    ANY_ERRORS=false
    for svc in "${TARGETS[@]}"; do
        if [[ -n "${SERVICE_ERRORS[$svc]}" ]]; then
            ANY_ERRORS=true
            echo -e "${YELLOW}>> ${svc}:${NC}"
            echo -e "${SERVICE_ERRORS[$svc]}"
            echo ""
        fi
    done

    if [ "$ANY_ERRORS" = false ]; then
        echo -e "${GREEN}Aucune erreur critique détectée dans les logs récents.${NC}"
    fi

    # SD Card Optimization: Cleanup
    log INFO "🧹 Cleanup: Removing unused docker images to save SD card space..."
    docker system prune -f > /dev/null 2>&1 || true

    echo -e "\n⚠️  ${BOLD}Sauvegardez vos identifiants maintenant !${NC}"

    # Exit code based on wait_for_healthy results
    if [ "$API_EXIT" -ne 0 ] || [ "$DASH_EXIT" -ne 0 ]; then
        exit 1
    fi
}

audit_services
exit 0
