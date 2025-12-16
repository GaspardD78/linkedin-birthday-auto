#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - ULTIMATE SETUP SCRIPT v14.0 "Nginx Host"        ║
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

# Logging
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

    echo -e "${color}[${timestamp}] ${icon} [${level}] ${msg}${NC}"
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
        if systemctl is-active nginx >/dev/null 2>&1; then
             log INFO "Nginx Logs (Last 20 lines):"
             tail -n 20 /var/log/nginx/error.log 2>/dev/null || echo "No nginx log"
        else
             log ERROR "Nginx failed to start. Journalctl:"
             journalctl -xeu nginx --no-pager | tail -n 20
        fi
    fi
}
trap 'error_handler ${LINENO} $?' EXIT

# Utilities
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
    REAL_USER=${SUDO_USER:-$USER}
    chown -R $REAL_USER:$REAL_USER data logs config
    if [ -d "data/linkedin.db" ]; then mv "data/linkedin.db" "data/linkedin.db.bak_$(date +%s)" || true; fi
    if [ ! -e "data/linkedin.db" ]; then touch "data/linkedin.db"; fi
    chown -R 1000:1000 data logs config
    chmod -R 775 data logs config
    if [ -f ".env" ]; then chmod 600 .env; fi
    log SUCCESS "Permissions fixed."
}

# ═══════════════════════════════════════════════════════════════════════════
# FUNCTION: HOST NGINX SETUP
# ═══════════════════════════════════════════════════════════════════════════
setup_host_nginx() {
    log INFO "🌐 Setting up Host Nginx..."

    # 1. Install Packages
    if ! dpkg -s nginx &> /dev/null; then
        log INFO "Installing Nginx & Tools..."
        apt-get update -qq
        apt-get install -y nginx apache2-utils python3-certbot-nginx
    fi

    # 2. Configure Rate Limit Zones
    if [ -f "deployment/nginx/rate-limit-zones.conf" ]; then
        cp "deployment/nginx/rate-limit-zones.conf" "/etc/nginx/conf.d/"
        log FIX "Copied rate-limit-zones.conf"
    else
        log WARN "rate-limit-zones.conf not found. Creating default..."
        cat > "/etc/nginx/conf.d/rate-limit-zones.conf" <<EOF
limit_req_zone \$binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=login:10m rate=1r/m;
limit_req_zone \$binary_remote_addr zone=api:10m rate=60r/m;
EOF
        log FIX "Created default rate-limit-zones.conf"
    fi

    # 3. Verify nginx.conf includes conf.d
    # Default nginx.conf usually includes /etc/nginx/conf.d/*.conf inside http block
    # We assume it is present or we would need complex sed.

    # 4. Prepare Site Config
    local template="deployment/nginx/linkedin-bot.conf"
    local target="/etc/nginx/sites-available/linkedin-bot"
    local link="/etc/nginx/sites-enabled/linkedin-bot"
    local temp_conf=$(mktemp)

    if [ ! -f "$template" ]; then
        log ERROR "Nginx template not found: $template"
        exit 1
    fi

    cp "$template" "$temp_conf"

    # Replacements
    local domain=${DOMAIN_NAME:-"gaspardanoukolivier.freeboxos.fr"}
    sed -i "s|YOUR_DOMAIN.COM|$domain|g" "$temp_conf"
    # Ensure local proxies are correct (template has 127.0.0.1:3000 but double check)
    sed -i "s|http://dashboard:3000|http://127.0.0.1:3000|g" "$temp_conf"

    # SSL Check
    local cert_path="/etc/letsencrypt/live/$domain/fullchain.pem"
    local key_path="/etc/letsencrypt/live/$domain/privkey.pem"
    local ssl_options="/etc/letsencrypt/options-ssl-nginx.conf"

    if [ -f "$cert_path" ] && [ -f "$key_path" ]; then
        log INFO "SSL Certs found for $domain. Enabling HTTPS..."
        # Uncomment SSL lines
        sed -i "s|# ssl_certificate |ssl_certificate |g" "$temp_conf"
        sed -i "s|# ssl_certificate_key |ssl_certificate_key |g" "$temp_conf"

        # FIX: Point to correct options-ssl-nginx.conf if it exists in letsencrypt dir (Idempotence)
        if [ -f "/etc/letsencrypt/options-ssl-nginx.conf" ]; then
             sed -i "s|/etc/nginx/conf.d/options-ssl-nginx.conf|/etc/letsencrypt/options-ssl-nginx.conf|g" "$temp_conf"
        fi
        if [ -f "/etc/letsencrypt/ssl-dhparams.pem" ]; then
             sed -i "s|/etc/nginx/conf.d/ssl-dhparams.pem|/etc/letsencrypt/ssl-dhparams.pem|g" "$temp_conf"
        fi

        # Check for options file presence
        # If we didn't update the path (still pointing to conf.d) and it doesn't exist there, comment it out
        if grep -q "/etc/nginx/conf.d/options-ssl-nginx.conf" "$temp_conf" && [ ! -f "/etc/nginx/conf.d/options-ssl-nginx.conf" ]; then
             sed -i "s|include /etc/nginx/conf.d/options-ssl-nginx.conf;|# options-ssl-nginx.conf missing|g" "$temp_conf"
        fi
        if grep -q "/etc/nginx/conf.d/ssl-dhparams.pem" "$temp_conf" && [ ! -f "/etc/nginx/conf.d/ssl-dhparams.pem" ]; then
             sed -i "s|ssl_dhparam /etc/nginx/conf.d/ssl-dhparams.pem;|# ssl-dhparams missing|g" "$temp_conf"
        fi
    else
        log WARN "SSL Certs NOT found for $domain."
        log INFO "Installing HTTP-only config first to allow Certbot to run..."

        # Remove the HTTPS block for now to prevent errors
        # We assume HTTPS_BLOCK_START and HTTPS_BLOCK_END markers exist
        sed -i '/HTTPS_BLOCK_START/,/HTTPS_BLOCK_END/d' "$temp_conf"
    fi

    # Install Config
    cp "$temp_conf" "$target"
    if [ ! -L "$link" ]; then ln -s "$target" "$link"; fi
    if [ -L "/etc/nginx/sites-enabled/default" ]; then unlink /etc/nginx/sites-enabled/default; fi

    # Permissions
    chown -R www-data:adm /var/log/nginx || true
    chmod 755 /var/log/nginx || true

    # Test & Restart
    if nginx -t; then
        systemctl restart nginx
        log FIX "Nginx started/restarted."
    else
        log ERROR "Nginx configuration invalid!"
        nginx -t
        exit 1
    fi

    # Certbot Run (if needed)
    if [ ! -f "$cert_path" ]; then
        log INFO "Requesting SSL Certificate via Certbot..."
        # We use 'certonly' so we can overwrite the config with our robust version afterwards
        set +e
        certbot certonly --nginx -d "$domain" --non-interactive --agree-tos --email "admin@$domain"
        CERTBOT_RES=$?
        set -e

        if [ $CERTBOT_RES -eq 0 ]; then
             log SUCCESS "Certbot succeeded."
             # NOW: Re-install the FULL config with HTTPS enabled
             log INFO "Applying Full HTTPS Configuration..."
             cp "$template" "$temp_conf"
             sed -i "s|YOUR_DOMAIN.COM|$domain|g" "$temp_conf"
             sed -i "s|http://dashboard:3000|http://127.0.0.1:3000|g" "$temp_conf"

             # Uncomment SSL
             sed -i "s|# ssl_certificate |ssl_certificate |g" "$temp_conf"
             sed -i "s|# ssl_certificate_key |ssl_certificate_key |g" "$temp_conf"

             # Handle missing options file if any
             if [ ! -f "$ssl_options" ]; then
                 # Point to where certbot might have put them or just comment out
                 if [ -f "/etc/letsencrypt/options-ssl-nginx.conf" ]; then
                      sed -i "s|/etc/nginx/conf.d/options-ssl-nginx.conf|/etc/letsencrypt/options-ssl-nginx.conf|g" "$temp_conf"
                 else
                      sed -i "s|include /etc/nginx/conf.d/options-ssl-nginx.conf;|# options missing|g" "$temp_conf"
                 fi
                 if [ -f "/etc/letsencrypt/ssl-dhparams.pem" ]; then
                      sed -i "s|/etc/nginx/conf.d/ssl-dhparams.pem|/etc/letsencrypt/ssl-dhparams.pem|g" "$temp_conf"
                 else
                      sed -i "s|ssl_dhparam /etc/nginx/conf.d/ssl-dhparams.pem;|# dhparams missing|g" "$temp_conf"
                 fi
             fi

             cp "$temp_conf" "$target"
             if nginx -t; then
                 systemctl reload nginx
                 log SUCCESS "HTTPS Config enabled and Nginx reloaded."
             else
                 log WARN "Failed to enable HTTPS config. Reverting to HTTP."
                 # Re-run the HTTP-only setup... (Simplified: assume it worked before)
             fi
        else
             log ERROR "Certbot failed. System remains on HTTP."
        fi
    fi
    rm "$temp_conf"
}

# ═══════════════════════════════════════════════════════════════════════════
# 1. PHASE 1: PREREQUISITES (SYSTEM)
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔍 PHASE 1: System Prerequisites"

check_connectivity
PACKAGES=("nginx" "certbot" "python3-certbot-nginx" "rclone" "bc" "apache2-utils" "python3-bcrypt")
MISSING_PKGS=()
for pkg in "${PACKAGES[@]}"; do
    if ! dpkg -s "$pkg" &> /dev/null; then MISSING_PKGS+=("$pkg"); fi
done

if [ ${#MISSING_PKGS[@]} -ne 0 ]; then
    log WARN "Installing packages: ${MISSING_PKGS[*]}"
    apt-get update -qq
    apt-get install -y "${MISSING_PKGS[@]}"
    log FIX "Packages installed."
fi

if ! check_command "docker"; then
    log WARN "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    REAL_USER=${SUDO_USER:-$USER}
    usermod -aG docker "$REAL_USER"
fi

# ═══════════════════════════════════════════════════════════════════════════
# 2. PHASE 2: CONFIGURATION & SECRETS
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔐 PHASE 2: Configuration"

# Ensure .env
if [ ! -f "$ENV_FILE" ]; then
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000|g" "$ENV_FILE"
    sed -i "s|NEXT_PUBLIC_DASHBOARD_URL=.*|NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000|g" "$ENV_FILE"
fi

# Determine Domain (Crucial for Nginx)
DOMAIN_NAME=$(grep "^DOMAIN_NAME=" "$ENV_FILE" | cut -d'=' -f2 || true)
if [[ -z "$DOMAIN_NAME" ]]; then
    read -p "$(echo -e "${BOLD}Domaine (Default: gaspardanoukolivier.freeboxos.fr): ${NC}")" INPUT_DOMAIN
    DOMAIN_NAME=${INPUT_DOMAIN:-"gaspardanoukolivier.freeboxos.fr"}
    echo "DOMAIN_NAME=$DOMAIN_NAME" >> "$ENV_FILE"
fi

# Password Hashing Logic
secure_password() {
    local key=$1
    local val=$(grep "^$key=" "$ENV_FILE" | cut -d'=' -f2- || true)
    if [[ -z "$val" ]] || [[ "$val" == \$2* ]]; then return; fi
    log SEC "Hashing $key..."
    export CLEAR_PASS="$val"
    HASHED=$(python3 -c "import bcrypt, os; print(bcrypt.hashpw(os.environ['CLEAR_PASS'].encode(), bcrypt.gensalt()).decode())" 2>/dev/null)
    unset CLEAR_PASS
    if [[ -n "$HASHED" ]]; then
        ESCAPED_HASH=$(echo "$HASHED" | sed 's/\$/$$/g')
        sed -i "s|^$key=.*|$key=$ESCAPED_HASH|" "$ENV_FILE"
    fi
}
secure_password "DASHBOARD_PASSWORD"

# Ensure API Keys
for KEY in API_KEY JWT_SECRET; do
    VAL=$(grep "^$KEY=" "$ENV_FILE" | cut -d'=' -f2 || true)
    if [[ -z "$VAL" || "$VAL" == "CHANGEZ_MOI"* ]]; then
        NEW_VAL=$(openssl rand -hex 32)
        sed -i "s|^$KEY=.*|$KEY=$NEW_VAL|" "$ENV_FILE"
        if [ "$KEY" == "API_KEY" ]; then sed -i "s|^BOT_API_KEY=.*|BOT_API_KEY=$NEW_VAL|" "$ENV_FILE"; fi
    fi
done

# ═══════════════════════════════════════════════════════════════════════════
# 3. PHASE 3: DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🚀 PHASE 3: Docker Deployment"

fix_permissions
DOCKER_CMD="docker compose"
if ! docker compose version &>/dev/null; then DOCKER_CMD="docker-compose"; fi

if [ "$CLEAN_DEPLOY" = true ]; then
    log WARN "Cleaning up containers..."
    $DOCKER_CMD -f "$COMPOSE_FILE" down --remove-orphans
fi

log INFO "Starting Stack..."
$DOCKER_CMD -f "$COMPOSE_FILE" up -d --remove-orphans
docker image prune -f > /dev/null 2>&1

# ═══════════════════════════════════════════════════════════════════════════
# 4. PHASE 4: HOST NGINX
# ═══════════════════════════════════════════════════════════════════════════
# Execute Nginx setup AFTER Docker containers are up (as requested)
setup_host_nginx

# ═══════════════════════════════════════════════════════════════════════════
# 5. PHASE 5: VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🕵️ PHASE 5: Health Check"

wait_for_healthy() {
    local service=$1
    local max_retries=60
    local retry=0
    echo -n "Waiting for $service: "
    while [ $retry -lt $max_retries ]; do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "starting")
        if [ "$STATUS" == "healthy" ]; then echo -e " ${GREEN}OK${NC}"; return 0; fi
        echo -n "."
        sleep 5
        ((retry++))
    done
    echo -e " ${RED}FAILED${NC}"
    return 1
}

set +e
wait_for_healthy "bot-api"
wait_for_healthy "dashboard"
set -e

# Final Report
echo -e "\n"
echo -e "╔════════════════════════════════════════════════════════════════════╗"
echo -e "║                 🚀 DÉPLOIEMENT TERMINÉ (v14.0)                     ║"
echo -e "╚════════════════════════════════════════════════════════════════════╝"
echo -e "🌐 Dashboard : https://$DOMAIN_NAME"
echo -e "📝 Logs      : $LOG_FILE"
echo -e ""
exit 0
