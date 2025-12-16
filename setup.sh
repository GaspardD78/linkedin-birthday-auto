#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - ULTIMATE SETUP SCRIPT v13.3 "Security First"    ║
# ║  Refactored & Hardened for Raspberry Pi 4                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# Strict Mode
set -e
set -o pipefail

# ═══════════════════════════════════════════════════════════════════════════
# 0. CORE FRAMEWORK & LOGGING
# ═══════════════════════════════════════════════════════════════════════════

# Pre-flight Check: Root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: This script must be run as root (sudo ./setup.sh)"
  exit 1
fi

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
        FIX)     color=$BLUE; icon="🔧" ;;
        SEC)     color=$YELLOW; icon="🔐" ;;
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
    # If running as root (sudo), $SUDO_USER holds the real user
    REAL_USER=${SUDO_USER:-$USER}
    chown -R $REAL_USER:$REAL_USER data logs config

    if [ -d "data/linkedin.db" ]; then
        log WARN "data/linkedin.db detected as a DIRECTORY. Fixing..."
        mv "data/linkedin.db" "data/linkedin.db.bak_$(date +%s)" || true
    fi
    if [ ! -e "data/linkedin.db" ]; then touch "data/linkedin.db"; fi

    # Apply secure permissions for container users (UID 1000)
    log INFO "Setting ownership to UID 1000:1000 (Container User)..."
    chown -R 1000:1000 data logs config
    chmod -R 775 data logs config

    # Security: Restrict .env access
    if [ -f ".env" ]; then
        chmod 600 .env
        log SEC "Secured .env permissions (600)."
    fi

    log SUCCESS "Permissions fixed: data, logs, config owned by 1000:1000."
}

# ═══════════════════════════════════════════════════════════════════════════
# 1. PHASE 1: PREREQUISITES (SYSTEM)
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔍 PHASE 1: System Prerequisites"

check_connectivity

# Essential Packages for Host
# nginx: Reverse Proxy
# certbot: SSL
# python3-certbot-nginx: SSL Plugin
# rclone: Backup (optional but good)
# bc: Calculator (required by audit script)
# apache2-utils: htpasswd utils
PACKAGES=("nginx" "certbot" "python3-certbot-nginx" "rclone" "bc" "apache2-utils" "python3-bcrypt")
MISSING_PKGS=()

for pkg in "${PACKAGES[@]}"; do
    if ! dpkg -s "$pkg" &> /dev/null; then
        MISSING_PKGS+=("$pkg")
    fi
done

if [ ${#MISSING_PKGS[@]} -ne 0 ]; then
    log WARN "Installing missing system packages: ${MISSING_PKGS[*]}"
    apt-get update -qq
    apt-get install -y "${MISSING_PKGS[@]}"
    log FIX "System packages installed."
else
    log SUCCESS "All system packages present."
fi

# Tools Check (Binaries)
if ! check_command "docker"; then
    log WARN "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    REAL_USER=${SUDO_USER:-$USER}
    usermod -aG docker "$REAL_USER"
    log FIX "Docker installed. Reboot might be required."
fi

# ═══════════════════════════════════════════════════════════════════════════
# 2. PHASE 2: SECRETS & CONFIGURATION (.env)
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔐 PHASE 2: Secrets & Configuration"

# Ensure .env exists
if [ ! -f "$ENV_FILE" ]; then
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000|g" "$ENV_FILE"
    sed -i "s|NEXT_PUBLIC_DASHBOARD_URL=.*|NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000|g" "$ENV_FILE"
    log FIX "Created .env from template."
else
    # Smart Merge
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ ^#.* ]] || [[ -z "$line" ]]; then continue; fi
        KEY=$(echo "$line" | cut -d'=' -f1 | xargs)
        if [[ -n "$KEY" ]] && ! grep -q "^${KEY}=" "$ENV_FILE"; then
            echo "$line" >> "$ENV_FILE"
            log FIX "Added missing key: $KEY"
        fi
    done < "$ENV_TEMPLATE"
fi

# --------------------------------------------------------------------------
# SECURE PASSWORD CHECK (Idempotent)
# --------------------------------------------------------------------------
secure_password() {
    local key=$1
    local val=$(grep "^$key=" "$ENV_FILE" | cut -d'=' -f2-)

    # Check if empty
    if [[ -z "$val" ]]; then
        log WARN "$key is empty."
        return
    fi

    # Check if already hashed (Bcrypt starts with $2b$ or $2a$)
    if [[ "$val" == \$2* ]]; then
        log SUCCESS "$key is already hashed."
        return
    fi

    # It is cleartext -> Hash it immediately
    log SEC "Detected cleartext $key. Hashing automatically..."

    # Python One-Liner to hash
    # Use 'export' to pass variable safely to python without command line visibility
    export CLEAR_PASS="$val"
    HASHED=$(python3 -c "import bcrypt, os; print(bcrypt.hashpw(os.environ['CLEAR_PASS'].encode(), bcrypt.gensalt()).decode())" 2>/dev/null)
    unset CLEAR_PASS

    if [[ -n "$HASHED" ]]; then
        # Escape $ for sed/env file (replace $ with $$ for docker compose,
        # BUT here we are writing to .env which is read by bash/docker.
        # Docker Compose needs $$ for single $, but usually .env doesn't interpret $ unless strict.
        # Standard .env: $ is literal. Docker Compose variable expansion: needs $$.
        # Let's use $$ to be safe for Compose.
        ESCAPED_HASH=$(echo "$HASHED" | sed 's/\$/$$/g')

        # Replace strictly
        sed -i "s|^$key=.*|$key=$ESCAPED_HASH|" "$ENV_FILE"
        log FIX "Hashed $key and updated .env"
    else
        log ERROR "Failed to hash password for $key"
        exit 1
    fi
}

# Check DASHBOARD_PASSWORD
secure_password "DASHBOARD_PASSWORD"

# Check LINKEDIN_PASSWORD if it exists (Optional, per user hint)
if grep -q "^LINKEDIN_PASSWORD=" "$ENV_FILE"; then
   # NOTE: LinkedIn password for the bot usually needs to be cleartext for the bot to use it
   # (unless the bot supports de-hashing, which is rare).
   # However, if the user requested it, we apply it.
   # But based on architecture, it's likely DASHBOARD_PASSWORD meant.
   # We log a warning if we see it cleartext but don't auto-hash to avoid breaking bot login.
   VAL=$(grep "^LINKEDIN_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2-)
   if [[ "$VAL" != \$2* ]]; then
       log WARN "LINKEDIN_PASSWORD found in cleartext. Not hashing automatically (Bot likely needs cleartext)."
   fi
fi

# Ensure Critical Keys
for KEY in API_KEY JWT_SECRET; do
    VAL=$(grep "^$KEY=" "$ENV_FILE" | cut -d'=' -f2)
    if [[ -z "$VAL" || "$VAL" == "CHANGEZ_MOI"* ]]; then
        NEW_VAL=$(openssl rand -hex 32)
        sed -i "s|^$KEY=.*|$KEY=$NEW_VAL|" "$ENV_FILE"
        if [ "$KEY" == "API_KEY" ]; then
            sed -i "s|^BOT_API_KEY=.*|BOT_API_KEY=$NEW_VAL|" "$ENV_FILE"
        fi
        log FIX "Generated secure $KEY."
    fi
done

# ═══════════════════════════════════════════════════════════════════════════
# 3. PHASE 3: HOST NGINX CONFIGURATION (Idempotent)
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🌐 PHASE 3: Host Nginx Configuration"

# Determine Domain
DOMAIN_NAME=$(grep "^DOMAIN_NAME=" "$ENV_FILE" | cut -d'=' -f2)
if [[ -z "$DOMAIN_NAME" ]]; then
    read -p "$(echo -e "${BOLD}Domaine (Default: gaspardanoukolivier.freeboxos.fr): ${NC}")" INPUT_DOMAIN
    DOMAIN_NAME=${INPUT_DOMAIN:-"gaspardanoukolivier.freeboxos.fr"}
    # Save to .env for future runs
    echo "DOMAIN_NAME=$DOMAIN_NAME" >> "$ENV_FILE"
fi

NGINX_TEMPLATE="deployment/nginx/linkedin-bot.conf"
NGINX_TARGET="/etc/nginx/sites-available/linkedin-bot"
NGINX_LINK="/etc/nginx/sites-enabled/linkedin-bot"

if [ ! -f "$NGINX_TEMPLATE" ]; then
    log ERROR "Nginx template $NGINX_TEMPLATE not found!"
    exit 1
fi

# Prepare expected configuration content (Simulate Template Rendering)
# We use a temp file
TEMP_CONF=$(mktemp)
cp "$NGINX_TEMPLATE" "$TEMP_CONF"

# Apply Substitutions (Host Mode)
sed -i "s/server_name .*/server_name $DOMAIN_NAME;/g" "$TEMP_CONF"
sed -i "s|http://dashboard:3000|http://127.0.0.1:3000|g" "$TEMP_CONF"
sed -i "s|http://bot-api:8000|http://127.0.0.1:8000|g" "$TEMP_CONF"
sed -i "s|root /var/www/certbot|root /var/www/html|g" "$TEMP_CONF"

# Compare with existing
NEEDS_RELOAD=false

if [ ! -f "$NGINX_TARGET" ]; then
    log INFO "Nginx config missing. Installing..."
    cp "$TEMP_CONF" "$NGINX_TARGET"
    NEEDS_RELOAD=true
else
    # Diff check
    if ! cmp -s "$TEMP_CONF" "$NGINX_TARGET"; then
        log INFO "Nginx config changed. Updating..."
        cp "$TEMP_CONF" "$NGINX_TARGET"
        NEEDS_RELOAD=true
    else
        log SUCCESS "Nginx config is up to date."
    fi
fi
rm "$TEMP_CONF"

# Symlink
if [ ! -L "$NGINX_LINK" ]; then
    ln -s "$NGINX_TARGET" "$NGINX_LINK"
    log FIX "Enabled Nginx site."
    NEEDS_RELOAD=true
fi

# Disable Default
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    unlink /etc/nginx/sites-enabled/default
    log FIX "Disabled default Nginx site."
    NEEDS_RELOAD=true
fi

# Test & Reload
if [ "$NEEDS_RELOAD" = true ]; then
    if nginx -t; then
        systemctl reload nginx
        log FIX "Nginx reloaded."
    else
        log ERROR "Nginx configuration test failed!"
        exit 1
    fi
fi

# Verify Ports
if ! lsof -i :80 | grep -q nginx; then
    log WARN "Port 80 is not held by Nginx. Check for conflicting services."
fi

# SSL Certs
if [ ! -d "/etc/letsencrypt/live/$DOMAIN_NAME" ]; then
    log INFO "Generating SSL certificates for $DOMAIN_NAME..."
    # Non-interactive, agree TOS, redirect HTTP->HTTPS
    certbot --nginx -d "$DOMAIN_NAME" --non-interactive --agree-tos --email "admin@$DOMAIN_NAME" --redirect || log WARN "Certbot failed."
else
    log SUCCESS "SSL Certificates present."
fi

# ═══════════════════════════════════════════════════════════════════════════
# 4. PHASE 4: DEPLOYMENT & OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🚀 PHASE 4: Docker Deployment"

fix_permissions

DOCKER_CMD="docker compose"
if ! docker compose version &>/dev/null; then DOCKER_CMD="docker-compose"; fi

if [ "$CLEAN_DEPLOY" = true ]; then
    log WARN "Cleaning up existing containers..."
    $DOCKER_CMD -f "$COMPOSE_FILE" down --remove-orphans
fi

log INFO "Pulling images..."
SERVICES="redis-bot redis-dashboard api bot-worker dashboard"
# Removed 'nginx' from services since we use Host Nginx now
for svc in $SERVICES; do
    $DOCKER_CMD -f "$COMPOSE_FILE" pull "$svc" || log WARN "Could not pull $svc"
done

log INFO "Starting Stack (Scaling up)..."
$DOCKER_CMD -f "$COMPOSE_FILE" up -d --remove-orphans

log INFO "🧹 Optimization: Pruning unused images..."
docker image prune -f > /dev/null 2>&1
log FIX "Docker images pruned."

# ═══════════════════════════════════════════════════════════════════════════
# 5. PHASE 5: VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🕵️ PHASE 5: Health Check"

wait_for_healthy() {
    local service=$1
    local max_retries=60 # 5 mins
    local retry=0

    echo -n "Waiting for $service: "
    while [ $retry -lt $max_retries ]; do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "starting")
        if [ "$STATUS" == "healthy" ]; then
            echo -e " ${GREEN}OK${NC}"
            return 0
        fi
        echo -n "."
        sleep 5
        ((retry++))
    done
    echo -e " ${RED}FAILED${NC}"
    return 1
}

# We allow wait_for_healthy to fail without exiting immediately to run diagnostics
set +e
wait_for_healthy "bot-api"
wait_for_healthy "dashboard"
set -e

# DB Init
docker exec bot-api python -m src.scripts.init_db || log WARN "DB Init warning"

# Final Report
echo -e "\n"
echo -e "╔════════════════════════════════════════════════════════════════════╗"
echo -e "║                 🚀 DÉPLOIEMENT TERMINÉ (v13.3)                     ║"
echo -e "╚════════════════════════════════════════════════════════════════════╝"
echo -e "🌐 Dashboard : https://$DOMAIN_NAME (ou http://$LOCAL_IP:3000)"
echo -e "🔐 Password  : (Hashé dans .env)"
echo -e "📝 Logs      : $LOG_FILE"
echo -e ""
exit 0
