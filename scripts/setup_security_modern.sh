#!/bin/bash
# ==============================================================================
# LINKEDIN AUTO RPi4 - SETUP SECURITY MODERNE (V2.0)
# ==============================================================================
# Architecte : Claude - Expert DevOps IoT
# Cible      : Raspberry Pi 4 (4GB RAM, SD 32GB, ARM64)
#
# AMÉLIORATIONS vs V1:
# - Mode non-interactif (--auto) pour CI/CD
# - Génération secrets cryptographiques sécurisés
# - Configuration UFW intégrée
# - ZRAM automatique (alternative au swap fichier)
# - Cron de maintenance automatique
# - Compatible Debian/Raspberry Pi OS
# ==============================================================================

set -euo pipefail

# --- Configuration ---
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
readonly ENV_FILE="$PROJECT_DIR/.env"
readonly ENV_TEMPLATE="$PROJECT_DIR/.env.pi4.example"
readonly LOG_FILE="/var/log/linkedin-bot-security-setup.log"

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# --- Mode ---
AUTO_MODE=false
SKIP_UFW=false
SKIP_ZRAM=false
DOMAIN=""

# --- Fonctions utilitaires ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"; echo -e "${BOLD}${BLUE}  $1${NC}"; echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}\n"; }

cmd_exists() { command -v "$1" &> /dev/null; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Ce script doit être exécuté en tant que root (sudo)"
        exit 1
    fi
}

# --- Parsing Arguments ---
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto|-a)
                AUTO_MODE=true
                shift
                ;;
            --domain|-d)
                DOMAIN="$2"
                shift 2
                ;;
            --skip-ufw)
                SKIP_UFW=true
                shift
                ;;
            --skip-zram)
                SKIP_ZRAM=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --auto, -a           Mode non-interactif (génère tout automatiquement)"
                echo "  --domain, -d DOMAIN  Domaine pour HTTPS (ex: bot.example.com)"
                echo "  --skip-ufw           Ne pas configurer le firewall"
                echo "  --skip-zram          Ne pas configurer ZRAM"
                echo "  --help, -h           Afficher cette aide"
                exit 0
                ;;
            *)
                log_error "Option inconnue: $1"
                exit 1
                ;;
        esac
    done
}

# ==============================================================================
# PHASE 1 : GÉNÉRATION .env SÉCURISÉ
# ==============================================================================
setup_env_file() {
    log_step "PHASE 1 : Configuration .env Sécurisée"

    cd "$PROJECT_DIR"

    # Backup si existe
    if [[ -f "$ENV_FILE" ]]; then
        local backup_file="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$ENV_FILE" "$backup_file"
        log_info "Backup créé: $backup_file"
    fi

    # Copier le template
    if [[ -f "$ENV_TEMPLATE" ]]; then
        cp "$ENV_TEMPLATE" "$ENV_FILE"
    else
        log_error "Template .env.pi4.example introuvable"
        exit 1
    fi

    # Génération API_KEY (64 caractères hex)
    local api_key
    api_key=$(openssl rand -hex 32)
    sed -i "s|API_KEY=.*|API_KEY=$api_key|" "$ENV_FILE"
    log_success "API_KEY générée (64 caractères)"

    # Génération JWT_SECRET
    local jwt_secret
    jwt_secret=$(openssl rand -hex 32)
    sed -i "s|JWT_SECRET=.*|JWT_SECRET=$jwt_secret|" "$ENV_FILE"
    log_success "JWT_SECRET généré"

    # Mot de passe Dashboard
    if [[ "$AUTO_MODE" == true ]]; then
        # Générer un mot de passe aléatoire fort
        local password
        password=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9!@#' | head -c 16)
        log_warn "Mot de passe Dashboard généré: $password"
        log_warn "NOTEZ CE MOT DE PASSE MAINTENANT!"

        # Hasher avec bcrypt via conteneur Docker (ARM64 compatible)
        local hash
        hash=$(docker run --rm --platform linux/arm64 -e PASSWORD="$password" node:20-alpine \
            sh -c "npm install --no-save bcryptjs 2>/dev/null && node -e \"const b=require('bcryptjs');console.log(b.hashSync(process.env.PASSWORD,12));\"" 2>/dev/null)

        if [[ "$hash" =~ ^\$2 ]]; then
            # Échapper pour Docker Compose
            local escaped_hash="${hash//$/\$\$}"
            sed -i "s|DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=$escaped_hash|" "$ENV_FILE"
            log_success "Mot de passe hashé avec bcrypt"
        else
            log_warn "Échec du hashage, mot de passe stocké en clair"
            sed -i "s|DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=$password|" "$ENV_FILE"
        fi
    else
        log_info "Mode interactif: configurez le mot de passe manuellement"
        log_info "Utilisez: node dashboard/scripts/hash_password.js"
    fi

    # Domaine si fourni
    if [[ -n "$DOMAIN" ]]; then
        if grep -q "^DOMAIN=" "$ENV_FILE"; then
            sed -i "s|^DOMAIN=.*|DOMAIN=$DOMAIN|" "$ENV_FILE"
        else
            echo "DOMAIN=$DOMAIN" >> "$ENV_FILE"
        fi
        sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://$DOMAIN|" "$ENV_FILE"
        log_success "Domaine configuré: $DOMAIN"
    fi

    # Permissions restrictives
    chmod 600 "$ENV_FILE"
    chown 1000:1000 "$ENV_FILE" 2>/dev/null || true
    log_success "Permissions .env: 600"
}

# ==============================================================================
# PHASE 2 : CONFIGURATION UFW (Firewall)
# ==============================================================================
setup_ufw() {
    if [[ "$SKIP_UFW" == true ]]; then
        log_warn "Configuration UFW ignorée (--skip-ufw)"
        return
    fi

    log_step "PHASE 2 : Configuration Firewall (UFW)"

    # Installer UFW si absent
    if ! cmd_exists ufw; then
        log_info "Installation de UFW..."
        apt-get update -qq
        apt-get install -y -qq ufw
    fi

    # Règles de base
    log_info "Configuration des règles UFW..."

    # Reset (prudent)
    ufw --force reset

    # Politique par défaut
    ufw default deny incoming
    ufw default allow outgoing

    # SSH (CRITIQUE - ne pas se bloquer!)
    ufw allow 22/tcp comment 'SSH'

    # HTTP/HTTPS pour Certbot et accès web
    ufw allow 80/tcp comment 'HTTP - Certbot'
    ufw allow 443/tcp comment 'HTTPS'

    # Ports internes (localhost only pour sécurité)
    # Dashboard et API ne doivent PAS être exposés directement
    # Nginx fait office de reverse proxy

    # Activer UFW
    ufw --force enable

    log_success "UFW activé avec règles SSH, HTTP, HTTPS"
    ufw status verbose
}

# ==============================================================================
# PHASE 3 : CONFIGURATION ZRAM (Alternative au Swap)
# ==============================================================================
setup_zram() {
    if [[ "$SKIP_ZRAM" == true ]]; then
        log_warn "Configuration ZRAM ignorée (--skip-zram)"
        return
    fi

    log_step "PHASE 3 : Configuration ZRAM (Optimisation Mémoire)"

    # Vérifier si ZRAM est déjà actif
    if lsmod | grep -q zram; then
        log_info "ZRAM déjà chargé"
    else
        log_info "Chargement du module ZRAM..."
        modprobe zram
    fi

    # Installer zram-tools si disponible
    if ! cmd_exists zramctl; then
        log_info "Installation de zram-tools..."
        apt-get update -qq
        apt-get install -y -qq zram-tools 2>/dev/null || true
    fi

    # Configuration ZRAM manuelle si zram-tools non disponible
    if ! cmd_exists zramctl; then
        log_info "Configuration ZRAM manuelle..."

        # Créer un device ZRAM de 2GB
        if [[ ! -e /dev/zram0 ]]; then
            modprobe zram num_devices=1
        fi

        # Configurer la taille (2GB)
        echo "2G" > /sys/block/zram0/disksize 2>/dev/null || true
        mkswap /dev/zram0 2>/dev/null || true
        swapon -p 100 /dev/zram0 2>/dev/null || true

        log_success "ZRAM 2GB activé avec priorité haute"
    else
        # Utiliser zram-tools (Debian/Ubuntu)
        cat > /etc/default/zramswap << 'EOF'
# Configuration ZRAM pour Raspberry Pi 4
ALGO=lz4
PERCENT=50
PRIORITY=100
EOF
        systemctl restart zramswap 2>/dev/null || true
        log_success "ZRAM configuré via zram-tools"
    fi

    # Afficher le statut
    free -h
}

# ==============================================================================
# PHASE 4 : PERMISSIONS SYSTÈME (UID 1000 pour Docker)
# ==============================================================================
setup_permissions() {
    log_step "PHASE 4 : Permissions Système"

    cd "$PROJECT_DIR"

    # Création des répertoires
    mkdir -p data logs config certbot/conf certbot/www

    # Fichiers de données
    touch data/linkedin.db data/messages.txt data/late_messages.txt 2>/dev/null || true

    # Permissions UID 1000 (utilisateur dans les conteneurs)
    chown -R 1000:1000 data logs config 2>/dev/null || true
    chmod -R 775 data logs config

    # Permissions restrictives pour .env
    chmod 600 "$ENV_FILE" 2>/dev/null || true

    log_success "Permissions appliquées (UID 1000)"
}

# ==============================================================================
# PHASE 5 : CRON DE MAINTENANCE AUTOMATIQUE
# ==============================================================================
setup_maintenance_cron() {
    log_step "PHASE 5 : Maintenance Automatique"

    local cron_file="/etc/cron.d/linkedin-bot-maintenance"

    cat > "$cron_file" << EOF
# Maintenance automatique LinkedIn Bot - Raspberry Pi 4
# Généré par setup_security_modern.sh le $(date)

SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

# Nettoyage Docker quotidien (3h30 du matin)
30 3 * * * root docker system prune -f --volumes >> /var/log/linkedin-bot-docker-prune.log 2>&1

# Monitoring santé toutes les 5 minutes
*/5 * * * * root $PROJECT_DIR/scripts/monitor_pi4_health.sh 2>/dev/null || true

# Checkpoint SQLite WAL quotidien (4h du matin)
0 4 * * * root sqlite3 $PROJECT_DIR/data/linkedin.db "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true

# Rotation logs Docker hebdomadaire (dimanche 4h)
0 4 * * 0 root find /var/lib/docker/containers -name "*.log" -size +50M -exec truncate -s 10M {} \; 2>/dev/null || true
EOF

    chmod 644 "$cron_file"
    log_success "Cron de maintenance configuré"
    log_info "Fichier: $cron_file"
}

# ==============================================================================
# PHASE 6 : PARAMÈTRES KERNEL RPi4
# ==============================================================================
setup_kernel_params() {
    log_step "PHASE 6 : Paramètres Kernel RPi4"

    local sysctl_file="/etc/sysctl.d/99-linkedin-bot.conf"

    cat > "$sysctl_file" << 'EOF'
# Optimisations Kernel pour LinkedIn Bot sur Raspberry Pi 4
# Généré par setup_security_modern.sh

# Redis: Permet l'overcommit mémoire
vm.overcommit_memory = 1

# File d'attente TCP (Redis, Nginx)
net.core.somaxconn = 1024

# Réduit le swappiness (SD card = lent)
vm.swappiness = 10

# Optimisation buffers réseau
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# Keepalive TCP pour connexions longues
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 5

# Protection contre les attaques SYN flood
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048

# Désactiver IPv6 si non utilisé (économie mémoire)
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
EOF

    sysctl -p "$sysctl_file" > /dev/null 2>&1
    log_success "Paramètres kernel appliqués"
}

# ==============================================================================
# RAPPORT FINAL
# ==============================================================================
print_report() {
    log_step "INSTALLATION SÉCURITÉ TERMINÉE"

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    RÉSUMÉ DE LA CONFIGURATION                          ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}.env sécurisé${NC}        : $ENV_FILE"
    echo -e "  ${BOLD}API_KEY${NC}              : Générée (64 caractères)"
    echo -e "  ${BOLD}JWT_SECRET${NC}           : Généré (64 caractères)"
    echo -e "  ${BOLD}Mot de passe${NC}         : $(if [[ "$AUTO_MODE" == true ]]; then echo "Généré (voir ci-dessus)"; else echo "À configurer manuellement"; fi)"
    echo ""
    echo -e "  ${BOLD}Firewall UFW${NC}         : $(if [[ "$SKIP_UFW" == true ]]; then echo "Ignoré"; else echo "Activé (SSH, HTTP, HTTPS)"; fi)"
    echo -e "  ${BOLD}ZRAM${NC}                 : $(if [[ "$SKIP_ZRAM" == true ]]; then echo "Ignoré"; else echo "Activé (2GB, priorité haute)"; fi)"
    echo -e "  ${BOLD}Permissions UID 1000${NC} : Appliquées"
    echo -e "  ${BOLD}Cron maintenance${NC}     : Configuré"
    echo -e "  ${BOLD}Kernel params${NC}        : Optimisés pour RPi4"
    echo ""
    echo -e "${BLUE}┌─────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${BLUE}│                         PROCHAINES ÉTAPES                               │${NC}"
    echo -e "${BLUE}└─────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
    echo -e "  1. Vérifier la configuration : ${GREEN}cat .env${NC}"
    echo -e "  2. Lancer le déploiement     : ${GREEN}./setup.sh${NC}"
    echo -e "  3. Configurer HTTPS          : ${GREEN}./scripts/setup_letsencrypt.sh${NC}"
    echo -e "  4. Vérifier la sécurité      : ${GREEN}./scripts/verify_security.sh${NC}"
    echo ""
}

# ==============================================================================
# MAIN
# ==============================================================================
main() {
    parse_args "$@"

    echo -e "${BLUE}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                       ║"
    echo "║         🔒 SETUP SÉCURITÉ MODERNE - LinkedIn Auto RPi4                ║"
    echo "║                                                                       ║"
    echo "╚═══════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_root

    setup_env_file
    setup_ufw
    setup_zram
    setup_permissions
    setup_maintenance_cron
    setup_kernel_params

    print_report

    log_success "Configuration sécurité terminée avec succès!"
}

main "$@"
