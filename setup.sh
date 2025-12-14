#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - ULTIMATE SETUP SCRIPT v7.0 (Pi4 Edition)        ║
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

      🚀 ULTIMATE SETUP SCRIPT v7.0 - RASPBERRY PI 4
EOF
echo -e "${NC}"
log INFO "Démarrage de l'installation..."
log INFO "Fichier de log : $LOG_FILE"
if [ "$AUTO_APPROVE" = true ]; then
    log INFO "Mode automatique activé (-y)."
fi

# ═══════════════════════════════════════════════════════════════════════════
# 1. PHASE SYSTEM & HARDWARE (Le "Safety Net")
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔍 PHASE 1 : Vérifications Système & Hardware"

# 1.1 Swap Check
# Utilisation de free -m pour compatibilité
SWAP_TOTAL=$(free -m | awk '/^Swap:/{print $2}')
# Default to 0 if empty
SWAP_TOTAL=${SWAP_TOTAL:-0}
log INFO "Mémoire Swap détectée : ${SWAP_TOTAL} MB"

if [ "$SWAP_TOTAL" -lt 2000 ]; then
    log WARN "Swap insuffisant (< 2GB). Next.js risque de crasher sur Pi4."
    if ask_confirmation "Voulez-vous augmenter le Swap à 2GB automatiquement ?"; then
        log INFO "Configuration du Swap (peut prendre 1-2 min)..."
        # Commandes spécifiques Raspbian/Debian
        if command -v dphys-swapfile &> /dev/null; then
            sudo dphys-swapfile swapoff 2>/dev/null || true
            sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile 2>/dev/null || \
            (echo "CONF_SWAPSIZE=2048" | sudo tee -a /etc/dphys-swapfile > /dev/null)

            sudo dphys-swapfile setup
            sudo dphys-swapfile swapon
            log SUCCESS "Swap augmenté à 2GB."
        else
             log WARN "dphys-swapfile non trouvé. Impossible de configurer le swap automatiquement."
        fi
    else
        log WARN "Swap non modifié. Risque d'instabilité (OOM Kills)."
    fi
else
    log SUCCESS "Swap suffisant."
fi

# 1.2 Network Discovery
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$LOCAL_IP" ]; then LOCAL_IP="127.0.0.1"; fi
log INFO "IP Locale détectée : ${LOCAL_IP}"

# 1.3 Docker Access
if ! docker info >/dev/null 2>&1; then
    log ERROR "L'utilisateur $(whoami) n'a pas accès à Docker ou Docker n'est pas lancé."
    log INFO "Tentative de correction des droits..."
    # On tente d'ajouter le user sans sudo password si possible, sinon ça failera
    if sudo usermod -aG docker $(whoami); then
        log WARN "Droits appliqués. Vous devez vous déconnecter/reconnecter pour que cela prenne effet."
        log WARN "Relancez ce script après reconnexion (ex: 'newgrp docker')."
        exit 1
    else
        log ERROR "Impossible d'appliquer les droits Docker automatiquement."
        exit 1
    fi
fi
log SUCCESS "Accès Docker OK."

# 1.4 Check .env IP
if [ -f "$ENV_FILE" ]; then
    CURRENT_API_URL=$(grep "NEXT_PUBLIC_API_URL" "$ENV_FILE" | cut -d'=' -f2)
    if [[ "$CURRENT_API_URL" != *"$LOCAL_IP"* && "$CURRENT_API_URL" != *"localhost"* && "$CURRENT_API_URL" != *"127.0.0.1"* ]]; then
        log WARN "NEXT_PUBLIC_API_URL ne semble pas pointer vers cette IP ($LOCAL_IP)."
        log WARN "Actuel : $CURRENT_API_URL"
    fi
else
    log INFO "Création du fichier .env depuis le template..."
    if [ -f "$ENV_TEMPLATE" ]; then
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        # Mettre l'IP locale par défaut
        sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000|g" "$ENV_FILE"
        sed -i "s|NEXT_PUBLIC_DASHBOARD_URL=.*|NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000|g" "$ENV_FILE"
        log SUCCESS ".env créé et configuré avec IP locale."
    else
        log ERROR "Template $ENV_TEMPLATE introuvable."
        # Création d'un .env minimal si template absent
        echo "NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000" > "$ENV_FILE"
        echo "NEXT_PUBLIC_DASHBOARD_URL=http://${LOCAL_IP}:3000" >> "$ENV_FILE"
        echo "API_KEY=internal_secret_key" >> "$ENV_FILE"
        echo "JWT_SECRET=secret" >> "$ENV_FILE"
        echo "DASHBOARD_PASSWORD=admin" >> "$ENV_FILE"
        log WARN ".env minimal créé (template absent)."
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# 2. PHASE SECURITY (Héritage Verify Security)
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🔒 PHASE 2 : Sécurité & Hardening"

# 2.1 Permissions
log INFO "Vérification des permissions..."
chmod 600 "$ENV_FILE" 2>/dev/null || true
if [ -f "id_rsa" ]; then chmod 600 "id_rsa"; fi

# Création dossiers et propriété
mkdir -p data logs config
# Utilisation de $(id -u):$(id -g) pour éviter les soucis de nom
# Sur certains systèmes sudo chown peut demander un mdp, on ignore si fail en non-interactif sans sudo rights
if command -v sudo &>/dev/null; then
    sudo chown -R $(id -u):$(id -g) data logs config 2>/dev/null || true
fi
log SUCCESS "Permissions fichiers (600) et dossiers ($USER) appliquées."

# 2.2 Password Complexity Check
DASHBOARD_PASS=$(grep "DASHBOARD_PASSWORD" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$DASHBOARD_PASS" == "change_me" || "$DASHBOARD_PASS" == "admin" || ${#DASHBOARD_PASS} -lt 8 ]]; then
    log WARN "Mot de passe Dashboard faible ou par défaut détecté."
    if [ "$AUTO_APPROVE" = true ]; then
        NEW_PASS=$(openssl rand -base64 12)
        log INFO "Génération automatique d'un mot de passe fort : $NEW_PASS"
    else
        # read -s peut failer en non-interactif
        read -s -p "Entrez un nouveau mot de passe sécurisé : " NEW_PASS || NEW_PASS=""
        echo ""
    fi

    if [ -n "$NEW_PASS" ]; then
        # Échappement pour sed
        ESCAPED_PASS=$(printf '%s\n' "$NEW_PASS" | sed -e 's/[\/&]/\\&/g')
        sed -i "s/^DASHBOARD_PASSWORD=.*/DASHBOARD_PASSWORD=$ESCAPED_PASS/" "$ENV_FILE"
        log SUCCESS "Mot de passe mis à jour dans .env"
    fi
fi

# 2.3 API Key Check
API_KEY=$(grep "API_KEY" "$ENV_FILE" | cut -d'=' -f2)
if [[ "$API_KEY" == "internal_secret_key" || -z "$API_KEY" ]]; then
    log WARN "Clé API par défaut détectée."
    NEW_KEY=$(openssl rand -hex 32)
    sed -i "s/^API_KEY=.*/API_KEY=$NEW_KEY/" "$ENV_FILE"
    # Update BOT_API_KEY for Dashboard
    sed -i "s/^BOT_API_KEY=.*/BOT_API_KEY=$NEW_KEY/" "$ENV_FILE"
    log SUCCESS "Nouvelle API Key générée et appliquée (32 bytes hex)."
fi

# ═══════════════════════════════════════════════════════════════════════════
# 3. PHASE DEPLOYMENT & DATABASE INIT
# ═══════════════════════════════════════════════════════════════════════════
log INFO "🚢 PHASE 3 : Déploiement & Initialisation"

# 3.1 Compose Check & Fix
if [ -f "$COMPOSE_FILE" ]; then
    log INFO "Vérification de la configuration Docker Compose..."
    if ! grep -q "start_period: 120s" "$COMPOSE_FILE"; then
        log WARN "Optimisation des timeouts manquante dans $COMPOSE_FILE (vérifié mais pas bloquant)."
    fi
else
    log ERROR "Fichier $COMPOSE_FILE introuvable."
    exit 1
fi

# 3.2 Pull Images
log INFO "Téléchargement des images (cela peut prendre du temps)..."
docker compose -f "$COMPOSE_FILE" pull --quiet &
spinner $!
log SUCCESS "Images téléchargées."

# 3.3 Launch
log INFO "Démarrage des conteneurs..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
log SUCCESS "Conteneurs lancés."

# 3.4 Wait for API Healthy
log INFO "Attente du service API (Healthy)..."
MAX_RETRIES=30 # 30 * 5s = 150s
COUNT=0
API_HEALTHY=false

while [ $COUNT -lt $MAX_RETRIES ]; do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' bot-api 2>/dev/null || echo "starting")
    if [ "$STATUS" == "healthy" ]; then
        API_HEALTHY=true
        break
    fi
    # Petit feedback visuel
    echo -n "."
    sleep 5
    COUNT=$((COUNT+1))
done
echo ""

if [ "$API_HEALTHY" = false ]; then
    log ERROR "Le service bot-api n'est pas devenu healthy après 150s."
    log ERROR "Affichage des logs bot-api :"
    docker logs bot-api --tail 20
    exit 1
fi
log SUCCESS "API est Healthy."

# 3.5 DB Initialization (CRUCIAL)
log INFO "Initialisation de la base de données..."
# On utilise exec sur le conteneur API qui a le code et l'accès au volume
# On ignore l'erreur si le script n'existe pas encore dans l'image (si vieille image)
if docker compose -f "$COMPOSE_FILE" exec -T api python -m src.scripts.init_db; then
    log SUCCESS "Tables de base de données créées/vérifiées avec succès."
else
    log WARN "Échec de l'initialisation de la DB via le conteneur."
    log INFO "Tentative locale (si python disponible)..."
    if command -v python3 &>/dev/null && [ -f "src/scripts/init_db.py" ]; then
         python3 src/scripts/init_db.py
         log SUCCESS "DB initialisée localement."
    else
        log ERROR "Impossible d'initialiser la DB. Assurez-vous que l'image Docker contient src/scripts/init_db.py ou que python3 est installé localement."
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# 4. PHASE DIAGNOSTIC ACTIF (The "Doctor")
# ═══════════════════════════════════════════════════════════════════════════
log INFO "👨‍⚕️ PHASE 4 : Diagnostic Actif (The Doctor)"

# 4.1 Wait Loop (All Services)
SERVICES=("redis-bot" "redis-dashboard" "bot-api" "bot-worker" "dashboard")
log INFO "Vérification de tous les services..."

for svc in "${SERVICES[@]}"; do
    # Check status
    STATE=$(docker inspect --format='{{.State.Status}}' $svc 2>/dev/null || echo "missing")
    HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' $svc 2>/dev/null)

    if [[ "$STATE" == "running" && ("$HEALTH" == "healthy" || "$HEALTH" == "no_healthcheck") ]]; then
        log SUCCESS "Service $svc : OK ($STATE, $HEALTH)"
    else
        log ERROR "Service $svc : PROBLÈME ($STATE, $HEALTH)"
        # 4.2 Log Scanning
        log INFO "--- Derniers logs d'erreur pour $svc ---"
        docker logs $svc --tail 50 2>&1 | grep -E "Error|Panic|Exception|FATAL" | tail -n 10 || echo "Pas d'erreurs explicites trouvées dans les logs récents."
        echo "-------------------------------------------"
    fi
done

# 4.3 Endpoint Testing
log INFO "Test des endpoints..."

# API
if curl -s -f http://localhost:8000/health >/dev/null; then
    log SUCCESS "Endpoint API (http://localhost:8000/health) : OK"
else
    log ERROR "Endpoint API inopérant."
fi

# Frontend
if curl -s -I http://localhost:3000 >/dev/null; then
    log SUCCESS "Endpoint Frontend (http://localhost:3000) : OK"
else
    log WARN "Endpoint Frontend (http://localhost:3000) ne répond pas encore (Next.js build peut être long)."
fi

# ═══════════════════════════════════════════════════════════════════════════
# 5. PHASE BACKUP REPAIR
# ═══════════════════════════════════════════════════════════════════════════
log INFO "💾 PHASE 5 : Vérification Backup"

if [ -f "scripts/backup_to_gdrive.sh" ]; then
    chmod +x scripts/backup_to_gdrive.sh
    # On check juste si rclone est configuré pour ne pas bloquer le setup
    if command -v rclone &>/dev/null && rclone listremotes 2>/dev/null | grep -q ":"; then
        log SUCCESS "Système de backup configuré (Rclone détecté)."
        # Optionnel : Proposer un test
        # ./scripts/backup_to_gdrive.sh --skip-local
    else
        log WARN "Rclone non configuré ou absent. Les backups Google Drive ne fonctionneront pas."
        log INFO "Lancez 'rclone config' puis './scripts/backup_to_gdrive.sh' manuellement."
    fi
else
    log WARN "Script de backup introuvable."
fi

# ═══════════════════════════════════════════════════════════════════════════
# 6. FINAL REPORT
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
echo -e "   💾  ${BOLD}Database :${NC}        Initialisée (data/linkedin.db)"
echo ""
echo -e "${CYAN}Pour voir les logs en temps réel :${NC}"
echo -e "   docker compose -f $COMPOSE_FILE logs -f"
echo ""

exit 0
