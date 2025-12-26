#!/bin/bash
# ==============================================================================
# LinkedIn Auto - Fix HTTPS Certificates and Configuration
# ==============================================================================
# This script diagnoses and fixes HTTPS certificate issues:
# 1. Checks current certificate status
# 2. Attempts to obtain proper Let's Encrypt certificates
# 3. Falls back to self-signed if Let's Encrypt fails
# 4. Generates proper HTTPS Nginx configuration
# 5. Restarts services and validates
# ==============================================================================

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
NGINX_TEMPLATE="$PROJECT_ROOT/deployment/nginx/linkedin-bot-https.conf.template"
NGINX_CONF="$PROJECT_ROOT/deployment/nginx/linkedin-bot.conf"
CERT_DIR="$PROJECT_ROOT/certbot/conf/live"

# --- Colors ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Logging Functions ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Load Environment ---
if [[ ! -f "$ENV_FILE" ]]; then
    log_error ".env file not found at $ENV_FILE"
    exit 1
fi

source "$ENV_FILE"

if [[ -z "${DOMAIN:-}" ]]; then
    log_error "DOMAIN not set in .env file"
    exit 1
fi

log_info "Domain: $DOMAIN"

# ==============================================================================
# Diagnostic Functions
# ==============================================================================

check_current_certificate() {
    log_info "Checking current certificate status..."

    local cert_path=""

    # Check for domain-specific cert
    if [[ -f "$CERT_DIR/$DOMAIN/fullchain.pem" ]]; then
        cert_path="$CERT_DIR/$DOMAIN/fullchain.pem"
    elif [[ -f "$CERT_DIR/localhost/fullchain.pem" ]]; then
        cert_path="$CERT_DIR/localhost/fullchain.pem"
        log_warn "Only localhost certificate found (self-signed)"
    else
        log_warn "No certificates found"
        return 1
    fi

    # Check certificate details
    local issuer=$(openssl x509 -in "$cert_path" -noout -issuer 2>/dev/null | sed 's/.*CN = //')
    local subject=$(openssl x509 -in "$cert_path" -noout -subject 2>/dev/null | sed 's/.*CN = //')
    local expiry=$(openssl x509 -in "$cert_path" -noout -enddate 2>/dev/null | sed 's/notAfter=//')

    log_info "Certificate found:"
    log_info "  Subject: $subject"
    log_info "  Issuer: $issuer"
    log_info "  Expiry: $expiry"

    # Check if it's self-signed
    if [[ "$issuer" == "$subject" ]] || [[ "$issuer" == *"localhost"* ]]; then
        log_warn "Certificate is SELF-SIGNED (not from Let's Encrypt)"
        return 2
    fi

    # Check if it's from Let's Encrypt
    if [[ "$issuer" == *"Let's Encrypt"* ]] || [[ "$issuer" == *"R3"* ]] || [[ "$issuer" == *"R10"* ]]; then
        log_success "Certificate is from Let's Encrypt"

        # Check expiry
        local expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || echo 0)
        local now_epoch=$(date +%s)
        local days_left=$(( ($expiry_epoch - $now_epoch) / 86400 ))

        if [[ $days_left -lt 30 ]]; then
            log_warn "Certificate expires in $days_left days (renewal recommended)"
            return 3
        else
            log_success "Certificate valid for $days_left days"
            return 0
        fi
    fi

    log_warn "Certificate issuer unknown: $issuer"
    return 4
}

check_domain_accessibility() {
    log_info "Checking if domain is accessible from internet..."

    # Try to connect to domain on port 80
    if timeout 10 curl -s -I "http://$DOMAIN" > /dev/null 2>&1; then
        log_success "Domain is accessible on port 80"
        return 0
    else
        log_warn "Domain is NOT accessible on port 80 (required for Let's Encrypt)"
        log_warn "Check your firewall and port forwarding settings"
        return 1
    fi
}

# ==============================================================================
# Certificate Management
# ==============================================================================

obtain_letsencrypt_certificate() {
    log_info "Attempting to obtain Let's Encrypt certificate..."

    # Check domain accessibility first
    if ! check_domain_accessibility; then
        log_error "Cannot obtain Let's Encrypt certificate - domain not accessible"
        return 1
    fi

    # Run the Let's Encrypt setup script
    if [[ -x "$SCRIPT_DIR/setup_letsencrypt.sh" ]]; then
        log_info "Running setup_letsencrypt.sh..."
        if "$SCRIPT_DIR/setup_letsencrypt.sh" --force; then
            log_success "Let's Encrypt certificate obtained successfully"
            return 0
        else
            log_error "setup_letsencrypt.sh failed"
            return 1
        fi
    else
        log_error "setup_letsencrypt.sh not found or not executable"
        return 1
    fi
}

create_self_signed_certificate() {
    log_info "Creating self-signed certificate for $DOMAIN..."

    local cert_dir="$CERT_DIR/$DOMAIN"
    mkdir -p "$cert_dir"

    # Generate self-signed certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$cert_dir/privkey.pem" \
        -out "$cert_dir/fullchain.pem" \
        -subj "/C=FR/ST=IDF/L=Paris/O=Development/CN=$DOMAIN" \
        2>/dev/null

    chmod 600 "$cert_dir/privkey.pem"
    chmod 644 "$cert_dir/fullchain.pem"

    log_warn "Self-signed certificate created (browsers will show security warning)"
    log_info "  Certificate: $cert_dir/fullchain.pem"
    log_info "  Key: $cert_dir/privkey.pem"
}

# ==============================================================================
# Nginx Configuration
# ==============================================================================

generate_https_config() {
    log_info "Generating HTTPS Nginx configuration..."

    if [[ ! -f "$NGINX_TEMPLATE" ]]; then
        log_error "Nginx template not found: $NGINX_TEMPLATE"
        return 1
    fi

    # Replace ${DOMAIN} with actual domain
    envsubst '${DOMAIN}' < "$NGINX_TEMPLATE" > "$NGINX_CONF"

    log_success "Nginx configuration generated: $NGINX_CONF"
}

validate_nginx_config() {
    log_info "Validating Nginx configuration..."

    if docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -t 2>&1 | grep -q "successful"; then
        log_success "Nginx configuration is valid"
        return 0
    else
        log_error "Nginx configuration is invalid"
        docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -t 2>&1 || true
        return 1
    fi
}

reload_nginx() {
    log_info "Reloading Nginx..."

    if docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload; then
        log_success "Nginx reloaded successfully"
        return 0
    else
        log_error "Failed to reload Nginx"
        return 1
    fi
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    echo "=============================================================================="
    echo "   HTTPS Certificate Fix Script"
    echo "=============================================================================="
    echo ""

    # Step 1: Check current certificate status
    log_info "Step 1: Diagnosing current certificate status..."
    check_current_certificate
    local cert_status=$?
    echo ""

    # Step 2: Decide action based on status
    case $cert_status in
        0)
            log_success "Valid Let's Encrypt certificate found - no action needed"
            ;;
        2|4)
            log_warn "Self-signed or unknown certificate detected"
            log_info "Step 2: Attempting to obtain Let's Encrypt certificate..."

            if obtain_letsencrypt_certificate; then
                log_success "Let's Encrypt certificate obtained"
            else
                log_warn "Failed to obtain Let's Encrypt certificate"
                log_info "Creating/keeping self-signed certificate..."

                if [[ ! -f "$CERT_DIR/$DOMAIN/fullchain.pem" ]]; then
                    create_self_signed_certificate
                fi
            fi
            ;;
        3)
            log_warn "Certificate expiring soon"
            log_info "Step 2: Renewing Let's Encrypt certificate..."
            obtain_letsencrypt_certificate || log_warn "Renewal failed"
            ;;
        *)
            log_warn "No certificate found"
            log_info "Step 2: Attempting to obtain Let's Encrypt certificate..."

            if obtain_letsencrypt_certificate; then
                log_success "Let's Encrypt certificate obtained"
            else
                log_warn "Failed to obtain Let's Encrypt certificate"
                log_info "Creating self-signed certificate..."
                create_self_signed_certificate
            fi
            ;;
    esac
    echo ""

    # Step 3: Generate HTTPS configuration
    log_info "Step 3: Generating HTTPS Nginx configuration..."
    if generate_https_config; then
        log_success "Configuration generated successfully"
    else
        log_error "Failed to generate configuration"
        exit 1
    fi
    echo ""

    # Step 4: Validate and reload
    log_info "Step 4: Validating and reloading Nginx..."
    if validate_nginx_config; then
        if reload_nginx; then
            log_success "Nginx reloaded with new configuration"
        else
            log_warn "Failed to reload Nginx - restart may be needed"
        fi
    else
        log_error "Invalid Nginx configuration - not reloading"
        exit 1
    fi
    echo ""

    # Step 5: Final validation
    log_info "Step 5: Final validation..."
    check_current_certificate
    echo ""

    echo "=============================================================================="
    log_success "HTTPS certificate fix completed!"
    echo "=============================================================================="
    echo ""
    echo "Next steps:"
    echo "  1. Test HTTPS access: https://$DOMAIN"
    echo "  2. Check certificate in browser (should show valid or self-signed)"
    echo "  3. If self-signed, ensure domain is accessible and re-run with Let's Encrypt"
    echo ""
    echo "To obtain Let's Encrypt certificate (if not already done):"
    echo "  - Ensure domain $DOMAIN points to this server's public IP"
    echo "  - Ensure ports 80 and 443 are open in firewall"
    echo "  - Run: ./scripts/setup_letsencrypt.sh --force"
    echo ""
}

main "$@"
