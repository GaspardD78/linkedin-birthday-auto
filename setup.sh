#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - ULTIMATE SETUP SCRIPT v7.2                      ║
# ║  Installation, Sécurisation, Diagnostic et Réparation Automatisée        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# Configuration stricte
set -e
set -o pipefail

# Options CLI
AUTO_APPROVE=false
for arg in "$@"; do
    case $arg in
        -y|--yes|--auto)
            AUTO_APPROVE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [-y|--yes]"
            echo "  -y, --yes   Accepter automatiquement toutes les propositions (Swap, Passwords, etc.)"
            exit 0
            ;;
    esac
done

# ═══════════════════════════════════════════════════════════════════════════
# 0. CORE UTILITIES (Log & Error Handling)
# ═══════════════════════════════════════════════════════════════════════════

# Fichiers
LOG_FILE="setup_$(date +%Y%m%d_%H%M%S).log"
ENV_FILE=".env"
ENV_TEMPLATE=".env.pi4.example"
COMPOSE_FILE="docker-compose.pi4-standalone.yml"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Variable de commande Docker (pour gérer les perms dynamiquement)
DOCKER_CMD="docker"
DOCKER_COMPOSE_CMD="docker compose"

# Logger
log() {
    local level=$1
    local msg=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local color=$NC

    case $level in
        INFO) color=$CYAN ;;
        SUCCESS) color=$GREEN ;;
        WARN) color=$YELLOW ;;
        ERROR) color=$RED ;;
    esac

    # Affichage console
    echo -e "${color}[${timestamp}] [${level}] ${msg}${NC}"

    # Écriture fichier (sans codes couleur)
    echo "[${timestamp}] [${level}] ${msg}" >> "$LOG_FILE"
}

# Gestion d'erreur (Trap)
error_handler() {
    local line_no=$1
    local exit_code=$2
    if [ "$exit_code" -ne 0 ]; then
        echo ""
        log ERROR "💥 Échec critique à la ligne $line_no (Code: $exit_code)"
        log ERROR "Dernière commande échouée."
        log ERROR "Consultez le fichier de log : $LOG_FILE"
        echo -e "${YELLOW}Conseil : Essayez de relancer avec 'DEBUG=1 ./setup.sh'${NC}"
    fi
}
trap 'error_handler ${LINENO} $?' EXIT

# Helper pour input utilisateur
ask_confirmation() {
    local prompt=$1
    if [ "$AUTO_APPROVE" = true ]; then
        return 0
    fi
    # read retourne non-zero si EOF ou timeout, on protège avec || return 1
    read -p "$prompt (o/n) " -n 1 -r || return 1
    echo ""
    if [[ $REPLY =~ ^[OoYy]$ ]]; then
        return 0
    else
        return 1
    fi
}

# Spinner
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Helper Check Command
check_command() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        log ERROR "Commande requise introuvable : $cmd"
        return 1
    fi
    return 0
}

# Banner
clear
echo -e "${BLUE}${BOLD}"
cat << "EOF"
  _      _       _            _ _             ____        _
 | |    (_)     | |          | (_)           |  _ \      | |
 | |     _ _ __ | | _____  __| |_ _ __ ______| |_) | ___ | |_
 | |    | | '_ \| |/ / _ \/ _` | | '_ \______|  _ < / _ \| __|
 | |____| | | | |   <  __/ (_| | | | | |     | |_) | (_) | |_
 |______|_|_| |_|_|\_\___|\__,_|_|_| |_|     |____/ \___/ \__|

      🚀 ULTIMATE SETUP SCRIPT v7.2
EOF
echo -e "${NC}"
log INFO "Démarrage de l'installation..."
log INFO "Fichier de log : $LOG_FILE"
if [ "$AUTO_APPROVE" = true ]; then
    log INFO "Mode automatique activé (-y)."
fi

# ═══════════════════════════════════════════════════════════════════════════
# 1. PHASE AUTO-DEPENDENCIES (Auto-Fix)
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔍 PHASE 1 : Vérification & Installation des Dépendances"

ensure_dependency() {
    local cmd=$1
    local pkg=$2
    if ! command -v "$cmd" &> /dev/null; then
        log INFO "Installation de $pkg..."
        sudo apt-get update -qq
        sudo apt-get install -y "$pkg" || log WARN "Impossible d'installer $pkg automatiquement."
    else
        log INFO "$pkg est déjà installé."
    fi
}

# 1.1 Git, Jq, Python (Minimal System Deps)
ensure_dependency "git" "git"
ensure_dependency "jq" "jq"
ensure_dependency "python3" "python3"
ensure_dependency "curl" "curl"
ensure_dependency "openssl" "openssl" # Required for Phase 2

# 1.2 Docker Engine (Official Script)
if ! command -v docker &> /dev/null; then
    log INFO "Installation de Docker via script officiel..."
    curl -fsSL https://get.docker.com | sh
    log SUCCESS "Docker installé."
else
    log INFO "Docker est déjà installé."
fi

# 1.3 Docker Compose Plugin
if ! docker compose version &> /dev/null; then
    log INFO "Installation de Docker Compose Plugin..."
    sudo apt-get install -y docker-compose-plugin
    # Verification
    if ! docker compose version &> /dev/null; then
         log WARN "docker compose plugin introuvable, tentative d'installation via pip (fallback)..."
         sudo apt-get install -y python3-pip
         sudo pip3 install docker-compose
         DOCKER_COMPOSE_CMD="docker-compose"
    fi
else
    log INFO "Docker Compose Plugin est déjà installé."
fi

# 1.4 Permissions Docker
CURRENT_USER=${SUDO_USER:-$USER}
if ! groups "$CURRENT_USER" | grep -q "docker"; then
    log INFO "Ajout de l'utilisateur $CURRENT_USER au groupe docker..."
    sudo usermod -aG docker "$CURRENT_USER"
    log WARN "Groupe 'docker' ajouté. Utilisation temporaire de 'sudo docker' pour la session actuelle."
    DOCKER_CMD="sudo docker"
    DOCKER_COMPOSE_CMD="sudo docker compose"
else
    # Test d'accès socket
    if ! docker info &> /dev/null; then
        log WARN "L'utilisateur est dans le groupe mais le socket est inaccessible sans redémarrage."
        log INFO "Basculement sur 'sudo docker' pour cette exécution."
        DOCKER_CMD="sudo docker"
        DOCKER_COMPOSE_CMD="sudo docker compose"
    else
        log INFO "Permissions Docker OK."
    fi
fi

# Vérification finale accès Docker
if ! $DOCKER_CMD info &> /dev/null; then
    log ERROR "Impossible de contacter le démon Docker même avec sudo."
    exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════
# 1b. HARDWARE CHECKS
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔍 PHASE 1b : Vérifications Hardware"

# Swap Check
SWAP_TOTAL=$(free -m | awk '/^Swap:/{print $2}')
SWAP_TOTAL=${SWAP_TOTAL:-0}
log INFO "Mémoire Swap détectée : ${SWAP_TOTAL} MB"

if [ "$SWAP_TOTAL" -lt 2000 ]; then
    log WARN "Swap insuffisant (< 2GB). Next.js risque de crasher sur Pi4."
    if ask_confirmation "Voulez-vous augmenter le Swap à 2GB automatiquement ?"; then
        log INFO "Configuration du Swap..."

        # 1. Check/Install dphys-swapfile
        if ! command -v dphys-swapfile &> /dev/null; then
             log WARN "dphys-swapfile manquant. Tentative d'installation..."
             sudo apt-get update -qq && sudo apt-get install -y dphys-swapfile || true
        fi

        if command -v dphys-swapfile &> /dev/null; then
            # Méthode standard Raspbian
            log INFO "Utilisation de dphys-swapfile..."
            sudo dphys-swapfile swapoff 2>/dev/null || true
            sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile 2>/dev/null || \
            (echo "CONF_SWAPSIZE=2048" | sudo tee -a /etc/dphys-swapfile > /dev/null)
            sudo dphys-swapfile setup
            sudo dphys-swapfile swapon
            log SUCCESS "Swap augmenté à 2GB (via dphys-swapfile)."
        else
             # Fallback: Manual Swapfile (Ubuntu Server etc)
             log WARN "dphys-swapfile introuvable ou installation échouée. Utilisation du fallback."
             log INFO "Tentative de création manuelle (fallback)..."
             SWAPFILE="/swapfile"

             # Utilisation de fallocate ou dd si fallocate n'est pas dispo
             if (sudo fallocate -l 2G $SWAPFILE 2>/dev/null || sudo dd if=/dev/zero of=$SWAPFILE bs=1M count=2048); then
                 sudo chmod 600 $SWAPFILE
                 sudo mkswap $SWAPFILE
                 sudo swapon $SWAPFILE
                 # Persistance
                 if ! grep -q "$SWAPFILE" /etc/fstab; then
                     echo "$SWAPFILE none swap sw 0 0" | sudo tee -a /etc/fstab
                 fi
                 log SUCCESS "Swap augmenté à 2GB (via fallback manuel)."
             else
                 log ERROR "Échec de la création du swap (fallback inclus). Le script continue mais risque d'instabilité."
             fi
        fi
    fi
fi

# Network
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$LOCAL_IP" ]; then LOCAL_IP="127.0.0.1"; fi
log INFO "IP Locale détectée : ${LOCAL_IP}"

# ═══════════════════════════════════════════════════════════════════════════
# 2. PHASE SECURITY
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔒 PHASE 2 : Configuration Sécurité (.env)"

# Verification OpenSSL
check_command "openssl" || log WARN "OpenSSL manquant, la génération de clés sera limitée."

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_TEMPLATE" ]; then
        log INFO "Création de $ENV_FILE depuis $ENV_TEMPLATE..."
        cp "$ENV_TEMPLATE" "$ENV_FILE" || { log ERROR "Impossible de copier $ENV_TEMPLATE vers $ENV_FILE"; exit 1; }
        sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000|g" "$ENV_FILE"
        sed -i "s|NEXT_PUBLIC_DASHBOARD_URL=.*|NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000|g" "$ENV_FILE"
        log SUCCESS ".env créé depuis template."
    else
        log WARN "Template $ENV_TEMPLATE absent. Création .env minimal."
        {
            echo "NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000"
            echo "NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000"
            echo "API_KEY=internal_secret_key"
            echo "JWT_SECRET=secret"
            echo "DASHBOARD_PASSWORD=admin"
        } > "$ENV_FILE" || { log ERROR "Impossible d'écrire dans $ENV_FILE"; exit 1; }
    fi
else
    # Check IP match
    CURRENT_API_URL=$(grep "NEXT_PUBLIC_API_URL" "$ENV_FILE" | cut -d'=' -f2 || echo "")
    if [[ -n "$CURRENT_API_URL" && "$CURRENT_API_URL" != *"$LOCAL_IP"* && "$CURRENT_API_URL" != *"localhost"* && "$CURRENT_API_URL" != *"127.0.0.1"* ]]; then
        log WARN "NEXT_PUBLIC_API_URL ($CURRENT_API_URL) diffère de IP locale ($LOCAL_IP)."
    fi
fi

# Permissions .env
chmod 600 "$ENV_FILE" 2>/dev/null || true

# Password Check
DASHBOARD_PASS=$(grep "DASHBOARD_PASSWORD" "$ENV_FILE" | cut -d'=' -f2 || echo "")
if [[ -z "$DASHBOARD_PASS" || "$DASHBOARD_PASS" == "change_me" || "$DASHBOARD_PASS" == "admin" || ${#DASHBOARD_PASS} -lt 8 ]]; then
    if ask_confirmation "Mot de passe faible ou manquant. Générer un mot de passe fort ?"; then
        if command -v openssl &>/dev/null; then
            NEW_PASS=$(openssl rand -base64 12)
            ESCAPED_PASS=$(printf '%s\n' "$NEW_PASS" | sed -e 's/[\/&]/\\&/g')

            if grep -q "DASHBOARD_PASSWORD" "$ENV_FILE"; then
                sed -i "s/^DASHBOARD_PASSWORD=.*/DASHBOARD_PASSWORD=$ESCAPED_PASS/" "$ENV_FILE"
            else
                echo "DASHBOARD_PASSWORD=$ESCAPED_PASS" >> "$ENV_FILE"
            fi
            log SUCCESS "Nouveau mot de passe généré : $NEW_PASS"
        else
            log ERROR "Impossible de générer un mot de passe (openssl manquant)."
        fi
    fi
fi

# API Key Check
API_KEY=$(grep "API_KEY" "$ENV_FILE" | cut -d'=' -f2 || echo "")
if [[ "$API_KEY" == "internal_secret_key" || -z "$API_KEY" ]]; then
    if command -v openssl &>/dev/null; then
        NEW_KEY=$(openssl rand -hex 32)

        if grep -q "API_KEY" "$ENV_FILE"; then
            sed -i "s/^API_KEY=.*/API_KEY=$NEW_KEY/" "$ENV_FILE"
        else
            echo "API_KEY=$NEW_KEY" >> "$ENV_FILE"
        fi

        if grep -q "BOT_API_KEY" "$ENV_FILE"; then
            sed -i "s/^BOT_API_KEY=.*/BOT_API_KEY=$NEW_KEY/" "$ENV_FILE"
        else
            echo "BOT_API_KEY=$NEW_KEY" >> "$ENV_FILE"
        fi
        log SUCCESS "Clés API régénérées."
    else
         log ERROR "Impossible de générer API KEY (openssl manquant)."
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# 3. PHASE PREPARE DIRS
# ═══════════════════════════════════════════════════════════════════════════
log INFO "📂 PHASE 3 : Préparation des dossiers"

mkdir -p data logs config
if command -v sudo &>/dev/null; then
    sudo chown -R $(id -u):$(id -g) data logs config 2>/dev/null || true
fi
log SUCCESS "Dossiers prêts."

# ═══════════════════════════════════════════════════════════════════════════
# 4. PHASE PULL IMAGES (Sequential for Pi4 Stability)
# ═══════════════════════════════════════════════════════════════════════════
log INFO "⬇️ PHASE 4 : Téléchargement des images (Mode Séquentiel)"

if [ ! -f "$COMPOSE_FILE" ]; then
    log ERROR "$COMPOSE_FILE introuvable."
    exit 1
fi

# Récupération de la liste des services
log INFO "Analyse du docker-compose..."
SERVICES=$($DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" config --services 2>/dev/null || echo "")

if [ -z "$SERVICES" ]; then
    log WARN "Impossible de lister les services via 'config'. Fallback vers pull global."
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" pull >> "$LOG_FILE" 2>&1 || { log ERROR "Échec du pull global"; exit 1; }
else
    for service in $SERVICES; do
        log INFO "⬇️ Téléchargement image pour : $service..."
        $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" pull "$service" >> "$LOG_FILE" 2>&1 || { log ERROR "Échec du pull pour $service"; exit 1; }
    done
fi
log SUCCESS "Toutes les images ont été téléchargées."

# ═══════════════════════════════════════════════════════════════════════════
# 5. PHASE START SERVICES
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🚀 PHASE 5 : Démarrage des services"

$DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d --remove-orphans
log SUCCESS "Conteneurs lancés."

# Wait for API Healthy
log INFO "Attente du service API (Healthy)..."
MAX_RETRIES=30
COUNT=0
API_HEALTHY=false

while [ $COUNT -lt $MAX_RETRIES ]; do
    STATUS=$($DOCKER_CMD inspect --format='{{.State.Health.Status}}' bot-api 2>/dev/null || echo "starting")
    if [ "$STATUS" == "healthy" ]; then
        API_HEALTHY=true
        break
    fi
    echo -n "."
    sleep 5
    COUNT=$((COUNT+1))
done
echo ""

if [ "$API_HEALTHY" = false ]; then
    log ERROR "Service bot-api non healthy après 150s."
    $DOCKER_CMD logs bot-api --tail 20
    exit 1
fi
log SUCCESS "API est Healthy."

# ═══════════════════════════════════════════════════════════════════════════
# 5a. PHASE DB INIT
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🗄️ PHASE 5a : Initialisation de la Base de Données"

# On utilise exec sur le conteneur API qui a le code et l'accès au volume
# Attente active du conteneur
log INFO "Attente que le conteneur bot-api soit prêt..."
MAX_API_WAIT=30
for i in $(seq 1 $MAX_API_WAIT); do
    if [ "$($DOCKER_CMD inspect -f '{{.State.Status}}' bot-api 2>/dev/null)" == "running" ]; then
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

# Verification sommaire du script
if ! $DOCKER_CMD exec bot-api test -f /app/src/scripts/init_db.py; then
    log WARN "Script src/scripts/init_db.py introuvable dans le conteneur bot-api."
fi

log INFO "Exécution du script d'initialisation DB..."
set +e
INIT_OUTPUT=$($DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T bot-api python -m src.scripts.init_db 2>&1)
INIT_EXIT_CODE=$?
set -e

if [ $INIT_EXIT_CODE -eq 0 ]; then
    log SUCCESS "Tables de base de données créées/vérifiées avec succès."
    echo "$INIT_OUTPUT" >> "$LOG_FILE"
else
    log ERROR "Échec de l'initialisation de la DB."
    log ERROR "Sortie de la commande :"
    echo "$INIT_OUTPUT" | tee -a "$LOG_FILE"
fi

# ═══════════════════════════════════════════════════════════════════════════
# 5b. PHASE IMPORT DATA (Messages)
# ═══════════════════════════════════════════════════════════════════════════
log INFO "📦 PHASE 5b : Importation des messages"

# Import messages.txt
if [ -f "./messages.txt" ]; then
    log INFO "Injection de messages.txt vers bot-api..."
    $DOCKER_CMD cp ./messages.txt bot-api:/app/data/messages.txt || log WARN "Échec copie messages.txt"
else
    log WARN "messages.txt non trouvé à la racine."
fi

# Import late_messages.txt
if [ -f "./late_messages.txt" ]; then
    log INFO "Injection de late_messages.txt vers bot-api..."
    $DOCKER_CMD cp ./late_messages.txt bot-api:/app/data/late_messages.txt || log WARN "Échec copie late_messages.txt"
else
    log WARN "late_messages.txt non trouvé à la racine."
fi

# Fix permissions inside container
log INFO "Application des permissions dans le conteneur..."
$DOCKER_CMD exec -u root bot-api chown -R 1000:1000 /app/data || true
log SUCCESS "Données importées."

# ═══════════════════════════════════════════════════════════════════════════
# 6. PHASE VALIDATION (The Doctor)
# ═══════════════════════════════════════════════════════════════════════════
log INFO "👨‍⚕️ PHASE 6 : Validation Finale"

SERVICES=("redis-bot" "redis-dashboard" "bot-api" "bot-worker" "dashboard")
for svc in "${SERVICES[@]}"; do
    STATE=$($DOCKER_CMD inspect --format='{{.State.Status}}' $svc 2>/dev/null || echo "missing")
    HEALTH=$($DOCKER_CMD inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' $svc 2>/dev/null)

    if [[ "$STATE" == "running" && ("$HEALTH" == "healthy" || "$HEALTH" == "no_healthcheck") ]]; then
        log SUCCESS "Service $svc : OK"
    else
        log ERROR "Service $svc : $STATE / $HEALTH"
    fi
done

# Endpoints
HTTP_CODE_API=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
if [ "$HTTP_CODE_API" == "200" ]; then
    log SUCCESS "API Endpoint : OK (200)"
else
    log ERROR "API Endpoint inaccessible (Code: $HTTP_CODE_API)."
    log INFO "Derniers logs bot-api :"
    $DOCKER_CMD logs bot-api --tail 20 | tee -a "$LOG_FILE"
fi

HTTP_CODE_DASH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "000")
if [[ "$HTTP_CODE_DASH" == "200" || "$HTTP_CODE_DASH" == "307" || "$HTTP_CODE_DASH" == "308" ]]; then
    log SUCCESS "Dashboard Endpoint : OK ($HTTP_CODE_DASH)"
else
    log WARN "Dashboard inaccessible (Code: $HTTP_CODE_DASH)."
    log INFO "Derniers logs dashboard :"
    $DOCKER_CMD logs dashboard --tail 50 | tee -a "$LOG_FILE"
fi

# ═══════════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ═══════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║           INSTALLATION TERMINÉE AVEC SUCCÈS !                ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "   🌐  ${BOLD}Accès Local :${NC}     http://localhost:3000"
echo -e "   🌍  ${BOLD}Accès Réseau :${NC}    http://${LOCAL_IP}:3000"
echo -e "   🔧  ${BOLD}API Backend :${NC}     http://${LOCAL_IP}:8000"
echo ""
echo -e "   📂  ${BOLD}Logs Setup :${NC}      $LOG_FILE"
echo ""
echo -e "${CYAN}Commande Docker utilisée pour cette session :${NC} $DOCKER_CMD"
echo -e "${CYAN}Si vous venez d'être ajouté au groupe docker, relancez votre session (logout/login).${NC}"
echo ""
exit 0
