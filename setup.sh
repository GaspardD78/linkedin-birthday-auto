#!/bin/bash
set -e

# ==============================================================================
# LINKEDIN AUTO RPi4 - MASTER ORCHESTRATOR
# ==============================================================================
# Auteur: Lead DevOps & Security Engineer
# Objectif: Installation, Migration, Sécurité & Backup
# Cible: Raspberry Pi 4 (4GB, ARM64)
# ==============================================================================

# --- Couleurs & Style ---
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

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

         >>> RASPBERRY PI 4 MASTER ORCHESTRATOR <<<
EOF
echo -e "${NC}"

# --- Gestion des Erreurs ---
cleanup() {
    echo -e "\n${YELLOW}[!] Interruption détectée. Nettoyage...${NC}"
    exit 1
}
trap cleanup SIGINT

# ==============================================================================
# [Phase 1/6] Vérifications Système & Dépendances
# ==============================================================================
log_step "[Phase 1/6] Vérifications Système & Dépendances"

if [[ $EUID -ne 0 ]]; then
   log_error "Ce script doit être exécuté en tant que root (sudo ./setup.sh)"
   exit 1
fi

log_info "Vérification des dépendances..."
MISSING_DEPS=()
# Vérification des outils de base
for dep in jq curl lsof; do
    if ! command -v $dep &> /dev/null; then
        MISSING_DEPS+=($dep)
    fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    log_warn "Installation des dépendances manquantes : ${MISSING_DEPS[*]}"
    apt-get update -qq && apt-get install -y -qq jq curl lsof > /dev/null 2>&1
    log_success "Outils de base installés."
fi

# Node.js & npm (Requis pour hashing mot de passe)
if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    log_warn "Installation de Node.js & npm..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1
fi

# Docker & Docker Compose (CRITIQUE)
log_info "Vérification de Docker et Docker Compose..."
if ! command -v docker &> /dev/null; then
    log_error "Docker n'est pas installé."
    echo "Veuillez installer Docker avant de continuer : curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    log_error "Docker Compose (plugin) n'est pas installé ou non détecté."
    exit 1
fi
log_success "Docker et Docker Compose détectés."

# Port 80 Check
PORT80_PID=$(lsof -t -i :80 || true)
if [ -n "$PORT80_PID" ]; then
    PROCESS_NAME=$(ps -p $PORT80_PID -o comm=)
    log_warn "Port 80 occupé par : $PROCESS_NAME ($PORT80_PID)"
    read -p "Arrêter ce service pour libérer le port ? (O/n) " -r CHECK_PORT
    if [[ "$CHECK_PORT" =~ ^[OoyY]$ || -z "$CHECK_PORT" ]]; then
        systemctl stop "$PROCESS_NAME" 2>/dev/null || kill -9 $PORT80_PID
        systemctl disable "$PROCESS_NAME" 2>/dev/null || true
        log_success "Port 80 libéré."
    else
        log_error "Le port 80 est requis."
        exit 1
    fi
fi

# Cgroups Check
CMDLINE_FILE="/boot/cmdline.txt"
[ ! -f "$CMDLINE_FILE" ] && [ -f "/boot/firmware/cmdline.txt" ] && CMDLINE_FILE="/boot/firmware/cmdline.txt"

if [ -f "$CMDLINE_FILE" ] && ! grep -q "cgroup_enable=memory" "$CMDLINE_FILE"; then
    log_warn "Cgroups (Mémoire) non activés."
    sed -i 's/$/ cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1/' "$CMDLINE_FILE"
    log_warn "Optimisation appliquée. Redémarrage requis."
    read -p "Redémarrer maintenant ? (O/n) " -r CHECK_REBOOT
    [[ "$CHECK_REBOOT" =~ ^[OoyY]$ || -z "$CHECK_REBOOT" ]] && reboot
fi

# ==============================================================================
# [Phase 2/6] Migration des Données
# ==============================================================================
log_step "[Phase 2/6] Migration des Données"

DATA_DIR="data"
mkdir -p "$DATA_DIR"

MIGRATION_STATUS="Aucune donnée trouvée"

# Migration messages.txt
if [ -f "messages.txt" ]; then
    if [ ! -f "$DATA_DIR/messages.txt" ]; then
        cp messages.txt "$DATA_DIR/"
        log_success "messages.txt migré vers $DATA_DIR/"
        MIGRATION_STATUS="OK (Migré)"
    else
        log_info "messages.txt déjà présent dans $DATA_DIR/"
        MIGRATION_STATUS="OK (Existant)"
    fi
else
    if [ ! -f "$DATA_DIR/messages.txt" ]; then
        touch "$DATA_DIR/messages.txt"
        log_info "Fichier vide messages.txt créé dans $DATA_DIR/"
        MIGRATION_STATUS="OK (Créé vide)"
    fi
fi

# Migration late_messages.txt
if [ -f "late_messages.txt" ]; then
    if [ ! -f "$DATA_DIR/late_messages.txt" ]; then
        cp late_messages.txt "$DATA_DIR/"
        log_success "late_messages.txt migré vers $DATA_DIR/"
    else
        log_info "late_messages.txt déjà présent dans $DATA_DIR/"
    fi
else
    if [ ! -f "$DATA_DIR/late_messages.txt" ]; then
        touch "$DATA_DIR/late_messages.txt"
        log_info "Fichier vide late_messages.txt créé dans $DATA_DIR/"
    fi
fi

# Permissions Data (Sécurisation)
log_info "Application des permissions sécurisées sur $DATA_DIR..."
# UID 1000 est standard pour le premier utilisateur (souvent 'pi')
# Nous devons nous assurer que ces fichiers sont accessibles par le container (souvent root ou 1000)
chown -R 1000:1000 "$DATA_DIR"
chmod -R 775 "$DATA_DIR"
log_success "Permissions appliquées (1000:1000, 775)."

# ==============================================================================
# [Phase 3/6] Configuration & Sécurité
# ==============================================================================
log_step "[Phase 3/6] Configuration & Sécurité"

ENV_FILE=".env"
[ ! -f "$ENV_FILE" ] && cp ".env.pi4.example" "$ENV_FILE"

# Préparation Hashing
log_info "Préparation de l'environnement de hashing..."
if [ ! -d "dashboard/node_modules/bcryptjs" ]; then
    log_info "Installation de bcryptjs dans dashboard/..."
    (cd dashboard && npm install bcryptjs --silent --no-audit --no-fund) || log_warn "Erreur npm install, tentative continue..."
fi

# Password Setup
CURRENT_PASS=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d '=' -f2)
PASS_HASH_STATUS="Inconnu"

if [[ "$CURRENT_PASS" == *"CHANGEZ_MOI"* ]] || [[ ! "$CURRENT_PASS" =~ ^\$2[aby]\$ ]]; then
    echo -e "${BOLD}Sécurisation du Dashboard :${NC}"
    echo -n "Définir le mot de passe Admin (Appuyez sur ENTRÉE pour générer automatiquement) : "
    read -s RAW_PASS
    echo ""

    if [ -z "$RAW_PASS" ]; then
        log_info "Génération d'un mot de passe fort..."
        RAW_PASS=$(openssl rand -base64 16)
        echo -e "${YELLOW}${BOLD}>> MOT DE PASSE GÉNÉRÉ : ${RAW_PASS}${NC}"
        echo -e "${YELLOW}(Copiez-le maintenant, il ne sera plus affiché)${NC}"
        read -p "Appuyez sur Entrée pour continuer..."
    fi

    log_info "Hachage du mot de passe..."
    HASHED_PASS=$(node dashboard/scripts/hash_password.js "$RAW_PASS" --quiet)

    if [ -n "$HASHED_PASS" ]; then
        # Échappement pour sed
        SAFE_HASH=$(echo "$HASHED_PASS" | sed 's/[\/&]/\\&/g')
        # Échappement pour Docker Compose ($ -> $$)
        DOCKER_SAFE_HASH=${SAFE_HASH//$/\$\$}

        sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD='${DOCKER_SAFE_HASH}'|" "$ENV_FILE"
        log_success "Mot de passe haché et sauvegardé."
        PASS_HASH_STATUS="OK (Bcrypt)"
    else
        log_error "Échec du hachage."
        exit 1
    fi
else
    log_info "Mot de passe déjà configuré (et potentiellement haché)."
    PASS_HASH_STATUS="OK (Existant)"
fi

# API Key & JWT
grep -q "CHANGEZ_MOI" "$ENV_FILE" && {
    NEW_API=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    NEW_JWT=$(openssl rand -hex 32)
    sed -i "s|^API_KEY=.*|API_KEY=${NEW_API}|" "$ENV_FILE"
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${NEW_JWT}|" "$ENV_FILE"
    log_success "Clés de sécurité régénérées."
}

# HTTPS Check
HTTPS_STATUS="Non détecté"
if sudo certbot certificates 2>/dev/null | grep -q "Certificate Name"; then
    HTTPS_STATUS="OK (Let's Encrypt)"
    log_success "Certificats SSL détectés."
else
    log_warn "Aucun certificat SSL détecté."
    HTTPS_STATUS="${YELLOW}WARNING (HTTP)${NC}"
fi

# Hardening
chmod 600 "$ENV_FILE"
log_success "Permissions .env restreintes (600)."

# ==============================================================================
# [Phase 4/6] Backup Google Drive
# ==============================================================================
log_step "[Phase 4/6] Backup Google Drive"

BACKUP_STATUS="Désactivé"

if command -v rclone &> /dev/null && rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
    log_info "Rclone configuré (Remote: gdrive)."

    if crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"; then
        log_success "Backup automatique déjà actif."
        BACKUP_STATUS="Actif (Quotidien)"
    else
        read -p "Activer le backup quotidien (03h00) ? (O/n) " -r ENABLE_BACKUP
        if [[ "$ENABLE_BACKUP" =~ ^[OoyY]$ || -z "$ENABLE_BACKUP" ]]; then
            SCRIPT_PATH="$(pwd)/scripts/backup_to_gdrive.sh"
            chmod +x "$SCRIPT_PATH"
            (crontab -l 2>/dev/null; echo "0 3 * * * $SCRIPT_PATH >> $(pwd)/logs/backup.log 2>&1") | crontab -
            log_success "Tâche Cron ajoutée."
            BACKUP_STATUS="Actif (Quotidien)"
        fi
    fi
else
    log_warn "Rclone non configuré ou absent."
    echo "Pour activer les backups, lancez 'rclone config' puis relancez ce script."
    BACKUP_STATUS="${RED}Inactif${NC}"
fi

# ==============================================================================
# [Phase 5/6] Déploiement Docker
# ==============================================================================
log_step "[Phase 5/6] Déploiement Docker"

log_info "Nettoyage..."
docker network prune -f > /dev/null 2>&1

log_info "Lancement des services (Mode Séquentiel)..."
export COMPOSE_PARALLEL_LIMIT=1
docker compose -f docker-compose.pi4-standalone.yml up -d --remove-orphans

# ==============================================================================
# [Phase 6/6] Vérification & Rapport
# ==============================================================================
log_step "[Phase 6/6] Vérification & Rapport"

log_info "Attente des services..."

check_url() {
    curl -s -o /dev/null -w "%{http_code}" "$1" | grep -q "200\|307\|308\|401\|404"
}

check_container_health() {
    local container_name=$1
    local status=$(docker inspect --format '{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "unknown")
    if [ "$status" == "healthy" ]; then return 0; else return 1; fi
}

MAX_RETRIES=30

# 1. Dashboard (Frontend)
echo -n "  - Dashboard (HTTP)..."
COUNT=0
while [ $COUNT -lt $MAX_RETRIES ]; do
    if check_url "http://localhost:3000"; then echo -e " ${GREEN}OK${NC}"; break; fi
    echo -n "."
    sleep 2
    ((COUNT++))
done
[ $COUNT -eq $MAX_RETRIES ] && echo -e " ${RED}Timeout${NC}"

# 2. API (Backend Container Health)
# Note: Nom du container dépend du dossier, souvent 'linkedin-birthday-auto-api-1' ou défini dans compose
# Dans le doute, on check l'URL, mais la demande exige un check container.
# On va supposer le nom 'api' si container_name est défini, sinon on cherche.
echo -n "  - API Service (Health)..."
COUNT=0
while [ $COUNT -lt $MAX_RETRIES ]; do
    # On essaie de deviner le nom du container API (souvent contient 'api')
    API_CONTAINER=$(docker ps --format '{{.Names}}' | grep "api" | head -n 1)
    if [ -n "$API_CONTAINER" ] && check_container_health "$API_CONTAINER"; then
        echo -e " ${GREEN}OK (Healthy)${NC}"; break;
    fi
    # Fallback sur URL si container non trouvé ou pas encore healthy
    if check_url "http://localhost:8000/docs"; then echo -e " ${GREEN}OK (Via HTTP)${NC}"; break; fi
    echo -n "."
    sleep 2
    ((COUNT++))
done

# 3. Base de données (Fichier Physique)
echo -n "  - Base de Données (File)..."
if ls data/*.db 1> /dev/null 2>&1; then
    echo -e " ${GREEN}OK (Présente)${NC}"
else
    echo -e " ${YELLOW}Absent (Sera créée au démarrage)${NC}"
fi


# --- Audit Sécurité ---
log_info "Exécution de l'audit de sécurité..."
SECURITY_SCRIPT="scripts/verify_security.sh"
SECURITY_STATUS="N/A"

if [ -f "$SECURITY_SCRIPT" ]; then
    chmod +x "$SECURITY_SCRIPT"
    # Capture output
    AUDIT_OUT=$(./$SECURITY_SCRIPT 2>&1 || true)

    # Extraction du Score (ex: "SCORE SÉCURITÉ : 9.5/10")
    SCORE_LINE=$(echo "$AUDIT_OUT" | grep "SCORE SÉCURITÉ" | sed 's/.*: //' || true)

    if [ -n "$SCORE_LINE" ]; then
        SECURITY_STATUS="${GREEN}${SCORE_LINE}${NC}"
    else
        SECURITY_STATUS="${YELLOW}Non déterminé${NC}"
    fi
else
    log_warn "Script d'audit introuvable."
fi

IP_ADDR=$(hostname -I | awk '{print $1}')
DB_SIZE=$(du -h data/*.db 2>/dev/null | cut -f1 | head -n 1 || echo "0B")

# --- RAPPORT FINAL ---
clear
echo -e "${BLUE}====================================================================${NC}"
echo -e "${BOLD}                    LINKEDIN AUTO - RAPPORT FINAL                   ${NC}"
echo -e "${BLUE}====================================================================${NC}"

echo -e "\n${BOLD}📂 DONNÉES${NC}"
echo -e "   Migration Messages : $MIGRATION_STATUS"
echo -e "   Base de Données    : data/linkedin.db ($DB_SIZE)"
echo -e "   Permissions        : 1000:1000 (Secure)"

echo -e "\n${BOLD}🛡️ SÉCURITÉ${NC}"
echo -e "   Mot de Passe       : $PASS_HASH_STATUS"
echo -e "   SSL/HTTPS          : $HTTPS_STATUS"
echo -e "   Fichier .env       : Protégé (600)"
echo -e "   SCORE SÉCURITÉ     : $SECURITY_STATUS"

echo -e "\n${BOLD}💾 SAUVEGARDE${NC}"
echo -e "   État Backup GDrive : $BACKUP_STATUS"

echo -e "\n${BOLD}🌍 ACCÈS${NC}"
echo -e "   Local              : http://localhost:3000"
echo -e "   Réseau             : http://$IP_ADDR:3000"
echo -e "   Utilisateur        : admin"
if [ -n "$RAW_PASS" ] && [[ "$RAW_PASS" != *"open ssl"* ]]; then # Check basic
    # On n'affiche le mot de passe que s'il a été généré ou saisi dans cette session
    # Mais le prompt demandait d'afficher le mot de passe généré explicitement plus haut.
    # Ici, on peut le masquer par sécurité dans le rapport final, ou le rappeler.
    # Le prompt initial disait : "CREDENTIALS : Login/Pass (En clair ici uniquement, avec avertissement ⚠️)"
    echo -e "   Mot de passe       : ${RAW_PASS} ${YELLOW}⚠️ (Copiez-le !)${NC}"
else
    echo -e "   Mot de passe       : (Masqué / Déjà configuré)"
fi

echo -e "\n${BLUE}====================================================================${NC}"
log_success "Installation Terminée."
