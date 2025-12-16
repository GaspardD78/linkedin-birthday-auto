#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - ULTIMATE SETUP SCRIPT v14.1 "SD-Safe"           ║
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

# --- NEW: Cgroups Check for Raspberry Pi 4 ---
check_and_enable_cgroups() {
    log INFO "Checking Cgroups configuration (Memory/CPU)..."
    CMDLINE_FILE=""
    if [ -f "/boot/cmdline.txt" ]; then
        CMDLINE_FILE="/boot/cmdline.txt"
    elif [ -f "/boot/firmware/cmdline.txt" ]; then
        CMDLINE_FILE="/boot/firmware/cmdline.txt"
    fi

    if [ -z "$CMDLINE_FILE" ]; then
        log WARN "Could not find cmdline.txt. Skipping Cgroups check."
        return
    fi

    # Check for cgroup_memory=1
    if ! grep -q "cgroup_memory=1" "$CMDLINE_FILE"; then
        log WARN "Cgroups memory limit MISSING. Required for Docker reliability on Pi 4."
        echo -e "${RED}⚠️  Kernel update required: Enabling cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1${NC}"

        # Backup
        cp "$CMDLINE_FILE" "${CMDLINE_FILE}.bak"

        # Append to line
        sed -i 's/$/ cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1/' "$CMDLINE_FILE"

        log FIX "Cgroups flags added to $CMDLINE_FILE."
        echo -e "${RED}🔴 A SYSTEM REBOOT IS REQUIRED TO APPLY KERNEL CHANGES.${NC}"
        echo -e "${YELLOW}Please reboot and re-run this script.${NC}"

        read -p "Reboot now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            reboot
        else
            log ERROR "Script aborted. Please reboot manually."
            exit 1
        fi
    else
        log SUCCESS "Cgroups already enabled (Kernel OK)."
    fi
}

# --- NEW: Port 80 Auto-Correction ---
check_and_fix_port_80() {
    log INFO "Checking Port 80 availability..."

    # Check if port 80 is used
    if lsof -i :80 -t >/dev/null 2>&1 || netstat -lnp | grep -q ":80 "; then
        log WARN "Port 80 is occupied. Attempting auto-fix..."

        # Identify Process
        PID=$(lsof -i :80 -t | head -n 1)
        if [ -z "$PID" ]; then
            PID=$(netstat -lnp | grep ":80 " | awk '{print $7}' | cut -d'/' -f1)
        fi

        if [ -n "$PID" ]; then
            PNAME=$(ps -p "$PID" -o comm=)
            log INFO "Found blocking process: $PNAME (PID: $PID)"

            case "$PNAME" in
                nginx|apache2|lighttpd|httpd)
                    log FIX "Stopping web server service: $PNAME..."
                    systemctl stop "$PNAME" || kill "$PID"
                    systemctl disable "$PNAME" 2>/dev/null || true
                    ;;
                *)
                    log WARN "Unknown process on Port 80 ($PNAME). Killing it..."
                    kill -9 "$PID"
                    ;;
            esac
        else
            log WARN "Could not identify PID. Trying blind stop of common web servers..."
            systemctl stop nginx apache2 lighttpd 2>/dev/null || true
        fi

        # Verify
        sleep 2
        if lsof -i :80 -t >/dev/null 2>&1; then
             log ERROR "Port 80 is STILL occupied. Please free it manually."
             exit 1
        else
             log SUCCESS "Port 80 liberated."
        fi
    else
        log SUCCESS "Port 80 is free."
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# FUNCTION: HOST NGINX SETUP
# ═══════════════════════════════════════════════════════════════════════════
setup_host_nginx() {
    log INFO "🌐 Setting up Host Nginx..."

    # 1. Install Packages (Already done in Phase 1)

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

    # 3. Prepare Site Config
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
    sed -i "s|http://dashboard:3000|http://127.0.0.1:3000|g" "$temp_conf"

    # SSL Check
    local cert_path="/etc/letsencrypt/live/$domain/fullchain.pem"
    local key_path="/etc/letsencrypt/live/$domain/privkey.pem"

    if [ -f "$cert_path" ] && [ -f "$key_path" ]; then
        log INFO "SSL Certs found for $domain. Enabling HTTPS..."
        sed -i "s|# ssl_certificate |ssl_certificate |g" "$temp_conf"
        sed -i "s|# ssl_certificate_key |ssl_certificate_key |g" "$temp_conf"

        # Check options (simplified for brevity)
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
    else
        log WARN "SSL Certs NOT found. Installing HTTP-only config..."
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

    # Certbot
    if [ ! -f "$cert_path" ]; then
        log INFO "Requesting SSL Certificate via Certbot..."
        set +e
        certbot certonly --nginx -d "$domain" --non-interactive --agree-tos --email "admin@$domain"
        CERTBOT_RES=$?
        set -e
        if [ $CERTBOT_RES -eq 0 ]; then
             log SUCCESS "Certbot succeeded. Re-running setup_host_nginx to enable HTTPS..."
             setup_host_nginx # Recursive call to apply SSL config
             return
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

# 1. Check Cgroups (Kernel)
check_and_enable_cgroups

# 2. Network
check_connectivity

# 3. Packages
# Added 'lsof' and 'net-tools' (for netstat) to ensure Port 80 check works
PACKAGES=("nginx" "certbot" "python3-certbot-nginx" "rclone" "bc" "apache2-utils" "python3-bcrypt" "lsof" "net-tools")
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

# 4. Docker
if ! check_command "docker"; then
    log WARN "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    REAL_USER=${SUDO_USER:-$USER}
    usermod -aG docker "$REAL_USER"
fi

# 5. Check Port 80
check_and_fix_port_80

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

# Determine Domain
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

log INFO "Starting Stack (Sequential Pull enabled for SD protection)..."

# PROTECTION SD CARD: TÉLÉCHARGEMENT SÉQUENTIEL
export COMPOSE_PARALLEL_LIMIT=1

$DOCKER_CMD -f "$COMPOSE_FILE" up -d --remove-orphans
docker image prune -f > /dev/null 2>&1

# ═══════════════════════════════════════════════════════════════════════════
# 4. PHASE 4: HOST NGINX
# ═══════════════════════════════════════════════════════════════════════════
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
echo -e "║                 🚀 DÉPLOIEMENT TERMINÉ (v14.1)                     ║"
echo -e "╚════════════════════════════════════════════════════════════════════╝"
echo -e "🌐 Dashboard : https://$DOMAIN_NAME"
echo -e "📝 Logs      : $LOG_FILE"
echo -e ""
exit 0
