#!/bin/bash

# =========================================================================
# Script de diagnostic pour le conteneur bot-api
# =========================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }

COMPOSE_FILE="docker-compose.pi4-standalone.yml"

print_header "Diagnostic du conteneur bot-api"

# 1. Vérifier si le conteneur existe
print_info "1. Vérification de l'existence du conteneur..."
if docker ps -a | grep -q bot-api; then
    print_success "Conteneur bot-api trouvé"
else
    print_error "Conteneur bot-api introuvable"
    exit 1
fi

# 2. Afficher le statut du conteneur
print_info "2. Statut du conteneur..."
docker ps -a --filter name=bot-api --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 3. Vérifier les logs
print_info "3. Derniers logs du conteneur (50 lignes)..."
docker logs bot-api --tail 50 2>&1

# 4. Vérifier le healthcheck
print_info "4. Détails du healthcheck..."
docker inspect bot-api --format='{{json .State.Health}}' | python3 -m json.tool 2>/dev/null || echo "Pas de healthcheck actif"

# 5. Vérifier les processus dans le conteneur
print_info "5. Processus en cours dans le conteneur..."
docker exec bot-api ps aux 2>/dev/null || print_warning "Impossible d'exécuter ps (conteneur arrêté?)"

# 6. Tester la connexion au port 8000
print_info "6. Test de connexion au port 8000..."
docker exec bot-api curl -f http://localhost:8000/health 2>/dev/null && print_success "Endpoint /health accessible" || print_error "Endpoint /health inaccessible"

# 7. Vérifier curl dans le conteneur
print_info "7. Vérification de la disponibilité de curl..."
docker exec bot-api which curl 2>/dev/null && print_success "curl installé" || print_warning "curl non installé (problème de healthcheck possible)"

# 8. Vérifier les permissions de la base de données
print_info "8. Permissions de la base de données..."
ls -la data/linkedin.db 2>/dev/null || print_warning "Base de données non trouvée"

# 9. Vérifier Redis
print_info "9. Connexion à Redis..."
docker exec bot-api python3 -c "import redis; r=redis.Redis(host='redis-bot', port=6379); r.ping(); print('OK')" 2>/dev/null && print_success "Redis accessible" || print_error "Redis inaccessible"

# 10. Recommandations
print_header "Recommandations"
print_info "Si le problème persiste:"
echo "  1. Vérifiez les logs complets: docker logs bot-api"
echo "  2. Redémarrez le conteneur: docker compose -f $COMPOSE_FILE restart api"
echo "  3. Supprimez et recréez: docker compose -f $COMPOSE_FILE up -d --force-recreate api"
echo "  4. Vérifiez que curl est installé dans l'image"
echo "  5. Augmentez start_period dans le healthcheck si l'API démarre lentement"
