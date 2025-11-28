#!/bin/bash

# =========================================================================
# 🧹 Script de Nettoyage COMPLET et INTELLIGENT pour Raspberry Pi 4
# =========================================================================
# Ce script analyse et supprime TOUS les conteneurs, réseaux, images et
# caches liés au projet, avec un rapport détaillé de l'espace libéré.
#
# Optimisé pour Raspberry Pi 4 : évite la surcharge mémoire et libère
# un maximum d'espace disque.
#
# USAGE:
#   ./scripts/full_cleanup_deployment.sh           (Mode interactif)
#   ./scripts/full_cleanup_deployment.sh -y        (Force / Yes to all)
#   ./scripts/full_cleanup_deployment.sh -y --deep (Nettoyage approfondi)
# =========================================================================

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Mode force et deep
FORCE=false
DEEP_CLEAN=false

for arg in "$@"; do
    if [[ "$arg" == "-y" || "$arg" == "--yes" ]]; then
        FORCE=true
    elif [[ "$arg" == "--deep" ]]; then
        DEEP_CLEAN=true
    fi
done

print_header() { echo -e "\n${BLUE}${BOLD}=== $1 ===${NC}\n"; }
print_info() { echo -e "ℹ️  $1"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_size() { echo -e "${CYAN}💾 $1${NC}"; }

# Fonction pour convertir bytes en human readable
human_readable_size() {
    local bytes=$1
    if [ "$bytes" -lt 1024 ]; then
        echo "${bytes}B"
    elif [ "$bytes" -lt 1048576 ]; then
        echo "$(($bytes / 1024))KB"
    elif [ "$bytes" -lt 1073741824 ]; then
        echo "$(($bytes / 1048576))MB"
    else
        echo "$(($bytes / 1073741824))GB"
    fi
}

# =========================================================================
# Bannière
# =========================================================================
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}║  ${BOLD}🧹 NETTOYAGE INTELLIGENT - LinkedIn Birthday Bot${NC}${CYAN}        ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"

# =========================================================================
# ÉTAPE 0 : Analyse Préliminaire
# =========================================================================
print_header "ANALYSE PRÉLIMINAIRE DU SYSTÈME"

# Espace disque AVANT
DISK_BEFORE=$(df -k . | awk 'NR==2 {print $3}')
DISK_AVAIL_BEFORE=$(df -h . | awk 'NR==2 {print $4}')
print_info "Espace disque utilisé : $(df -h . | awk 'NR==2 {print $3}') / $(df -h . | awk 'NR==2 {print $2}')"
print_info "Espace disponible : ${DISK_AVAIL_BEFORE}"
echo ""

# Analyse des conteneurs du projet
print_info "Recherche des conteneurs liés au projet..."
CONTAINERS_TO_REMOVE=$(docker ps -a --filter "name=linkedin" --format "{{.Names}}" 2>/dev/null || true)
CONTAINER_COUNT=$(echo "$CONTAINERS_TO_REMOVE" | grep -v "^$" | wc -l)

if [ "$CONTAINER_COUNT" -gt 0 ]; then
    print_warning "Conteneurs détectés (${CONTAINER_COUNT}) :"
    echo "$CONTAINERS_TO_REMOVE" | sed 's/^/  - /'
else
    print_success "Aucun conteneur détecté"
fi
echo ""

# Analyse des images du projet
print_info "Recherche des images liées au projet..."
IMAGES_TO_REMOVE=$(docker images --filter=reference="linkedin*" --filter=reference="*bot*" --format "{{.Repository}}:{{.Tag}} {{.Size}}" 2>/dev/null || true)
IMAGE_COUNT=$(echo "$IMAGES_TO_REMOVE" | grep -v "^$" | wc -l)

if [ "$IMAGE_COUNT" -gt 0 ]; then
    print_warning "Images détectées (${IMAGE_COUNT}) :"
    echo "$IMAGES_TO_REMOVE" | sed 's/^/  - /'
else
    print_success "Aucune image du projet détectée"
fi
echo ""

# Analyse des volumes Docker
print_info "Recherche des volumes Docker..."
VOLUMES_COUNT=$(docker volume ls -q 2>/dev/null | wc -l)
print_info "Volumes Docker totaux : ${VOLUMES_COUNT}"
echo ""

# Analyse des images dangling
DANGLING_COUNT=$(docker images -f "dangling=true" -q 2>/dev/null | wc -l)
if [ "$DANGLING_COUNT" -gt 0 ]; then
    DANGLING_SIZE=$(docker images -f "dangling=true" --format "{{.Size}}" 2>/dev/null | head -1)
    print_warning "Images intermédiaires (dangling) : ${DANGLING_COUNT}"
else
    print_success "Aucune image intermédiaire à nettoyer"
fi
echo ""

# Analyse de la mémoire
TOTAL_MEM=$(free -h | awk 'NR==2 {print $2}')
AVAILABLE_MEM=$(free -h | awk 'NR==2 {print $7}')
print_info "Mémoire disponible : ${AVAILABLE_MEM} / ${TOTAL_MEM}"
echo ""

# Estimation de l'espace qui sera libéré
print_header "ESTIMATION DE L'ESPACE À LIBÉRER"

ESTIMATED_SPACE=0
if [ "$IMAGE_COUNT" -gt 0 ]; then
    print_info "Images du projet : ~1-3GB (estimé)"
fi
if [ "$DANGLING_COUNT" -gt 0 ]; then
    print_info "Images intermédiaires : ~500MB-2GB (estimé)"
fi
if [ "$DEEP_CLEAN" = true ]; then
    print_info "Cache Docker (deep clean) : ~500MB-1GB (estimé)"
    print_info "Fichiers temporaires Python/Node : ~100-500MB (estimé)"
fi
echo ""

# =========================================================================
# Confirmation
# =========================================================================
if [ "$FORCE" = false ]; then
    print_warning "Ce script va supprimer :"
    print_warning "  • Tous les conteneurs liés au projet LinkedIn Bot"
    print_warning "  • Toutes les images Docker du projet"
    print_warning "  • Les volumes Docker orphelins"
    print_warning "  • Les images intermédiaires (dangling)"
    print_warning "  • Les processus Python zombies"
    print_warning "  • Les fichiers temporaires (__pycache__, .next)"

    if [ "$DEEP_CLEAN" = true ]; then
        print_warning "  • Cache Docker système (deep clean)"
        print_warning "  • Cache npm et node_modules (deep clean)"
    fi

    echo ""
    print_info "Les données persistantes (data/, config/, auth_state.json) seront CONSERVÉES."
    echo ""
    read -p "Voulez-vous continuer ? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Annulé."
        exit 1
    fi
fi

# =========================================================================
# ÉTAPE 1 : Arrêt des services Docker
# =========================================================================
print_header "ÉTAPE 1/8 : Arrêt des Services Docker"

# Arrêt via Docker Compose si possible
if [ -f "docker-compose.pi4-standalone.yml" ]; then
    print_info "Arrêt des services via docker-compose..."
    docker compose -f docker-compose.pi4-standalone.yml down --remove-orphans 2>/dev/null || true
    print_success "Services arrêtés via docker-compose"
else
    print_warning "Fichier docker-compose.pi4-standalone.yml non trouvé"
fi

# Arrêt forcé des conteneurs résiduels par pattern
print_info "Recherche de conteneurs résiduels..."
ALL_LINKEDIN_CONTAINERS=$(docker ps -a --filter "name=linkedin" --format "{{.Names}}" 2>/dev/null || true)

if [ ! -z "$ALL_LINKEDIN_CONTAINERS" ]; then
    echo "$ALL_LINKEDIN_CONTAINERS" | while read container; do
        if [ ! -z "$container" ]; then
            print_info "Arrêt et suppression de $container..."
            docker rm -f "$container" 2>/dev/null || true
        fi
    done
    print_success "Conteneurs résiduels supprimés"
else
    print_success "Aucun conteneur résiduel détecté"
fi

# =========================================================================
# ÉTAPE 2 : Nettoyage des Images Docker du Projet
# =========================================================================
print_header "ÉTAPE 2/8 : Nettoyage des Images Docker"

# Suppression des images spécifiques au projet
IMAGES_PATTERNS="linkedin-bot-worker linkedin-bot-api linkedin-dashboard"
TOTAL_IMAGES_REMOVED=0

for pattern in $IMAGES_PATTERNS; do
    IMG_IDS=$(docker images --filter=reference="$pattern*" -q 2>/dev/null)
    if [ ! -z "$IMG_IDS" ]; then
        IMG_COUNT=$(echo "$IMG_IDS" | wc -l)
        print_info "Suppression de ${IMG_COUNT} image(s) correspondant à '$pattern'..."
        echo "$IMG_IDS" | xargs -r docker rmi -f 2>/dev/null || true
        TOTAL_IMAGES_REMOVED=$((TOTAL_IMAGES_REMOVED + IMG_COUNT))
    fi
done

if [ "$TOTAL_IMAGES_REMOVED" -gt 0 ]; then
    print_success "${TOTAL_IMAGES_REMOVED} image(s) du projet supprimée(s)"
else
    print_success "Aucune image du projet à supprimer"
fi

# =========================================================================
# ÉTAPE 3 : Nettoyage des Volumes Docker
# =========================================================================
print_header "ÉTAPE 3/8 : Nettoyage des Volumes Docker"

if [ -f "docker-compose.pi4-standalone.yml" ]; then
    print_info "Suppression des volumes définis dans docker-compose..."
    docker compose -f docker-compose.pi4-standalone.yml down -v --remove-orphans 2>/dev/null || true
    print_success "Volumes du compose supprimés"
fi

print_info "Suppression des volumes orphelins..."
REMOVED_VOLUMES=$(docker volume prune -f 2>/dev/null || true)
print_success "Volumes orphelins nettoyés"

# =========================================================================
# ÉTAPE 4 : Nettoyage des Réseaux Docker
# =========================================================================
print_header "ÉTAPE 4/8 : Nettoyage des Réseaux Docker"

print_info "Suppression des réseaux Docker non utilisés..."
docker network prune -f 2>/dev/null || true
print_success "Réseaux non utilisés nettoyés"

# =========================================================================
# ÉTAPE 5 : Nettoyage des Images Intermédiaires
# =========================================================================
print_header "ÉTAPE 5/8 : Nettoyage des Images Intermédiaires"

print_info "Suppression des images 'dangling' (intermédiaires)..."
DANGLING_REMOVED=$(docker image prune -f 2>/dev/null || echo "")
print_success "Images intermédiaires supprimées"

# =========================================================================
# ÉTAPE 6 : Nettoyage Approfondi Docker (Deep Clean)
# =========================================================================
if [ "$DEEP_CLEAN" = true ]; then
    print_header "ÉTAPE 6/8 : Nettoyage Approfondi Docker (Deep Clean)"

    print_warning "Nettoyage du cache de build Docker..."
    docker builder prune -f 2>/dev/null || true

    print_warning "Nettoyage de TOUTES les images non utilisées..."
    docker image prune -a -f 2>/dev/null || true

    print_warning "Nettoyage du système Docker complet..."
    docker system prune -a -f --volumes 2>/dev/null || true

    print_success "Nettoyage approfondi Docker terminé"
else
    print_header "ÉTAPE 6/8 : Nettoyage Approfondi (Ignoré)"
    print_info "Utiliser --deep pour un nettoyage approfondi du cache Docker"
fi

# =========================================================================
# ÉTAPE 7 : Nettoyage des Processus Zombies
# =========================================================================
print_header "ÉTAPE 7/8 : Nettoyage des Processus Zombies"

# Tuer les processus Python liés au bot qui tourneraient hors Docker
PIDS=$(pgrep -f "src.queue.worker|src.api.app|linkedin.*bot" 2>/dev/null || true)
if [ ! -z "$PIDS" ]; then
    print_warning "Processus Python zombies détectés, arrêt en cours..."
    echo "$PIDS" | while read pid; do
        if [ ! -z "$pid" ]; then
            print_info "Arrêt du processus PID: $pid"
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
    print_success "Processus zombies tués"
else
    print_success "Aucun processus zombie détecté"
fi

# =========================================================================
# ÉTAPE 8 : Nettoyage des Fichiers Temporaires
# =========================================================================
print_header "ÉTAPE 8/8 : Nettoyage des Fichiers Temporaires"

# Comptage avant suppression
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
NEXT_COUNT=$(find . -type d -name ".next" 2>/dev/null | wc -l)

print_info "Suppression des caches Python (__pycache__)..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
[ "$PYCACHE_COUNT" -gt 0 ] && print_success "${PYCACHE_COUNT} dossier(s) __pycache__ supprimé(s)"

print_info "Suppression des caches Next.js (.next)..."
find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
[ "$NEXT_COUNT" -gt 0 ] && print_success "${NEXT_COUNT} dossier(s) .next supprimé(s)"

# Nettoyage des fichiers .pyc
print_info "Suppression des fichiers .pyc..."
find . -type f -name "*.pyc" -delete 2>/dev/null || true
print_success "Fichiers .pyc supprimés"

# Deep clean : node_modules et cache npm
if [ "$DEEP_CLEAN" = true ]; then
    print_warning "Suppression de node_modules (deep clean)..."
    find . -type d -name "node_modules" -prune -exec rm -rf {} + 2>/dev/null || true

    print_warning "Nettoyage du cache npm..."
    npm cache clean --force 2>/dev/null || true

    print_success "Cache Node.js nettoyé (sera retéléchargé au prochain build)"
fi

# =========================================================================
# Analyse POST-NETTOYAGE
# =========================================================================
print_header "RAPPORT FINAL"

# Espace disque APRÈS
DISK_AFTER=$(df -k . | awk 'NR==2 {print $3}')
DISK_AVAIL_AFTER=$(df -h . | awk 'NR==2 {print $4}')
DISK_FREED=$((DISK_BEFORE - DISK_AFTER))
DISK_FREED_HUMAN=$(human_readable_size $((DISK_FREED * 1024)))

echo ""
print_success "Nettoyage terminé avec succès !"
echo ""
print_size "Espace disque libéré : ${DISK_FREED_HUMAN}"
print_info "Espace disponible maintenant : ${DISK_AVAIL_AFTER}"
echo ""

# Résumé
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                      RÉSUMÉ DU NETTOYAGE                     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}✅${NC} Conteneurs supprimés"
echo -e "  ${GREEN}✅${NC} Images Docker du projet supprimées"
echo -e "  ${GREEN}✅${NC} Volumes orphelins nettoyés"
echo -e "  ${GREEN}✅${NC} Réseaux non utilisés nettoyés"
echo -e "  ${GREEN}✅${NC} Images intermédiaires supprimées"
echo -e "  ${GREEN}✅${NC} Processus zombies arrêtés"
echo -e "  ${GREEN}✅${NC} Fichiers temporaires supprimés"
if [ "$DEEP_CLEAN" = true ]; then
    echo -e "  ${GREEN}✅${NC} Cache Docker système nettoyé (deep clean)"
    echo -e "  ${GREEN}✅${NC} node_modules supprimé (deep clean)"
fi
echo ""

print_info "Vous pouvez maintenant relancer le déploiement avec :"
echo -e "  ${CYAN}./scripts/easy_deploy.sh${NC}"
echo ""
print_info "Ou directement :"
echo -e "  ${CYAN}./scripts/deploy_pi4_standalone.sh${NC}"
echo ""
