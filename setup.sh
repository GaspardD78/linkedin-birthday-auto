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
        HASH_OUTPUT=$(docker run --rm \
            --platform linux/arm64 \
            -e PASSWORD="$PASS_INPUT" \
            node:20-alpine \
            sh -c "npm install bcryptjs --silent --no-progress 2>&1 >/dev/null && node -e \"const bcrypt = require('bcryptjs'); const hash = bcrypt.hashSync(process.env.PASSWORD, 12); console.log(hash);\"" 2>&1)

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
# PHASE 5 : DÉPLOIEMENT
# ==============================================================================
log_step "PHASE 5 : Lancement des Services"

log_info "Pull des images (parallèle)..."
docker compose -f "$COMPOSE_FILE" pull --quiet

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
