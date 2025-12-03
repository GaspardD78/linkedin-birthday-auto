#!/bin/bash

# =========================================================================
# Script de désinstallation complète des automatisations LinkedIn Bot
# Supprime tous les services systemd, timers et configurations
# =========================================================================

set -e

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

print_header() { echo -e "\n${BLUE}${BOLD}═══ $1 ═══${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }

# Vérification des droits root
if [ "$EUID" -ne 0 ]; then
    print_error "Ce script doit être exécuté avec sudo"
    print_info "Usage: sudo ./scripts/uninstall_automation_pi4.sh"
    exit 1
fi

print_header "🗑️  Désinstallation Automatisations LinkedIn Bot"

echo -e "${YELLOW}${BOLD}⚠️  ATTENTION ⚠️${NC}"
echo ""
echo "Ce script va désinstaller COMPLÈTEMENT toutes les automatisations :"
echo "  • Service de démarrage automatique (linkedin-bot.service)"
echo "  • Monitoring horaire (linkedin-bot-monitor)"
echo "  • Backup quotidien (linkedin-bot-backup)"
echo "  • Nettoyage hebdomadaire (linkedin-bot-cleanup)"
echo ""
echo "Le bot et les données NE SERONT PAS supprimés."
echo "Seules les automatisations systemd seront retirées."
echo ""

read -p "Voulez-vous continuer ? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Désinstallation annulée"
    exit 0
fi

# =========================================================================
# 1. Arrêt de tous les services et timers
# =========================================================================
print_header "1. Arrêt des Services et Timers"

SERVICES=(
    "linkedin-bot.service"
    "linkedin-bot-monitor.service"
    "linkedin-bot-monitor.timer"
    "linkedin-bot-backup.service"
    "linkedin-bot-backup.timer"
    "linkedin-bot-cleanup.service"
    "linkedin-bot-cleanup.timer"
)

for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        print_info "Arrêt de $service..."
        systemctl stop "$service" 2>/dev/null || print_warning "Impossible d'arrêter $service"
        print_success "$service arrêté"
    else
        print_info "$service déjà arrêté ou inexistant"
    fi
done

# =========================================================================
# 2. Désactivation des services
# =========================================================================
print_header "2. Désactivation des Services"

for service in "${SERVICES[@]}"; do
    if systemctl is-enabled --quiet "$service" 2>/dev/null; then
        print_info "Désactivation de $service..."
        systemctl disable "$service" 2>/dev/null || print_warning "Impossible de désactiver $service"
        print_success "$service désactivé"
    else
        print_info "$service déjà désactivé ou inexistant"
    fi
done

# =========================================================================
# 3. Suppression des fichiers systemd
# =========================================================================
print_header "3. Suppression des Fichiers Systemd"

SYSTEMD_DIR="/etc/systemd/system"

for service in "${SERVICES[@]}"; do
    SERVICE_FILE="$SYSTEMD_DIR/$service"
    if [ -f "$SERVICE_FILE" ]; then
        print_info "Suppression de $SERVICE_FILE..."
        rm -f "$SERVICE_FILE"
        print_success "$service supprimé"
    else
        print_info "$service n'existe pas dans $SYSTEMD_DIR"
    fi
done

# Rechargement de systemd
print_info "Rechargement de systemd..."
systemctl daemon-reload
print_success "Systemd rechargé"

# =========================================================================
# 4. Arrêt des conteneurs Docker (optionnel)
# =========================================================================
print_header "4. Gestion des Conteneurs Docker"

echo ""
read -p "Voulez-vous aussi arrêter les conteneurs Docker du bot ? [y/N] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    COMPOSE_FILE="docker-compose.pi4-standalone.yml"

    if [ -f "$COMPOSE_FILE" ]; then
        print_info "Arrêt des conteneurs Docker..."
        docker compose -f "$COMPOSE_FILE" down 2>/dev/null || print_warning "Échec de l'arrêt des conteneurs"
        print_success "Conteneurs Docker arrêtés"
    else
        print_warning "Fichier $COMPOSE_FILE introuvable"
    fi
else
    print_info "Conteneurs Docker conservés en l'état"
    print_warning "Pour les arrêter manuellement : docker compose -f docker-compose.pi4-standalone.yml down"
fi

# =========================================================================
# 5. Nettoyage des configurations système (optionnel)
# =========================================================================
print_header "5. Nettoyage Configurations Système"

echo ""
read -p "Voulez-vous supprimer les configurations sysctl optimisées ? [y/N] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    SYSCTL_FILE="/etc/sysctl.d/99-docker-linkedin.conf"

    if [ -f "$SYSCTL_FILE" ]; then
        print_info "Suppression de $SYSCTL_FILE..."
        rm -f "$SYSCTL_FILE"
        sysctl --system > /dev/null 2>&1
        print_success "Configuration sysctl supprimée"
    else
        print_info "Fichier sysctl introuvable"
    fi
else
    print_info "Configuration sysctl conservée"
fi

# =========================================================================
# 6. Vérification finale
# =========================================================================
print_header "6. Vérification Finale"

echo -e "${BOLD}Services restants :${NC}"
REMAINING=$(systemctl list-units --all 'linkedin-bot*' --no-pager 2>/dev/null | grep linkedin-bot || echo "Aucun")

if [ "$REMAINING" = "Aucun" ]; then
    print_success "Tous les services ont été désinstallés"
else
    print_warning "Certains services persistent :"
    echo "$REMAINING"
fi

echo ""
echo -e "${BOLD}Timers restants :${NC}"
REMAINING_TIMERS=$(systemctl list-timers --all 'linkedin-bot*' --no-pager 2>/dev/null | grep linkedin-bot || echo "Aucun")

if [ "$REMAINING_TIMERS" = "Aucun" ]; then
    print_success "Tous les timers ont été désinstallés"
else
    print_warning "Certains timers persistent :"
    echo "$REMAINING_TIMERS"
fi

# =========================================================================
# 7. Résumé
# =========================================================================
print_header "✅ Désinstallation Terminée"

cat << EOF

${GREEN}${BOLD}Services désinstallés :${NC}
  ✅ linkedin-bot.service (démarrage auto)
  ✅ linkedin-bot-monitor.timer (monitoring horaire)
  ✅ linkedin-bot-backup.timer (backup quotidien)
  ✅ linkedin-bot-cleanup.timer (nettoyage hebdomadaire)

${BOLD}Ce qui reste :${NC}
  • Projet LinkedIn Bot : $(pwd)
  • Base de données SQLite : data/linkedin.db
  • Fichiers de configuration : .env, config/
  • Images Docker : $(docker images | grep -c linkedin || echo "0") image(s)

${BOLD}Pour gérer le bot manuellement :${NC}
  • Démarrer :  docker compose -f docker-compose.pi4-standalone.yml up -d
  • Arrêter :   docker compose -f docker-compose.pi4-standalone.yml down
  • Logs :      docker compose -f docker-compose.pi4-standalone.yml logs -f

${BOLD}Pour réinstaller les automatisations :${NC}
  ${CYAN}sudo ./scripts/install_automation_pi4.sh${NC}

${BOLD}Pour supprimer COMPLÈTEMENT le bot (données incluses) :${NC}
  ${RED}# ATTENTION : Ceci supprimera TOUTES les données !${NC}
  docker compose -f docker-compose.pi4-standalone.yml down -v
  docker rmi \$(docker images 'linkedin*' -q) 2>/dev/null
  rm -rf data/ logs/ backups/

EOF

print_success "Désinstallation réussie ! 🎉"
print_info "Le trafic réseau anormal devrait maintenant cesser."
