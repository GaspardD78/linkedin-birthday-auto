#!/bin/bash
# ==============================================================================
# Script de validation de la configuration Raspberry Pi 4
# Vérifie que toutes les optimisations sont en place
# ==============================================================================

set -euo pipefail

# Déterminer le répertoire du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Charger les libs
if [[ -f "$SCRIPT_DIR/lib/common.sh" ]]; then
    source "$SCRIPT_DIR/lib/common.sh"
elif [[ -f "$PROJECT_ROOT/scripts/lib/common.sh" ]]; then
    source "$PROJECT_ROOT/scripts/lib/common.sh"
else
    # Fallback si common.sh n'est pas trouvé
    BLUE='\033[0;34m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    NC='\033[0m'
    BOLD='\033[1m'
fi

ERRORS=0
WARNINGS=0
SUCCESS=0

echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}  Validation de la Configuration Raspberry Pi 4${NC}"
echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"

# Fonction de vérification
check_pass() {
    echo -e "${GREEN}✅ PASS${NC} $1"
    ((SUCCESS++))
}

check_warn() {
    echo -e "${YELLOW}⚠️  WARN${NC} $1"
    ((WARNINGS++))
}

check_fail() {
    echo -e "${RED}❌ FAIL${NC} $1"
    ((ERRORS++))
}

# ==============================================================================
# 1. VÉRIFICATION MÉMOIRE
# ==============================================================================
echo -e "\n${BOLD}[1] Vérification Mémoire${NC}"
echo "─────────────────────────────────"

# Total RAM + SWAP
TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_SWAP_KB=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
TOTAL_MEM_GB=$(( (TOTAL_MEM_KB + TOTAL_SWAP_KB) / 1024 / 1024 ))

if [[ $TOTAL_MEM_GB -ge 6 ]]; then
    check_pass "Mémoire totale: ${TOTAL_MEM_GB}GB (RAM+SWAP >= 6GB recommandé)"
else
    check_fail "Mémoire totale: ${TOTAL_MEM_GB}GB (< 6GB - Risque de crash!)"
fi

# Vérifier ZRAM
if lsblk | grep -q "zram0"; then
    ZRAM_SIZE=$(lsblk | grep zram0 | awk '{print $4}')
    check_pass "ZRAM actif: ${ZRAM_SIZE}"
else
    check_warn "ZRAM non configuré (recommandé pour optimiser la RAM)"
fi

# ==============================================================================
# 2. VÉRIFICATION KERNEL
# ==============================================================================
echo -e "\n${BOLD}[2] Paramètres Kernel${NC}"
echo "─────────────────────────────────"

# vm.overcommit_memory
OVERCOMMIT=$(sysctl -n vm.overcommit_memory 2>/dev/null || echo "0")
if [[ "$OVERCOMMIT" == "1" ]]; then
    check_pass "vm.overcommit_memory = 1 (requis pour Redis)"
else
    check_fail "vm.overcommit_memory = $OVERCOMMIT (doit être 1 pour Redis AOF)"
fi

# vm.swappiness
SWAPPINESS=$(sysctl -n vm.swappiness 2>/dev/null || echo "60")
if [[ "$SWAPPINESS" -le 10 ]]; then
    check_pass "vm.swappiness = $SWAPPINESS (optimisé pour SD card)"
else
    check_warn "vm.swappiness = $SWAPPINESS (recommandé: <= 10 pour SD card)"
fi

# net.core.somaxconn
SOMAXCONN=$(sysctl -n net.core.somaxconn 2>/dev/null || echo "128")
if [[ "$SOMAXCONN" -ge 1024 ]]; then
    check_pass "net.core.somaxconn = $SOMAXCONN (TCP backlog optimal)"
else
    check_warn "net.core.somaxconn = $SOMAXCONN (recommandé: >= 1024)"
fi

# ==============================================================================
# 3. VÉRIFICATION DOCKER
# ==============================================================================
echo -e "\n${BOLD}[3] Configuration Docker${NC}"
echo "─────────────────────────────────"

# Docker installé
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    check_pass "Docker installé: v${DOCKER_VERSION}"
else
    check_fail "Docker non installé"
fi

# DNS Configuration
if [[ -f /etc/docker/daemon.json ]]; then
    if grep -q '"dns"' /etc/docker/daemon.json 2>/dev/null; then
        DNS=$(grep -A1 '"dns"' /etc/docker/daemon.json | grep -Eo '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
        check_pass "DNS Docker configuré: $DNS (évite timeouts DNS)"
    else
        check_warn "DNS Docker non configuré (peut causer timeouts sur Freebox)"
    fi

    if grep -q '"ipv6": false' /etc/docker/daemon.json 2>/dev/null; then
        check_pass "IPv6 désactivé (évite problèmes réseau RPi4)"
    else
        check_warn "IPv6 non désactivé (peut causer lenteurs réseau)"
    fi
else
    check_fail "/etc/docker/daemon.json absent"
fi

# ==============================================================================
# 4. VÉRIFICATION DISQUE
# ==============================================================================
echo -e "\n${BOLD}[4] Espace Disque${NC}"
echo "─────────────────────────────────"

DISK_USAGE=$(df -h / | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}')

if [[ "$DISK_USAGE" -lt 80 ]]; then
    check_pass "Espace disque: ${DISK_USAGE}% utilisé (${DISK_AVAIL} disponible)"
else
    check_warn "Espace disque: ${DISK_USAGE}% utilisé (${DISK_AVAIL} disponible) - Nettoyage recommandé"
fi

# ==============================================================================
# 5. VÉRIFICATION BASE DE DONNÉES
# ==============================================================================
echo -e "\n${BOLD}[5] Configuration SQLite${NC}"
echo "─────────────────────────────────"

DB_PATH="./data/linkedin.db"
if [[ -f "$DB_PATH" ]]; then
    # Vérifier le mode journal
    JOURNAL_MODE=$(sqlite3 "$DB_PATH" "PRAGMA journal_mode;" 2>/dev/null || echo "unknown")
    if [[ "$JOURNAL_MODE" == "wal" ]]; then
        check_pass "SQLite journal_mode = WAL (optimisé pour concurrence)"
    else
        check_warn "SQLite journal_mode = $JOURNAL_MODE (recommandé: WAL)"
    fi

    # Taille DB
    DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
    check_pass "Base de données: $DB_SIZE"
else
    check_warn "Base de données non trouvée (sera créée au premier démarrage)"
fi

# ==============================================================================
# 6. VÉRIFICATION PROCESSUS ZOMBIES
# ==============================================================================
echo -e "\n${BOLD}[6] Processus Zombies${NC}"
echo "─────────────────────────────────"

ZOMBIE_COUNT=$(ps aux | grep -i "chromium" | grep -v grep | wc -l)
if [[ "$ZOMBIE_COUNT" -eq 0 ]]; then
    check_pass "Aucun processus Chromium zombie détecté"
else
    check_warn "Processus Chromium détectés: $ZOMBIE_COUNT (exécutez cleanup_chromium_zombies.sh)"
fi

# ==============================================================================
# 7. VÉRIFICATION FICHIERS CRITIQUES
# ==============================================================================
echo -e "\n${BOLD}[7] Fichiers de Configuration${NC}"
echo "─────────────────────────────────"

# .env
if [[ -f .env ]]; then
    check_pass "Fichier .env présent"

    # API_KEY
    if grep -q "^API_KEY=" .env && ! grep -q "^API_KEY=your_secure_random_key_here" .env; then
        check_pass "API_KEY configuré"
    else
        check_fail "API_KEY non configuré ou par défaut"
    fi

    # DASHBOARD_PASSWORD
    if grep -q "^DASHBOARD_PASSWORD=" .env && grep -q "^DASHBOARD_PASSWORD=\$\$2" .env; then
        check_pass "DASHBOARD_PASSWORD haché (bcrypt)"
    else
        check_warn "DASHBOARD_PASSWORD non haché (exécutez setup.sh)"
    fi
else
    check_fail "Fichier .env absent (exécutez setup.sh)"
fi

# docker-compose.yml
if [[ -f docker-compose.yml ]]; then
    check_pass "docker-compose.yml présent"
else
    check_fail "docker-compose.yml absent"
fi

# ==============================================================================
# 8. VÉRIFICATION SERVICES (SI DOCKER COMPOSE ACTIF)
# ==============================================================================
echo -e "\n${BOLD}[8] Services Docker (si actifs)${NC}"
echo "─────────────────────────────────"

if docker compose -f docker-compose.yml ps &>/dev/null; then
    RUNNING_SERVICES=$(docker compose -f docker-compose.yml ps --services --filter "status=running" 2>/dev/null | wc -l)
    TOTAL_SERVICES=$(docker compose -f docker-compose.yml config --services 2>/dev/null | wc -l)

    if [[ "$RUNNING_SERVICES" -eq "$TOTAL_SERVICES" ]]; then
        check_pass "Services Docker: ${RUNNING_SERVICES}/${TOTAL_SERVICES} actifs"
    else
        check_warn "Services Docker: ${RUNNING_SERVICES}/${TOTAL_SERVICES} actifs (certains services arrêtés)"
    fi
else
    check_warn "Services Docker non démarrés (exécutez setup.sh pour démarrer)"
fi

# ==============================================================================
# RAPPORT FINAL
# ==============================================================================
echo -e "\n${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}  Résumé de la Validation${NC}"
echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"

TOTAL_CHECKS=$((SUCCESS + WARNINGS + ERRORS))
echo -e "  ${BOLD}Total de vérifications:${NC} $TOTAL_CHECKS"
echo -e "  ${GREEN}✅ Succès:${NC} $SUCCESS"
echo -e "  ${YELLOW}⚠️  Avertissements:${NC} $WARNINGS"
echo -e "  ${RED}❌ Erreurs:${NC} $ERRORS"

echo ""

if [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}✨ Configuration Raspberry Pi 4 PARFAITE!${NC}"
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
elif [[ $ERRORS -eq 0 ]]; then
    echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}${BOLD}⚠️  Configuration OK avec quelques avertissements${NC}"
    echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Recommandation: Corriger les avertissements pour une performance optimale${NC}"
else
    echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}${BOLD}❌ Configuration INCOMPLÈTE - Corrections requises${NC}"
    echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}Action requise: Exécutez ./setup.sh pour corriger les erreurs${NC}"
fi

echo ""

# Code de sortie
if [[ $ERRORS -gt 0 ]]; then
    exit 1
else
    exit 0
fi
