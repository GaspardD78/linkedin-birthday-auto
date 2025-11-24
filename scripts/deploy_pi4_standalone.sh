#!/bin/bash

# =========================================================================
# Script de déploiement simplifié pour Raspberry Pi 4
# Architecture: Pi4 + Freebox Pop (sans Synology)
# =========================================================================
#
# Services déployés:
# - Bot Worker (LinkedIn automation avec RQ)
# - Dashboard (Next.js sur port 3000)
# - Redis x2 (queue bot + cache dashboard)
# - SQLite (base de données locale partagée)
#
# Utilisation:
#   ./scripts/deploy_pi4_standalone.sh
#
# Prérequis:
# - Raspberry Pi 4 (4GB RAM minimum)
# - Docker + Docker Compose installés
# - Connexion Freebox Pop (IP résidentielle)
# =========================================================================

set -e  # Arrêt en cas d'erreur

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Emojis
CHECKMARK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"
ROCKET="🚀"

# Variables
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
ENV_FILE=".env"
ENV_TEMPLATE=".env.pi4"
PROJECT_NAME="linkedin-bot-pi4"

# =========================================================================
# Fonctions utilitaires
# =========================================================================

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}${CHECKMARK} $1${NC}"
}

print_error() {
    echo -e "${RED}${CROSS} $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}${WARNING} $1${NC}"
}

print_info() {
    echo -e "${BLUE}${INFO} $1${NC}"
}

# =========================================================================
# Vérifications préalables
# =========================================================================

print_header "Vérifications système"

# Vérifier que le script est exécuté depuis le répertoire racine
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "Le fichier $COMPOSE_FILE n'existe pas"
    print_info "Exécutez ce script depuis le répertoire racine du projet"
    exit 1
fi
print_success "Fichier docker-compose trouvé"

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker n'est pas installé"
    print_info "Installez Docker avec: curl -fsSL https://get.docker.com | sh"
    exit 1
fi
print_success "Docker installé: $(docker --version | cut -d' ' -f3 | tr -d ',')"

# Vérifier Docker Compose
if ! docker compose version &> /dev/null; then
    print_error "Docker Compose n'est pas disponible"
    print_info "Installez Docker Compose ou mettez à jour Docker"
    exit 1
fi
print_success "Docker Compose installé: $(docker compose version | cut -d' ' -f4)"

# Vérifier les permissions Docker
if ! docker ps &> /dev/null; then
    print_error "Impossible d'accéder à Docker"
    print_info "Ajoutez votre utilisateur au groupe docker: sudo usermod -aG docker $USER"
    print_info "Puis déconnectez-vous et reconnectez-vous"
    exit 1
fi
print_success "Permissions Docker OK"

# Vérifier la RAM disponible
TOTAL_RAM=$(free -m | awk 'NR==2{print $2}')
if [ "$TOTAL_RAM" -lt 3500 ]; then
    print_warning "RAM détectée: ${TOTAL_RAM}MB (minimum recommandé: 4GB)"
    print_info "Le déploiement peut être instable avec moins de 4GB"
    read -p "Voulez-vous continuer ? (o/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Oo]$ ]]; then
        exit 1
    fi
else
    print_success "RAM disponible: ${TOTAL_RAM}MB"
fi

# Vérifier l'espace disque
DISK_SPACE=$(df -h . | awk 'NR==2{print $4}' | sed 's/G//')
# Convertir en entier pour la comparaison (supprime les décimales)
DISK_SPACE_INT=${DISK_SPACE%.*}
if [ "$DISK_SPACE_INT" -lt 5 ] 2>/dev/null; then
    print_warning "Espace disque disponible: ${DISK_SPACE}GB (minimum recommandé: 5GB)"
fi
print_success "Espace disque disponible: ${DISK_SPACE}GB"

# =========================================================================
# Configuration de l'environnement
# =========================================================================

print_header "Configuration de l'environnement"

# Créer le fichier .env si nécessaire
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_TEMPLATE" ]; then
        print_info "Copie de $ENV_TEMPLATE vers $ENV_FILE"
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        print_success "Fichier .env créé"
        print_warning "Vérifiez et modifiez les variables dans $ENV_FILE si nécessaire"
    else
        print_warning "Template $ENV_TEMPLATE introuvable, création d'un .env minimal"
        cat > "$ENV_FILE" << 'EOF'
# Configuration Pi4 Standalone
DASHBOARD_PORT=3000
DATABASE_URL=sqlite:///app/data/linkedin.db
REDIS_URL=redis://redis-dashboard:6379
REDIS_HOST=redis-bot
REDIS_PORT=6379
LOG_LEVEL=INFO
PYTHONPATH=/app
HEADLESS=true
NEXT_TELEMETRY_DISABLED=1
EOF
        print_success "Fichier .env minimal créé"
    fi
else
    print_success "Fichier .env existant trouvé"
fi

# Créer les répertoires nécessaires
print_info "Création des répertoires de données..."
mkdir -p data logs config
print_success "Répertoires créés: data/, logs/, config/"

# Vérifier config.yaml
if [ ! -f "config/config.yaml" ]; then
    print_warning "Fichier config/config.yaml manquant"
    print_info "Créez config/config.yaml avec vos paramètres LinkedIn"
fi

# Vérifier auth_state.json
if [ ! -f "auth_state.json" ]; then
    print_warning "Fichier auth_state.json manquant"
    print_info "Vous devrez vous authentifier au premier lancement"
fi

# =========================================================================
# Affichage de l'IP locale
# =========================================================================

print_header "Configuration réseau"

# Détecter l'IP locale
LOCAL_IP=$(hostname -I | awk '{print $1}')
print_info "IP locale détectée: $LOCAL_IP"
print_info "Le dashboard sera accessible sur: http://${LOCAL_IP}:3000"
print_warning "Configurez une IP fixe sur votre Freebox pour cette adresse MAC"

# =========================================================================
# Arrêt des anciens containers
# =========================================================================

print_header "Nettoyage des anciens containers"

# Arrêter les anciens containers s'ils existent
if docker ps -a | grep -q linkedin; then
    print_info "Arrêt des anciens containers LinkedIn..."
    docker compose -f docker-compose.queue.yml down 2>/dev/null || true
    docker compose -f dashboard/docker-compose.yml down 2>/dev/null || true
    docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true
    print_success "Anciens containers arrêtés"
else
    print_info "Aucun ancien container trouvé"
fi

# =========================================================================
# Build des images
# =========================================================================

print_header "Construction des images Docker"

print_info "Construction des images (peut prendre 10-15 minutes sur Pi4)..."
if docker compose -f "$COMPOSE_FILE" build --pull; then
    print_success "Images construites avec succès"
else
    print_error "Échec de la construction des images"
    exit 1
fi

# =========================================================================
# Démarrage des services
# =========================================================================

print_header "Démarrage des services"

print_info "Démarrage de tous les services..."
if docker compose -f "$COMPOSE_FILE" up -d; then
    print_success "Services démarrés"
else
    print_error "Échec du démarrage des services"
    exit 1
fi

# Attendre que les services soient prêts
print_info "Attente du démarrage complet des services (30s)..."
sleep 30

# =========================================================================
# Vérification des services
# =========================================================================

print_header "Vérification des services"

# Fonction pour vérifier un container
check_container() {
    local container_name=$1
    local service_name=$2

    if docker ps | grep -q "$container_name"; then
        local status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "unknown")
        if [ "$status" = "healthy" ] || [ "$status" = "unknown" ]; then
            print_success "$service_name: OK"
            return 0
        else
            print_warning "$service_name: Démarrage en cours (status: $status)"
            return 1
        fi
    else
        print_error "$service_name: NON DÉMARRÉ"
        return 1
    fi
}

# Vérifier chaque service
check_container "linkedin-bot-redis" "Redis Bot"
check_container "linkedin-dashboard-redis" "Redis Dashboard"
check_container "linkedin-bot-worker" "Bot Worker"
check_container "linkedin-dashboard" "Dashboard"

# =========================================================================
# Affichage des logs
# =========================================================================

print_header "Derniers logs"

print_info "Logs du Dashboard:"
docker compose -f "$COMPOSE_FILE" logs --tail=10 dashboard

print_info "Logs du Bot Worker:"
docker compose -f "$COMPOSE_FILE" logs --tail=10 bot-worker

# =========================================================================
# Statistiques ressources
# =========================================================================

print_header "Utilisation des ressources"

echo ""
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
    linkedin-dashboard linkedin-bot-worker linkedin-bot-redis linkedin-dashboard-redis 2>/dev/null || true

# =========================================================================
# Résumé final
# =========================================================================

print_header "Déploiement terminé ${ROCKET}"

echo ""
print_success "Tous les services sont démarrés"
echo ""
print_info "URLs d'accès:"
echo "  • Dashboard: http://${LOCAL_IP}:3000"
echo "  • Health Check: http://${LOCAL_IP}:3000/api/health"
echo ""
print_info "Commandes utiles:"
echo "  • Voir les logs:        docker compose -f $COMPOSE_FILE logs -f"
echo "  • Arrêter les services: docker compose -f $COMPOSE_FILE down"
echo "  • Redémarrer:           docker compose -f $COMPOSE_FILE restart"
echo "  • Voir le statut:       docker compose -f $COMPOSE_FILE ps"
echo ""
print_info "Fichiers de données:"
echo "  • Base de données: ./data/linkedin.db"
echo "  • Logs:            ./logs/"
echo "  • Config:          ./config/config.yaml"
echo ""
print_warning "Prochaines étapes:"
echo "  1. Accédez au dashboard: http://${LOCAL_IP}:3000"
echo "  2. Vérifiez la configuration: ./config/config.yaml"
echo "  3. Authentifiez-vous sur LinkedIn si nécessaire"
echo "  4. Configurez une IP fixe sur la Freebox (DHCP statique)"
echo ""
