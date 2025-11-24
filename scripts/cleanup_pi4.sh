#!/bin/bash
#
# Script de nettoyage pour Raspberry Pi 4
# Nettoie les containers, images et cache Docker d'une installation échouée
#
# Usage: ./scripts/cleanup_pi4.sh [--keep-volumes]
#

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions d'affichage
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# Parse arguments
KEEP_VOLUMES=false
if [ "$1" == "--keep-volumes" ]; then
    KEEP_VOLUMES=true
    print_warning "Mode de conservation des volumes activé (données préservées)"
fi

print_header "Nettoyage de l'installation Docker Pi4"

# =========================================================================
# 1. Arrêter les containers
# =========================================================================

print_info "Arrêt des containers en cours..."

# Arrêter les containers du projet
docker compose -f docker-compose.pi4-standalone.yml down 2>/dev/null || true

# Arrêter manuellement les containers si docker-compose a échoué
for container in linkedin-bot-worker linkedin-dashboard linkedin-bot-redis linkedin-dashboard-redis; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        print_info "Arrêt et suppression de $container..."
        docker stop "$container" 2>/dev/null || true
        docker rm "$container" 2>/dev/null || true
        print_success "Container $container nettoyé"
    fi
done

print_success "Containers arrêtés et supprimés"

# =========================================================================
# 2. Supprimer les images cassées ou incomplètes
# =========================================================================

print_info "Suppression des images Docker du projet..."

# Supprimer les images avec le tag du projet
for image in linkedin-birthday-auto-dashboard linkedin-birthday-auto-bot-worker; do
    if docker images --format '{{.Repository}}' | grep -q "^${image}$"; then
        print_info "Suppression de l'image $image..."
        docker rmi "$image" 2>/dev/null || docker rmi -f "$image" 2>/dev/null || true
        print_success "Image $image supprimée"
    fi
done

# Nettoyer les images "dangling" (images intermédiaires sans tag)
print_info "Nettoyage des images intermédiaires..."
DANGLING_COUNT=$(docker images -f "dangling=true" -q | wc -l)
if [ "$DANGLING_COUNT" -gt 0 ]; then
    docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || true
    print_success "$DANGLING_COUNT image(s) intermédiaire(s) supprimée(s)"
else
    print_info "Aucune image intermédiaire à nettoyer"
fi

# =========================================================================
# 3. Nettoyer le cache de build Docker
# =========================================================================

print_info "Nettoyage du cache de build Docker..."

# Afficher l'espace utilisé par le cache
CACHE_SIZE=$(docker system df | grep "Build Cache" | awk '{print $3}')
print_info "Taille du cache actuel: $CACHE_SIZE"

# Nettoyer le cache de build
docker builder prune -f
print_success "Cache de build nettoyé"

# =========================================================================
# 4. Gérer les volumes (optionnel)
# =========================================================================

if [ "$KEEP_VOLUMES" = false ]; then
    print_warning "Suppression des volumes Docker (données perdues)..."
    print_warning "Pour conserver les données, utilisez: $0 --keep-volumes"
    echo -n "Continuer ? [y/N] "
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        for volume in linkedin-bot-redis-data linkedin-dashboard-redis-data linkedin-shared-data; do
            if docker volume ls --format '{{.Name}}' | grep -q "^${volume}$"; then
                print_info "Suppression du volume $volume..."
                docker volume rm "$volume" 2>/dev/null || true
                print_success "Volume $volume supprimé"
            fi
        done
    else
        print_info "Volumes conservés"
        KEEP_VOLUMES=true
    fi
else
    print_success "Volumes conservés (données préservées)"
fi

# =========================================================================
# 5. Nettoyage général du système Docker
# =========================================================================

print_info "Nettoyage général du système Docker..."

# Nettoyer les réseaux inutilisés
docker network prune -f 2>/dev/null || true

# Afficher l'espace libéré
print_success "Nettoyage terminé"

# =========================================================================
# Résumé
# =========================================================================

print_header "Résumé du nettoyage"

echo "État du système Docker après nettoyage:"
echo ""
docker system df

echo ""
print_success "Nettoyage terminé avec succès!"
echo ""
print_info "Vous pouvez maintenant relancer le déploiement:"
echo -e "${BLUE}  ./scripts/deploy_pi4_standalone.sh${NC}"
echo ""

if [ "$KEEP_VOLUMES" = true ]; then
    print_info "Les volumes et données ont été conservés"
else
    print_warning "Les volumes ont été supprimés - vous repartez de zéro"
fi
