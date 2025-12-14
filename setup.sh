#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - ULTIMATE SETUP SCRIPT v7.0                      ║
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

      🚀 ULTIMATE SETUP SCRIPT v7.0
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
        sudo apt-get install -y "$pkg"
    else
        log INFO "$pkg est déjà installé."
    fi
}

# 1.1 Git, Jq, Python (Minimal System Deps)
ensure_dependency "git" "git"
ensure_dependency "jq" "jq"
ensure_dependency "python3" "python3"
ensure_dependency "curl" "curl"

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
        if command -v dphys-swapfile &> /dev/null; then
            sudo dphys-swapfile swapoff 2>/dev/null || true
            sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile 2>/dev/null || \
            (echo "CONF_SWAPSIZE=2048" | sudo tee -a /etc/dphys-swapfile > /dev/null)
            sudo dphys-swapfile setup
            sudo dphys-swapfile swapon
            log SUCCESS "Swap augmenté à 2GB."
        else
             log WARN "dphys-swapfile non trouvé."
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

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_TEMPLATE" ]; then
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000|g" "$ENV_FILE"
        sed -i "s|NEXT_PUBLIC_DASHBOARD_URL=.*|NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000|g" "$ENV_FILE"
        log SUCCESS ".env créé depuis template."
    else
        log WARN "Template absent. Création .env minimal."
        echo "NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000" > "$ENV_FILE"
        echo "NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000" >> "$ENV_FILE"
        echo "API_KEY=internal_secret_key" >> "$ENV_FILE"
        echo "JWT_SECRET=secret" >> "$ENV_FILE"
        echo "DASHBOARD_PASSWORD=admin" >> "$ENV_FILE"
    fi
else
    # Check IP match
    CURRENT_API_URL=$(grep "NEXT_PUBLIC_API_URL" "$ENV_FILE" | cut -d'=' -f2)
    if [[ "$CURRENT_API_URL" != *"$LOCAL_IP"* && "$CURRENT_API_URL" != *"localhost"* && "$CURRENT_API_URL" != *"127.0.0.1"* ]]; then
        log WARN "NEXT_PUBLIC_API_URL ($CURRENT_API_URL) diffère de IP locale ($LOCAL_IP)."
    fi
fi

# Permissions .env
chmod 600 "$ENV_FILE" 2>/dev/null || true

# Password Check
DASHBOARD_PASS=$(grep "DASHBOARD_PASSWORD" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$DASHBOARD_PASS" == "change_me" || "$DASHBOARD_PASS" == "admin" || ${#DASHBOARD_PASS} -lt 8 ]]; then
    if ask_confirmation "Mot de passe faible détecté. Générer un mot de passe fort ?"; then
        NEW_PASS=$(openssl rand -base64 12)
        ESCAPED_PASS=$(printf '%s\n' "$NEW_PASS" | sed -e 's/[\/&]/\\&/g')
        sed -i "s/^DASHBOARD_PASSWORD=.*/DASHBOARD_PASSWORD=$ESCAPED_PASS/" "$ENV_FILE"
        log SUCCESS "Nouveau mot de passe généré : $NEW_PASS"
    fi
fi

# API Key Check
API_KEY=$(grep "API_KEY" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$API_KEY" == "internal_secret_key" || -z "$API_KEY" ]]; then
    NEW_KEY=$(openssl rand -hex 32)
    sed -i "s/^API_KEY=.*/API_KEY=$NEW_KEY/" "$ENV_FILE"
    sed -i "s/^BOT_API_KEY=.*/BOT_API_KEY=$NEW_KEY/" "$ENV_FILE"
    log SUCCESS "Clés API régénérées."
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
# 4. PHASE PULL IMAGES
# ═══════════════════════════════════════════════════════════════════════════
log INFO "⬇️ PHASE 4 : Téléchargement des images"

if [ ! -f "$COMPOSE_FILE" ]; then
    log ERROR "$COMPOSE_FILE introuvable."
    exit 1
fi

$DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" pull --quiet &
spinner $!
log SUCCESS "Images téléchargées."

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
# On ignore l'erreur si le script n'existe pas encore dans l'image
log INFO "Exécution du script d'initialisation DB..."
if $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" exec -T bot-api python -m src.scripts.init_db; then
    log SUCCESS "Tables de base de données créées/vérifiées avec succès."
else
    log WARN "Échec de l'initialisation de la DB via le conteneur."
    log WARN "Le conteneur est peut-être inaccessible ou le script est manquant."
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
if curl -s -f http://localhost:8000/health >/dev/null; then
    log SUCCESS "API Endpoint : OK"
else
    log ERROR "API Endpoint inaccessible."
fi

if curl -s -I http://localhost:3000 >/dev/null; then
    log SUCCESS "Dashboard Endpoint : OK"
else
    log WARN "Dashboard démarre encore (Next.js build)."
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
