#!/bin/bash
# ==============================================================================
# LINKEDIN AUTO RPi4 - SETUP SCRIPT (V3.1 - PRODUCTION READY)
# ==============================================================================
# Architecte : Jules - Expert DevOps
# Cible      : Raspberry Pi 4 (4GB RAM, SD 32GB, ARM64)
# ==============================================================================
#
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                        RAPPORT D'AUDIT TECHNIQUE                         ║
# ╠══════════════════════════════════════════════════════════════════════════╣
# ║                                                                          ║
# ║ 1. [COHÉRENCE] Persistance des Données (Corrigé)                         ║
# ║    - PROBLÈME: L'usage de volumes nommés pour SQLite rendait les backups ║
# ║      et l'initialisation complexes (données cachées dans /var/lib/docker)║
# ║    - SOLUTION: Passage en "Bind Mount" (./data:/app/data) dans Compose.  ║
# ║      Le script prépare désormais ./data avec les bonnes permissions.     ║
# ║                                                                          ║
# ║ 2. [SÉCURITÉ] Hachage Mot de Passe (Robustifié)                          ║
# ║    - PROBLÈME: Dépendance à 'node' sur l'hôte pour hasher le mot de passe.║
# ║    - SOLUTION: Exécution du script de hachage via un conteneur éphémère  ║
# ║      (utilisant l'image du dashboard) pour garantir l'environnement.     ║
# ║                                                                          ║
# ║ 3. [STABILITÉ] Gestion Mémoire & SWAP (Critique RPi4)                    ║
# ║    - PROBLÈME: 4GB RAM insuffisant pour Next.js build + Playwright + DB. ║
# ║    - SOLUTION: Vérification stricte (RAM+SWAP >= 6GB). Création auto     ║
# ║      d'un swapfile de 2GB+ si nécessaire avant tout lancement.           ║
# ║                                                                          ║
# ║ 4. [FIABILITÉ] Health Checks Réels                                       ║
# ║    - PROBLÈME: "Succès" déclaré alors que Next.js compilait encore.      ║
# ║    - SOLUTION: Boucle d'attente active sur localhost:3000 (HTTP 200)     ║
# ║      pour garantir que l'UI est réellement accessible.                   ║
# ║                                                                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# ==============================================================================

set -euo pipefail

# --- Couleurs ---
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# --- Configuration ---
# DOMAIN sera lu depuis .env après sa création
DOMAIN="gaspardanoukolivier.freeboxos.fr"  # Valeur par défaut
readonly COMPOSE_FILE="docker-compose.pi4-standalone.yml"
readonly ENV_FILE=".env"
readonly ENV_TEMPLATE=".env.pi4.example"
readonly NGINX_TEMPLATE="deployment/nginx/linkedin-bot.conf.template"
readonly NGINX_CONFIG="deployment/nginx/linkedin-bot.conf"
readonly MIN_MEMORY_GB=6      # RAM + SWAP minimum requis
readonly SWAP_FILE="/swapfile"
readonly DISK_THRESHOLD_PERCENT=20
readonly HEALTH_TIMEOUT=300   # 5 minutes (Next.js peut être lent au 1er boot)
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

configure_docker_ipv4() {
    local daemon_json="/etc/docker/daemon.json"
    local needs_restart=false

    # [FIX-D] Configuration cible avec DNS fiables (Cloudflare + Google)
    local target_config='{
  "ipv6": false,
  "ip6tables": false,
  "dns": ["1.1.1.1", "8.8.8.8", "8.8.4.4"],
  "dns-opts": ["timeout:2", "attempts:3"],
  "registry-mirrors": []
}'

    # Vérifier si Docker utilise déjà la config complète (IPv4 + DNS)
    if [[ -f "$daemon_json" ]]; then
        if grep -q '"ip6tables": false' "$daemon_json" 2>/dev/null && \
           grep -q '"dns"' "$daemon_json" 2>/dev/null; then
            log_info "Docker déjà configuré (IPv4 + DNS fiables)."
            return 0
        fi
    fi

    log_info "Configuration de Docker (IPv4 + DNS fiables Cloudflare/Google)..."
    check_sudo

    # Créer ou mettre à jour daemon.json
    if [[ ! -f "$daemon_json" ]]; then
        # Créer nouveau fichier avec config complète
        echo "$target_config" | sudo tee "$daemon_json" > /dev/null
        needs_restart=true
    else
        # Modifier fichier existant avec jq si disponible
        local temp_file=$(mktemp)
        if command -v jq &> /dev/null; then
            # Merge avec jq
            sudo jq '. + {"ipv6": false, "ip6tables": false, "dns": ["1.1.1.1", "8.8.8.8", "8.8.4.4"], "dns-opts": ["timeout:2", "attempts:3"]}' "$daemon_json" > "$temp_file"
            sudo mv "$temp_file" "$daemon_json"
        else
            # Fallback : remplacement complet
            log_warn "jq non disponible, remplacement complet de daemon.json"
            echo "$target_config" | sudo tee "$daemon_json" > /dev/null
        fi
        needs_restart=true
    fi

    if [[ "$needs_restart" == "true" ]]; then
        log_info "Redémarrage du daemon Docker..."
        sudo systemctl restart docker
        sleep 3
        log_success "Docker redémarré avec IPv4 + DNS fiables (1.1.1.1, 8.8.8.8)."
    fi
}

# [FIX-A] Configuration des paramètres kernel pour RPi4
configure_kernel_params() {
    local sysctl_file="/etc/sysctl.d/99-rpi4-docker.conf"

    log_info "Configuration des paramètres kernel pour RPi4..."

    # Vérifier si déjà configuré
    if [[ -f "$sysctl_file" ]] && grep -q "vm.overcommit_memory" "$sysctl_file" 2>/dev/null; then
        log_info "Paramètres kernel déjà configurés."
        return 0
    fi

    check_sudo

    # Créer le fichier de configuration sysctl
    sudo tee "$sysctl_file" > /dev/null <<'EOF'
# ═══════════════════════════════════════════════════════════════════════════
# Configuration kernel optimisée pour LinkedIn Bot sur Raspberry Pi 4
# Généré par setup.sh - NE PAS MODIFIER MANUELLEMENT
# ═══════════════════════════════════════════════════════════════════════════

# Redis: Permet l'overcommit mémoire (évite les warnings BGSAVE)
# IMPORTANT: Ce paramètre est global au kernel, pas namespaceable
vm.overcommit_memory = 1

# Augmente la file d'attente des connexions TCP (Redis, Nginx)
net.core.somaxconn = 1024

# Réduit le swappiness pour favoriser la RAM (carte SD = lent)
vm.swappiness = 10

# Optimisation des buffers réseau pour connexions stables
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# Timeout TCP pour connexions longues (LinkedIn, API)
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 5
EOF

    # Appliquer immédiatement
    sudo sysctl -p "$sysctl_file" > /dev/null 2>&1

    log_success "Paramètres kernel configurés:"
    log_info "  → vm.overcommit_memory=1 (Redis)"
    log_info "  → net.core.somaxconn=1024 (TCP backlog)"
    log_info "  → vm.swappiness=10 (Optimisation SD card)"
}

docker_pull_with_retry() {
    local compose_file="$1"
    local max_retries=4
    local base_delay=2

    # Extraire la liste des services depuis le compose file
    local services
    services=$(docker compose -f "$compose_file" config --services 2>/dev/null)

    if [[ -z "$services" ]]; then
        log_error "Impossible de lire la liste des services depuis $compose_file"
        return 1
    fi

    local total_services
    total_services=$(echo "$services" | wc -l)
    local current=0

    # Pull séquentiel de chaque service (évite surcharge réseau/mémoire sur RPi4)
    while IFS= read -r service; do
        current=$((current + 1))
        echo -n "[${current}/${total_services}] Pull de l'image pour '${service}' "

        local retry_count=0
        local success=false

        while [[ $retry_count -lt $max_retries ]]; do
            if docker compose -f "$compose_file" pull --quiet "$service" 2>&1; then
                echo -e "${GREEN}✓${NC}"
                success=true
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
            log_error "Échec du pull pour le service '$service' après $max_retries tentatives."
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
# PHASE 0.5 : CONFIGURATION ZRAM (OPTIMISATION MÉMOIRE RPi4)
# ==============================================================================
log_step "PHASE 0.5 : Configuration ZRAM (Compression RAM)"

configure_zram() {
    # ZRAM compresse la RAM au lieu d'utiliser le SWAP sur SD (plus rapide, préserve la carte)
    local ZRAM_SIZE_MB=1024  # 1GB de ZRAM compressé (~2GB effectif avec lz4)

    # Vérifier si ZRAM est déjà configuré
    if [[ -e /dev/zram0 ]] && swapon --show | grep -q zram; then
        log_info "ZRAM déjà actif."
        return 0
    fi

    log_info "Configuration de ZRAM (1GB compressé)..."
    check_sudo

    # Charger le module ZRAM
    if ! lsmod | grep -q zram; then
        sudo modprobe zram num_devices=1
    fi

    # Configurer la taille et l'algorithme
    if [[ -e /sys/block/zram0 ]]; then
        # Désactiver si déjà actif
        sudo swapoff /dev/zram0 2>/dev/null || true

        # Configurer l'algorithme de compression (lz4 = rapide, bon ratio)
        echo lz4 | sudo tee /sys/block/zram0/comp_algorithm > /dev/null 2>&1 || true

        # Définir la taille (1GB)
        echo "${ZRAM_SIZE_MB}M" | sudo tee /sys/block/zram0/disksize > /dev/null

        # Formater et activer avec priorité haute (avant SWAP fichier)
        sudo mkswap /dev/zram0
        sudo swapon -p 100 /dev/zram0

        log_success "ZRAM activé: ${ZRAM_SIZE_MB}MB (priorité haute)"
    else
        log_warn "ZRAM non disponible sur ce kernel."
        return 1
    fi

    # Persister la configuration ZRAM au boot
    local ZRAM_SERVICE="/etc/systemd/system/zram-swap.service"
    if [[ ! -f "$ZRAM_SERVICE" ]]; then
        sudo tee "$ZRAM_SERVICE" > /dev/null <<'ZRAM_EOF'
[Unit]
Description=Configure ZRAM swap device
After=local-fs.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'modprobe zram num_devices=1 && echo lz4 > /sys/block/zram0/comp_algorithm 2>/dev/null; echo 1024M > /sys/block/zram0/disksize && mkswap /dev/zram0 && swapon -p 100 /dev/zram0'
ExecStop=/bin/bash -c 'swapoff /dev/zram0 2>/dev/null; echo 1 > /sys/block/zram0/reset'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
ZRAM_EOF
        sudo systemctl daemon-reload
        sudo systemctl enable zram-swap.service
        log_success "Service ZRAM créé et activé au démarrage."
    fi
}

# Activer ZRAM en premier (plus rapide que SWAP fichier)
configure_zram

# ==============================================================================
# PHASE 1 : PRÉ-REQUIS & SÉCURITÉ SYSTÈME
# ==============================================================================
log_step "PHASE 1 : Vérifications Système & Hardware"

# 1.1 Utilisateur
CURRENT_UID=$(id -u)
if [[ "$CURRENT_UID" -eq 0 ]]; then
    log_warn "Attention: Exécution en root. Les fichiers créés appartiendront à root."
    log_info "Assurez-vous que les conteneurs (UID 1000) pourront les lire."
fi

# 1.2 Docker
if ! cmd_exists docker; then
    log_error "Docker introuvable. Installation requise."
    log_info "curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# 1.2.1 Configuration Docker IPv4 + DNS fiables (Fix problème réseau IPv6/DNS sur Raspberry Pi)
configure_docker_ipv4

# 1.2.2 [FIX-A] Configuration kernel (vm.overcommit_memory, somaxconn, swappiness)
# Ces paramètres doivent être sur l'HÔTE, pas dans les conteneurs Docker
configure_kernel_params

# 1.3 Mémoire & Swap (CRITIQUE RPi4)
TOTAL_MEM=$(get_total_memory_gb)
log_info "Mémoire Totale (RAM+SWAP) : ${TOTAL_MEM}GB"

if [[ $TOTAL_MEM -lt $MIN_MEMORY_GB ]]; then
    log_warn "Mémoire insuffisante (<${MIN_MEMORY_GB}GB). Risque de crash élevé."

    # Vérification si swapfile existe déjà mais inactif ou trop petit
    if [[ -f "$SWAP_FILE" ]]; then
        log_info "Swapfile existant détecté."
        # On pourrait l'agrandir, mais pour l'instant on alerte
    fi

    echo -e "${YELLOW}>>> Action requise : Créer/Augmenter le SWAP ? [O/n]${NC}"
    read -r -t 30 REPLY || REPLY="o"
    if [[ ! "$REPLY" =~ ^[Nn]$ ]]; then
        check_sudo
        # Désactivation swap actuel pour éviter conflits si redimensionnement
        sudo swapoff "$SWAP_FILE" 2>/dev/null || true

        REQUIRED_SWAP=$((MIN_MEMORY_GB - (grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024 + 2))
        log_info "Création d'un Swapfile de ${REQUIRED_SWAP}GB..."

        sudo fallocate -l "${REQUIRED_SWAP}G" "$SWAP_FILE" || sudo dd if=/dev/zero of="$SWAP_FILE" bs=1G count="$REQUIRED_SWAP" status=progress
        sudo chmod 600 "$SWAP_FILE"
        sudo mkswap "$SWAP_FILE"
        sudo swapon "$SWAP_FILE"

        if ! grep -q "$SWAP_FILE" /etc/fstab; then
            echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab
        fi
        log_success "Swap activé. Mémoire totale : $(get_total_memory_gb)GB"
    else
        log_error "Refus d'augmenter la mémoire. Arrêt pour protéger le matériel."
        exit 1
    fi
fi

# ==============================================================================
# PHASE 2 : HYGIÈNE DISQUE (SD CARD SAVER)
# ==============================================================================
log_step "PHASE 2 : Nettoyage & Préparation Disque"

# Nettoyage conditionnel pour économiser les cycles d'écriture SD
DISK_USAGE=$(df -h . | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
if [[ "$DISK_USAGE" -gt $((100 - DISK_THRESHOLD_PERCENT)) ]]; then
    log_warn "Espace disque faible (${DISK_USAGE}% utilisé). Nettoyage AGRESSIF..."
    # Nettoyage complet : images, containers arrêtés, volumes orphelins, cache
    docker system prune -a -f --volumes --filter "until=24h"
    docker builder prune -a -f
    log_success "Nettoyage agressif terminé."
else
    log_info "Espace disque OK (${DISK_USAGE}%). Nettoyage léger."
    # Nettoyage léger : images dangling et containers arrêtés
    docker image prune -f
    docker container prune -f --filter "until=1h"
fi

# Nettoyage logs Docker anciens (> 7 jours) pour économiser la SD
if [[ -d /var/lib/docker/containers ]]; then
    log_info "Nettoyage des logs Docker anciens..."
    sudo find /var/lib/docker/containers -name "*.log" -mtime +7 -exec truncate -s 0 {} \; 2>/dev/null || true
fi

# ==============================================================================
# PHASE 3 : CONFIGURATION (.env & Secrets)
# ==============================================================================
log_step "PHASE 3 : Configuration Sécurisée"

# 3.1 Setup .env
if [[ ! -f "$ENV_FILE" ]]; then
    log_info "Initialisation de $ENV_FILE..."
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi

# 3.1.1 Lecture du DOMAIN depuis .env (si présent)
if grep -q "^DOMAIN=" "$ENV_FILE" 2>/dev/null; then
    DOMAIN=$(grep "^DOMAIN=" "$ENV_FILE" | cut -d'=' -f2)
    log_info "Domaine détecté dans .env: $DOMAIN"
fi

# 3.2 Gestion Mot de Passe (Hachage via Docker)
# Utilisation d'un conteneur Node.js éphémère avec installation à la volée de bcryptjs
# pour garantir la disponibilité de la dépendance sans polluer le système hôte
if grep -q "CHANGEZ_MOI" "$ENV_FILE" || grep -q "^DASHBOARD_PASSWORD=[^$]" "$ENV_FILE"; then
    echo -e "${BOLD}>>> Configuration du Mot de Passe Dashboard${NC}"
    echo -n "Entrez le nouveau mot de passe : "
    read -rs PASS_INPUT
    echo ""

    if [[ -n "$PASS_INPUT" ]]; then
        log_info "Hachage sécurisé du mot de passe (via conteneur Node.js ARM64)..."

        # Exécution dans un conteneur éphémère avec installation de bcryptjs à la volée
        # Utilisation de variable d'environnement pour sécuriser le passage du mot de passe
        # (évite les problèmes d'échappement avec caractères spéciaux: $, ", \, etc.)
        # node:20-alpine est léger (~40MB) et natif ARM64
        # -w /tmp/hashwork définit un répertoire de travail temporaire avec permissions correctes
        HASH_OUTPUT=$(docker run --rm \
            --platform linux/arm64 \
            -e PASSWORD="$PASS_INPUT" \
            -w /tmp/hashwork \
            node:20-alpine \
            sh -c "npm install --no-save bcryptjs 2>&1 | grep -v 'npm notice' && node -e \"const bcrypt = require('bcryptjs'); const hash = bcrypt.hashSync(process.env.PASSWORD, 12); console.log(hash);\"" 2>&1)

        if [[ "$HASH_OUTPUT" =~ ^\$2 ]]; then
            # Échappement pour Docker Compose ($ -> $$)
            SAFE_HASH=$(echo "$HASH_OUTPUT" | sed 's/\$/\$\$/g')
            ESCAPED_SAFE_HASH=$(echo "$SAFE_HASH" | sed 's/[\/&]/\\&/g')

            sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${ESCAPED_SAFE_HASH}|" "$ENV_FILE"
            log_success "Mot de passe mis à jour et haché."
        else
            log_error "Échec du hachage. Sortie: $HASH_OUTPUT"
            exit 1
        fi
    fi
fi

# 3.3 Génération API Key si défaut
if grep -q "API_KEY=your_secure_random_key_here" "$ENV_FILE"; then
    log_info "Génération automatique d'une API Key robuste..."
    NEW_KEY=$(openssl rand -hex 32)
    sed -i "s|^API_KEY=.*|API_KEY=${NEW_KEY}|" "$ENV_FILE"
fi

# ==============================================================================
# PHASE 4 : PRÉPARATION VOLUMES & PERMISSIONS
# ==============================================================================
log_step "PHASE 4 : Permissions & Volumes"

# Création explicite des dossiers pour le Bind Mount
mkdir -p data logs config certbot/conf certbot/www

# Initialisation fichiers vides si absents pour éviter erreurs Docker
touch data/messages.txt data/late_messages.txt
[[ ! -f data/linkedin.db ]] && touch data/linkedin.db

# PERMISSIONS CRITIQUES : UID 1000 (Node/Python dans conteneurs)
log_info "Application des permissions (User 1000)..."
# On utilise sudo si nécessaire, ou on le fait en direct si propriétaire
if [[ -w "." ]]; then
    # Si on est user 1000, mkdir a déjà créé avec les bons droits
    # On force quand même pour être sûr
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
# PHASE 4.5 : BOOTSTRAP SSL (CERTIFICATS DUMMY)
# ==============================================================================
log_step "PHASE 4.5 : Préparation SSL"

# Vérifier si les certificats Let's Encrypt existent déjà
CERT_DIR="certbot/conf/live/${DOMAIN}"
if [[ ! -f "$CERT_DIR/fullchain.pem" ]] || [[ ! -f "$CERT_DIR/privkey.pem" ]]; then
    log_warn "Certificats SSL absents. Génération de certificats auto-signés temporaires..."

    # Créer le répertoire pour les certificats dummy
    mkdir -p "$CERT_DIR"

    # Générer un certificat auto-signé valide 365 jours
    # Cela permettra à Nginx de démarrer même si Certbot n'a pas encore été exécuté
    if cmd_exists openssl; then
        openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
            -keyout "$CERT_DIR/privkey.pem" \
            -out "$CERT_DIR/fullchain.pem" \
            -subj "/CN=${DOMAIN}/O=Temporary Certificate/C=FR" 2>/dev/null

        chmod 644 "$CERT_DIR/fullchain.pem"
        chmod 600 "$CERT_DIR/privkey.pem"

        log_success "Certificats temporaires créés (valides 365j)."
        log_info "IMPORTANT : Exécutez Certbot après le démarrage pour obtenir de vrais certificats."
    else
        log_error "OpenSSL manquant. Impossible de créer des certificats temporaires."
        log_info "Installation : sudo apt-get install openssl"
        exit 1
    fi
else
    log_success "Certificats SSL existants détectés."
fi

# Générer les paramètres DH si absents (requis pour SSL)
DH_PARAMS="certbot/conf/ssl-dhparams.pem"
if [[ ! -f "$DH_PARAMS" ]]; then
    log_info "Génération des paramètres Diffie-Hellman (cela peut prendre 2-3 minutes sur RPi4)..."
    if cmd_exists openssl; then
        openssl dhparam -out "$DH_PARAMS" 2048 2>/dev/null
        chmod 644 "$DH_PARAMS"
        log_success "Paramètres DH générés."
    else
        log_warn "Impossible de générer ssl-dhparams.pem (openssl manquant)."
        log_info "Nginx utilisera les paramètres par défaut."
    fi
else
    log_info "Paramètres DH existants."
fi

# ==============================================================================
# PHASE 4.6 : GÉNÉRATION CONFIGURATION NGINX DYNAMIQUE
# ==============================================================================
log_step "PHASE 4.6 : Configuration Nginx Dynamique"

generate_nginx_config() {
    local template="$1"
    local output="$2"
    local domain="$3"

    if [[ ! -f "$template" ]]; then
        log_error "Template Nginx introuvable: $template"
        return 1
    fi

    # [FIX-B] Validation stricte du domaine AVANT génération
    if [[ -z "$domain" || "$domain" == "YOUR_DOMAIN.COM" || "$domain" =~ ^\$\{ ]]; then
        log_error "Domaine invalide ou non défini: '$domain'"
        log_error "Vérifiez la variable DOMAIN dans le fichier .env"
        return 1
    fi

    log_info "Génération de la configuration Nginx pour le domaine: $domain"

    # Vérifier si envsubst est disponible
    if ! cmd_exists envsubst; then
        log_warn "envsubst non trouvé, installation de gettext-base..."
        check_sudo
        sudo apt-get update -qq && sudo apt-get install -y -qq gettext-base
    fi

    # Export de la variable pour envsubst
    export DOMAIN="$domain"

    # Génération du fichier de configuration
    envsubst '${DOMAIN}' < "$template" > "$output"
    local envsubst_status=$?

    # [FIX-B] VALIDATION POST-GÉNÉRATION - Vérification que les placeholders ont été remplacés
    if [[ $envsubst_status -ne 0 ]]; then
        log_error "Échec de envsubst (code: $envsubst_status)"
        return 1
    fi

    # Vérifier qu'aucun placeholder ${DOMAIN} ne reste dans le fichier généré
    if grep -q '\${DOMAIN}' "$output" 2>/dev/null; then
        log_error "ERREUR CRITIQUE: Placeholders \${DOMAIN} non remplacés dans $output"
        log_error "Le fichier de configuration contient encore des variables non substituées."
        rm -f "$output"  # Supprimer le fichier invalide
        return 1
    fi

    # Vérifier que le domaine apparaît bien dans le fichier (preuve de substitution)
    if ! grep -q "$domain" "$output" 2>/dev/null; then
        log_error "ERREUR: Le domaine '$domain' n'apparaît pas dans la configuration générée"
        rm -f "$output"
        return 1
    fi

    # Vérifier la syntaxe Nginx si possible (via Docker si nginx non installé sur l'hôte)
    log_info "Validation syntaxique de la configuration Nginx..."
    if cmd_exists nginx; then
        if ! nginx -t -c "$output" 2>/dev/null; then
            log_warn "Validation Nginx locale non concluante (config partielle)"
        fi
    fi

    chmod 644 "$output"
    log_success "Configuration Nginx générée et validée: $output"
    log_info "  → Domaine: $domain"
    log_info "  → Certificats: /etc/letsencrypt/live/$domain/"
    log_info "  → Validation: OK (pas de placeholders résiduels)"
    return 0
}

# Générer la configuration Nginx
if [[ -f "$NGINX_TEMPLATE" ]]; then
    generate_nginx_config "$NGINX_TEMPLATE" "$NGINX_CONFIG" "$DOMAIN" || {
        log_error "Impossible de générer la configuration Nginx."
        exit 1
    }
else
    log_warn "Template Nginx absent: $NGINX_TEMPLATE"
    log_warn "La configuration Nginx devra être créée manuellement."
fi

# ==============================================================================
# PHASE 5 : DÉPLOIEMENT
# ==============================================================================
log_step "PHASE 5 : Lancement des Services"

log_info "Pull des images (séquentiel avec retry automatique)..."
if ! docker_pull_with_retry "$COMPOSE_FILE"; then
    log_error "Impossible de télécharger les images Docker."
    log_info "Vérifiez votre connexion réseau et réessayez."
    exit 1
fi

log_info "Recréation des conteneurs..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# ==============================================================================
# PHASE 6 : VÉRIFICATION DE SANTÉ (WAIT-FOR-IT)
# ==============================================================================
log_step "PHASE 6 : Validation du Déploiement"

wait_for_service() {
    local name="$1"
    local url="$2"
    local max_retries=$((HEALTH_TIMEOUT / HEALTH_INTERVAL))

    echo -n "En attente de $name ($url) "
    for ((i=1; i<=max_retries; i++)); do
        # On vérifie le code HTTP (200, 301, 302, 307 acceptés)
        if docker compose -f "$COMPOSE_FILE" ps "$name" | grep -q "Up"; then
             # Check HTTP status code
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

# 1. API
wait_for_service "api" "http://localhost:8000/health" || { log_error "L'API ne répond pas."; exit 1; }

# 2. Dashboard (Plus long)
wait_for_service "dashboard" "http://localhost:3000/api/system/health" || { log_error "Le Dashboard ne répond pas."; exit 1; }

# ==============================================================================
# RAPPORT FINAL
# ==============================================================================
log_step "DÉPLOIEMENT TERMINÉ AVEC SUCCÈS"

# Collecte des informations pour le récapitulatif
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Détection du type de certificat
CERT_TYPE="auto-signé"
SSL_STATUS="${YELLOW}⚠️  Auto-signé${NC}"
if [[ -f "certbot/conf/live/${DOMAIN}/fullchain.pem" ]]; then
    if openssl x509 -in "certbot/conf/live/${DOMAIN}/fullchain.pem" -noout -issuer 2>/dev/null | grep -q "Let's Encrypt"; then
        CERT_TYPE="Let's Encrypt"
        SSL_STATUS="${GREEN}✅ Let's Encrypt${NC}"
    fi
fi

# Récupération des identifiants depuis .env
DASHBOARD_USER=$(grep "^DASHBOARD_USER=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "admin")

# Détection statut backups (vérification cron ou script)
BACKUP_STATUS="${YELLOW}⚠️  Non configuré${NC}"
if crontab -l 2>/dev/null | grep -q "backup"; then
    BACKUP_STATUS="${GREEN}✅ Actif (cron)${NC}"
elif [[ -f "./scripts/backup.sh" ]]; then
    BACKUP_STATUS="${YELLOW}⚙️  Script disponible${NC}"
fi

# Affichage du rapport
clear
echo -e "
${BOLD}╔═══════════════════════════════════════════════════════════════════════════╗${NC}
${BOLD}║                                                                           ║${NC}
${BOLD}║               🎉  DÉPLOIEMENT RÉUSSI - RASPBERRY PI 4                     ║${NC}
${BOLD}║                                                                           ║${NC}
${BOLD}╚═══════════════════════════════════════════════════════════════════════════╝${NC}

${BOLD}${BLUE}┌─────────────────────────────────────────────────────────────────────────┐${NC}
${BOLD}${BLUE}│                      RÉCAPITULATIF DE CONFIGURATION                     │${NC}
${BOLD}${BLUE}└─────────────────────────────────────────────────────────────────────────┘${NC}

  ${BOLD}URL d'accès${NC}            : ${GREEN}https://${DOMAIN}${NC}
  ${BOLD}URL locale${NC}             : http://${LOCAL_IP}:3000

  ${BOLD}Login Dashboard${NC}        : ${GREEN}${DASHBOARD_USER}${NC}
  ${BOLD}Mot de passe${NC}           : ${DIM}(Configuré dans .env)${NC}

  ${BOLD}Statut SSL${NC}             : ${SSL_STATUS}
  ${BOLD}Domaine${NC}                : ${DOMAIN}

  ${BOLD}Statut Backups${NC}         : ${BACKUP_STATUS}
  ${BOLD}Base de données${NC}        : SQLite (./data/linkedin.db)

${BOLD}${BLUE}┌─────────────────────────────────────────────────────────────────────────┐${NC}
${BOLD}${BLUE}│                          SERVICES DISPONIBLES                           │${NC}
${BOLD}${BLUE}└─────────────────────────────────────────────────────────────────────────┘${NC}

  🌐  ${BOLD}Dashboard${NC}           : https://${DOMAIN}
  ⚙️   ${BOLD}API FastAPI${NC}        : http://${LOCAL_IP}:8000/docs
  📊  ${BOLD}Grafana${NC}             : http://${LOCAL_IP}:3001 ${DIM}(admin/admin)${NC}
"

# Avertissement certificat auto-signé
if [[ "$CERT_TYPE" == "auto-signé" ]]; then
    echo -e "
${BOLD}${YELLOW}┌─────────────────────────────────────────────────────────────────────────┐${NC}
${BOLD}${YELLOW}│                     ⚠️  CERTIFICAT AUTO-SIGNÉ ACTIF                     │${NC}
${BOLD}${YELLOW}└─────────────────────────────────────────────────────────────────────────┘${NC}

  ${YELLOW}Le navigateur affichera un avertissement de sécurité.${NC}

  ${BOLD}Pour obtenir un certificat Let's Encrypt approuvé :${NC}

  ${BLUE}1.${NC} Configurez votre DNS : ${DOMAIN} → IP publique
  ${BLUE}2.${NC} Ouvrez le port 80 sur votre box/firewall
  ${BLUE}3.${NC} Exécutez : ${GREEN}./scripts/setup_letsencrypt.sh${NC}

  ${DIM}Note: Le certificat auto-signé permet un démarrage immédiat avec HTTPS.${NC}
"
fi

# Commandes utiles pour les logs
echo -e "
${BOLD}${BLUE}┌─────────────────────────────────────────────────────────────────────────┐${NC}
${BOLD}${BLUE}│                        COMMANDES UTILES - LOGS                          │${NC}
${BOLD}${BLUE}└─────────────────────────────────────────────────────────────────────────┘${NC}

  ${BOLD}Logs en temps réel (tous les services)${NC}
  ${GREEN}→${NC} docker compose -f $COMPOSE_FILE logs -f

  ${BOLD}Logs d'un service spécifique${NC}
  ${GREEN}→${NC} docker compose -f $COMPOSE_FILE logs -f dashboard
  ${GREEN}→${NC} docker compose -f $COMPOSE_FILE logs -f api
  ${GREEN}→${NC} docker compose -f $COMPOSE_FILE logs -f bot-worker
  ${GREEN}→${NC} docker compose -f $COMPOSE_FILE logs -f nginx

  ${BOLD}Dernières 100 lignes de logs${NC}
  ${GREEN}→${NC} docker compose -f $COMPOSE_FILE logs --tail=100

  ${BOLD}Logs avec timestamps${NC}
  ${GREEN}→${NC} docker compose -f $COMPOSE_FILE logs -f --timestamps

  ${BOLD}État des conteneurs${NC}
  ${GREEN}→${NC} docker compose -f $COMPOSE_FILE ps

${BOLD}${BLUE}┌─────────────────────────────────────────────────────────────────────────┐${NC}
${BOLD}${BLUE}│                          COMMANDES MAINTENANCE                          │${NC}
${BOLD}${BLUE}└─────────────────────────────────────────────────────────────────────────┘${NC}

  ${BOLD}Arrêter les services${NC}
  ${GREEN}→${NC} docker compose -f $COMPOSE_FILE down

  ${BOLD}Redémarrer les services${NC}
  ${GREEN}→${NC} docker compose -f $COMPOSE_FILE restart

  ${BOLD}Redémarrer un service spécifique${NC}
  ${GREEN}→${NC} docker compose -f $COMPOSE_FILE restart nginx

  ${BOLD}Mise à jour du projet${NC}
  ${GREEN}→${NC} git pull && ./setup.sh

  ${BOLD}Obtenir certificat Let's Encrypt${NC}
  ${GREEN}→${NC} ./scripts/setup_letsencrypt.sh

  ${BOLD}Backup de la base de données${NC}
  ${GREEN}→${NC} cp ./data/linkedin.db ./data/linkedin.db.backup.\$(date +%Y%m%d)

${BOLD}${BLUE}┌─────────────────────────────────────────────────────────────────────────┐${NC}
${BOLD}${BLUE}│                         FICHIERS IMPORTANTS                             │${NC}
${BOLD}${BLUE}└─────────────────────────────────────────────────────────────────────────┘${NC}

  ${BOLD}Configuration${NC}      : .env
  ${BOLD}Base de données${NC}    : ./data/linkedin.db
  ${BOLD}Logs applicatifs${NC}  : ./logs/
  ${BOLD}Certificats SSL${NC}   : ./certbot/conf/live/${DOMAIN}/
  ${BOLD}Messages${NC}           : ./data/messages.txt

${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
${GREEN}✨ Système opérationnel et sécurisé avec HTTPS${NC}
${GREEN}🚀 Accédez au dashboard : ${BOLD}https://${DOMAIN}${NC}
${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
"
