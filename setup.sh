#!/bin/bash
# ==============================================================================
# LINKEDIN AUTO RPi4 - SETUP MANAGER (V4.1 - STATE MANAGER)
# ==============================================================================
# Architecture : State Machine Pattern
# Objectif : Idempotence, Atomicité, Maintenance Préventive
# ==============================================================================

set -euo pipefail

# --- Configuration & Constantes ---
readonly MIN_MEMORY_GB=6      # RAM + SWAP minimum requis
readonly SWAP_FILE="/swapfile"
readonly ENV_FILE=".env"
readonly COMPOSE_FILE="docker-compose.pi4-standalone.yml"
readonly NGINX_TEMPLATE="deployment/nginx/linkedin-bot.conf.template"
readonly NGINX_CONFIG="deployment/nginx/linkedin-bot.conf"

# --- Couleurs ---
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

# --- Fonctions de Logging ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${BLUE}=== $1 ===${NC}\n"; }

# ==============================================================================
# MODULE 1: HARDWARE STATE (ZRAM, SWAP, KERNEL)
# ==============================================================================
ensure_hardware_state() {
    log_step "PHASE 1 : Hardware State Enforcement"

    # 1.1 Kernel Parameters (Idempotent)
    local sysctl_file="/etc/sysctl.d/99-rpi4-docker.conf"
    if ! grep -q "vm.overcommit_memory = 1" "$sysctl_file" 2>/dev/null; then
        log_info "Applying Kernel Optimizations..."
        cat <<EOF | sudo tee "$sysctl_file" > /dev/null
vm.overcommit_memory = 1
net.core.somaxconn = 1024
vm.swappiness = 10
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
EOF
        sudo sysctl -p "$sysctl_file" > /dev/null
    else
        log_success "Kernel parameters already optimized."
    fi

    # 1.2 ZRAM State & Persistence
    if ! lsblk | grep -q "zram0"; then
        log_info "Activating ZRAM (1GB)..."

        # Check module availability with sudo
        if sudo modprobe zram num_devices=1 2>/dev/null; then
            echo lz4 | sudo tee /sys/block/zram0/comp_algorithm > /dev/null
            echo 1G | sudo tee /sys/block/zram0/disksize > /dev/null
            sudo mkswap /dev/zram0 > /dev/null
            sudo swapon -p 10 /dev/zram0

            # Create Systemd Service for Persistence
            log_info "Creating ZRAM persistence service..."
            cat <<EOF | sudo tee /etc/systemd/system/zram-swap.service > /dev/null
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
            log_success "ZRAM Activated and Persisted."
        else
            log_warn "ZRAM module not available. Skipping."
        fi
    else
        log_success "ZRAM already active."
    fi

    # 1.3 Swap File State
    local total_mem_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local swap_total_kb=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
    local total_gb=$(( (total_mem_kb + swap_total_kb) / 1024 / 1024 ))

    if [[ $total_gb -lt $MIN_MEMORY_GB ]]; then
        log_warn "Memory low ($total_gb GB). Enforcing Swap..."
        if [[ ! -f "$SWAP_FILE" ]]; then
            sudo fallocate -l 4G "$SWAP_FILE"
            sudo chmod 600 "$SWAP_FILE"
            sudo mkswap "$SWAP_FILE"
            sudo swapon "$SWAP_FILE"
            echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab
            log_success "Created 4GB Swapfile."
        fi
    else
        log_success "Memory sufficient ($total_gb GB)."
    fi
}

# ==============================================================================
# MODULE 2: SECURITY STATE (Permissions, Secrets, Nginx)
# ==============================================================================
ensure_security_state() {
    log_step "PHASE 2 : Security State Enforcement"

    # 2.1 File Permissions (UID 1000)
    mkdir -p data logs config certbot/conf certbot/www
    # Only chown if needed to save I/O
    if [[ $(stat -c '%u' data) -ne 1000 ]]; then
        log_info "Fixing permissions..."
        sudo chown -R 1000:1000 data logs config
    fi
    log_success "Permissions OK."

    # 2.2 Secrets (.env)
    if [[ ! -f "$ENV_FILE" ]]; then
        cp ".env.pi4.example" "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        log_warn "Created .env from template."
    fi

    # 2.3 Dashboard Password Hashing (UX Helper)
    if grep -q "CHANGEZ_MOI" "$ENV_FILE" || grep -q "^DASHBOARD_PASSWORD=[^$]" "$ENV_FILE"; then
        log_warn "Unsecured or default password detected."
        echo -n "Enter new Dashboard Password: "
        read -rs PASS_INPUT
        echo ""

        if [[ -n "$PASS_INPUT" ]]; then
            log_info "Hashing password via Docker (Node.js)..."
            # Use ephemeral container to hash password securely without local node
            HASH_OUTPUT=$(docker run --rm \
                --platform linux/arm64 \
                -e PASSWORD="$PASS_INPUT" \
                -w /tmp \
                node:20-alpine \
                sh -c "npm install --no-save bcryptjs >/dev/null 2>&1 && node -e \"const bcrypt = require('bcryptjs'); console.log(bcrypt.hashSync(process.env.PASSWORD, 10));\"")

            if [[ "$HASH_OUTPUT" =~ ^\$2 ]]; then
                # Escape $ for Docker Compose ($ -> $$)
                SAFE_HASH=$(echo "$HASH_OUTPUT" | sed 's/\$/\$\$/g')
                # Escape / and & for sed
                ESCAPED_SAFE_HASH=$(echo "$SAFE_HASH" | sed 's/[\/&]/\\&/g')

                sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${ESCAPED_SAFE_HASH}|" "$ENV_FILE"
                log_success "Password hashed and saved to .env"
            else
                log_error "Failed to hash password. Please ensure Docker is running."
                exit 1
            fi
        fi
    fi

    # 2.4 Nginx Configuration (Hardened)
    if [[ -f "$NGINX_TEMPLATE" ]]; then
        # Generate Config
        local domain=$(grep "^DOMAIN=" "$ENV_FILE" | cut -d'=' -f2)
        if [[ -n "$domain" ]]; then
            export DOMAIN="$domain"
            envsubst '${DOMAIN}' < "$NGINX_TEMPLATE" > "$NGINX_CONFIG"
            log_success "Nginx Config Generated for $domain."
        fi
    fi
}

# ==============================================================================
# MODULE 3: MAINTENANCE STATE (Clean, Optimize)
# ==============================================================================
ensure_maintenance_state() {
    log_step "PHASE 3 : Maintenance Routines"

    # 3.1 Disk Hygiene (Docker Prune)
    local disk_usage=$(df -h . | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
    if [[ "$disk_usage" -gt 85 ]]; then
        log_warn "Disk usage high ($disk_usage%). Pruning Docker..."
        docker system prune -a -f --volumes
    else
        docker system prune -f # Dangling only
    fi

    # 3.2 Database Optimization (VACUUM)
    if [[ -f "data/linkedin.db" ]]; then
        log_info "Optimizing SQLite Database..."
        if command -v sqlite3 &> /dev/null; then
            sqlite3 data/linkedin.db "VACUUM;"
            sqlite3 data/linkedin.db "PRAGMA journal_mode=WAL;"
            log_success "Database VACUUM completed."
        fi
    fi
}

# ==============================================================================
# MODULE 4: APPLICATION STATE (Atomic Update)
# ==============================================================================
ensure_application_state() {
    log_step "PHASE 4 : Atomic Application Deployment"

    # 4.1 Pull Images (Retry Logic)
    log_info "Pulling images..."
    local services=("bot-worker" "api" "dashboard")
    for service in "${services[@]}"; do
        if ! docker compose -f "$COMPOSE_FILE" pull -q "$service"; then
             log_warn "Pull failed for $service. Using local cache if available."
        fi
    done

    # 4.2 Configuration Check
    if ! docker compose -f "$COMPOSE_FILE" config > /dev/null; then
        log_error "Docker Compose configuration is invalid. Aborting update."
        exit 1
    fi

    # 4.3 Atomic Restart
    log_info "Recreating containers..."
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

    # 4.4 Health Verification
    log_info "Verifying deployment health..."
    local retries=30
    local healthy=false

    # Wait for API
    for ((i=0; i<retries; i++)); do
        if curl -s -f http://localhost:8000/health > /dev/null; then
             log_success "API is Healthy."
             healthy=true
             break
        fi
        sleep 2
    done

    if [[ "$healthy" == "false" ]]; then
        log_error "Deployment Verification Failed: API Unreachable."
        # Rollback logic could go here (e.g., retag previous image)
        exit 1
    fi
}

# ==============================================================================
# MAIN EXECUTION FLOW
# ==============================================================================
main() {
    # Check Sudo
    if [[ $EUID -ne 0 ]]; then
       # Check if we can sudo without password or ask
       sudo -v || { echo "Sudo privileges required"; exit 1; }
    fi

    ensure_hardware_state
    ensure_security_state
    ensure_maintenance_state
    ensure_application_state

    log_step "DEPLOYMENT COMPLETE"
    log_info "Access your dashboard at https://$(grep "^DOMAIN=" "$ENV_FILE" | cut -d'=' -f2)"
}

main "$@"
