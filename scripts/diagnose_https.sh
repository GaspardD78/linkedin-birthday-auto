#!/bin/bash
# ==============================================================================
# LinkedIn Auto RPi4 - HTTPS Diagnostic Script
# ==============================================================================
# Diagnostic complet pour troubleshooter les problèmes de certificat SSL/HTTPS
# Usage: ./scripts/diagnose_https.sh
# ==============================================================================

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
CERT_ROOT="$PROJECT_ROOT/certbot"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# --- Couleurs ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# --- Counters ---
TESTS_PASSED=0
TESTS_FAILED=0

# --- Functions ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; ((TESTS_PASSED++)); }
log_warn()    { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error()   { echo -e "${RED}[✗]${NC} $1"; ((TESTS_FAILED++)); }

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║${NC}  $1"
    echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# --- START ---
clear
echo -e "${BOLD}${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         LINKEDIN AUTO - HTTPS DIAGNOSTIC SCRIPT                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
log_info "Diagnostic complet du système HTTPS..."
echo ""

# ==============================================================================
# 1. VÉRIFICATIONS DE BASE
# ==============================================================================
print_header "1️⃣  VÉRIFICATIONS DE BASE"

# 1.1 .env file
if [[ ! -f "$ENV_FILE" ]]; then
    log_error ".env file not found: $ENV_FILE"
    exit 1
else
    log_success ".env file exists"
fi

# 1.2 Extract DOMAIN
DOMAIN=$(grep "^DOMAIN=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "")
if [[ -z "$DOMAIN" ]]; then
    log_error "DOMAIN not configured in .env"
    exit 1
else
    log_success "DOMAIN configured: $DOMAIN"
fi

# 1.3 Extract EMAIL
EMAIL=$(grep "^LETSENCRYPT_EMAIL=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "")
if [[ -z "$EMAIL" ]]; then
    log_warn "LETSENCRYPT_EMAIL not configured"
else
    log_success "LETSENCRYPT_EMAIL: $EMAIL"
fi

# ==============================================================================
# 2. CERTIFICAT ACTUEL
# ==============================================================================
print_header "2️⃣  CERTIFICAT ACTUEL"

CERT_FILE="$CERT_ROOT/conf/live/$DOMAIN/fullchain.pem"
KEY_FILE="$CERT_ROOT/conf/live/$DOMAIN/privkey.pem"

if [[ ! -f "$CERT_FILE" ]]; then
    log_error "Certificate not found: $CERT_FILE"
else
    log_success "Certificate file exists"

    # 2.1 Certificate validity
    if openssl x509 -checkend 0 -noout -in "$CERT_FILE" >/dev/null 2>&1; then
        log_success "Certificate is NOT expired"
    else
        log_error "Certificate is EXPIRED"
    fi

    # 2.2 Self-signed check
    SUBJECT=$(openssl x509 -noout -subject -in "$CERT_FILE" 2>/dev/null || echo "")
    ISSUER=$(openssl x509 -noout -issuer -in "$CERT_FILE" 2>/dev/null || echo "")

    if [[ "$SUBJECT" == "$ISSUER" ]] && [[ -n "$SUBJECT" ]]; then
        log_error "Certificate is SELF-SIGNED (subject = issuer)"
        log_error "  Subject: $SUBJECT"
        log_error "  Issuer:  $ISSUER"
    else
        log_success "Certificate is NOT self-signed (issued by CA)"
        log_info "  Subject: ${SUBJECT#*=}"
        log_info "  Issuer:  ${ISSUER#*=}"
    fi

    # 2.3 Certificate expiration date
    EXPIRY=$(openssl x509 -noout -enddate -in "$CERT_FILE" 2>/dev/null | cut -d= -f2)
    log_info "  Expiration: $EXPIRY"

    # 2.4 Certificate details
    echo ""
    log_info "Certificate Details:"
    openssl x509 -noout -text -in "$CERT_FILE" 2>/dev/null | grep -E "Subject:|Issuer:|Not Before|Not After" | sed 's/^/    /'
fi

if [[ ! -f "$KEY_FILE" ]]; then
    log_error "Private key not found: $KEY_FILE"
else
    log_success "Private key exists"

    # Check key permissions
    PERMS=$(stat -c "%a" "$KEY_FILE" 2>/dev/null || echo "unknown")
    if [[ "$PERMS" == "600" ]]; then
        log_success "Private key permissions correct (600)"
    else
        log_warn "Private key permissions: $PERMS (should be 600)"
    fi
fi

# ==============================================================================
# 3. VÉRIFICATIONS RÉSEAU
# ==============================================================================
print_header "3️⃣  VÉRIFICATIONS RÉSEAU"

# 3.1 DNS resolution
log_info "Testing DNS resolution for $DOMAIN..."
if command -v nslookup >/dev/null 2>&1; then
    if RESOLVED_IP=$(nslookup "$DOMAIN" 8.8.8.8 2>/dev/null | grep -A 1 "Name:" | tail -1 | awk '{print $NF}'); then
        if [[ -n "$RESOLVED_IP" ]] && [[ "$RESOLVED_IP" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            log_success "DNS resolution works: $DOMAIN → $RESOLVED_IP"
        else
            log_error "DNS resolution failed or invalid IP"
        fi
    else
        log_error "DNS resolution failed"
    fi
else
    log_warn "nslookup not available, skipping DNS check"
fi

# 3.2 Port 80 (HTTP for ACME)
log_info "Testing port 80 (HTTP for Let's Encrypt ACME)..."
if timeout 3 bash -c "echo > /dev/tcp/127.0.0.1/80" 2>/dev/null; then
    log_success "Port 80 is accessible locally"
else
    log_warn "Port 80 not accessible locally (may be blocked by Docker)"
fi

# 3.3 Port 443 (HTTPS)
log_info "Testing port 443 (HTTPS)..."
if timeout 3 bash -c "echo > /dev/tcp/127.0.0.1/443" 2>/dev/null; then
    log_success "Port 443 is accessible locally"
else
    log_warn "Port 443 not accessible locally"
fi

# 3.4 SSL connection test
log_info "Testing HTTPS connection..."
if command -v openssl >/dev/null 2>&1; then
    if timeout 5 openssl s_client -connect 127.0.0.1:443 -servername "$DOMAIN" </dev/null >/dev/null 2>&1; then
        log_success "HTTPS connection successful"
    else
        log_warn "HTTPS connection failed"
    fi
else
    log_warn "openssl not available"
fi

# ==============================================================================
# 4. DOCKER & NGINX
# ==============================================================================
print_header "4️⃣  DOCKER & NGINX STATUS"

# 4.1 Docker status
if command -v docker >/dev/null 2>&1; then
    if docker ps >/dev/null 2>&1; then
        log_success "Docker is accessible"
    else
        log_error "Docker is not accessible (permission denied?)"
    fi
else
    log_error "Docker not installed"
fi

# 4.2 Docker compose
DOCKER_CMD="docker compose"
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    DOCKER_CMD="docker-compose"
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "Docker compose not available"
    fi
fi

# 4.3 nginx container
if $DOCKER_CMD -f "$COMPOSE_FILE" ps nginx >/dev/null 2>&1; then
    NGINX_STATUS=$($DOCKER_CMD -f "$COMPOSE_FILE" ps --status running --quiet nginx 2>/dev/null | wc -l)
    if [[ $NGINX_STATUS -gt 0 ]]; then
        log_success "Nginx container is running"
    else
        log_error "Nginx container is NOT running"
    fi
else
    log_warn "Could not check Nginx status (docker compose issue?)"
fi

# 4.4 Nginx config
log_info "Testing Nginx configuration..."
if $DOCKER_CMD -f "$COMPOSE_FILE" exec -T nginx nginx -t >/dev/null 2>&1; then
    log_success "Nginx configuration is valid"
else
    log_error "Nginx configuration has errors"
    $DOCKER_CMD -f "$COMPOSE_FILE" exec -T nginx nginx -t 2>&1 | sed 's/^/    /'
fi

# ==============================================================================
# 5. CERTBOT LOGS
# ==============================================================================
print_header "5️⃣  CERTBOT LOGS ANALYSIS"

CERTBOT_LOG="$CERT_ROOT/logs/letsencrypt.log"
if [[ -f "$CERTBOT_LOG" ]]; then
    log_success "Certbot log file exists"

    # Check for recent errors
    if grep -i "error" "$CERTBOT_LOG" | tail -5 >/dev/null 2>&1; then
        log_warn "Recent errors found in Certbot log:"
        echo ""
        grep -i "error" "$CERTBOT_LOG" | tail -5 | sed 's/^/    /'
        echo ""
    else
        log_success "No recent errors in Certbot log"
    fi

    # Show last renewal attempt
    if grep -i "renewal" "$CERTBOT_LOG" >/dev/null 2>&1; then
        log_info "Last renewal attempt:"
        grep -i "renewal" "$CERTBOT_LOG" | tail -1 | sed 's/^/    /'
    fi
else
    log_warn "Certbot log file not found: $CERTBOT_LOG"
fi

# ==============================================================================
# 6. SUMMARY
# ==============================================================================
print_header "📊 SUMMARY"

echo ""
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}✓ All checks passed!${NC}"
    echo -e "Your HTTPS setup appears to be working correctly."
    exit 0
else
    echo -e "${RED}${BOLD}✗ Some checks failed!${NC}"
    echo ""
    echo "Recommended actions:"
    echo "  1. Check the errors above"
    echo "  2. Review certbot logs: cat $CERTBOT_LOG"
    echo "  3. Verify DNS: nslookup $DOMAIN 8.8.8.8"
    echo "  4. Check port 80/443 accessibility"
    echo "  5. Retry: ./scripts/setup_letsencrypt.sh --force"
    echo ""
    exit 1
fi
