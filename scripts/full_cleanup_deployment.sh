#!/bin/bash

# =========================================================================
# 🧹 Script de Nettoyage COMPLET des Déploiements Précédents
# =========================================================================
# Ce script supprime TOUS les conteneurs, réseaux et images liés au projet.
# Il est conçu pour remettre le système "à propre" avant une réinstallation.
#
# USAGE:
#   ./scripts/full_cleanup_deployment.sh       (Mode interactif)
#   ./scripts/full_cleanup_deployment.sh -y    (Force / Yes to all)
# =========================================================================

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Mode force
FORCE=false
if [[ "$1" == "-y" || "$1" == "--yes" ]]; then
    FORCE=true
fi

print_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }
print_info() { echo -e "ℹ️  $1"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Confirmation
if [ "$FORCE" = false ]; then
    print_warning "Ce script va supprimer TOUS les conteneurs et images Docker du projet."
    print_warning "Les données persistantes (dossier data/, config/) seront conservées."
    read -p "Voulez-vous continuer ? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Annulé."
        exit 1
    fi
fi

print_header "1. Arrêt des services Docker"

# Arrêt via Docker Compose si possible
if [ -f "docker-compose.pi4-standalone.yml" ]; then
    print_info "Arrêt via docker-compose..."
    docker compose -f docker-compose.pi4-standalone.yml down --remove-orphans || true
fi

# Arrêt forcé des conteneurs résiduels par nom
CONTAINERS="linkedin-bot-worker linkedin-bot-api linkedin-dashboard linkedin-bot-redis linkedin-dashboard-redis"
for container in $CONTAINERS; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        print_info "Arrêt forcé et suppression de $container..."
        docker rm -f $container 2>/dev/null || true
    fi
done

print_header "2. Nettoyage des Images Docker"

# Suppression des images spécifiques au projet
IMAGES="linkedin-bot-worker linkedin-bot-api linkedin-dashboard"
for image in $IMAGES; do
    # Trouver l'ID de l'image (y compris les tags)
    IMG_IDS=$(docker images --filter=reference="$image" -q)
    if [ ! -z "$IMG_IDS" ]; then
        print_info "Suppression de l'image $image..."
        docker rmi -f $IMG_IDS 2>/dev/null || true
    else
        print_info "Image $image non trouvée (déjà supprimée)."
    fi
done

print_header "3. Nettoyage des Volumes Docker (Cache)"

# Supprimer les volumes nommés (redis data) si demandé ?
# Par défaut on garde les volumes pour ne pas perdre la queue Redis si c'était pas voulu.
# Mais pour un "full cleanup deployment", on reset souvent tout.
# On va supprimer les volumes définis dans le compose
if [ -f "docker-compose.pi4-standalone.yml" ]; then
    print_info "Suppression des volumes Docker orphelins..."
    docker compose -f docker-compose.pi4-standalone.yml down -v --remove-orphans || true
fi

print_header "4. Nettoyage Système (Dangling)"

print_info "Suppression des images 'dangling' (intermédiaires)..."
docker image prune -f 2>/dev/null || true

print_header "5. Nettoyage Processus Zombies"

# Tuer les processus Python liés au bot qui tourneraient hors Docker
PIDS=$(pgrep -f "src.queue.worker|src.api.app" || true)
if [ ! -z "$PIDS" ]; then
    print_warning "Processus Python zombies détectés, arrêt en cours..."
    echo "$PIDS" | xargs kill -9 2>/dev/null || true
    print_success "Processus tués."
else
    print_info "Aucun processus zombie détecté."
fi

print_header "6. Nettoyage Fichiers Temporaires"

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
# Ne pas supprimer node_modules car long à réinstaller, sauf si flag spécifique ?
# On va le laisser pour l'instant.

print_header "✅ Nettoyage Complet Terminé"
print_info "Vous pouvez maintenant relancer le déploiement avec :"
print_info "./scripts/deploy_pi4_standalone.sh"
