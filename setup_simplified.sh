#!/bin/bash

# ╔══════════════════════════════════════════════════════════════╗
# ║                                                              ║
# ║  🚀 LinkedIn Birthday Bot - Installation Simplifiée      ║
# ║                                                              ║
# ║  Version 3.0 - Installation Tout-en-Un avec Auto-Diagnostic║
# ║                                                              ║
# ╚══════════════════════════════════════════════════════════════╝

set -e

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Configuration ---
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
ENV_FILE=".env"
ENV_TEMPLATE=".env.pi4.example"
MIN_DISK_GB=3

# --- Fonctions d'affichage ---
print_banner() {
    echo -e "${CYAN}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║  🚀 LinkedIn Birthday Bot - Installation Simplifiée      ║
║                                                              ║
║  Version 3.0 - Installation Tout-en-Un                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

print_header() { echo -e "\n${BLUE}${BOLD}═══ $1 ═══${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }
print_question() { echo -e "${CYAN}❓ $1${NC}"; }

# --- Fonction d'erreur avec diagnostic ---
handle_error() {
    local error_msg="$1"
    local service="$2"

    print_error "$error_msg"

    if [ -n "$service" ] && docker ps -a | grep -q "$service"; then
        print_info "Affichage des logs du service $service:"
        docker logs "$service" --tail 30 2>&1 || true

        print_info "Statut du conteneur:"
        docker inspect "$service" --format='État: {{.State.Status}} | Health: {{.State.Health.Status}}' 2>&1 || true
    fi

    print_header "Solutions possibles"
    echo "  1. Vérifiez les logs complets: docker logs $service"
    echo "  2. Vérifiez que tous les prérequis sont satisfaits"
    echo "  3. Essayez de redémarrer: docker compose -f $COMPOSE_FILE restart"
    echo "  4. Nettoyez et recommencez: docker compose -f $COMPOSE_FILE down -v"
    echo "  5. Consultez la documentation: docs/RASPBERRY_PI_TROUBLESHOOTING.md"

    exit 1
}

# --- Fonction de validation ---
wait_for_healthy() {
    local service_name="$1"
    local max_wait="${2:-120}"
    local waited=0

    print_info "Attente du démarrage de $service_name (max ${max_wait}s)..."

    while [ $waited -lt $max_wait ]; do
        local health_status=$(docker inspect "$service_name" --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")
        local running_status=$(docker inspect "$service_name" --format='{{.State.Status}}' 2>/dev/null || echo "none")

        if [ "$health_status" = "healthy" ]; then
            print_success "$service_name est démarré et sain"
            return 0
        elif [ "$running_status" = "running" ] && [ "$health_status" = "none" ]; then
            print_success "$service_name est démarré (pas de healthcheck)"
            return 0
        elif [ "$running_status" != "running" ]; then
            handle_error "$service_name n'est pas en cours d'exécution" "$service_name"
        fi

        echo -n "."
        sleep 2
        waited=$((waited + 2))
    done

    print_warning "$service_name n'est pas encore healthy après ${max_wait}s"
    print_info "Le service peut encore démarrer, vérifiez les logs..."
    docker logs "$service_name" --tail 20 2>&1 || true

    # Ne pas échouer immédiatement, laisser une chance
    return 0
}

# =========================================================================
# DÉBUT DE L'INSTALLATION
# =========================================================================

print_banner

print_info "Bienvenue dans l'assistant d'installation du LinkedIn Birthday Bot !"
print_info "Ce script va vous guider pas à pas dans l'installation et la configuration."
echo ""

# =========================================================================
# ÉTAPE 0 : Détection de l'environnement
# =========================================================================
print_header "ÉTAPE 0 : Détection de l'environnement"

# Détection plateforme
if [ -f /proc/device-tree/model ]; then
    DEVICE_MODEL=$(cat /proc/device-tree/model)
    print_success "Plateforme détectée : $DEVICE_MODEL"
else
    print_info "Plateforme : $(uname -m)"
fi

# Informations système
if command -v free &> /dev/null; then
    TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
    print_info "Mémoire RAM : ${TOTAL_RAM}MB"
fi

DISK_AVAIL=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')
print_info "Espace disque disponible : ${DISK_AVAIL}GB"

# =========================================================================
# ÉTAPE 1 : Vérification des prérequis
# =========================================================================
print_header "ÉTAPE 1 : Vérification des prérequis"

# Docker
print_info "Vérification de Docker..."
if docker --version &> /dev/null; then
    print_success "Docker est installé"
    docker --version | head -n1
else
    print_error "Docker n'est pas installé !"
    print_info "Installation: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Permissions Docker
print_success "Permissions Docker OK"
if ! docker ps &> /dev/null; then
    print_error "L'utilisateur actuel n'a pas les droits Docker"
    print_info "Exécutez: sudo usermod -aG docker $USER"
    print_info "Puis redémarrez votre session"
    exit 1
fi

# Docker Compose V2
print_info "Vérification de Docker Compose V2..."
if docker compose version &> /dev/null; then
    print_success "Docker Compose V2 est installé"
    docker compose version | head -n1
else
    print_error "Docker Compose V2 n'est pas installé !"
    print_info "Installation: sudo apt install docker-compose-plugin"
    exit 1
fi

# Espace disque
if [ "$DISK_AVAIL" -lt "$MIN_DISK_GB" ]; then
    print_warning "Espace disque faible: ${DISK_AVAIL}GB"
    print_warning "Minimum recommandé: ${MIN_DISK_GB}GB"
    print_question "Voulez-vous continuer quand même ? [o/N]"
    read -r response
    if [[ ! "$response" =~ ^[OoYy]$ ]]; then
        exit 1
    fi
fi

# =========================================================================
# ÉTAPE 2 : Configuration
# =========================================================================
print_header "ÉTAPE 2 : Configuration"

# Gestion auth_state.json
if [ -f "auth_state.json" ]; then
    print_success "✅ Fichier auth_state.json détecté localement."
else
    print_warning "Fichier auth_state.json non trouvé"
    print_info "Vous devrez le configurer plus tard via le dashboard"
    echo "{}" > auth_state.json
fi

# Configuration .env
print_info "Configuration du fichier .env"
if [ -f "$ENV_FILE" ]; then
    print_success "Fichier .env existant détecté"
else
    if [ ! -f "$ENV_TEMPLATE" ]; then
        print_error "Template $ENV_TEMPLATE introuvable !"
        exit 1
    fi

    cp "$ENV_TEMPLATE" "$ENV_FILE"
    print_success "Fichier .env créé depuis le template"
fi

# Demander configuration de base
print_question "Voulez-vous configurer les paramètres de base maintenant ? [O/n]"
read -r configure_now

if [[ "$configure_now" =~ ^[Nn]$ ]]; then
    print_info "Configuration ignorée. Vous pourrez éditer .env manuellement"
else
    print_info "Configuration de base :"

    # Mode DRY RUN
    print_question "Mode DRY RUN (test sans envoyer) [true]"
    read -r dry_run
    dry_run=${dry_run:-true}

    # Mode du bot
    print_question "Mode du bot (standard/unlimited) [standard]"
    read -r bot_mode
    bot_mode=${bot_mode:-standard}

    # Mode headless
    print_question "Mode headless (navigateur invisible) [true]"
    read -r headless
    headless=${headless:-true}

    # Limite hebdomadaire
    print_question "Limite hebdomadaire de messages [80]"
    read -r weekly_limit
    weekly_limit=${weekly_limit:-80}

    # Mise à jour du .env
    sed -i "s/DRY_RUN=.*/DRY_RUN=$dry_run/" "$ENV_FILE"
    sed -i "s/MODE=.*/MODE=$bot_mode/" "$ENV_FILE"
    sed -i "s/HEADLESS=.*/HEADLESS=$headless/" "$ENV_FILE"
    sed -i "s/WEEKLY_MESSAGE_LIMIT=.*/WEEKLY_MESSAGE_LIMIT=$weekly_limit/" "$ENV_FILE"

    # Génération des secrets
    if ! grep -q "^JWT_SECRET=.\+" "$ENV_FILE"; then
        JWT_SECRET=$(openssl rand -hex 32)
        sed -i "s/JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" "$ENV_FILE"
    fi

    if ! grep -q "^API_KEY=.\+" "$ENV_FILE"; then
        API_KEY=$(openssl rand -hex 32)
        sed -i "s/API_KEY=.*/API_KEY=$API_KEY/" "$ENV_FILE"
    fi

    print_success "Configuration .env mise à jour"
fi

# Configuration SMTP
print_question "Voulez-vous configurer les notifications par email (SMTP) ? [o/N]"
read -r configure_smtp

if [[ "$configure_smtp" =~ ^[OoYy]$ ]]; then
    print_question "Hôte SMTP (ex: smtp.gmail.com):"
    read -r smtp_host
    print_question "Port SMTP (ex: 587):"
    read -r smtp_port
    print_question "Email expéditeur:"
    read -r smtp_from
    print_question "Email destinataire:"
    read -r smtp_to
    print_question "Utilisateur SMTP:"
    read -r smtp_user
    print_question "Mot de passe SMTP:"
    read -rs smtp_password
    echo ""

    sed -i "s/SMTP_HOST=.*/SMTP_HOST=$smtp_host/" "$ENV_FILE"
    sed -i "s/SMTP_PORT=.*/SMTP_PORT=$smtp_port/" "$ENV_FILE"
    sed -i "s/SMTP_FROM=.*/SMTP_FROM=$smtp_from/" "$ENV_FILE"
    sed -i "s/SMTP_TO=.*/SMTP_TO=$smtp_to/" "$ENV_FILE"
    sed -i "s/SMTP_USER=.*/SMTP_USER=$smtp_user/" "$ENV_FILE"
    sed -i "s/SMTP_PASSWORD=.*/SMTP_PASSWORD=$smtp_password/" "$ENV_FILE"

    print_success "Configuration SMTP enregistrée"
else
    print_info "Configuration SMTP ignorée"
    print_info "Vous pourrez la configurer plus tard en éditant .env"
fi

# Création des dossiers
for dir in data logs config; do
    mkdir -p "$dir"
    chmod 777 "$dir" 2>/dev/null || sudo chmod 777 "$dir" 2>/dev/null || true
done

# Fichier config.yaml minimal si absent
if [ ! -f "config/config.yaml" ]; then
    cat > config/config.yaml << 'EOF'
# Configuration minimale du bot
bot:
  headless: true
  timeout: 30000

linkedin:
  login:
    max_retries: 3

messages:
  default_template: "messages.txt"
  late_template: "late_messages.txt"
EOF
    print_success "Fichier config/config.yaml créé avec configuration minimale"
fi

# =========================================================================
# ÉTAPE 3 : Déploiement
# =========================================================================
print_header "ÉTAPE 3 : Déploiement"

print_info "Le déploiement va maintenant commencer."
print_info "Cette étape peut prendre 15-20 minutes (compilation Next.js)."
echo ""

print_question "Voulez-vous continuer avec le déploiement ? [O/n]"
read -r deploy_now

if [[ "$deploy_now" =~ ^[Nn]$ ]]; then
    print_info "Déploiement annulé"
    print_info "Pour déployer plus tard: ./scripts/deploy_pi4_pull.sh"
    exit 0
fi

print_info "Lancement du déploiement optimisé via deploy_pi4_pull.sh..."
print_info "Cela permet d'utiliser les images pré-compilées (gain de ~20 minutes)."
echo ""

# Patch temporaire du healthcheck si nécessaire
if grep -q '"curl"' "$COMPOSE_FILE"; then
    print_info "Optimisation du healthcheck de l'API..."

    # Backup
    cp "$COMPOSE_FILE" "${COMPOSE_FILE}.backup"

    # Remplacer curl par python dans le healthcheck
    sed -i 's/test: \["CMD", "curl", "-f", "http:\/\/localhost:8000\/health"\]/test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('\''http:\/\/localhost:8000\/health'\'').read()"]/' "$COMPOSE_FILE"
    sed -i 's/start_period: 30s/start_period: 60s/' "$COMPOSE_FILE"
    sed -i 's/retries: 3/retries: 5/' "$COMPOSE_FILE"

    print_success "Healthcheck optimisé (utilise Python au lieu de curl)"
fi

# Déploiement via le script existant
if [ -f "scripts/deploy_pi4_pull.sh" ]; then
    bash scripts/deploy_pi4_pull.sh
else
    # Déploiement manuel si le script n'existe pas
    docker compose -f "$COMPOSE_FILE" down --remove-orphans || true
    docker compose -f "$COMPOSE_FILE" pull
    docker compose -f "$COMPOSE_FILE" up -d
fi

# =========================================================================
# ÉTAPE 4 : Validation
# =========================================================================
print_header "ÉTAPE 4 : Validation du déploiement"

print_info "Attente du démarrage des services (cela peut prendre 2-3 minutes)..."
sleep 10

# Vérifier les services critiques
wait_for_healthy "redis-bot" 60
wait_for_healthy "redis-dashboard" 60
wait_for_healthy "bot-api" 120
wait_for_healthy "dashboard" 180

# Afficher le statut final
print_header "État des services"
docker compose -f "$COMPOSE_FILE" ps

# =========================================================================
# FIN
# =========================================================================
print_header "🎉 INSTALLATION TERMINÉE"

LOCAL_IP=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}${BOLD}"
cat << EOF

╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              ✅ Installation réussie !                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

EOF
echo -e "${NC}"

echo -e "📍 ${BOLD}Accès Dashboard :${NC} http://${LOCAL_IP}:3000"
echo -e "📂 ${BOLD}Base de données :${NC} ./data/linkedin.db"
echo -e "📄 ${BOLD}Logs :${NC}           docker compose -f $COMPOSE_FILE logs -f"
echo ""
echo -e "${BOLD}Commandes utiles :${NC}"
echo "  • Voir les logs:          docker compose -f $COMPOSE_FILE logs -f"
echo "  • Arrêter:                docker compose -f $COMPOSE_FILE stop"
echo "  • Redémarrer:             docker compose -f $COMPOSE_FILE restart"
echo "  • Nettoyer complètement:  docker compose -f $COMPOSE_FILE down -v"
echo ""
echo -e "${YELLOW}${BOLD}Note importante :${NC}"
echo "  Si le dashboard affiche une erreur au premier accès, patientez"
echo "  1-2 minutes le temps que Next.js finisse son initialisation."
echo ""
print_success "Profitez de votre bot LinkedIn Birthday !"
