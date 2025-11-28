#!/bin/bash

# =========================================================================
# 🚀 Easy Deploy - Orchestrateur Intelligent de Déploiement
# =========================================================================
# Ce script simplifie le déploiement complet sur Raspberry Pi 4 en
# orchestrant automatiquement les étapes de vérification, nettoyage et installation.
#
# USAGE:
#   ./scripts/easy_deploy.sh
#
# Ce script appelle dans l'ordre :
#   1. verify_rpi_docker.sh      - Vérification état actuel
#   2. full_cleanup_deployment.sh - Nettoyage conditionnel (si nécessaire)
#   3. deploy_pi4_standalone.sh  - Installation/Déploiement
#   4. verify_rpi_docker.sh      - Vérification finale
# =========================================================================

set -e  # Arrêt immédiat en cas d'erreur

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Emojis ---
ROCKET="🚀"
CHECK="✅"
CROSS="❌"
WARN="⚠️"
INFO="ℹ️"
CLEAN="🧹"
HAMMER="🔨"

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERIFY_SCRIPT="$SCRIPT_DIR/verify_rpi_docker.sh"
CLEANUP_SCRIPT="$SCRIPT_DIR/full_cleanup_deployment.sh"
DEPLOY_SCRIPT="$SCRIPT_DIR/deploy_pi4_standalone.sh"
REPAIR_SCRIPT="$SCRIPT_DIR/repair_deployment.sh"

# --- Mode d'opération ---
MODE="auto"  # auto, repair, repair-rebuild, repair-quick

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --repair)
            MODE="repair"
            ;;
        --repair-rebuild)
            MODE="repair-rebuild"
            ;;
        --repair-quick)
            MODE="repair-quick"
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  (aucun)           Mode automatique complet (vérification + nettoyage + déploiement)"
            echo "  --repair          Mode réparation (corrige permissions + redémarre)"
            echo "  --repair-rebuild  Mode réparation avec reconstruction complète des images"
            echo "  --repair-quick    Mode réparation rapide (sans rebuild)"
            echo "  --help, -h        Affiche cette aide"
            echo ""
            exit 0
            ;;
    esac
done

# --- Fonctions ---

print_banner() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║  ${BOLD}${ROCKET} EASY DEPLOY - LinkedIn Birthday Bot Deployment${NC}${CYAN}  ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}=== $1 ===${NC}"
    echo ""
}

print_success() { echo -e "${GREEN}${CHECK} $1${NC}"; }
print_error() { echo -e "${RED}${CROSS} $1${NC}"; }
print_warning() { echo -e "${YELLOW}${WARN} $1${NC}"; }
print_info() { echo -e "${INFO}  $1"; }

# Fonction pour vérifier et rendre les scripts exécutables
ensure_executable() {
    local script=$1
    if [ ! -f "$script" ]; then
        print_error "Script introuvable: $script"
        exit 1
    fi

    if [ ! -x "$script" ]; then
        print_info "Application des permissions d'exécution sur $(basename $script)..."
        chmod +x "$script"
    fi
}

# Fonction pour demander confirmation à l'utilisateur
ask_user() {
    local question=$1
    local response

    echo -e "${YELLOW}${WARN} ${BOLD}${question}${NC}"
    read -p "Votre choix [o/n]: " -n 1 -r response
    echo ""

    if [[ $response =~ ^[OoYy]$ ]]; then
        return 0
    else
        return 1
    fi
}

# =========================================================================
# MAIN - Orchestration du déploiement
# =========================================================================

cd "$PROJECT_ROOT"

print_banner

print_info "Répertoire de travail: $PROJECT_ROOT"

# Afficher le mode d'opération si ce n'est pas le mode auto
if [ "$MODE" != "auto" ]; then
    case "$MODE" in
        repair)
            print_info "Mode : RÉPARATION (standard)"
            ;;
        repair-rebuild)
            print_info "Mode : RÉPARATION avec reconstruction complète"
            ;;
        repair-quick)
            print_info "Mode : RÉPARATION rapide"
            ;;
    esac
fi

echo ""

# =========================================================================
# MODE RÉPARATION : Exécution directe du script de réparation
# =========================================================================

if [[ "$MODE" == "repair"* ]]; then
    ensure_executable "$REPAIR_SCRIPT"

    print_header "MODE RÉPARATION ACTIVÉ"
    echo ""

    case "$MODE" in
        repair-rebuild)
            print_info "Lancement de la réparation avec reconstruction complète..."
            "$REPAIR_SCRIPT" --rebuild
            ;;
        repair-quick)
            print_info "Lancement de la réparation rapide..."
            "$REPAIR_SCRIPT" --quick
            ;;
        *)
            print_info "Lancement de la réparation standard..."
            "$REPAIR_SCRIPT"
            ;;
    esac

    exit $?
fi

# =========================================================================
# ÉTAPE 1 : Vérification initiale de l'état du système
# =========================================================================

print_header "ÉTAPE 1/4 : Vérification initiale de l'état du système"

ensure_executable "$VERIFY_SCRIPT"

print_info "Lancement de la vérification..."
echo ""

# Lancer le script de vérification (capture du code de sortie)
set +e  # Désactiver temporairement l'arrêt sur erreur
"$VERIFY_SCRIPT"
VERIFY_EXIT_CODE=$?
set -e  # Réactiver l'arrêt sur erreur

echo ""

NEEDS_CLEANUP=false

# Analyser le résultat de la vérification
if [ $VERIFY_EXIT_CODE -eq 0 ]; then
    print_success "Système vérifié : aucune erreur détectée."
    print_info "Installation précédente potentiellement présente."
    NEEDS_CLEANUP=true
else
    print_warning "Vérification terminée avec $VERIFY_EXIT_CODE erreur(s)."

    # Vérifier si des conteneurs existent (signe d'installation précédente)
    if docker ps -a --format '{{.Names}}' | grep -qE "bot-worker|bot-api|dashboard|redis-bot|redis-dashboard"; then
        print_warning "Des conteneurs du projet LinkedIn Bot ont été détectés."
        NEEDS_CLEANUP=true
    else
        print_info "Aucun conteneur précédent détecté. Prêt pour une installation fraîche."
    fi
fi

# =========================================================================
# ÉTAPE 2 : Nettoyage conditionnel
# =========================================================================

print_header "ÉTAPE 2/4 : Nettoyage conditionnel"

if [ "$NEEDS_CLEANUP" = true ]; then
    if ask_user "Une installation précédente existe. Voulez-vous effectuer un nettoyage complet et réinstaller ?"; then
        echo ""
        ensure_executable "$CLEANUP_SCRIPT"

        print_info "Lancement du nettoyage complet (mode automatique -y)..."
        echo ""

        "$CLEANUP_SCRIPT" -y

        echo ""
        print_success "Nettoyage terminé avec succès !"
    else
        print_info "Nettoyage ignoré. Tentative de déploiement sans nettoyage préalable..."
        print_warning "Attention : cela peut causer des conflits si des conteneurs existent déjà."
        echo ""
    fi
else
    print_info "Aucun nettoyage nécessaire. Passage à l'installation..."
fi

# =========================================================================
# ÉTAPE 3 : Installation et déploiement
# =========================================================================

print_header "ÉTAPE 3/4 : Installation et déploiement"

ensure_executable "$DEPLOY_SCRIPT"

print_info "Lancement du déploiement complet..."
print_warning "Cette étape peut prendre 15-20 minutes (compilation Next.js)..."
echo ""

"$DEPLOY_SCRIPT"

echo ""
print_success "Déploiement terminé !"

# =========================================================================
# ÉTAPE 4 : Vérification finale
# =========================================================================

print_header "ÉTAPE 4/4 : Vérification finale"

print_info "Vérification de l'installation..."
echo ""

# Attendre quelques secondes pour laisser les services démarrer complètement
print_info "Attente de 10 secondes pour la stabilisation des services..."
sleep 10

set +e
"$VERIFY_SCRIPT"
FINAL_VERIFY_EXIT_CODE=$?
set -e

echo ""

# =========================================================================
# RÉSULTAT FINAL
# =========================================================================

print_header "RÉSULTAT FINAL"

if [ $FINAL_VERIFY_EXIT_CODE -eq 0 ]; then
    print_success "Tous les tests sont VERTS ! ${ROCKET}"
    echo ""

    # Récupérer l'IP locale
    LOCAL_IP=$(hostname -I | awk '{print $1}')

    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║  ${BOLD}${GREEN}${CHECK} DÉPLOIEMENT RÉUSSI !${NC}${CYAN}                                   ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "📍 ${BOLD}Accès Dashboard :${NC} ${GREEN}http://${LOCAL_IP}:3000${NC}"
    echo ""
    echo -e "${BOLD}Commandes utiles :${NC}"
    echo -e "  📊 Voir les logs :          ${CYAN}docker compose -f docker-compose.pi4-standalone.yml logs -f${NC}"
    echo -e "  🔄 Redémarrer services :    ${CYAN}docker compose -f docker-compose.pi4-standalone.yml restart${NC}"
    echo -e "  🛑 Arrêter services :       ${CYAN}docker compose -f docker-compose.pi4-standalone.yml down${NC}"
    echo -e "  ✅ Vérifier l'état :        ${CYAN}./scripts/verify_rpi_docker.sh${NC}"
    echo ""
    echo -e "${YELLOW}${INFO} Note :${NC} Si le dashboard affiche une erreur au début, attendez 1-2 minutes"
    echo -e "  que Next.js termine sa compilation initiale."
    echo ""

    exit 0
else
    print_error "La vérification finale a détecté des problèmes."
    echo ""
    print_warning "Actions recommandées :"
    echo -e "  1. Vérifier les logs : ${CYAN}docker compose -f docker-compose.pi4-standalone.yml logs${NC}"
    echo -e "  2. Relancer la vérification : ${CYAN}./scripts/verify_rpi_docker.sh${NC}"
    echo -e "  3. En cas de problème persistant, relancer : ${CYAN}./scripts/easy_deploy.sh${NC}"
    echo ""

    exit 1
fi
