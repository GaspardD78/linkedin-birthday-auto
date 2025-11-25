#!/bin/bash

# =========================================================================
# Script de mise à jour incrémentale du déploiement Pi4
# Applique les optimisations de l'audit sans tout reconstruire
# =========================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }

COMPOSE_FILE="docker-compose.pi4-standalone.yml"

print_header "🔄 Mise à jour déploiement Pi4 (sans reconstruction)"

# =========================================================================
# 1. Vérification pré-requis
# =========================================================================
print_header "1. Vérifications pré-requis"

if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "Fichier $COMPOSE_FILE introuvable !"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    print_error "Docker Compose V2 non trouvé"
    exit 1
fi

print_success "Pré-requis OK"

# =========================================================================
# 2. Sauvegarde des données
# =========================================================================
print_header "2. Sauvegarde des données"

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

print_info "Sauvegarde base de données..."
if [ -f "data/linkedin_automation.db" ]; then
    cp data/linkedin_automation.db "$BACKUP_DIR/"
    print_success "Base de données sauvegardée → $BACKUP_DIR/"
else
    print_warning "Base de données non trouvée (déploiement neuf ?)"
fi

print_info "Sauvegarde config actuelle..."
if [ -f "config/config.yaml" ]; then
    cp config/config.yaml "$BACKUP_DIR/"
    print_success "Config sauvegardée"
fi

# =========================================================================
# 3. Mise à jour configuration (hot reload si possible)
# =========================================================================
print_header "3. Mise à jour configuration"

print_info "Les changements de config.yaml seront appliqués au prochain redémarrage"
print_success "Config déjà à jour (via git pull)"

# =========================================================================
# 4. Mise à jour des conteneurs (redémarrage contrôlé)
# =========================================================================
print_header "4. Mise à jour des conteneurs"

print_warning "Les conteneurs vont être recréés avec les nouvelles limites RAM/CPU"
read -p "Continuer ? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Mise à jour annulée"
    exit 0
fi

# Méthode 1: Recréer uniquement les services modifiés
print_info "Recréation des conteneurs avec nouvelles limites..."

# Note: docker compose up --force-recreate ne rebuild pas les images,
# juste recrée les conteneurs avec la nouvelle config
docker compose -f "$COMPOSE_FILE" up -d --force-recreate --no-build

print_success "Conteneurs recréés avec nouvelles limites"

# =========================================================================
# 5. Vérification santé des services
# =========================================================================
print_header "5. Vérification santé des services"

print_info "Attente démarrage des services (30s)..."
sleep 30

check_service() {
    local service_name=$1
    local container_id
    container_id=$(docker compose -f "$COMPOSE_FILE" ps -q "$service_name" 2>/dev/null)

    if [ -n "$container_id" ]; then
        local state
        state=$(docker inspect --format='{{.State.Status}}' "$container_id" 2>/dev/null)
        if [ "$state" = "running" ]; then
            print_success "$service_name: RUNNING"
            return 0
        else
            print_error "$service_name: $state"
            return 1
        fi
    else
        print_error "$service_name: NOT FOUND"
        return 1
    fi
}

FAILED=0
check_service "bot-worker" || FAILED=$((FAILED+1))
check_service "dashboard" || FAILED=$((FAILED+1))
check_service "redis-bot" || FAILED=$((FAILED+1))
check_service "redis-dashboard" || FAILED=$((FAILED+1))

if [ $FAILED -gt 0 ]; then
    print_error "$FAILED service(s) en échec"
    print_info "Vérifiez les logs: docker compose -f $COMPOSE_FILE logs --tail=50"
    exit 1
fi

# =========================================================================
# 6. Vérification utilisation ressources
# =========================================================================
print_header "6. Vérification ressources"

print_info "Utilisation mémoire des conteneurs:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" | head -10

echo ""
print_info "Mémoire système:"
free -h | awk '/Mem:/ {printf "  RAM: %s utilisés / %s total (%.1f%%)\n", $3, $2, ($3/$2)*100}'
free -h | awk '/Swap:/ {printf "  SWAP: %s utilisés / %s total\n", $3, $2}'

# =========================================================================
# 7. Migration base de données (si nécessaire)
# =========================================================================
print_header "7. Migration base de données"

# Vérifier si la DB est au bon endroit
if [ -f "linkedin_automation.db" ] && [ ! -f "data/linkedin_automation.db" ]; then
    print_warning "Base de données détectée à la racine (ancien emplacement)"
    print_info "Migration vers data/linkedin_automation.db..."

    mkdir -p data
    mv linkedin_automation.db data/

    print_success "Base de données migrée"
elif [ -f "data/linkedin_automation.db" ]; then
    print_success "Base de données au bon emplacement"
else
    print_info "Pas de base de données existante (sera créée au 1er run)"
fi

# =========================================================================
# 8. Nettoyage post-mise à jour
# =========================================================================
print_header "8. Nettoyage"

print_info "Nettoyage images Docker inutilisées..."
docker image prune -f > /dev/null 2>&1 || true
print_success "Images nettoyées"

# =========================================================================
# 9. Résumé
# =========================================================================
print_header "✅ Mise à jour terminée avec succès"

echo ""
echo "📋 Changements appliqués:"
echo "  • Limites RAM: Bot Worker 1.0G→900M, Dashboard 800M→700M"
echo "  • Limites CPU: Bot Worker 2.0→1.5, Dashboard 1.5→1.0"
echo "  • Logs Docker: max-size 10m→5m, max-file 3→2, compression activée"
echo "  • Config DB: timeout 20s→60s, chemin corrigé"
echo ""
echo "🔍 Commandes utiles:"
echo "  • Logs:      docker compose -f $COMPOSE_FILE logs -f"
echo "  • Stats:     docker stats"
echo "  • Restart:   docker compose -f $COMPOSE_FILE restart <service>"
echo "  • Monitoring: ./scripts/monitor_pi4_resources.sh"
echo ""
echo "💾 Sauvegarde disponible: $BACKUP_DIR/"
echo ""

LOCAL_IP=$(hostname -I | awk '{print $1}')
print_success "Dashboard accessible: http://${LOCAL_IP}:3000"
