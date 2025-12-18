#!/bin/bash
# ==============================================================================
# SETUP SSL CERTIFICATE AUTO-RENEWAL FOR LINKEDIN BOT
# ==============================================================================
# Configures automatic Let's Encrypt certificate renewal with systemd timer
# Requirements: Domain must point to your public IP for ACME validation
# Run: sudo ./scripts/setup_ssl_renewal.sh
# ==============================================================================

set -euo pipefail

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

# Logging functions
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN="${1:-}"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.pi4-standalone.yml"
ENV_FILE="${PROJECT_DIR}/.env"

echo ""
echo -e "${BOLD}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║     SETUP SSL CERTIFICATE AUTO-RENEWAL (Let's Encrypt)        ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running with sudo
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run with sudo"
    echo "Usage: sudo ./scripts/setup_ssl_renewal.sh [domain]"
    exit 1
fi

# ============================================================================
# PHASE 1: GET DOMAIN
# ============================================================================
if [[ -z "$DOMAIN" ]]; then
    log_info "Reading domain from .env file..."
    if [ -f "$ENV_FILE" ]; then
        DOMAIN=$(grep "^DOMAIN=" "$ENV_FILE" | cut -d'=' -f2 | tr -d ' ')
    fi

    if [[ -z "$DOMAIN" ]]; then
        log_error "Domain not found in .env file"
        echo ""
        echo "Please provide domain as argument:"
        echo "  sudo ./scripts/setup_ssl_renewal.sh example.com"
        echo ""
        echo "Or add DOMAIN variable to .env:"
        echo "  DOMAIN=example.com"
        exit 1
    fi
fi

log_success "Using domain: $DOMAIN"

# ============================================================================
# PHASE 2: INSTALL CERTBOT
# ============================================================================
log_info "Installing Certbot..."
if command -v certbot &> /dev/null; then
    log_success "Certbot already installed: $(certbot --version)"
else
    apt-get update -qq
    apt-get install -y -qq certbot python3-certbot-nginx certbot-dns-cloudflare 2>/dev/null || \
    apt-get install -y -qq certbot python3-certbot-nginx
    log_success "Certbot installed"
fi

# ============================================================================
# PHASE 3: CREATE SYSTEMD SERVICE FOR RENEWAL
# ============================================================================
log_info "Creating systemd service for certificate renewal..."

sudo tee /etc/systemd/system/certbot-renew.service > /dev/null <<EOF
[Unit]
Description=Certbot Renewal Service for LinkedIn Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet \
  --deploy-hook "docker compose -f ${COMPOSE_FILE} exec -T nginx nginx -s reload"
User=root
StandardOutput=journal
StandardError=journal
EOF

log_success "Systemd service created: /etc/systemd/system/certbot-renew.service"

# ============================================================================
# PHASE 4: CREATE SYSTEMD TIMER
# ============================================================================
log_info "Creating systemd timer for daily renewal..."

sudo tee /etc/systemd/system/certbot-renew.timer > /dev/null <<EOF
[Unit]
Description=Certbot Renewal Timer for LinkedIn Bot
Requires=certbot-renew.service

[Timer]
# Run daily at 3:00 AM (03:00)
OnCalendar=daily
OnCalendar=*-*-* 03:00:00
# Run immediately if timer was missed (e.g., system was off)
Persistent=true

[Install]
WantedBy=timers.target
EOF

log_success "Systemd timer created: /etc/systemd/system/certbot-renew.timer"

# ============================================================================
# PHASE 5: ENABLE AND START TIMER
# ============================================================================
log_info "Enabling systemd timer..."
sudo systemctl daemon-reload
sudo systemctl enable certbot-renew.timer
sudo systemctl start certbot-renew.timer

log_success "Timer enabled and started"

# ============================================================================
# PHASE 6: VERIFICATION
# ============================================================================
log_info "Verifying setup..."
echo ""

# Check timer status
echo -e "${BOLD}⏰ Timer Status:${NC}"
sudo systemctl status certbot-renew.timer || true

echo ""
echo -e "${BOLD}📅 Next Renewal Scheduled:${NC}"
sudo systemctl list-timers --all certbot-renew.timer || true

echo ""
echo -e "${BOLD}🔐 Current Certificate:${NC}"
if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    openssl x509 -in "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" -noout -dates || \
    echo "  Certificate file found but could not read dates"
    echo ""
    echo -e "${BOLD}📜 Certificate Issuer:${NC}"
    openssl x509 -in "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" -noout -issuer || true
else
    log_warn "Certificate not found yet at /etc/letsencrypt/live/${DOMAIN}/"
fi

# ============================================================================
# PHASE 7: TEST DRY RUN
# ============================================================================
echo ""
log_info "Running Certbot renewal dry-run (no actual renewal)..."
echo "This may take 1-2 minutes..."
echo ""

if sudo certbot renew --dry-run --quiet; then
    log_success "Dry-run completed successfully"
    echo "   Renewal will work when certificates are close to expiration"
else
    log_warn "Dry-run had issues - check configuration above"
fi

# ============================================================================
# PHASE 8: SUMMARY & INSTRUCTIONS
# ============================================================================
echo ""
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║             ✅ SSL RENEWAL CONFIGURED                          ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BOLD}📋 CONFIGURATION SUMMARY${NC}"
echo "  🌐 Domain: $DOMAIN"
echo "  ⏰ Schedule: Daily at 03:00 AM"
echo "  📜 Service: certbot-renew.service"
echo "  ⏱️  Timer: certbot-renew.timer"
echo "  📂 Certificates: /etc/letsencrypt/live/${DOMAIN}/"

echo ""
echo -e "${BOLD}✅ MANAGEMENT COMMANDS${NC}"
echo "  Check timer status:"
echo "    sudo systemctl status certbot-renew.timer"
echo ""
echo "  View timer schedule:"
echo "    sudo systemctl list-timers certbot-renew.timer"
echo ""
echo "  View service logs:"
echo "    sudo journalctl -u certbot-renew.service -n 50 -f"
echo ""
echo "  Manual renewal (if needed):"
echo "    sudo certbot renew --force-renewal"
echo ""
echo "  Disable timer (if needed):"
echo "    sudo systemctl disable certbot-renew.timer"
echo "    sudo systemctl stop certbot-renew.timer"

echo ""
echo -e "${BOLD}🚀 NEXT STEPS${NC}"
if [ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    echo "  1. Get initial certificate (required before auto-renewal works):"
    echo "     sudo certbot certonly --standalone -d ${DOMAIN}"
    echo ""
    echo "  2. Update Nginx configuration (if not auto-configured)"
    echo "     sudo nginx -t && sudo systemctl reload nginx"
    echo ""
fi

echo "  3. Wait for daily timer (03:00 AM) or manually test:"
echo "     sudo certbot renew --dry-run"
echo ""
echo "  4. Monitor renewal attempts:"
echo "     tail -f /var/log/letsencrypt/letsencrypt.log"
echo ""

echo -e "${BOLD}📖 DOCUMENTATION${NC}"
echo "  • SSL/HTTPS troubleshooting: docs/DISASTER_RECOVERY.md § 5"
echo "  • Backup strategy: docs/BACKUP_STRATEGY.md"
echo ""

log_success "SSL renewal setup complete!"
exit 0
