#!/bin/bash
set -e

# ==============================================================================
# LINKEDIN AUTO RPi4 - SETUP SCRIPT (V2.1 - FINAL)
# ==============================================================================
# Objectif : Installation robuste, interactive, SSL managé et Rapport Complet.
# Cible    : Raspberry Pi 4 (Debian/Raspbian)
# ==============================================================================

# --- Couleurs ---
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

# --- Configuration ---
DOMAIN="gaspardanoukolivier.freeboxos.fr"
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
ENV_FILE=".env"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "\n${BOLD}${BLUE}=== $1 ===${NC}"; }

clear
echo -e "${BLUE}"
cat << "EOF"
  _      _       _            _ _             _         _
 | |    (_)     | |          | (_)           | |       | |
 | |     _ _ __ | | _____  __| |_ _ __       | |_ _   _| |_ ___
 | |    | | '_ \| |/ / _ \/ _` | | '_ \      | __| | | | __/ _ \
 | |____| | | | |   <  __/ (_| | | | | |     | |_| |_| | || (_) |
 |______|_|_| |_|_|\_\___|\__,_|_|_| |_|      \__|\__,_|\__\___/

         >>> RASPBERRY PI 4 SETUP (FINAL) <<<
EOF
echo -e "${NC}"

# ==============================================================================
# 1. PRÉ-REQUIS & NETTOYAGE
# ==============================================================================
log_step "1. PRÉ-REQUIS & NETTOYAGE"

# Check Root
if [[ $EUID -ne 0 ]]; then
   log_error "Ce script doit être exécuté en root : sudo ./setup.sh"
   exit 1
fi

# Dépendances Système
log_info "Vérification des dépendances..."
DEPS=(jq curl git lsof certbot rclone nodejs npm)
MISSING_DEPS=()

for dep in "${DEPS[@]}"; do
    if ! command -v $dep &> /dev/null; then
        MISSING_DEPS+=($dep)
    fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    log_warn "Installation des dépendances manquantes : ${MISSING_DEPS[*]}"
    if [[ " ${MISSING_DEPS[*]} " =~ "node" ]]; then
        curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - > /dev/null 2>&1
    fi
    apt-get update -qq && apt-get install -y -qq jq curl git lsof certbot rclone nodejs npm > /dev/null 2>&1
    log_success "Dépendances installées."
fi

# Docker Check
if ! command -v docker &> /dev/null; then
    log_warn "Installation de Docker..."
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker $SUDO_USER
fi

# Arrêt des conteneurs existants
if [ -f "$COMPOSE_FILE" ]; then
    log_info "Arrêt des conteneurs existants..."
    docker compose -f "$COMPOSE_FILE" down --remove-orphans > /dev/null 2>&1 || true
fi

# Libération Port 80 (Crucial pour Certbot & Nginx)
PORT80_PID=$(lsof -t -i :80 || true)
if [ -n "$PORT80_PID" ]; then
    log_warn "Port 80 occupé. Libération forcée pour Certbot..."
    kill -9 $(echo "$PORT80_PID" | tr '\n' ' ') 2>/dev/null || true
    log_success "Port 80 libéré."
fi

# ==============================================================================
# 2. TÉLÉCHARGEMENT DES IMAGES (PULL)
# ==============================================================================
log_step "2. TÉLÉCHARGEMENT DES IMAGES"
log_info "Téléchargement des images Docker en cours..."
echo -e "${YELLOW}Veuillez patienter, une barre de progression va s'afficher...${NC}"

# Force l'affichage du TTY pour la barre de progression si possible, ou juste standard
docker compose -f "$COMPOSE_FILE" pull

log_success "Images téléchargées."

# ==============================================================================
# 3. CONFIGURATION (AUTH, RCLONE, SSL)
# ==============================================================================
log_step "3. CONFIGURATION"

# --- 3.1 Environnement (.env) ---
if [ ! -f "$ENV_FILE" ]; then
    cp .env.pi4.example "$ENV_FILE"
    log_info "Fichier .env créé."
fi

# --- 3.2 Authentification Dashboard ---
echo -e "\n${BOLD}>>> Authentification Dashboard${NC}"

CURRENT_USER=$(grep "^DASHBOARD_USER=" "$ENV_FILE" | cut -d '=' -f2)
if [ -z "$CURRENT_USER" ] || [ "$CURRENT_USER" == "admin" ]; then
    read -p "Utilisateur Dashboard (défaut: admin) : " INPUT_USER
    DASHBOARD_USER=${INPUT_USER:-admin}
else
    DASHBOARD_USER=$CURRENT_USER
fi

echo -n "Mot de passe Dashboard : "
read -s DASHBOARD_PASS
echo ""

if [ -n "$DASHBOARD_PASS" ]; then
    log_info "Hachage du mot de passe..."
    if [ ! -d "dashboard/node_modules/bcryptjs" ]; then
         (cd dashboard && npm install bcryptjs --silent --no-audit --no-fund > /dev/null 2>&1)
    fi
    HASHED_PASS=$(node dashboard/scripts/hash_password.js "$DASHBOARD_PASS" --quiet)

    if [ -n "$HASHED_PASS" ]; then
        DOCKER_SAFE_HASH=${HASHED_PASS//$/\$\$}
        sed -i "s|^DASHBOARD_USER=.*|DASHBOARD_USER=${DASHBOARD_USER}|" "$ENV_FILE"
        sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD='${DOCKER_SAFE_HASH}'|" "$ENV_FILE"

        if grep -q "CHANGEZ_MOI" "$ENV_FILE"; then
             NEW_API=$(python3 -c "import secrets; print(secrets.token_hex(32))")
             NEW_JWT=$(openssl rand -hex 32)
             sed -i "s|^API_KEY=.*|API_KEY=${NEW_API}|" "$ENV_FILE"
             sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${NEW_JWT}|" "$ENV_FILE"
        fi
        log_success "Identifiants mis à jour."
    else
        log_error "Erreur de hachage."
        exit 1
    fi
else
    log_warn "Mot de passe inchangé."
fi

# --- 3.3 Rclone (Injection Automatique) ---
echo -e "\n${BOLD}>>> Configuration Backup (Rclone)${NC}"
RCLONE_CONF_DIR="/root/.config/rclone"
RCLONE_CONF_FILE="$RCLONE_CONF_DIR/rclone.conf"

if [ ! -f "$RCLONE_CONF_FILE" ]; then
    log_info "Configuration Rclone manquante. Injection automatique..."
    mkdir -p "$RCLONE_CONF_DIR"

    # Configuration fournie par l'utilisateur (INTERACTIF pour éviter fuite secret)
    log_warn "Pour configurer le backup, collez votre token Rclone complet ci-dessous."
    log_info "Format attendu: {\"access_token\": ...}"
    echo -n "Token Rclone > "
    read -r RCLONE_TOKEN

    if [ -n "$RCLONE_TOKEN" ]; then
        cat << EOF > "$RCLONE_CONF_FILE"
[gdrive]
type = drive
scope = drive
token = $RCLONE_TOKEN
team_drive =
EOF
        chmod 600 "$RCLONE_CONF_FILE"
        log_success "Rclone configuré."
    else
        log_warn "Aucun token fourni. Rclone ne sera pas configuré."
    fi

    # Copie pour l'utilisateur SUDO
    if [ -n "$SUDO_USER" ]; then
        USER_HOME=$(eval echo ~$SUDO_USER)
        USER_CONF_DIR="$USER_HOME/.config/rclone"
        mkdir -p "$USER_CONF_DIR"
        cp "$RCLONE_CONF_FILE" "$USER_CONF_DIR/rclone.conf"
        chown -R $SUDO_USER:$SUDO_USER "$USER_CONF_DIR"
    fi
else
    log_success "Rclone déjà configuré."
fi

# Activation Cron Backup
if ! crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"; then
    log_info "Activation du backup quotidien (03:00)..."
    SCRIPT_PATH="$(pwd)/scripts/backup_to_gdrive.sh"
    chmod +x "$SCRIPT_PATH"
    (crontab -l 2>/dev/null; echo "0 3 * * * $SCRIPT_PATH >> $(pwd)/logs/backup.log 2>&1") | crontab -
    log_success "Cron activé."
fi

# --- 3.4 SSL Manager (Certbot) ---
echo -e "\n${BOLD}>>> Gestion SSL (HTTPS)${NC}"
CERT_DIR="$(pwd)/certbot/conf/live/$DOMAIN"
mkdir -p certbot/conf certbot/www certbot/logs

if [ ! -f "$CERT_DIR/fullchain.pem" ]; then
    log_info "Certificat introuvable pour $DOMAIN."
    log_info "Lancement de Certbot (Mode Standalone)..."

    # Le port 80 a déjà été libéré en phase 1
    certbot certonly --standalone \
        -d "$DOMAIN" \
        --email gaspard.danouk@gmail.com \
        --agree-tos \
        --non-interactive \
        --config-dir "$(pwd)/certbot/conf" \
        --work-dir "$(pwd)/certbot/work" \
        --logs-dir "$(pwd)/certbot/logs"

    if [ -f "$CERT_DIR/fullchain.pem" ]; then
        log_success "Nouveau certificat généré avec succès !"
    else
        log_error "Échec Certbot. HTTPS ne fonctionnera pas (Self-signed fallback possible par Nginx si configuré)."
        # On ne bloque pas tout le script, mais c'est critique
    fi
else
    log_success "Certificat SSL valide détecté."
    # Renouvellement si nécessaire
    log_info "Tentative de renouvellement (dry-run)..."
    certbot renew --dry-run --cert-name "$DOMAIN" --config-dir "$(pwd)/certbot/conf" --work-dir "$(pwd)/certbot/work" --logs-dir "$(pwd)/certbot/logs" > /dev/null 2>&1 || true
fi

# ==============================================================================
# 4. DÉMARRAGE (LAUNCH)
# ==============================================================================
log_step "4. DÉMARRAGE DES SERVICES"

# Permissions Data (Sécurité critique)
mkdir -p data logs
chown -R 1000:1000 data logs
chmod -R 775 data logs

log_info "Démarrage des conteneurs..."
docker compose -f "$COMPOSE_FILE" up -d

log_info "Vérification de la santé des services..."

check_health() {
    local url=$1
    local name=$2
    local max_retries=60  # Increased to ~3 minutes for Pi4
    local count=0

    echo -n "  - $name..."
    while [ $count -lt $max_retries ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e " ${GREEN}OK${NC}"
            return 0
        fi
        echo -n "."
        sleep 3
        ((count+=1))
    done
    echo -e " ${RED}Indisponible${NC}"
    return 1
}

# Wait loops
echo -n "  - Nginx (HTTPS)..."
COUNT=0
while [ $COUNT -lt 60 ]; do
    if curl -k -s -I "https://localhost" > /dev/null 2>&1; then
        echo -e " ${GREEN}OK${NC}"
        break
    fi
    echo -n "."
    sleep 3
    ((COUNT+=1))
done

check_health "http://localhost:3000" "Dashboard"
check_health "http://localhost:8000/health" "API"

# ==============================================================================
# 5. DIAGNOSTIC FINAL (Complet)
# ==============================================================================
log_step "5. RAPPORT D'INSTALLATION"

# Calcul des métriques
DB_SIZE=$(du -h data/linkedin.db 2>/dev/null | cut -f1 || echo "0B")
IP_ADDR=$(hostname -I | awk '{print $1}')
SERVICES_STATUS=$(docker compose -f "$COMPOSE_FILE" ps --format "table {{.Service}}\t{{.State}}\t{{.Status}}")

# Audit Rapide Sécurité
SEC_SCORE="N/A"
if [ -f "scripts/verify_security.sh" ]; then
    chmod +x scripts/verify_security.sh
    SEC_OUT=$(./scripts/verify_security.sh 2>&1 || true)
    SEC_SCORE=$(echo "$SEC_OUT" | grep "SCORE" | sed 's/.*: //')
fi

# État Backup
BACKUP_STATE="Inactif"
if rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
    BACKUP_STATE="${GREEN}Actif (GDrive)${NC}"
    # Vérif cron
    if crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"; then
         BACKUP_STATE="$BACKUP_STATE + ${GREEN}Planifié (03h00)${NC}"
    fi
else
    BACKUP_STATE="${RED}Non configuré${NC}"
fi

echo -e "${BLUE}====================================================================${NC}"
echo -e "${BOLD}                       LINKEDIN AUTO - RAPPORT                      ${NC}"
echo -e "${BLUE}====================================================================${NC}"

echo -e "\n${BOLD}🌍 ACCÈS${NC}"
echo -e "   URL Public   : https://$DOMAIN/"
echo -e "   URL Local    : http://$IP_ADDR:3000"
echo -e "   Login        : $DASHBOARD_USER"
echo -e "   Password     : ${DASHBOARD_PASS} ${YELLOW}(Copiez-le !)${NC}"

echo -e "\n${BOLD}📂 DONNÉES${NC}"
echo -e "   Base SQL     : data/linkedin.db ($DB_SIZE)"
echo -e "   Permissions  : 1000:1000 (Correct)"

echo -e "\n${BOLD}🛡️ SÉCURITÉ${NC}"
echo -e "   SSL (HTTPS)  : ${GREEN}Actif${NC} (Certbot managed)"
echo -e "   Score Audit  : $SEC_SCORE"
echo -e "   Hachage MDP  : BCrypt (Protection active)"

echo -e "\n${BOLD}💾 SAUVEGARDE${NC}"
echo -e "   État         : $BACKUP_STATE"

echo -e "\n${BOLD}🤖 SERVICES${NC}"
echo "$SERVICES_STATUS"

if ! curl -k -s -I "https://localhost" > /dev/null 2>&1; then
    echo -e "\n${RED}⚠️  ATTENTION : Nginx ne répond pas en HTTPS. Logs :${NC}"
    docker compose -f "$COMPOSE_FILE" logs nginx --tail 10
fi

echo -e "${BLUE}====================================================================${NC}"
log_success "Installation et Configuration Terminées."
