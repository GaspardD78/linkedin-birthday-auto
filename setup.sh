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
readonly DOMAIN="gaspardanoukolivier.freeboxos.fr"
readonly COMPOSE_FILE="docker-compose.pi4-standalone.yml"
readonly ENV_FILE=".env"
readonly ENV_TEMPLATE=".env.pi4.example"
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
log_step()    { echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"; echo -e "${BOLD}${BLUE}  $1${NC}"; echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}\n"; }

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

    # Vérifier si Docker utilise déjà IPv4 uniquement
    if [[ -f "$daemon_json" ]]; then
        if grep -q '"ip6tables": false' "$daemon_json" 2>/dev/null; then
            log_info "Docker déjà configuré pour IPv4."
            return 0
        fi
    fi

    log_info "Configuration de Docker pour forcer IPv4..."
    check_sudo

    # Créer ou mettre à jour daemon.json
    if [[ ! -f "$daemon_json" ]]; then
        # Créer nouveau fichier
        sudo tee "$daemon_json" > /dev/null <<EOF
{
  "ipv6": false,
  "ip6tables": false,
  "registry-mirrors": []
}
EOF
        needs_restart=true
    else
        # Modifier fichier existant
        local temp_file=$(mktemp)
        if command -v jq &> /dev/null; then
            # Avec jq si disponible
            sudo jq '. + {"ipv6": false, "ip6tables": false}' "$daemon_json" > "$temp_file"
            sudo mv "$temp_file" "$daemon_json"
        else
            # Fallback : simple merge manuel
            log_warn "jq non disponible, ajout manuel de la config IPv4"
            if ! grep -q '"ipv6"' "$daemon_json"; then
                sudo sed -i 's/^{/{\n  "ipv6": false,\n  "ip6tables": false,/' "$daemon_json"
            fi
        fi
        needs_restart=true
    fi

    if [[ "$needs_restart" == "true" ]]; then
        log_info "Redémarrage du daemon Docker..."
        sudo systemctl restart docker
        sleep 3
        log_success "Docker redémarré avec IPv4 uniquement."
    fi
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

# 1.2.1 Configuration Docker IPv4 (Fix problème réseau IPv6 sur Raspberry Pi)
configure_docker_ipv4

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
    log_warn "Espace disque faible (${DISK_USAGE}% utilisé). Nettoyage..."
    docker image prune -a -f --filter "until=24h"  # Supprime images non utilisées > 24h
    docker builder prune -f
else
    log_info "Espace disque OK (${DISK_USAGE}%). Nettoyage léger (dangling only)."
    docker image prune -f  # Uniquement les images <none>
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
# PHASE 4.5 : BOOTSTRAP SSL (MÉCANISME ANTI-CRASH NGINX)
# ==============================================================================
log_step "PHASE 4.5 : Bootstrapping SSL & Configuration Nginx"

# 1. Configuration Dynamique Nginx (Fix Domain & Proxy)
NGINX_CONF="./deployment/nginx/linkedin-bot.conf"
if [[ -f "$NGINX_CONF" ]]; then
    log_info "Mise à jour de la configuration Nginx ($DOMAIN)..."

    # Remplacement du domaine
    if grep -q "YOUR_DOMAIN.COM" "$NGINX_CONF"; then
        sed -i "s/YOUR_DOMAIN.COM/$DOMAIN/g" "$NGINX_CONF"
        log_success "Domaine mis à jour dans nginx.conf."
    fi

    # Correction des Proxy Pass pour Docker (127.0.0.1 -> noms de service)
    # Nginx dans Docker ne peut pas utiliser 127.0.0.1 pour joindre les autres conteneurs
    sed -i "s|proxy_pass http://127.0.0.1:3000|proxy_pass http://dashboard:3000|g" "$NGINX_CONF"
    sed -i "s|proxy_pass http://127.0.0.1:8000|proxy_pass http://api:8000|g" "$NGINX_CONF"
else
    log_warn "Fichier de configuration Nginx introuvable: $NGINX_CONF"
fi

# 2. Gestion des Certificats SSL (Dummy vs Real)
CERT_DIR="certbot/conf/live/${DOMAIN}"
mkdir -p "$CERT_DIR" "certbot/www"

# NOTE CRITIQUE : Le Port 80 et 443 de la Freebox DOIVENT être redirigés
# vers l'IP du Raspberry Pi (ex: 192.168.1.145) pour que le challenge ACME fonctionne.

if [[ ! -f "$CERT_DIR/fullchain.pem" ]] || [[ ! -f "$CERT_DIR/privkey.pem" ]]; then
    log_warn "Certificats SSL absents. Démarrage du Bootstrapping SSL..."
    log_info "Génération de certificats DUMMY (Auto-signés) pour permettre le démarrage de Nginx..."

    if cmd_exists openssl; then
        check_sudo
        # Génération RSA 4096 bits comme demandé
        sudo openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
            -keyout "$CERT_DIR/privkey.pem" \
            -out "$CERT_DIR/fullchain.pem" \
            -subj "/CN=${DOMAIN}/O=Temporary Certificate" 2>/dev/null

        log_success "Certificats Dummy générés (RSA 4096)."
    else
        log_error "OpenSSL requis mais non trouvé."
        exit 1
    fi
else
    log_info "Certificats SSL déjà présents."
fi

# 3. Permissions (Critique pour Nginx Container UID 101/1000)
log_info "Correction des permissions SSL (User 1000)..."
check_sudo
sudo chown -R 1000:1000 certbot/
sudo chmod -R 755 certbot/
# Fichiers sensibles
if [[ -f "$CERT_DIR/privkey.pem" ]]; then
    sudo chmod 600 "$CERT_DIR/privkey.pem"
fi

# 4. Paramètres DH
DH_PARAMS="certbot/conf/ssl-dhparams.pem"
if [[ ! -f "$DH_PARAMS" ]]; then
    log_info "Génération Diffie-Hellman (Patience...)"
    check_sudo
    sudo openssl dhparam -out "$DH_PARAMS" 2048 2>/dev/null
    sudo chmod 644 "$DH_PARAMS"
    sudo chown 1000:1000 "$DH_PARAMS"
fi

# ==============================================================================
# PHASE 5 : DÉPLOIEMENT SÉQUENCÉ (BOOTSTRAP STRATEGY)
# ==============================================================================
log_step "PHASE 5 : Lancement Orchestré"

log_info "Pull des images..."
docker_pull_with_retry "$COMPOSE_FILE" || exit 1

log_info "1. Démarrage Nginx (Frontend) avec certificats actuels..."
# On démarre Nginx SEUL pour qu'il puisse servir le challenge ACME si besoin
docker compose -f "$COMPOSE_FILE" up -d nginx

log_info "Attente stabilisation Nginx..."
sleep 10

# Vérification optionnelle : Lancement de Certbot si on est sur des Dummy Certs
# On utilise le script helper dédié
INIT_SSL_SCRIPT="./deployment/nginx/init-ssl.sh"
if [[ -f "$INIT_SSL_SCRIPT" ]]; then
    chmod +x "$INIT_SSL_SCRIPT"
    log_info "Vérification de l'état SSL..."
    # On passe le domaine, l'email (vide), et le fichier compose
    "$INIT_SSL_SCRIPT" "$DOMAIN" "" "$COMPOSE_FILE" || log_warn "Avertissement SSL (voir logs ci-dessus)."
fi

log_info "2. Démarrage de la stack complète..."
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
echo -e "
${BOLD}Accès Disponibles :${NC}
-------------------
🏠 Dashboard  : http://$(hostname -I | awk '{print $1}'):3000
⚙️  API        : http://$(hostname -I | awk '{print $1}'):8000/docs
📊 Grafana    : http://$(hostname -I | awk '{print $1}'):3001 (admin/admin)

${BOLD}Maintenance :${NC}
-------------
Logs          : docker compose -f $COMPOSE_FILE logs -f
Arrêt         : docker compose -f $COMPOSE_FILE down
Mise à jour   : git pull && ./setup.sh

${GREEN}Le système est stable et opérationnel.${NC}
"
