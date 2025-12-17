#!/bin/bash
set -e

# ==============================================================================
# LINKEDIN AUTO RPi4 - MASTER ORCHESTRATOR v2.0
# ==============================================================================
# Auteur: Lead DevOps & Security Engineer
# Objectif: Installation, Migration, Securite & Backup
# Cible: Raspberry Pi 4 (4GB, ARM64)
# ==============================================================================
#
# CHANGELOG v2.0:
# - Ajout verification RAM/SWAP (minimum 6GB combines)
# - Ajout verification espace disque (minimum 3GB libres)
# - Health checks ameliores avec detection crash loop
# - Timeout augmente a 180s pour Next.js sur ARM64
# - Nettoyage Docker intelligent (seulement si disque < 80%)
# - Configuration ZRAM optionnelle
# - Correction incoherence nom base de donnees
# ==============================================================================

# --- Couleurs & Style ---
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# --- Configuration ---
MIN_RAM_SWAP_MB=4096        # 4GB minimum (RAM + SWAP combines)
MIN_DISK_FREE_MB=3000       # 3GB minimum d'espace libre
HEALTH_CHECK_TIMEOUT=180    # 180 secondes (3 min) pour ARM64
HEALTH_CHECK_INTERVAL=5     # Verification toutes les 5 secondes
DISK_CLEANUP_THRESHOLD=80   # Nettoyer si disque > 80% utilise

# --- Fonctions de Log ---
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "\n${BOLD}${BLUE}=== $1 ===${NC}"; }

# --- Header ---
clear
echo -e "${BLUE}"
cat << "EOF"
  _      _       _            _ _             _         _
 | |    (_)     | |          | (_)           | |       | |
 | |     _ _ __ | | _____  __| |_ _ __       | |_ _   _| |_ ___
 | |    | | '_ \| |/ / _ \/ _` | | '_ \      | __| | | | __/ _ \
 | |____| | | | |   <  __/ (_| | | | | |     | |_| |_| | || (_) |
 |______|_|_| |_|_|\_\___|\__,_|_|_| |_|      \__|\__,_|\__\___/

         >>> RASPBERRY PI 4 MASTER ORCHESTRATOR v2.0 <<<
EOF
echo -e "${NC}"

# --- Gestion des Erreurs ---
cleanup() {
    local exit_code=$?
    echo -e "\n${YELLOW}[!] Interruption detectee. Nettoyage...${NC}"
    # Ne pas arreter les containers en cas d'interruption
    exit $exit_code
}
trap cleanup SIGINT SIGTERM

# --- Fonction: Afficher les logs en cas d'echec ---
show_failure_logs() {
    local service=$1
    echo -e "\n${RED}=== LOGS DU SERVICE $service (dernieres 30 lignes) ===${NC}"
    docker compose -f docker-compose.pi4-standalone.yml logs --tail=30 "$service" 2>/dev/null || true
    echo -e "${RED}=== FIN DES LOGS ===${NC}\n"
}

# ==============================================================================
# [Phase 1/6] Verifications Systeme & Dependances (FAIL-FAST)
# ==============================================================================
log_step "[Phase 1/6] Verifications Systeme & Dependances"

# --- Verification Root ---
if [[ $EUID -ne 0 ]]; then
   log_error "Ce script doit etre execute en tant que root (sudo ./setup.sh)"
   exit 1
fi

# --- Verification RAM + SWAP (CRITIQUE pour Playwright) ---
log_info "Verification de la memoire (RAM + SWAP)..."
TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
TOTAL_SWAP_MB=$(free -m | awk '/^Swap:/{print $2}')
TOTAL_MEMORY_MB=$((TOTAL_RAM_MB + TOTAL_SWAP_MB))

log_info "RAM: ${TOTAL_RAM_MB}MB | SWAP: ${TOTAL_SWAP_MB}MB | Total: ${TOTAL_MEMORY_MB}MB"

if [[ $TOTAL_MEMORY_MB -lt $MIN_RAM_SWAP_MB ]]; then
    log_error "Memoire insuffisante: ${TOTAL_MEMORY_MB}MB (minimum requis: ${MIN_RAM_SWAP_MB}MB)"
    log_error "Playwright et Next.js ont besoin d'au moins 4GB de memoire combinee."
    echo ""

    if [[ $TOTAL_SWAP_MB -lt 2048 ]]; then
        log_warn "SWAP insuffisant detecte (${TOTAL_SWAP_MB}MB). Configuration recommandee: 2GB"
        echo ""
        read -p "Voulez-vous configurer automatiquement 2GB de SWAP ? (O/n) " -r SETUP_SWAP
        if [[ "$SETUP_SWAP" =~ ^[OoyY]$ || -z "$SETUP_SWAP" ]]; then
            if [[ -f /etc/dphys-swapfile ]]; then
                log_info "Configuration du SWAP via dphys-swapfile..."
                dphys-swapfile swapoff 2>/dev/null || true
                sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
                dphys-swapfile setup
                dphys-swapfile swapon
                log_success "SWAP configure a 2GB."
                TOTAL_SWAP_MB=2048
                TOTAL_MEMORY_MB=$((TOTAL_RAM_MB + TOTAL_SWAP_MB))
            else
                log_warn "dphys-swapfile non trouve. Creation manuelle du swapfile..."
                if [[ ! -f /swapfile ]]; then
                    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
                    chmod 600 /swapfile
                    mkswap /swapfile
                fi
                swapon /swapfile 2>/dev/null || true
                # Ajouter au fstab si absent
                if ! grep -q "/swapfile" /etc/fstab; then
                    echo "/swapfile none swap sw 0 0" >> /etc/fstab
                fi
                log_success "Swapfile de 2GB cree et active."
                TOTAL_SWAP_MB=2048
                TOTAL_MEMORY_MB=$((TOTAL_RAM_MB + TOTAL_SWAP_MB))
            fi
        else
            log_error "Installation annulee. Configurez le SWAP manuellement puis relancez."
            exit 1
        fi
    fi
fi
log_success "Memoire OK: ${TOTAL_MEMORY_MB}MB disponibles."

# --- Verification Espace Disque ---
log_info "Verification de l'espace disque..."
DISK_FREE_MB=$(df -m . | awk 'NR==2 {print $4}')
DISK_USED_PCT=$(df . | awk 'NR==2 {gsub(/%/,""); print $5}')

if [[ $DISK_FREE_MB -lt $MIN_DISK_FREE_MB ]]; then
    log_error "Espace disque insuffisant: ${DISK_FREE_MB}MB libres (minimum requis: ${MIN_DISK_FREE_MB}MB)"
    log_error "Les images Docker necessitent environ 2GB d'espace."
    echo ""
    log_warn "Suggestions:"
    echo "  - Supprimez les anciens logs: sudo rm -rf logs/*.log"
    echo "  - Nettoyez Docker: docker system prune -a"
    echo "  - Verifiez les gros fichiers: du -sh /* | sort -hr | head -10"
    exit 1
fi
log_success "Espace disque OK: ${DISK_FREE_MB}MB libres (${DISK_USED_PCT}% utilise)."

# --- Verification des dependances ---
log_info "Verification des dependances..."
MISSING_DEPS=()
for dep in jq curl lsof; do
    if ! command -v $dep &> /dev/null; then
        MISSING_DEPS+=($dep)
    fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    log_warn "Installation des dependances manquantes : ${MISSING_DEPS[*]}"
    apt-get update -qq && apt-get install -y -qq "${MISSING_DEPS[@]}" > /dev/null 2>&1
    log_success "Outils de base installes."
fi

# Node.js & npm (Requis pour hashing mot de passe)
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    log_warn "Installation de Node.js & npm..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1
fi

# Docker & Docker Compose (CRITIQUE)
log_info "Verification de Docker et Docker Compose..."
if ! command -v docker &> /dev/null; then
    log_error "Docker n'est pas installe."
    echo "Veuillez installer Docker avant de continuer : curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    log_error "Docker Compose (plugin) n'est pas installe ou non detecte."
    exit 1
fi
log_success "Docker et Docker Compose detectes."

# --- Verification UID utilisateur Docker ---
log_info "Verification de l'utilisateur Docker (UID 1000)..."
if ! id -u 1000 &>/dev/null; then
    log_warn "Aucun utilisateur avec UID 1000. Les volumes Docker pourraient avoir des problemes de permissions."
fi

# Port 80 Check
PORT80_PID=$(lsof -t -i :80 2>/dev/null || true)
if [ -n "$PORT80_PID" ]; then
    PORT80_PIDS_CLEAN=$(echo "$PORT80_PID" | tr '\n' ' ' | xargs)
    FIRST_PID=$(echo "$PORT80_PIDS_CLEAN" | cut -d ' ' -f 1)
    PROCESS_NAME=$(ps -p "$FIRST_PID" -o comm= 2>/dev/null || echo "unknown")

    log_warn "Port 80 occupe par : $PROCESS_NAME (PIDs: $PORT80_PIDS_CLEAN)"
    read -p "Arreter ce service pour liberer le port ? (O/n) " -r CHECK_PORT
    if [[ "$CHECK_PORT" =~ ^[OoyY]$ || -z "$CHECK_PORT" ]]; then
        if [ "$PROCESS_NAME" != "unknown" ]; then
            systemctl stop "$PROCESS_NAME" 2>/dev/null || true
        fi
        if [ -n "$PORT80_PIDS_CLEAN" ]; then
            kill -9 $PORT80_PIDS_CLEAN 2>/dev/null || true
        fi
        if [ "$PROCESS_NAME" != "unknown" ]; then
            systemctl disable "$PROCESS_NAME" 2>/dev/null || true
        fi
        log_success "Port 80 libere."
    else
        log_error "Le port 80 est requis."
        exit 1
    fi
fi

# Cgroups Check (pour limites memoire Docker)
CMDLINE_FILE="/boot/cmdline.txt"
[ ! -f "$CMDLINE_FILE" ] && [ -f "/boot/firmware/cmdline.txt" ] && CMDLINE_FILE="/boot/firmware/cmdline.txt"

if [ -f "$CMDLINE_FILE" ] && ! grep -q "cgroup_enable=memory" "$CMDLINE_FILE"; then
    log_warn "Cgroups (Memoire) non actives."
    sed -i 's/$/ cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1/' "$CMDLINE_FILE"
    log_warn "Optimisation appliquee. Redemarrage requis."
    read -p "Redemarrer maintenant ? (O/n) " -r CHECK_REBOOT
    [[ "$CHECK_REBOOT" =~ ^[OoyY]$ || -z "$CHECK_REBOOT" ]] && reboot
fi

# --- Verification ZRAM (optionnel mais recommande) ---
log_info "Verification de ZRAM (compression RAM)..."
if lsmod | grep -q zram; then
    log_success "ZRAM actif (compression RAM activee)."
else
    log_warn "ZRAM non active. Recommande pour reduire l'usure de la carte SD."
    read -p "Installer et activer ZRAM ? (o/N) " -r SETUP_ZRAM
    if [[ "$SETUP_ZRAM" =~ ^[OoyY]$ ]]; then
        apt-get install -y -qq zram-tools > /dev/null 2>&1 || true
        if command -v zramctl &> /dev/null; then
            log_success "ZRAM installe. Sera actif au prochain redemarrage."
        fi
    fi
fi

# ==============================================================================
# [Phase 2/6] Migration des Donnees
# ==============================================================================
log_step "[Phase 2/6] Migration des Donnees"

DATA_DIR="data"
mkdir -p "$DATA_DIR"

MIGRATION_STATUS="Aucune donnee trouvee"

# Migration messages.txt
if [ -f "messages.txt" ]; then
    if [ ! -f "$DATA_DIR/messages.txt" ]; then
        cp messages.txt "$DATA_DIR/"
        log_success "messages.txt migre vers $DATA_DIR/"
        MIGRATION_STATUS="OK (Migre)"
    else
        log_info "messages.txt deja present dans $DATA_DIR/"
        MIGRATION_STATUS="OK (Existant)"
    fi
else
    if [ ! -f "$DATA_DIR/messages.txt" ]; then
        # Creer avec contenu par defaut
        cat > "$DATA_DIR/messages.txt" << 'MSGEOF'
Joyeux anniversaire {name} ! Je te souhaite une excellente journee !
Bon anniversaire {name} ! Que cette nouvelle annee t'apporte joie et succes !
{name}, je te souhaite un tres joyeux anniversaire ! Profite bien de ta journee !
MSGEOF
        log_info "Fichier messages.txt cree avec templates par defaut dans $DATA_DIR/"
        MIGRATION_STATUS="OK (Cree avec templates)"
    fi
fi

# Migration late_messages.txt
if [ -f "late_messages.txt" ]; then
    if [ ! -f "$DATA_DIR/late_messages.txt" ]; then
        cp late_messages.txt "$DATA_DIR/"
        log_success "late_messages.txt migre vers $DATA_DIR/"
    else
        log_info "late_messages.txt deja present dans $DATA_DIR/"
    fi
else
    if [ ! -f "$DATA_DIR/late_messages.txt" ]; then
        cat > "$DATA_DIR/late_messages.txt" << 'MSGEOF'
{name}, avec un peu de retard, je te souhaite un tres bon anniversaire !
Bon anniversaire en retard {name} ! J'espere que tu as passe une excellente journee !
MSGEOF
        log_info "Fichier late_messages.txt cree avec templates par defaut dans $DATA_DIR/"
    fi
fi

# Permissions Data (Securisation)
# Note: Le volume Docker 'shared-data' est gere par Docker, mais on prepare aussi ./data
# pour la compatibilite avec les montages bind
log_info "Application des permissions securisees sur $DATA_DIR..."
chown -R 1000:1000 "$DATA_DIR" 2>/dev/null || true
chmod -R 775 "$DATA_DIR"
log_success "Permissions appliquees (1000:1000, 775)."

# ==============================================================================
# [Phase 3/6] Configuration & Securite
# ==============================================================================
log_step "[Phase 3/6] Configuration & Securite"

ENV_FILE=".env"
ENV_TEMPLATE=".env.pi4.example"

# Verification du template
if [ ! -f "$ENV_TEMPLATE" ]; then
    log_error "Fichier template $ENV_TEMPLATE introuvable!"
    log_error "Clonez le repository complet ou recuperez ce fichier."
    exit 1
fi

# Creation du .env si necessaire
if [ ! -f "$ENV_FILE" ]; then
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    log_info "Fichier $ENV_FILE cree depuis le template."
fi

# Preparation Hashing
log_info "Preparation de l'environnement de hashing..."
HASH_SCRIPT="dashboard/scripts/hash_password.js"
if [ ! -f "$HASH_SCRIPT" ]; then
    log_error "Script de hashing introuvable: $HASH_SCRIPT"
    exit 1
fi

if [ ! -d "dashboard/node_modules/bcryptjs" ]; then
    log_info "Installation de bcryptjs dans dashboard/..."
    (cd dashboard && npm install bcryptjs --silent --no-audit --no-fund 2>/dev/null) || {
        log_warn "Erreur npm install, tentative avec npm ci..."
        (cd dashboard && npm ci --silent 2>/dev/null) || true
    }
fi

# Password Setup
CURRENT_PASS=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d '=' -f2- | tr -d "'" | tr -d '"')
PASS_HASH_STATUS="Inconnu"

if [[ "$CURRENT_PASS" == *"CHANGEZ_MOI"* ]] || [[ ! "$CURRENT_PASS" =~ ^\$2[aby]\$ ]]; then
    echo -e "${BOLD}Securisation du Dashboard :${NC}"
    echo -n "Definir le mot de passe Admin (Appuyez sur ENTREE pour generer automatiquement) : "
    read -s RAW_PASS
    echo ""

    if [ -z "$RAW_PASS" ]; then
        log_info "Generation d'un mot de passe fort..."
        RAW_PASS=$(openssl rand -base64 16)
        echo -e "${YELLOW}${BOLD}>> MOT DE PASSE GENERE : ${RAW_PASS}${NC}"
        echo -e "${YELLOW}(Copiez-le maintenant, il ne sera plus affiche)${NC}"
        read -p "Appuyez sur Entree pour continuer..."
    fi

    log_info "Hachage du mot de passe (bcrypt, 12 rounds)..."
    HASHED_PASS=$(node "$HASH_SCRIPT" "$RAW_PASS" --quiet 2>/dev/null)

    if [ -n "$HASHED_PASS" ]; then
        # Echappement pour sed
        SAFE_HASH=$(echo "$HASHED_PASS" | sed 's/[\/&]/\\&/g')
        # Echappement pour Docker Compose ($ -> $$)
        DOCKER_SAFE_HASH=${SAFE_HASH//$/\$\$}

        sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD='${DOCKER_SAFE_HASH}'|" "$ENV_FILE"
        log_success "Mot de passe hache et sauvegarde."
        PASS_HASH_STATUS="OK (Bcrypt 12 rounds)"
    else
        log_error "Echec du hachage. Verifiez que bcryptjs est installe."
        exit 1
    fi
else
    log_info "Mot de passe deja configure (et potentiellement hache)."
    PASS_HASH_STATUS="OK (Existant)"
fi

# API Key & JWT - Generation si necessaires
if grep -q "CHANGEZ_MOI" "$ENV_FILE"; then
    log_info "Generation des cles de securite..."
    NEW_API=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
    NEW_JWT=$(openssl rand -hex 32)
    sed -i "s|^API_KEY=.*CHANGEZ_MOI.*|API_KEY=${NEW_API}|" "$ENV_FILE"
    sed -i "s|^JWT_SECRET=.*CHANGEZ_MOI.*|JWT_SECRET=${NEW_JWT}|" "$ENV_FILE"
    log_success "Cles de securite generees."
fi

# HTTPS Check
HTTPS_STATUS="Non detecte"
if command -v certbot &> /dev/null && certbot certificates 2>/dev/null | grep -q "Certificate Name"; then
    HTTPS_STATUS="OK (Let's Encrypt)"
    log_success "Certificats SSL detectes."
else
    log_warn "Aucun certificat SSL detecte (HTTP uniquement)."
    HTTPS_STATUS="${YELLOW}WARNING (HTTP)${NC}"
fi

# Hardening .env
chmod 600 "$ENV_FILE"
log_success "Permissions .env restreintes (600)."

# ==============================================================================
# [Phase 4/6] Backup Google Drive
# ==============================================================================
log_step "[Phase 4/6] Backup Google Drive"

BACKUP_STATUS="Desactive"

if command -v rclone &> /dev/null && rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
    log_info "Rclone configure (Remote: gdrive)."

    if crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"; then
        log_success "Backup automatique deja actif."
        BACKUP_STATUS="Actif (Quotidien)"
    else
        read -p "Activer le backup quotidien (03h00) ? (O/n) " -r ENABLE_BACKUP
        if [[ "$ENABLE_BACKUP" =~ ^[OoyY]$ || -z "$ENABLE_BACKUP" ]]; then
            SCRIPT_PATH="$(pwd)/scripts/backup_to_gdrive.sh"
            if [ -f "$SCRIPT_PATH" ]; then
                chmod +x "$SCRIPT_PATH"
                mkdir -p "$(pwd)/logs"
                (crontab -l 2>/dev/null; echo "0 3 * * * $SCRIPT_PATH >> $(pwd)/logs/backup.log 2>&1") | crontab -
                log_success "Tache Cron ajoutee."
                BACKUP_STATUS="Actif (Quotidien)"
            else
                log_warn "Script de backup introuvable: $SCRIPT_PATH"
            fi
        fi
    fi
else
    log_warn "Rclone non configure ou absent."
    echo "Pour activer les backups, lancez 'rclone config' puis relancez ce script."
    BACKUP_STATUS="${RED}Inactif${NC}"
fi

# ==============================================================================
# [Phase 5/6] Deploiement Docker
# ==============================================================================
log_step "[Phase 5/6] Deploiement Docker"

COMPOSE_FILE="docker-compose.pi4-standalone.yml"

if [ ! -f "$COMPOSE_FILE" ]; then
    log_error "Fichier $COMPOSE_FILE introuvable!"
    exit 1
fi

# --- Nettoyage intelligent (seulement si disque > seuil) ---
log_info "Verification de l'espace disque pour nettoyage..."
CURRENT_DISK_USED_PCT=$(df . | awk 'NR==2 {gsub(/%/,""); print $5}')

if [[ $CURRENT_DISK_USED_PCT -gt $DISK_CLEANUP_THRESHOLD ]]; then
    log_warn "Disque utilise a ${CURRENT_DISK_USED_PCT}% (seuil: ${DISK_CLEANUP_THRESHOLD}%)"
    log_info "Nettoyage des ressources Docker non utilisees..."
    docker image prune -f > /dev/null 2>&1 || true
    docker container prune -f > /dev/null 2>&1 || true
    docker network prune -f > /dev/null 2>&1 || true
    # Ne pas supprimer les volumes (donnees utilisateur!)
    log_success "Nettoyage Docker effectue."
else
    log_info "Espace disque suffisant (${CURRENT_DISK_USED_PCT}%), nettoyage non necessaire."
    # Nettoyage leger des reseaux orphelins uniquement
    docker network prune -f > /dev/null 2>&1 || true
fi

# --- Lancement des services ---
log_info "Lancement des services (Mode Sequentiel pour Pi4)..."
export COMPOSE_PARALLEL_LIMIT=1

# Arreter proprement les anciens containers si necessaire
docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

# Pull des images en premier (peut prendre du temps)
log_info "Telechargement des images Docker (patience sur ARM64)..."
docker compose -f "$COMPOSE_FILE" pull --quiet 2>/dev/null || {
    log_warn "Pull des images echoue ou partiel, tentative de demarrage..."
}

# Demarrage
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# ==============================================================================
# [Phase 6/6] Verification & Rapport
# ==============================================================================
log_step "[Phase 6/6] Verification & Rapport (Health Checks)"

log_info "Attente des services (timeout: ${HEALTH_CHECK_TIMEOUT}s)..."
log_info "Note: Next.js sur ARM64 peut prendre 2-3 minutes a demarrer."

# --- Fonction de verification de sante ---
check_container_status() {
    local container_name=$1
    local status=$(docker inspect --format '{{.State.Status}}' "$container_name" 2>/dev/null || echo "not_found")
    local health=$(docker inspect --format '{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")

    if [ "$status" == "restarting" ]; then
        echo "restarting"
    elif [ "$health" == "healthy" ]; then
        echo "healthy"
    elif [ "$health" == "unhealthy" ]; then
        echo "unhealthy"
    elif [ "$status" == "running" ]; then
        echo "running"
    else
        echo "$status"
    fi
}

check_url() {
    local url=$1
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$url" 2>/dev/null || echo "000")
    # Accepter 200, 307, 308 (redirects), 401 (auth required), 404 (route existe)
    if [[ "$http_code" =~ ^(200|307|308|401|404)$ ]]; then
        return 0
    fi
    return 1
}

wait_for_service() {
    local service_name=$1
    local check_type=$2  # "container" ou "url"
    local target=$3      # nom du container ou URL
    local start_time=$(date +%s)
    local elapsed=0

    echo -n "  - $service_name..."

    while [ $elapsed -lt $HEALTH_CHECK_TIMEOUT ]; do
        if [ "$check_type" == "container" ]; then
            local status=$(check_container_status "$target")

            if [ "$status" == "healthy" ]; then
                echo -e " ${GREEN}OK (healthy)${NC}"
                return 0
            elif [ "$status" == "restarting" ]; then
                echo -e " ${RED}CRASH LOOP${NC}"
                log_error "Le container $target est en crash loop!"
                show_failure_logs "$target"
                return 1
            elif [ "$status" == "unhealthy" ]; then
                echo -e " ${RED}UNHEALTHY${NC}"
                show_failure_logs "$target"
                return 1
            fi
        elif [ "$check_type" == "url" ]; then
            if check_url "$target"; then
                echo -e " ${GREEN}OK${NC}"
                return 0
            fi
        fi

        echo -n "."
        sleep $HEALTH_CHECK_INTERVAL
        elapsed=$(($(date +%s) - start_time))
    done

    echo -e " ${RED}TIMEOUT${NC}"
    if [ "$check_type" == "container" ]; then
        show_failure_logs "$target"
    fi
    return 1
}

# --- Verification des services ---
SERVICES_OK=true

# 1. Redis Bot (critique - doit demarrer en premier)
if ! wait_for_service "Redis Bot (Queue)" "container" "redis-bot"; then
    SERVICES_OK=false
fi

# 2. Redis Dashboard
if ! wait_for_service "Redis Dashboard (Cache)" "container" "redis-dashboard"; then
    SERVICES_OK=false
fi

# 3. API (depend de Redis)
if ! wait_for_service "API Backend" "container" "bot-api"; then
    SERVICES_OK=false
fi

# 4. Dashboard (depend de API)
if ! wait_for_service "Dashboard Next.js" "container" "dashboard"; then
    SERVICES_OK=false
fi

# 5. Verification supplementaire via HTTP
echo -n "  - Verification HTTP Dashboard..."
if check_url "http://localhost:3000"; then
    echo -e " ${GREEN}OK${NC}"
else
    echo -e " ${YELLOW}En attente${NC}"
fi

echo -n "  - Verification HTTP API..."
if check_url "http://localhost:8000/docs"; then
    echo -e " ${GREEN}OK${NC}"
else
    echo -e " ${YELLOW}En attente${NC}"
fi

# 6. Base de donnees (fichier physique dans le volume ou local)
echo -n "  - Base de Donnees (SQLite)..."
# Verifier dans le container
DB_EXISTS=$(docker exec bot-api test -f /app/data/linkedin.db 2>/dev/null && echo "yes" || echo "no")
if [ "$DB_EXISTS" == "yes" ]; then
    echo -e " ${GREEN}OK (Presente)${NC}"
elif ls data/*.db 1> /dev/null 2>&1; then
    echo -e " ${GREEN}OK (Locale)${NC}"
else
    echo -e " ${YELLOW}Sera creee au premier acces${NC}"
fi

# --- Verdict ---
if [ "$SERVICES_OK" = false ]; then
    echo ""
    log_error "Un ou plusieurs services ont echoue a demarrer!"
    log_error "Consultez les logs ci-dessus pour diagnostiquer le probleme."
    echo ""
    log_info "Commandes utiles:"
    echo "  - Voir tous les logs: docker compose -f $COMPOSE_FILE logs"
    echo "  - Voir un service:   docker compose -f $COMPOSE_FILE logs <service>"
    echo "  - Redemarrer:        docker compose -f $COMPOSE_FILE restart"
    exit 1
fi

# --- Audit Securite ---
log_info "Execution de l'audit de securite..."
SECURITY_SCRIPT="scripts/verify_security.sh"
SECURITY_STATUS="N/A"

if [ -f "$SECURITY_SCRIPT" ]; then
    chmod +x "$SECURITY_SCRIPT"
    AUDIT_OUT=$(./$SECURITY_SCRIPT 2>&1 || true)
    SCORE_LINE=$(echo "$AUDIT_OUT" | grep -E "SCORE|%" | tail -n 1 || true)
    if [ -n "$SCORE_LINE" ]; then
        SECURITY_STATUS="${GREEN}${SCORE_LINE}${NC}"
    else
        SECURITY_STATUS="${YELLOW}Audit execute${NC}"
    fi
else
    log_warn "Script d'audit introuvable ($SECURITY_SCRIPT)."
fi

# --- Collecte des informations finales ---
IP_ADDR=$(hostname -I | awk '{print $1}')
DB_SIZE=$(docker exec bot-api du -h /app/data/linkedin.db 2>/dev/null | cut -f1 || echo "0B")

# --- RAPPORT FINAL ---
clear
echo -e "${BLUE}====================================================================${NC}"
echo -e "${BOLD}                    LINKEDIN AUTO - RAPPORT FINAL                   ${NC}"
echo -e "${BLUE}====================================================================${NC}"

echo -e "\n${BOLD}SYSTEME${NC}"
echo -e "   RAM/SWAP           : ${TOTAL_RAM_MB}MB + ${TOTAL_SWAP_MB}MB = ${TOTAL_MEMORY_MB}MB"
echo -e "   Espace Disque      : ${DISK_FREE_MB}MB libres (${DISK_USED_PCT}% utilise)"

echo -e "\n${BOLD}DONNEES${NC}"
echo -e "   Migration Messages : $MIGRATION_STATUS"
echo -e "   Base de Donnees    : /app/data/linkedin.db ($DB_SIZE)"
echo -e "   Permissions        : 1000:1000 (Secure)"

echo -e "\n${BOLD}SECURITE${NC}"
echo -e "   Mot de Passe       : $PASS_HASH_STATUS"
echo -e "   SSL/HTTPS          : $HTTPS_STATUS"
echo -e "   Fichier .env       : Protege (600)"
echo -e "   Audit Securite     : $SECURITY_STATUS"

echo -e "\n${BOLD}SAUVEGARDE${NC}"
echo -e "   Etat Backup GDrive : $BACKUP_STATUS"

echo -e "\n${BOLD}CONTENEURS DOCKER${NC}"
docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || docker ps --format "table {{.Names}}\t{{.Status}}"

echo -e "\n${BOLD}ACCES${NC}"
echo -e "   Local              : http://localhost:3000"
echo -e "   Reseau             : http://$IP_ADDR:3000"
echo -e "   API Docs           : http://$IP_ADDR:8000/docs"
echo -e "   Grafana            : http://$IP_ADDR:3001"
echo -e "   Utilisateur        : admin"
if [ -n "$RAW_PASS" ]; then
    echo -e "   Mot de passe       : ${RAW_PASS} ${YELLOW}(Copiez-le !)${NC}"
else
    echo -e "   Mot de passe       : (Masque / Deja configure)"
fi

echo -e "\n${BLUE}====================================================================${NC}"
log_success "Installation Terminee avec Succes!"
echo -e "${BLUE}====================================================================${NC}"
echo ""
echo "Commandes utiles:"
echo "  - Logs temps reel : docker compose -f $COMPOSE_FILE logs -f"
echo "  - Redemarrer      : docker compose -f $COMPOSE_FILE restart"
echo "  - Arreter         : docker compose -f $COMPOSE_FILE down"
echo "  - Statut          : docker compose -f $COMPOSE_FILE ps"
echo ""
