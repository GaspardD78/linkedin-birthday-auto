#!/bin/bash

# =========================================================================
# Script de diagnostic du trafic réseau pour LinkedIn Birthday Bot
# Identifie quelle application/conteneur consomme de la bande passante
# =========================================================================

set -e

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_header() { echo -e "\n${BLUE}${BOLD}═══ $1 ═══${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${CYAN}ℹ️  $1${NC}"; }

print_header "🔍 Diagnostic Trafic Réseau - LinkedIn Birthday Bot"

# =========================================================================
# 1. Vérification des services actifs
# =========================================================================
print_header "1. Services Systemd Actifs"

echo -e "${BOLD}Service linkedin-bot :${NC}"
if systemctl is-active --quiet linkedin-bot 2>/dev/null; then
    print_warning "Le service linkedin-bot est ACTIF (bot tourne en continu)"
    echo "  → C'est probablement la source du trafic réseau"
    echo "  → Le bot se connecte régulièrement à LinkedIn"
else
    print_success "Le service linkedin-bot est INACTIF"
fi

echo ""
echo -e "${BOLD}Timers actifs :${NC}"
systemctl list-timers linkedin-bot* --all --no-pager 2>/dev/null || print_info "Aucun timer trouvé"

# =========================================================================
# 2. État des conteneurs Docker
# =========================================================================
print_header "2. Conteneurs Docker Actifs"

if command -v docker &> /dev/null; then
    COMPOSE_FILE="docker-compose.pi4-standalone.yml"

    if [ -f "$COMPOSE_FILE" ]; then
        echo -e "${BOLD}Conteneurs en cours d'exécution :${NC}"
        docker compose -f "$COMPOSE_FILE" ps 2>/dev/null || docker ps

        echo ""
        echo -e "${BOLD}Utilisation réseau des conteneurs (dernières 30s) :${NC}"
        docker stats --no-stream --format "table {{.Name}}\t{{.NetIO}}" 2>/dev/null || print_warning "Impossible de récupérer les stats réseau"
    else
        print_warning "Fichier docker-compose.pi4-standalone.yml introuvable"
        docker ps 2>/dev/null || print_info "Aucun conteneur actif"
    fi
else
    print_error "Docker non installé ou non accessible"
fi

# =========================================================================
# 3. Surveillance du trafic réseau en temps réel
# =========================================================================
print_header "3. Trafic Réseau Temps Réel (30 secondes)"

print_info "Monitoring du trafic pendant 30 secondes..."
print_info "Cela vous donnera une idée de la quantité de données échangées."
echo ""

if command -v ifstat &> /dev/null; then
    timeout 30 ifstat -t 5 2>/dev/null || print_warning "ifstat interrompu"
elif command -v vnstat &> /dev/null; then
    vnstat -l 1 -i eth0 2>/dev/null || vnstat -l 1 -i wlan0 2>/dev/null || print_warning "vnstat échoué"
else
    print_warning "Outils de monitoring réseau non installés (ifstat, vnstat)"
    print_info "Installez-les avec : sudo apt install ifstat vnstat"

    # Fallback basique avec netstat
    if command -v netstat &> /dev/null; then
        print_info "Connexions réseau actives :"
        netstat -tunap 2>/dev/null | grep ESTABLISHED | head -20
    fi
fi

# =========================================================================
# 4. Processus consommant le plus de réseau
# =========================================================================
print_header "4. Top Processus Réseau"

if command -v nethogs &> /dev/null; then
    print_info "Surveillance pendant 15 secondes avec nethogs..."
    print_info "(Nécessite sudo pour fonctionner correctement)"
    echo ""

    if [ "$EUID" -eq 0 ]; then
        timeout 15 nethogs -t -d 5 2>/dev/null || print_warning "nethogs interrompu"
    else
        print_warning "Exécutez avec sudo pour utiliser nethogs : sudo $0"
    fi
else
    print_warning "nethogs non installé"
    print_info "Installez-le avec : sudo apt install nethogs"
    print_info "Puis relancez avec sudo : sudo $0"
fi

# =========================================================================
# 5. Analyse des logs du bot
# =========================================================================
print_header "5. Logs Récents du Bot"

if systemctl is-active --quiet linkedin-bot 2>/dev/null; then
    print_info "Dernières lignes des logs du service linkedin-bot :"
    echo ""
    journalctl -u linkedin-bot -n 50 --no-pager 2>/dev/null || print_warning "Impossible de lire les logs"
else
    print_info "Service linkedin-bot inactif, vérification des logs Docker..."

    if [ -f "docker-compose.pi4-standalone.yml" ]; then
        echo ""
        echo -e "${BOLD}Logs bot-worker (20 dernières lignes) :${NC}"
        docker compose -f docker-compose.pi4-standalone.yml logs --tail 20 bot-worker 2>/dev/null || print_warning "Impossible de lire les logs"
    fi
fi

# =========================================================================
# 6. Configuration du bot
# =========================================================================
print_header "6. Configuration Bot (Variables Réseau)"

if [ -f ".env" ]; then
    print_info "Variables potentiellement liées au réseau dans .env :"
    echo ""
    grep -E "DRY_RUN|MODE|INTERVAL|SCHEDULE|DELAY" .env 2>/dev/null || print_info "Aucune variable pertinente trouvée"
else
    print_warning "Fichier .env introuvable"
fi

# =========================================================================
# 7. Recommandations
# =========================================================================
print_header "🎯 Diagnostic & Recommandations"

echo -e "${BOLD}Causes probables du trafic réseau :${NC}"
echo ""

if systemctl is-active --quiet linkedin-bot 2>/dev/null; then
    echo "  ${RED}1. Service linkedin-bot actif en permanence${NC}"
    echo "     → Le bot se connecte régulièrement à LinkedIn"
    echo "     → ${CYAN}Solution${NC} : Arrêtez le service auto si non désiré :"
    echo "       ${YELLOW}sudo systemctl stop linkedin-bot${NC}"
    echo "       ${YELLOW}sudo systemctl disable linkedin-bot${NC}"
    echo ""
fi

echo "  ${YELLOW}2. Bot configuré pour tourner en continu${NC}"
echo "     → Vérifiez la configuration dans .env"
echo "     → Cherchez : LINKEDIN_BOT_MODE, DRY_RUN, etc."
echo ""

echo "  ${YELLOW}3. Docker télécharge/upload des images${NC}"
echo "     → Vérifiez avec : ${CYAN}docker events${NC}"
echo ""

echo ""
echo -e "${BOLD}Pour arrêter COMPLÈTEMENT le trafic :${NC}"
echo "  1. Arrêter le service : ${CYAN}sudo systemctl stop linkedin-bot${NC}"
echo "  2. Arrêter les conteneurs : ${CYAN}docker compose -f docker-compose.pi4-standalone.yml down${NC}"
echo "  3. Désactiver auto-start : ${CYAN}sudo systemctl disable linkedin-bot${NC}"
echo ""

echo -e "${BOLD}Pour désinstaller complètement les automatisations :${NC}"
echo "  ${CYAN}sudo ./scripts/uninstall_automation_pi4.sh${NC}"
echo ""

print_success "Diagnostic terminé !"
