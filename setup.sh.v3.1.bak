#!/bin/bash
# ==============================================================================
# LINKEDIN AUTO RPi4 - SETUP SCRIPT (V3.1 - PRODUCTION READY)
# ==============================================================================
# Architecte : Jules - Expert DevOps
# Cible      : Raspberry Pi 4 (4GB RAM, SD 32GB, ARM64)
# ==============================================================================

set -euo pipefail

# --- Déterminer le répertoire de base du script (utiliser avant tout cd) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Couleurs ---
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# --- Configuration ---
DOMAIN="gaspardanoukolivier.freeboxos.fr"  # Valeur par défaut
readonly COMPOSE_FILE="docker-compose.pi4-standalone.yml"
readonly ENV_FILE=".env"
readonly ENV_TEMPLATE=".env.pi4.example"
readonly NGINX_TEMPLATE="deployment/nginx/linkedin-bot.conf.template"
readonly NGINX_CONFIG="deployment/nginx/linkedin-bot.conf"
readonly MIN_MEMORY_GB=6      # RAM + SWAP minimum requis
readonly SWAP_FILE="/swapfile"
readonly DISK_THRESHOLD_PERCENT=20
readonly HEALTH_TIMEOUT=300   # 5 minutes
readonly HEALTH_INTERVAL=10

# --- Logging ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"; echo -e "${BOLD}${BLUE}  $1${NC}"; echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}\n"; sleep 2; }

# --- Gestion d'erreurs ---
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo ""
        log_error "Le script a échoué (Code $exit_code)."
        log_info "Derniers logs pour diagnostic :"
        docker compose -f "$COMPOSE_FILE" logs --tail=20 2>/dev/null || true
    fi
}
trap cleanup EXIT

# --- Fonctions Utilitaires ---

cmd_exists() { command -v "$1" &> /dev/null; }

check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        log_warn "Privilèges sudo requis."
        sudo true || { log_error "Sudo refusé."; exit 1; }
    fi
}

# --- Fonctions d'Interaction Utilisateur ---

# Pose une question yes/no avec timeout
# Usage: prompt_yes_no "Voulez-vous continuer ?" [default]
# default: "y" pour yes par défaut, "n" pour no par défaut, ou "" pour pas de défaut
prompt_yes_no() {
    local question="$1"
    local default="${2:-}"
    local timeout=30
    local reply

    if [[ "$default" == "y" ]]; then
        echo -ne "${YELLOW}${question} [Y/n] : ${NC}"
    elif [[ "$default" == "n" ]]; then
        echo -ne "${YELLOW}${question} [y/N] : ${NC}"
    else
        echo -ne "${YELLOW}${question} [y/n] : ${NC}"
    fi

    read -r -t "$timeout" reply || reply="$default"

    if [[ -z "$reply" && -z "$default" ]]; then
        log_error "Pas de réponse (timeout ${timeout}s)"
        return 1
    fi

    case "$reply" in
        [Yy]|"") [[ "$default" != "n" ]] && return 0 || return 1 ;;
        [Nn]|"") [[ "$default" == "n" ]] && return 0 || return 1 ;;
        *) log_error "Réponse invalide. Veuillez répondre par 'y' ou 'n'"; return 2 ;;
    esac
}

# Affiche un menu numéroté et attend un choix
# Usage: prompt_menu "Titre" "Option 1" "Option 2" "Option 3"
# Returns: l'index de l'option choisie (1-based)
prompt_menu() {
    local title="$1"
    shift
    local options=("$@")
    local choice
    local timeout=30

    echo -e "\n${BOLD}${BLUE}${title}${NC}\n"

    local i=1
    for option in "${options[@]}"; do
        echo "  ${BOLD}${i})${NC} ${option}"
        i=$((i + 1))
    done

    echo -ne "\n${YELLOW}Votre choix [1-$#] (timeout ${timeout}s) : ${NC}"

    read -r -t "$timeout" choice || { log_error "Timeout"; return 1; }

    if ! [[ "$choice" =~ ^[0-9]+$ ]] || [[ "$choice" -lt 1 ]] || [[ "$choice" -gt $# ]]; then
        log_error "Choix invalide. Veuillez entrer un nombre entre 1 et $#"
        return 2
    fi

    echo "$choice"
    return 0
}

# Menu spécifique pour la configuration du mot de passe dashboard
# Returns: "new" (nouveau), "keep" (garder), "cancel" (annuler)
prompt_password_action() {
    local has_existing="$1"  # true ou false
    local choice

    if [[ "$has_existing" == "true" ]]; then
        choice=$(prompt_menu \
            "Configuration du Mot de Passe Dashboard" \
            "Définir/Changer le mot de passe maintenant" \
            "Garder le mot de passe existant" \
            "Annuler la configuration pour l'instant")
    else
        choice=$(prompt_menu \
            "Configuration du Mot de Passe Dashboard" \
            "Définir un nouveau mot de passe" \
            "Annuler la configuration pour l'instant")
    fi

    case "$choice" in
        1) echo "new" ;;
        2) [[ "$has_existing" == "true" ]] && echo "keep" || echo "cancel" ;;
        3) echo "cancel" ;;
    esac
}

configure_docker_ipv4() {
    local daemon_json="/etc/docker/daemon.json"
    local needs_restart=false
    local target_config='{
  "ipv6": false,
  "ip6tables": false,
  "dns": ["1.1.1.1", "8.8.8.8", "8.8.4.4"],
  "dns-opts": ["timeout:2", "attempts:3"],
  "registry-mirrors": []
}'

    if [[ -f "$daemon_json" ]]; then
        if grep -q '"ip6tables": false' "$daemon_json" 2>/dev/null && \
           grep -q '"dns"' "$daemon_json" 2>/dev/null; then
            log_info "Docker déjà configuré (IPv4 + DNS fiables)."
            return 0
        fi
    fi

    log_info "Configuration de Docker (IPv4 + DNS fiables Cloudflare/Google)..."
    check_sudo

    if [[ ! -f "$daemon_json" ]]; then
        echo "$target_config" | sudo tee "$daemon_json" > /dev/null
        needs_restart=true
    else
        local temp_file=$(mktemp)
        if command -v jq &> /dev/null; then
            sudo jq '. + {"ipv6": false, "ip6tables": false, "dns": ["1.1.1.1", "8.8.8.8", "8.8.4.4"], "dns-opts": ["timeout:2", "attempts:3"]}' "$daemon_json" > "$temp_file"
            sudo mv "$temp_file" "$daemon_json"
        else
            log_warn "jq non disponible, remplacement complet de daemon.json"
            echo "$target_config" | sudo tee "$daemon_json" > /dev/null
        fi
        needs_restart=true
    fi

    if [[ "$needs_restart" == "true" ]]; then
        log_info "Redémarrage du daemon Docker..."
        sudo systemctl restart docker
        sleep 3
        log_success "Docker redémarré avec IPv4 + DNS fiables."
    fi
}

configure_kernel_params() {
    local sysctl_file="/etc/sysctl.d/99-rpi4-docker.conf"
    log_info "Configuration des paramètres kernel pour RPi4..."

    if [[ -f "$sysctl_file" ]]; then
         if grep -q "vm.overcommit_memory" "$sysctl_file" && \
            grep -q "net.core.somaxconn" "$sysctl_file" && \
            grep -q "vm.swappiness" "$sysctl_file"; then
             log_info "Paramètres kernel déjà configurés."
             return 0
         fi
    fi

    check_sudo
    sudo tee "$sysctl_file" > /dev/null <<'EOF'
# Configuration kernel optimisée pour LinkedIn Bot sur Raspberry Pi 4
vm.overcommit_memory = 1
net.core.somaxconn = 1024
vm.swappiness = 10
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 5
EOF
    sudo sysctl -p "$sysctl_file" > /dev/null 2>&1
    log_success "Paramètres kernel configurés (overcommit_memory=1, swappiness=10)."
}

configure_zram() {
    log_info "Configuration ZRAM (Swap compressé en RAM)..."
    if lsblk | grep -q "zram0"; then
        log_info "ZRAM déjà configuré et actif"
        return 0
    fi
    if ! modprobe zram 2>/dev/null; then
        log_warn "Module ZRAM non disponible. Skip."
        return 0
    fi

    check_sudo
    local ZRAM_SIZE="1G"
    sudo modprobe zram num_devices=1
    echo lz4 | sudo tee /sys/block/zram0/comp_algorithm > /dev/null
    echo "$ZRAM_SIZE" | sudo tee /sys/block/zram0/disksize > /dev/null
    sudo mkswap /dev/zram0
    sudo swapon -p 10 /dev/zram0

    if ! grep -q "zram" /etc/modules 2>/dev/null; then
        echo "zram" | sudo tee -a /etc/modules > /dev/null
    fi

    # [FIX-PERSISTENCE] Restauration du service systemd pour persistance ZRAM au reboot
    local ZRAM_SERVICE="/etc/systemd/system/zram-swap.service"
    if [[ ! -f "$ZRAM_SERVICE" ]]; then
        sudo tee "$ZRAM_SERVICE" > /dev/null <<'EOF'
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
    fi

    log_success "ZRAM activé (1GB) et rendu persistant."
}

docker_pull_with_retry() {
    local compose_file="$1"
    local max_retries=4
    local base_delay=2
    local services
    local error_log="/tmp/setup_docker_services.err"

    # ============ VÉRIFICATION PRÉ-PULL ============
    log_info "Vérification du fichier docker-compose..."

    # 1️⃣ Vérifier que le fichier existe
    if [[ ! -f "$compose_file" ]]; then
        log_error "Fichier docker-compose introuvable: $(cd . && pwd)/$compose_file"
        log_info "Chemin absolu attendu: $SCRIPT_DIR/$compose_file"
        return 1
    fi
    log_info "✓ Fichier trouvé: $compose_file"

    # 2️⃣ Vérifier la validité YAML avec docker compose config
    log_info "Validation YAML du fichier docker-compose..."
    if ! docker compose -f "$compose_file" config > /dev/null 2>"$error_log"; then
        log_error "Le fichier $compose_file est invalide (YAML malformé)"
        log_error "Détails de l'erreur :"
        cat "$error_log" | sed 's/^/  /'
        rm -f "$error_log"
        return 1
    fi
    log_info "✓ YAML valide"

    # 3️⃣ Récupérer la liste des services (SANS supprimer les erreurs)
    log_info "Lecture de la liste des services..."
    services=$(docker compose -f "$compose_file" config --services 2>"$error_log")
    local docker_exit_code=$?

    # Vérifier le code de retour ET que la liste n'est pas vide
    if [[ $docker_exit_code -ne 0 ]] || [[ -z "$services" ]]; then
        log_error "Impossible de lire la liste des services depuis $compose_file"
        if [[ -s "$error_log" ]]; then
            log_error "Message d'erreur Docker :"
            cat "$error_log" | sed 's/^/  /'
        fi
        log_info "Conseil : Vérifier que docker compose est disponible et fonctionnel"
        log_info "  $ docker compose -f $compose_file config --services"
        rm -f "$error_log"
        return 1
    fi
    rm -f "$error_log"

    # ============ PULL DES IMAGES ============
    log_info "Téléchargement des images Docker..."

    local total_services
    total_services=$(echo "$services" | wc -l)
    local current=0

    while IFS= read -r service; do
        # Ignorer les lignes vides
        [[ -z "$service" ]] && continue

        current=$((current + 1))
        echo -n "[${current}/${total_services}] Pull de l'image pour '${service}' "
        local retry_count=0
        local success=false

        while [[ $retry_count -lt $max_retries ]]; do
            if docker compose -f "$compose_file" pull --quiet "$service" 2>"$error_log"; then
                echo -e "${GREEN}✓${NC}"
                success=true
                rm -f "$error_log"
                break
            else
                retry_count=$((retry_count + 1))
                if [[ $retry_count -lt $max_retries ]]; then
                    local delay=$((base_delay ** retry_count))
                    echo -n "${YELLOW}✗${NC} (retry dans ${delay}s) "
                    sleep "$delay"
                else
                    echo -e "${RED}✗ ÉCHEC${NC}"
                fi
            fi
        done

        if [[ "$success" != "true" ]]; then
            log_error "Échec du pull pour le service '$service'."
            if [[ -s "$error_log" ]]; then
                log_error "Détails :"
                cat "$error_log" | sed 's/^/  /'
            fi
            rm -f "$error_log"
            return 1
        fi
    done <<< "$services"

    log_success "Toutes les images ont été téléchargées avec succès."
    return 0
}

get_total_memory_gb() {
    local ram_kb swap_kb total_kb
    ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    swap_kb=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
    total_kb=$((ram_kb + swap_kb))
    echo $((total_kb / 1024 / 1024))
}

# ==============================================================================
# NOUVELLES FONCTIONS - HTTPS, GOOGLE DRIVE, SÉCURITÉ
# ==============================================================================

configure_https_menu() {
    local choice
    log_step "Configuration HTTPS / SSL / TLS"

    choice=$(prompt_menu \
        "Quel scénario HTTPS s'applique à vous ?" \
        "🏠 LAN uniquement (HTTP, pas HTTPS nécessaire)" \
        "🌐 Domaine avec Let's Encrypt (production recommandée)" \
        "🔒 Certificats existants (import)" \
        "⚙️  Configuration manuelle (gérerez après setup)")

    case "$choice" in
        1)
            log_warn "⚠️  HTTPS désactivé (LAN uniquement)"
            log_info "  Accès : http://$(hostname -I | awk '{print $1}' 2>/dev/null || echo 'localhost'):3000"
            log_warn "  ⚠️  POUR PRODUCTION SUR INTERNET : Utilisez Let's Encrypt (option 2)"
            HTTPS_MODE="lan"
            ;;
        2)
            log_info "Let's Encrypt activé. Utilisez setup_letsencrypt.sh après le setup initial."
            log_info "  ./scripts/setup_letsencrypt.sh"
            HTTPS_MODE="letsencrypt"
            ;;
        3)
            log_step "Import de Certificats Existants"
            read -p "Chemin fullchain.pem : " CERT_FILE
            read -p "Chemin privkey.pem : " KEY_FILE

            if [[ ! -f "$CERT_FILE" ]] || [[ ! -f "$KEY_FILE" ]]; then
                log_error "Fichiers certificats non trouvés."
                return 1
            fi

            mkdir -p "certbot/conf/live/${DOMAIN}"
            cp "$CERT_FILE" "certbot/conf/live/${DOMAIN}/fullchain.pem"
            cp "$KEY_FILE" "certbot/conf/live/${DOMAIN}/privkey.pem"
            chmod 600 "certbot/conf/live/${DOMAIN}/privkey.pem"
            chmod 644 "certbot/conf/live/${DOMAIN}/fullchain.pem"

            log_success "Certificats importés."
            HTTPS_MODE="existing"
            ;;
        4)
            log_warn "Configuration manuelle HTTPS sélectionnée."
            log_info "Vous êtes responsable de placer les certificats dans : certbot/conf/live/${DOMAIN}/"
            HTTPS_MODE="manual"
            ;;
    esac

    return 0
}

configure_google_drive_menu() {
    local choice
    log_step "PHASE 5.1 : Configuration Sauvegardes Google Drive"

    choice=$(prompt_menu \
        "Activation des Sauvegardes Google Drive" \
        "Oui, activer avec chiffrement (recommandé)" \
        "Oui, activer sans chiffrement" \
        "Non, configurer plus tard")

    if [[ "$choice" == "1" ]] || [[ "$choice" == "2" ]]; then

        log_info "Installation/vérification rclone..."

        if ! cmd_exists rclone; then
            log_warn "rclone non installé. Installation..."
            check_sudo
            sudo apt-get update -qq && sudo apt-get install -y -qq rclone
        fi

        log_success "✓ rclone disponible"

        # Vérifier remote existant
        EXISTING_REMOTE=$(rclone listremotes 2>/dev/null | head -1 | sed 's/://')

        if [[ -z "$EXISTING_REMOTE" ]]; then
            log_warn "Aucun remote rclone configuré."
            log_info "Lancement configuration interactive Google Drive..."

            if prompt_yes_no "Continuer la configuration rclone ?" "y"; then
                rclone config
                EXISTING_REMOTE=$(rclone listremotes 2>/dev/null | head -1 | sed 's/://')

                if [[ -z "$EXISTING_REMOTE" ]]; then
                    log_error "Configuration rclone échouée ou annulée."
                    log_warn "Vous pouvez configurer manuellement plus tard: rclone config"
                    BACKUP_CONFIGURED="false"
                    return 0
                fi
            else
                log_info "Configuration rclone annulée. Vous pourrez la configurer plus tard."
                BACKUP_CONFIGURED="false"
                return 0
            fi
        else
            log_success "✓ Remote rclone détecté: $EXISTING_REMOTE"
        fi

        BACKUP_REMOTE="$EXISTING_REMOTE"

        # Cron setup
        CRON_ENTRY="0 2 * * * cd ${SCRIPT_DIR} && ./scripts/backup_to_gdrive.sh >> logs/cron.log 2>&1"

        if ! (crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"); then
            log_info "Ajout cron quotidien (02:00)..."

            if (echo "$(crontab -l 2>/dev/null || true)"; echo "$CRON_ENTRY") | crontab - 2>/dev/null; then
                log_success "✓ Cron ajouté (backup quotidien 02:00)"
            else
                log_warn "Impossible d'ajouter cron automatiquement."
                log_info "Vous pouvez le faire manuellement: crontab -e"
                log_info "Ligne à ajouter: $CRON_ENTRY"
            fi
        else
            log_success "✓ Cron backup déjà configuré"
        fi

        # Test backup (optionnel)
        if prompt_yes_no "Effectuer un test backup maintenant ?" "n"; then
            log_info "Lancement test backup..."
            if bash ./scripts/backup_to_gdrive.sh >/dev/null 2>&1; then
                log_success "✓ Test backup réussi"
            else
                log_error "Test backup échoué. Vérifiez :"
                log_error "  - Configuration rclone: rclone listremotes"
                log_error "  - Logs: cat logs/backup_gdrive.log"
            fi
        fi

        log_success "✓ Sauvegardes Google Drive configurées"
        BACKUP_CONFIGURED="true"
    else
        log_warn "Sauvegardes Google Drive non activées"
        log_info "Vous pouvez les configurer plus tard: rclone config"
        BACKUP_CONFIGURED="false"
    fi

    echo "$BACKUP_CONFIGURED" > ".backup_configured"
    return 0
}

generate_security_report() {
    local score_current=0
    local score_total=4

    echo ""
    log_step "🔒 RÉSUMÉ SÉCURITÉ & CONFIGURATION"
    echo ""

    # --- Check 1: Mot de passe Dashboard ---
    echo -n "  1. Mot de passe Dashboard... "
    if grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" "$ENV_FILE" 2>/dev/null; then
        echo -e "${GREEN}✓ OK${NC} (hash bcrypt détecté)"
        ((score_current++))
    elif grep -q "CHANGEZ_MOI\|your_password\|12345" "$ENV_FILE" 2>/dev/null; then
        echo -e "${RED}✗ CRITIQUE${NC} (mot de passe par défaut)"
    else
        echo -e "${YELLOW}⚠ INCONNU${NC} (format non reconnu)"
    fi

    # --- Check 2: HTTPS ---
    echo -n "  2. HTTPS... "
    if [[ -f "certbot/conf/live/${DOMAIN}/fullchain.pem" ]]; then
        if openssl x509 -in "certbot/conf/live/${DOMAIN}/fullchain.pem" -noout >/dev/null 2>&1; then
            CERT_ISSUER=$(openssl x509 -in "certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -text 2>/dev/null | grep "Issuer:" | head -1 | sed 's/.*Issuer: //')

            if [[ "$CERT_ISSUER" =~ "Let's Encrypt" ]]; then
                echo -e "${GREEN}✓ PRODUCTION${NC} (Let's Encrypt)"
                ((score_current++))
            elif [[ "$CERT_ISSUER" =~ "Temporary" ]]; then
                echo -e "${YELLOW}⚠ DÉVELOPPEMENT${NC} (Self-signed)"
            else
                echo -e "${GREEN}✓ OK${NC} (Certificat valide)"
                ((score_current++))
            fi
        fi
    else
        echo -e "${YELLOW}⚠ SELF-SIGNED${NC} (temporaire)"
    fi

    # --- Check 3: Sauvegardes ---
    echo -n "  3. Sauvegardes Google Drive... "
    if [[ -f ".backup_configured" ]] && grep -q "true" ".backup_configured" 2>/dev/null; then
        echo -e "${GREEN}✓ OK${NC} (configurées)"
        ((score_current++))
    else
        echo -e "${YELLOW}⚠ OPTIONNEL${NC} (non configurées)"
    fi

    # --- Check 4: .env secrets ---
    echo -n "  4. Fichier .env secrets... "
    ENV_ISSUES=0
    if grep -iE "PASSWORD=.*[a-zA-Z0-9]{1,10}$|PASSWORD=12345|PASSWORD=admin" "$ENV_FILE" 2>/dev/null | grep -v "DASHBOARD_PASSWORD=\$2"; then
        ((ENV_ISSUES++))
    fi
    if grep -iE "API_KEY=.*your_|API_KEY=test" "$ENV_FILE" 2>/dev/null; then
        ((ENV_ISSUES++))
    fi

    if [[ $ENV_ISSUES -eq 0 ]]; then
        echo -e "${GREEN}✓ OK${NC} (pas de secrets en clair)"
        ((score_current++))
    else
        echo -e "${RED}✗ ATTENTION${NC} ($ENV_ISSUES potentiellement visibles)"
    fi

    # --- Résumé ---
    echo ""
    echo "  ═══════════════════════════════════════════"
    echo "  SCORE SÉCURITÉ : $score_current / $score_total"
    echo "  ═══════════════════════════════════════════"
    echo ""

    if [[ $score_current -eq 4 ]]; then
        echo -e "  ${GREEN}🎉 EXCELLENT - Production Ready${NC}"
    elif [[ $score_current -ge 3 ]]; then
        echo -e "  ${YELLOW}✓ BON - Améliorations recommandées${NC}"
    else
        echo -e "  ${RED}⚠️  À AMÉLIORER - Actions requises${NC}"
    fi

    echo ""
}

show_postsetup_menu() {
    echo ""
    log_step "Scripts Disponibles Post-Setup"

    echo -e "\n${BOLD}Pour modifier la configuration après le setup :${NC}\n"
    echo "  • ${BOLD}Mot de passe Dashboard${NC}"
    echo "    ./scripts/manage_dashboard_password.sh"
    echo ""
    echo "  • ${BOLD}Certificat Let's Encrypt${NC}"
    echo "    ./scripts/setup_letsencrypt.sh"
    echo ""
    echo "  • ${BOLD}Sauvegardes Google Drive${NC}"
    echo "    rclone config"
    echo ""
    echo "  • ${BOLD}Santé Système${NC}"
    echo "    ./scripts/monitor_pi4_health.sh"
    echo ""
}

# ==============================================================================
# PHASE 1 : PRÉ-REQUIS & SÉCURITÉ SYSTÈME
# ==============================================================================
log_step "PHASE 1 : Vérifications Système & Hardware"

CURRENT_UID=$(id -u)
if [[ "$CURRENT_UID" -eq 0 ]]; then
    log_warn "Attention: Exécution en root. Les fichiers créés appartiendront à root."
fi

if ! cmd_exists docker; then
    log_error "Docker introuvable. Installation requise."
    log_info "curl -fsSL https://get.docker.com | sh"
    exit 1
fi

configure_docker_ipv4
configure_kernel_params
configure_zram

# 1.3 Mémoire & Swap (CRITIQUE RPi4)
TOTAL_MEM=$(get_total_memory_gb)
log_info "Mémoire Totale (RAM+SWAP) : ${TOTAL_MEM}GB"

if [[ $TOTAL_MEM -lt $MIN_MEMORY_GB ]]; then
    log_warn "Mémoire insuffisante (<${MIN_MEMORY_GB}GB). Risque de crash élevé."

    if [[ -f "$SWAP_FILE" ]] && grep -q "$SWAP_FILE" /proc/swaps; then
         log_info "Swapfile actif détecté."
    else
         echo -e "${YELLOW}>>> Action requise : Créer/Augmenter le SWAP ? [O/n]${NC}"
         read -r -t 30 REPLY || REPLY="o"
         if [[ ! "$REPLY" =~ ^[Nn]$ ]]; then
            check_sudo
            # Désactivation swap actuel
            sudo swapoff "$SWAP_FILE" 2>/dev/null || true

            REQUIRED_SWAP=$((MIN_MEMORY_GB - (grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024 + 2))
            log_info "Création d'un Swapfile de ${REQUIRED_SWAP}GB..."

            # Allocation plus rapide avec fallocate, fallback dd
            if ! sudo fallocate -l "${REQUIRED_SWAP}G" "$SWAP_FILE"; then
                sudo dd if=/dev/zero of="$SWAP_FILE" bs=1G count="$REQUIRED_SWAP" status=progress
            fi

            sudo chmod 600 "$SWAP_FILE"
            sudo mkswap "$SWAP_FILE"
            sudo swapon "$SWAP_FILE"

            if ! grep -q "$SWAP_FILE" /etc/fstab; then
                echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab
            fi
            log_success "Swap activé. Mémoire totale : $(get_total_memory_gb)GB"
         else
            log_error "Refus d'augmenter la mémoire."
            exit 1
         fi
    fi
fi

# ==============================================================================
# PHASE 2 : HYGIÈNE DISQUE
# ==============================================================================
log_step "PHASE 2 : Nettoyage & Préparation Disque"

DISK_USAGE=$(df -h . | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
if [[ "$DISK_USAGE" -gt $((100 - DISK_THRESHOLD_PERCENT)) ]]; then
    log_warn "Espace disque faible (${DISK_USAGE}% utilisé). Nettoyage..."
    docker image prune -a -f --filter "until=24h"
    docker builder prune -f
else
    docker image prune -f
fi

# ==============================================================================
# PHASE 3 : CONFIGURATION (.env & Secrets)
# ==============================================================================
log_step "PHASE 3 : Configuration Sécurisée"

if [[ ! -f "$ENV_FILE" ]]; then
    log_info "Initialisation de $ENV_FILE..."
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi

if grep -q "^DOMAIN=" "$ENV_FILE" 2>/dev/null; then
    DOMAIN=$(grep "^DOMAIN=" "$ENV_FILE" | cut -d'=' -f2)
    log_info "Domaine détecté: $DOMAIN"
fi

# ============================================================================
# 3.2 GESTION MOT DE PASSE DASHBOARD (Idempotent & Sécurisé)
# ============================================================================
#
# NOTES IMPORTANTES SUR LE HACHAGE :
#
# 1. HASH BCRYPT ET CARACTÈRES SPÉCIAUX ($)
#    Les hashes bcrypt contiennent des caractères $ (ex: $2b$12$...).
#    Dans un fichier shell .env, les $ peuvent être interprétés comme
#    des EXPANSIONS DE VARIABLES (ex: $VAR → valeur de VAR).
#
# 2. SOLUTION : DOUBLAGE DES $
#    Avant d'écrire dans .env, chaque $ du hash est doublé ($ → $$).
#    Exemple:
#      Hash brut : $2b$12$abcdef$ghijkl$123456789...
#      Dans .env : $$2b$$12$$abcdef$$ghijkl$$123456789...
#
#    Lors de la lecture par l'application, le shell/parseur interprète
#    $$ comme un seul $, donc l'app reçoit le hash original correct.
#
# 3. PROCESSUS DANS CE SCRIPT :
#    a) Générer le hash bcrypt avec bcryptjs (via Docker)
#    b) Doubler les $ pour la sécurité shell (sed 's/\$/\$\$/g')
#    c) Échapper les / et & pour sed (sed 's/[\/&]/\\&/g')
#    d) Écrire dans .env avec sed (syntaxe: sed -i "s|pattern|replacement|")
#    e) L'app relit .env → shell interprète $$ comme $, app reçoit hash correct
#
# 4. IDEMPOTENCE :
#    - Premier lancement : demande le mot de passe
#    - Re-lancement avec hash valide : SKIP (pas de redémande)
#    - Reset : remplacer DASHBOARD_PASSWORD=CHANGEZ_MOI puis relancer
#
# ============================================================================

# Déterminer s'il y a déjà un mot de passe configuré
HAS_BCRYPT_HASH=false
if grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" "$ENV_FILE"; then
    HAS_BCRYPT_HASH=true
fi

# Déterminer s'il faut demander un nouveau mot de passe
NEEDS_PASSWORD_CONFIG=false
if grep -q "CHANGEZ_MOI" "$ENV_FILE" || [[ "$HAS_BCRYPT_HASH" == "false" ]]; then
    NEEDS_PASSWORD_CONFIG=true
fi

if [[ "$NEEDS_PASSWORD_CONFIG" == "true" ]]; then
    if [[ "$HAS_BCRYPT_HASH" == "true" ]]; then
        # Hash valide détecté mais CHANGEZ_MOI existe aussi (scénario rare)
        ACTION=$(prompt_password_action "true")
    else
        # Pas de hash valide détecté
        ACTION=$(prompt_password_action "false")
    fi

    case "$ACTION" in
        new)
            echo -e "\n${BOLD}Entrez le nouveau mot de passe dashboard :${NC}"
            echo -n "Mot de passe (caché) : "
            read -rs PASS_INPUT
            echo ""

            if [[ -n "$PASS_INPUT" ]]; then
                log_info "Hachage sécurisé du mot de passe avec bcryptjs..."

                # Image dashboard pour le hachage (compatibilité ARM64 RPi4)
                DASHBOARD_IMG="ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest"

                # Pull si nécessaire
                if ! docker image inspect "$DASHBOARD_IMG" >/dev/null 2>&1; then
                    log_info "Téléchargement de l'image dashboard pour outils crypto..."
                    docker pull -q "$DASHBOARD_IMG"
                fi

                # Générer le hash bcrypt via Node.js dans le conteneur
                HASH_OUTPUT=$(docker run --rm \
                    --entrypoint node \
                    -e PWD_INPUT="$PASS_INPUT" \
                    "$DASHBOARD_IMG" \
                    -e "console.log(require('bcryptjs').hashSync(process.env.PWD_INPUT, 12))" 2>/dev/null)

                if [[ "$HASH_OUTPUT" =~ ^\$2 ]]; then
                    # ================== DOUBLAGE DES $ ==================
                    # Remplacer chaque $ par $$ pour éviter l'expansion shell
                    SAFE_HASH=$(echo "$HASH_OUTPUT" | sed 's/\$/\$\$/g')
                    # Échapper les / et & pour sed (caractères spéciaux en sed)
                    ESCAPED_SAFE_HASH=$(echo "$SAFE_HASH" | sed 's/[\/&]/\\&/g')
                    # ====================================================

                    # Écrire le hash sécurisé dans .env
                    sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${ESCAPED_SAFE_HASH}|" "$ENV_FILE"
                    log_success "✓ Mot de passe haché et stocké dans .env (avec $$ doublés pour sécurité shell)"
                    log_info "  Hash: ${SAFE_HASH:0:20}... (doublage des $)"
                else
                    log_error "Échec du hachage bcrypt. Sortie: $HASH_OUTPUT"
                    log_error "Vérifiez que l'image dashboard est disponible."
                    exit 1
                fi
            else
                log_warn "Mot de passe vide. Configuration annulée."
            fi
            ;;

        keep)
            log_info "✓ Mot de passe existant conservé (hash bcrypt valide détecté)"
            ;;

        cancel)
            log_warn "Configuration du mot de passe annulée. Vous pouvez le configurer manuellement plus tard."
            log_info "Pour configurer : sed -i 's|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=CHANGEZ_MOI|' .env && ./setup.sh"
            ;;
    esac
else
    if [[ "$HAS_BCRYPT_HASH" == "true" ]]; then
        log_info "✓ Mot de passe Dashboard déjà configuré (hash bcrypt détecté). Skip."
    fi
fi

if grep -q "API_KEY=your_secure_random_key_here" "$ENV_FILE"; then
    log_info "Génération automatique d'une API Key robuste..."
    NEW_KEY=$(openssl rand -hex 32)
    sed -i "s|^API_KEY=.*|API_KEY=${NEW_KEY}|" "$ENV_FILE"
fi

if grep -q "JWT_SECRET=" "$ENV_FILE" && grep -q "your_jwt_secret_here" "$ENV_FILE"; then
    log_info "Génération automatique d'un JWT Secret robuste..."
    NEW_JWT=$(openssl rand -base64 48 | tr -d '\n\r')
    ESCAPED_JWT=$(echo "$NEW_JWT" | sed 's/[\/&]/\\&/g')
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${ESCAPED_JWT}|" "$ENV_FILE"
fi

# ==============================================================================
# PHASE 4 : PRÉPARATION VOLUMES & PERMISSIONS
# ==============================================================================
log_step "PHASE 4 : Permissions & Volumes"

mkdir -p data logs config certbot/conf certbot/www
touch data/messages.txt data/late_messages.txt
[[ ! -f data/linkedin.db ]] && touch data/linkedin.db

log_info "Application des permissions (User 1000)..."
if [[ -w "." ]]; then
    if [[ "$CURRENT_UID" -ne 1000 ]] && [[ "$CURRENT_UID" -ne 0 ]]; then
        check_sudo
        sudo chown -R 1000:1000 data logs config
    elif [[ "$CURRENT_UID" -eq 0 ]]; then
        chown -R 1000:1000 data logs config
    fi
else
    check_sudo
    sudo chown -R 1000:1000 data logs config
fi

chmod -R 775 data logs config
log_success "Permissions appliquées."

# ==============================================================================
# PHASE 4.5 : BOOTSTRAP SSL
# ==============================================================================
log_step "PHASE 4.5 : Préparation SSL"

CERT_DIR="certbot/conf/live/${DOMAIN}"
if [[ ! -f "$CERT_DIR/fullchain.pem" ]] || [[ ! -f "$CERT_DIR/privkey.pem" ]]; then
    log_warn "Certificats SSL absents. Génération de certificats temporaires..."
    mkdir -p "$CERT_DIR"
    if cmd_exists openssl; then
        openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
            -keyout "$CERT_DIR/privkey.pem" \
            -out "$CERT_DIR/fullchain.pem" \
            -subj "/CN=${DOMAIN}/O=Temporary Certificate/C=FR" 2>/dev/null
        chmod 644 "$CERT_DIR/fullchain.pem"
        chmod 600 "$CERT_DIR/privkey.pem"
        log_success "Certificats temporaires créés."
    else
        log_error "OpenSSL manquant."
        exit 1
    fi
fi

DH_PARAMS="certbot/conf/ssl-dhparams.pem"
if [[ ! -f "$DH_PARAMS" ]]; then
    log_info "Génération des paramètres Diffie-Hellman..."
    if cmd_exists openssl; then
        openssl dhparam -out "$DH_PARAMS" 2048 2>/dev/null
        chmod 644 "$DH_PARAMS"
    fi
fi

# ==============================================================================
# PHASE 4.6 : NGINX CONFIG
# ==============================================================================
log_step "PHASE 4.6 : Configuration Nginx Dynamique"

generate_nginx_config() {
    local template="$1"
    local output="$2"
    local domain="$3"

    if [[ ! -f "$template" ]]; then log_error "Template Nginx introuvable"; return 1; fi
    if [[ -z "$domain" || "$domain" == "YOUR_DOMAIN.COM" || "$domain" =~ ^\$\{ ]]; then
        log_error "Domaine invalide dans .env"; return 1
    fi

    if ! cmd_exists envsubst; then
        log_warn "Installation de gettext-base (envsubst)..."
        check_sudo
        sudo apt-get update -qq && sudo apt-get install -y -qq gettext-base
    fi

    export DOMAIN="$domain"
    envsubst '${DOMAIN}' < "$template" > "$output"

    if grep -q '\${DOMAIN}' "$output" 2>/dev/null; then
        log_error "Erreur substitution template Nginx"
        rm -f "$output"
        return 1
    fi
    chmod 644 "$output"
    log_success "Configuration Nginx générée."
    return 0
}

if [[ -f "$NGINX_TEMPLATE" ]]; then
    generate_nginx_config "$NGINX_TEMPLATE" "$NGINX_CONFIG" "$DOMAIN" || {
        log_error "Impossible de générer la configuration Nginx."
        exit 1
    }
fi

# ==============================================================================
# PHASE 4.7 : CONFIGURATION HTTPS
# ==============================================================================
configure_https_menu || {
    log_error "Configuration HTTPS échouée"
    exit 1
}

# ==============================================================================
# PHASE 5 : DÉPLOIEMENT
# ==============================================================================
log_step "PHASE 5 : Lancement des Services"

log_info "Répertoire de travail: $(pwd)"
log_info "Fichier docker-compose: $COMPOSE_FILE"

# Étape 1 : Téléchargement des images
if ! docker_pull_with_retry "$COMPOSE_FILE"; then
    log_error "Échec du téléchargement des images. Vérifiez :"
    log_info "  - La connectivité réseau"
    log_info "  - L'accès à Docker et docker-compose"
    log_info "  - La disponibilité des registries Docker"
    exit 1
fi

# Étape 2 : Démarrage des conteneurs
log_info "Démarrage des conteneurs..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans || {
    log_error "Impossible de démarrer les conteneurs"
    log_info "Logs pour diagnostic :"
    docker compose -f "$COMPOSE_FILE" logs --tail=30 2>/dev/null || true
    exit 1
}

# ==============================================================================
# PHASE 5.1 : SAUVEGARDES GOOGLE DRIVE
# ==============================================================================
configure_google_drive_menu || {
    log_error "Configuration Google Drive échouée"
    exit 1
}

# ==============================================================================
# PHASE 6 : VALIDATION
# ==============================================================================
log_step "PHASE 6 : Validation du Déploiement"

wait_for_service() {
    local name="$1"
    local url="$2"
    local max_retries=$((HEALTH_TIMEOUT / HEALTH_INTERVAL))

    echo -n "En attente de $name ($url) "
    for ((i=1; i<=max_retries; i++)); do
        if docker compose -f "$COMPOSE_FILE" ps "$name" | grep -q "Up"; then
             local status
             status=$(curl -o /dev/null -s -w "%{http_code}" "$url" || echo "000")
             if [[ "$status" =~ ^(200|301|302|307|308|401)$ ]]; then
                 echo -e "${GREEN} OK ($status)${NC}"
                 return 0
             fi
        else
             echo -e "${RED} CRASHED${NC}"
             return 1
        fi
        echo -n "."
        sleep $HEALTH_INTERVAL
    done
    echo -e "${RED} TIMEOUT${NC}"
    return 1
}

wait_for_service "api" "http://localhost:8000/health" || { log_error "API HS"; exit 1; }
wait_for_service "dashboard" "http://localhost:3000/api/system/health" || { log_error "Dashboard HS"; exit 1; }

# Cleanup Chromium zombies
[[ -x "./scripts/cleanup_chromium_zombies.sh" ]] && ./scripts/cleanup_chromium_zombies.sh 2>/dev/null

# ==============================================================================
# RAPPORT SÉCURITÉ
# ==============================================================================
generate_security_report

# ==============================================================================
# RAPPORT FINAL
# ==============================================================================
log_step "DÉPLOIEMENT TERMINÉ AVEC SUCCÈS"

LOCAL_IP=$(hostname -I | awk '{print $1}')
DASHBOARD_USER=$(grep "^DASHBOARD_USER=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "admin")

echo -e "
${BOLD}${BLUE}┌─────────────────────────────────────────────────────────────────────────┐${NC}
${BOLD}${BLUE}│                      RÉCAPITULATIF DE CONFIGURATION                     │${NC}
${BOLD}${BLUE}└─────────────────────────────────────────────────────────────────────────┘${NC}

  ${BOLD}URL d'accès${NC}            : ${GREEN}https://${DOMAIN}${NC}
  ${BOLD}URL locale${NC}             : http://${LOCAL_IP}:3000

  ${BOLD}Login Dashboard${NC}        : ${GREEN}${DASHBOARD_USER}${NC}

  ${BOLD}Commandes utiles:${NC}
  - Logs: docker compose -f $COMPOSE_FILE logs -f
  - Stop: docker compose -f $COMPOSE_FILE down
  - Update: git pull && ./setup.sh

${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
"

# Afficher les scripts post-setup
show_postsetup_menu

log_success "✓ Setup Terminé avec Succès !"
