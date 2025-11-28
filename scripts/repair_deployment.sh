#!/bin/bash

# =========================================================================
# 🔧 Script de RÉPARATION pour Raspberry Pi 4
# =========================================================================
# Ce script répare une installation existante sans la réinstaller complètement.
# Il corrige les permissions, redémarre les services et peut reconstruire
# les images si nécessaire.
#
# USAGE:
#   ./scripts/repair_deployment.sh           (Mode standard)
#   ./scripts/repair_deployment.sh --rebuild (Force la reconstruction)
#   ./scripts/repair_deployment.sh --quick   (Réparation rapide, pas de rebuild)
# =========================================================================

set -e  # Arrêt immédiat en cas d'erreur

# --- Configuration ---
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
REBUILD=false
QUICK=false

# Parse arguments
for arg in "$@"; do
    if [[ "$arg" == "--rebuild" ]]; then
        REBUILD=true
    elif [[ "$arg" == "--quick" ]]; then
        QUICK=true
    fi
done

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Fonctions ---

print_banner() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║  ${BOLD}🔧 RÉPARATION - LinkedIn Birthday Bot${NC}${CYAN}                    ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_header() { echo -e "\n${BLUE}${BOLD}=== $1 ===${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }

# =========================================================================
# MAIN
# =========================================================================

print_banner

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "Fichier $COMPOSE_FILE introuvable !"
    print_info "Exécutez ce script à la racine du projet."
    exit 1
fi

# =========================================================================
# ÉTAPE 1 : Vérification de l'état actuel
# =========================================================================
print_header "1. Vérification de l'état actuel"

# Vérifier Docker
if ! docker ps &> /dev/null; then
    print_error "Docker n'est pas accessible."
    print_info "Vérifiez que Docker est installé et que vous avez les permissions."
    exit 1
fi

print_success "Docker accessible"

# Vérifier si des conteneurs existent
CONTAINER_COUNT=$(docker ps -a --filter "name=linkedin" --format "{{.Names}}" 2>/dev/null | wc -l)
if [ "$CONTAINER_COUNT" -eq 0 ]; then
    print_warning "Aucun conteneur détecté. Une installation complète est nécessaire."
    print_info "Utilisez plutôt : ./scripts/easy_deploy.sh"
    exit 1
fi

print_info "Conteneurs détectés : $CONTAINER_COUNT"

# =========================================================================
# ÉTAPE 2 : Réparation des permissions
# =========================================================================
print_header "2. Réparation des permissions"

# Créer les dossiers s'ils n'existent pas
print_info "Vérification des dossiers requis..."
for dir in data logs config; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "Dossier $dir créé"
    else
        print_info "Dossier $dir existe"
    fi
done

# Réparer les permissions des dossiers
print_info "Application des permissions..."
for dir in data logs; do
    if [ -d "$dir" ]; then
        # Essayer de changer les permissions, sinon utiliser sudo
        if ! chmod 777 "$dir" 2>/dev/null; then
            print_warning "Permissions insuffisantes pour $dir, utilisation de sudo..."
            if command -v sudo &> /dev/null; then
                if sudo chmod 777 "$dir"; then
                    print_success "Permissions de $dir réparées (avec sudo)"
                else
                    print_error "Impossible de modifier les permissions de $dir"
                fi
            else
                print_error "sudo non disponible"
                print_info "Essayez manuellement : sudo chmod 777 $dir"
            fi
        else
            print_success "Permissions de $dir réparées"
        fi
    fi
done

# Réparer les permissions du fichier de base de données
if [ -f "data/linkedin.db" ]; then
    if ! chmod 666 data/linkedin.db 2>/dev/null; then
        print_warning "Utilisation de sudo pour data/linkedin.db..."
        sudo chmod 666 data/linkedin.db 2>/dev/null || true
    fi
    print_success "Permissions de la base de données réparées"
fi

# Vérifier les fichiers de configuration
print_info "Vérification des fichiers de configuration..."
for file in "auth_state.json" "config/config.yaml"; do
    if [ ! -f "$file" ]; then
        print_warning "Fichier manquant: $file"
        if [ "$file" == "auth_state.json" ]; then
            echo "{}" > "$file"
            print_success "Fichier $file créé (vide)"
        fi
    else
        print_success "Fichier $file présent"
    fi
done

# =========================================================================
# ÉTAPE 3 : Gestion des conteneurs
# =========================================================================
print_header "3. Gestion des conteneurs"

if [ "$REBUILD" = true ]; then
    print_info "Arrêt des conteneurs pour reconstruction..."
    docker compose -f "$COMPOSE_FILE" down

    print_info "Reconstruction des images..."
    print_warning "Cela peut prendre 15-20 minutes..."
    export DOCKER_BUILDKIT=1
    export NPM_CONFIG_TIMEOUT=600000

    if docker compose -f "$COMPOSE_FILE" build; then
        print_success "Images reconstruites"
    else
        print_error "Échec de la reconstruction"
        exit 1
    fi

    print_info "Démarrage des nouveaux conteneurs..."
    docker compose -f "$COMPOSE_FILE" up -d
    print_success "Conteneurs redémarrés"

elif [ "$QUICK" = true ]; then
    print_info "Redémarrage rapide des conteneurs..."
    docker compose -f "$COMPOSE_FILE" restart
    print_success "Conteneurs redémarrés"

else
    # Mode standard : vérifier si rebuild nécessaire
    print_info "Vérification de l'état des conteneurs..."

    RUNNING_COUNT=$(docker compose -f "$COMPOSE_FILE" ps --services --filter "status=running" 2>/dev/null | wc -l)
    TOTAL_COUNT=$(docker compose -f "$COMPOSE_FILE" ps --services 2>/dev/null | wc -l)

    print_info "Conteneurs en cours d'exécution : $RUNNING_COUNT / $TOTAL_COUNT"

    if [ "$RUNNING_COUNT" -eq "$TOTAL_COUNT" ] && [ "$TOTAL_COUNT" -gt 0 ]; then
        print_success "Tous les conteneurs sont en cours d'exécution"
        print_info "Redémarrage pour appliquer les changements..."
        docker compose -f "$COMPOSE_FILE" restart
        print_success "Conteneurs redémarrés"
    else
        print_warning "Certains conteneurs ne sont pas en cours d'exécution"
        print_info "Tentative de démarrage..."
        docker compose -f "$COMPOSE_FILE" up -d
        print_success "Conteneurs démarrés"
    fi
fi

# =========================================================================
# ÉTAPE 4 : Vérification finale
# =========================================================================
print_header "4. Vérification finale"

print_info "Attente de l'initialisation (15s)..."
sleep 15

# Vérifier l'état des conteneurs
check_service() {
    local service_name=$1
    local container_id
    container_id=$(docker compose -f "$COMPOSE_FILE" ps -q "$service_name" 2>/dev/null)

    if [ -n "$container_id" ]; then
        local state
        state=$(docker inspect --format='{{.State.Status}}' "$container_id" 2>/dev/null || echo "unknown")
        if [ "$state" == "running" ]; then
            echo -e "  • $service_name: ${GREEN}✓ Running${NC}"
            return 0
        else
            echo -e "  • $service_name: ${RED}✗ $state${NC}"
            return 1
        fi
    else
        echo -e "  • $service_name: ${RED}✗ Not found${NC}"
        return 1
    fi
}

print_info "État des services :"
ALL_OK=true
check_service "bot-worker" || ALL_OK=false
check_service "dashboard" || ALL_OK=false
check_service "redis-bot" || ALL_OK=false
check_service "redis-dashboard" || ALL_OK=false

echo ""

# =========================================================================
# RÉSULTAT FINAL
# =========================================================================
print_header "RÉSULTAT FINAL"

if [ "$ALL_OK" = true ]; then
    print_success "Réparation terminée avec succès !"
    echo ""

    LOCAL_IP=$(hostname -I | awk '{print $1}')

    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║  ${BOLD}${GREEN}✅ RÉPARATION RÉUSSIE !${NC}${CYAN}                                   ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "📍 ${BOLD}Accès Dashboard :${NC} ${GREEN}http://${LOCAL_IP}:3000${NC}"
    echo ""
    echo -e "${BOLD}Commandes utiles :${NC}"
    echo -e "  📊 Voir les logs :       ${CYAN}docker compose -f $COMPOSE_FILE logs -f${NC}"
    echo -e "  🔄 Redémarrer :          ${CYAN}docker compose -f $COMPOSE_FILE restart${NC}"
    echo -e "  ✅ Vérifier l'état :     ${CYAN}./scripts/verify_rpi_docker.sh${NC}"
    echo ""

    exit 0
else
    print_error "Certains services ne fonctionnent pas correctement"
    echo ""
    print_warning "Actions recommandées :"
    echo -e "  1. Vérifier les logs : ${CYAN}docker compose -f $COMPOSE_FILE logs${NC}"
    echo -e "  2. Tenter une reconstruction : ${CYAN}./scripts/repair_deployment.sh --rebuild${NC}"
    echo -e "  3. En cas de problème persistant : ${CYAN}./scripts/easy_deploy.sh${NC}"
    echo ""

    exit 1
fi
