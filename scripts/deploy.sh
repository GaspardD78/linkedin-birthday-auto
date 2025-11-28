#!/bin/bash
#
# Script de déploiement automatique pour LinkedIn Birthday Auto
#
# Ce script automatise le processus de déploiement complet :
# - Git pull pour récupérer les dernières modifications
# - Rebuild des images Docker
# - Restart des services
#
# Usage:
#   ./scripts/deploy.sh [options]
#
# Options:
#   --no-pull       Ne pas faire de git pull
#   --no-rebuild    Ne pas rebuild les images
#   --service NAME  Redémarrer uniquement le service spécifié (api, worker, dashboard)
#   --help          Afficher cette aide

set -euo pipefail

# Configuration
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Options par défaut
DO_PULL=true
DO_REBUILD=true
SPECIFIC_SERVICE=""

# Fonction d'aide
show_help() {
    cat << EOF
Script de déploiement automatique - LinkedIn Birthday Auto

Usage:
  ./scripts/deploy.sh [options]

Options:
  --no-pull       Ne pas faire de git pull
  --no-rebuild    Ne pas rebuild les images Docker
  --service NAME  Redémarrer uniquement le service spécifié (api, worker, dashboard)
  --help          Afficher cette aide

Exemples:
  # Déploiement complet (pull + rebuild + restart)
  ./scripts/deploy.sh

  # Redémarrer uniquement le worker
  ./scripts/deploy.sh --no-pull --no-rebuild --service bot-worker

  # Mise à jour du code sans rebuild
  ./scripts/deploy.sh --no-rebuild

EOF
}

# Parser les arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-pull)
            DO_PULL=false
            shift
            ;;
        --no-rebuild)
            DO_REBUILD=false
            shift
            ;;
        --service)
            SPECIFIC_SERVICE="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Option inconnue: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Fonction de logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Vérifier qu'on est dans le bon répertoire
cd "$PROJECT_ROOT"

log "🚀 Démarrage du déploiement automatique"
log "Répertoire de travail: $PROJECT_ROOT"

# Étape 1: Git pull
if [ "$DO_PULL" = true ]; then
    log "📥 Récupération des dernières modifications (git pull)..."

    # Vérifier qu'on est dans un repo git
    if [ ! -d ".git" ]; then
        log_error "Pas de repository Git trouvé dans $PROJECT_ROOT"
        exit 1
    fi

    # Vérifier qu'il n'y a pas de modifications locales
    if [ -n "$(git status --porcelain)" ]; then
        log_warning "Modifications locales détectées. Stash automatique..."
        git stash save "Auto-stash before deploy $(date +'%Y-%m-%d %H:%M:%S')"
    fi

    # Pull
    if git pull; then
        log_success "Code mis à jour depuis Git"
    else
        log_error "Erreur lors du git pull"
        exit 1
    fi
else
    log_warning "Skip git pull (--no-pull)"
fi

# Étape 2: Rebuild des images
if [ "$DO_REBUILD" = true ]; then
    log "🔨 Rebuild des images Docker..."

    if docker compose -f "$COMPOSE_FILE" build; then
        log_success "Images Docker rebuilds"
    else
        log_error "Erreur lors du rebuild des images"
        exit 1
    fi
else
    log_warning "Skip rebuild (--no-rebuild)"
fi

# Étape 3: Restart des services
if [ -n "$SPECIFIC_SERVICE" ]; then
    log "🔄 Redémarrage du service: $SPECIFIC_SERVICE"

    if docker compose -f "$COMPOSE_FILE" restart "$SPECIFIC_SERVICE"; then
        log_success "Service $SPECIFIC_SERVICE redémarré"
    else
        log_error "Erreur lors du restart de $SPECIFIC_SERVICE"
        exit 1
    fi
else
    log "🔄 Redémarrage de tous les services..."

    if docker compose -f "$COMPOSE_FILE" up -d --remove-orphans; then
        log_success "Tous les services redémarrés"
    else
        log_error "Erreur lors du restart des services"
        exit 1
    fi
fi

# Étape 4: Vérification de la santé des services
log "🏥 Vérification de la santé des services..."
sleep 5  # Attendre que les services démarrent

# Vérifier l'API
log "Vérification de l'API..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    log_success "API: healthy"
else
    log_warning "API: non accessible (vérifier les logs)"
fi

# Vérifier le Dashboard
log "Vérification du Dashboard..."
DASHBOARD_PORT="${DASHBOARD_PORT:-3000}"
if curl -s http://localhost:$DASHBOARD_PORT/api/system/health > /dev/null 2>&1; then
    log_success "Dashboard: healthy"
else
    log_warning "Dashboard: non accessible (vérifier les logs)"
fi

# Afficher les logs récents
log "📋 Logs récents des services:"
docker compose -f "$COMPOSE_FILE" logs --tail=10

log_success "🎉 Déploiement terminé avec succès!"
log "Pour voir les logs en temps réel:"
echo -e "  ${BLUE}docker compose -f $COMPOSE_FILE logs -f${NC}"
