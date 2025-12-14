#!/bin/bash

# =========================================================================
# Script de nettoyage COMPLET pour Raspberry Pi 4 (Reset Environnement)
# Supprime TOUS les conteneurs, TOUTES les images et TOUS les volumes
# Opère SANS sudo (suppose que l'utilisateur est dans le groupe docker)
# =========================================================================

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# 0. Avertissement et Confirmation
echo -e "${RED}######################################################################${NC}"
echo -e "${RED}#                        ATTENTION - DANGER                          #${NC}"
echo -e "${RED}######################################################################${NC}"
echo -e "${YELLOW}Ce script va effectuer un NETTOYAGE COMPLET de l'environnement Docker.${NC}"
echo -e "${YELLOW}Les actions suivantes seront effectuées :${NC}"
echo -e "  1. Arrêt de tous les conteneurs"
echo -e "  2. Suppression de TOUS les conteneurs"
echo -e "  3. Suppression de TOUTES les images Docker (même utilisées ailleurs !)"
echo -e "  4. Suppression de TOUS les volumes et réseaux Docker"
echo -e "  5. Arrêt forcé des processus Python/Chrome liés au bot"
echo -e ""
echo -e "Note : Les données persistantes (dossier data/, config/, .env) sont CONSERVÉES."
echo -e ""

read -p "Êtes-vous sûr de vouloir continuer ? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Opération annulée."
    exit 1
fi

print_header "🧹 Démarrage du Grand Nettoyage"

# 1. Arrêt via Docker Compose (tentative propre)
print_info "Arrêt des services via Docker Compose..."
if [ -f "docker-compose.pi4-standalone.yml" ]; then
    docker compose -f docker-compose.pi4-standalone.yml down --volumes --remove-orphans 2>/dev/null || true
else
    print_warning "Fichier docker-compose.pi4-standalone.yml non trouvé, passage à l'arrêt forcé."
fi

# 2. Arrêt forcé et suppression de tous les conteneurs
print_info "Arrêt et suppression de TOUS les conteneurs..."
CONTAINERS=$(docker ps -aq)
if [ -n "$CONTAINERS" ]; then
    docker stop $CONTAINERS 2>/dev/null || true
    docker rm -f $CONTAINERS 2>/dev/null || true
    print_success "Tous les conteneurs ont été supprimés."
else
    print_info "Aucun conteneur à supprimer."
fi

# 3. Suppression des images (y compris non-dangling)
print_info "Suppression de TOUTES les images Docker..."
# -a : remove all unused images, not just dangling ones
# -f : force (no confirmation prompt)
docker image prune -a -f
print_success "Toutes les images Docker résiduelles ont été supprimées."

# 4. Nettoyage des volumes et réseaux
print_info "Nettoyage des volumes et réseaux orphelins..."
docker volume prune -f
docker network prune -f
print_success "Volumes et réseaux nettoyés."

# 5. Tuer les processus zombies (Bot & Dashboard)
print_info "Arrêt des processus zombies résiduels..."
# Tuer les processus Python liés au projet (en évitant de se tuer soi-même si lancé via python, though this is bash)
pkill -f "python.*linkedin" 2>/dev/null || true
pkill -f "python.*visit_profiles" 2>/dev/null || true
pkill -f "chrome" 2>/dev/null || true
pkill -f "chromium" 2>/dev/null || true
# Tuer node (Dashboard)
pkill -f "next-server" 2>/dev/null || true
print_success "Processus zombies nettoyés."

# 6. Nettoyage fichiers temporaires locaux
print_info "Nettoyage des fichiers temporaires Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
print_success "Cache Python nettoyé."

# Rapport final
print_header "✨ Nettoyage Terminé"
print_info "Votre environnement est propre."
print_info "Pour redéployer, utilisez : ./scripts/deploy_pi4_standalone.sh"
