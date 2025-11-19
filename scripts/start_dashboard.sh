#!/bin/bash
# Script pour démarrer le dashboard LinkedIn Birthday Auto
# Usage: ./scripts/start_dashboard.sh [port]

set -e

# Configuration
PORT=${1:-5000}
MODE=${FLASK_DEBUG:-true}

# Couleurs pour les logs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   LinkedIn Birthday Auto - Dashboard                  ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Vérifier que Python est installé
if ! command -v python &> /dev/null; then
    echo -e "${YELLOW}⚠️  Python n'est pas installé${NC}"
    exit 1
fi

# Vérifier que Flask est installé
if ! python -c "import flask" &> /dev/null; then
    echo -e "${YELLOW}⚠️  Flask n'est pas installé. Installation...${NC}"
    pip install flask
fi

# Vérifier que la base de données existe
if [ ! -f "linkedin_automation.db" ]; then
    echo -e "${YELLOW}⚠️  Base de données non trouvée. Initialisation...${NC}"
    python database.py
fi

# Afficher les informations
echo -e "${GREEN}✓${NC} Port: ${BLUE}${PORT}${NC}"
echo -e "${GREEN}✓${NC} Mode debug: ${BLUE}${MODE}${NC}"
echo -e "${GREEN}✓${NC} URL: ${BLUE}http://localhost:${PORT}${NC}"
echo ""

# Vérifier si le port est déjà utilisé
if lsof -Pi :${PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠️  Le port ${PORT} est déjà utilisé${NC}"
    echo -e "   Essayez: ./scripts/start_dashboard.sh $((PORT + 1))"
    exit 1
fi

echo -e "${GREEN}🚀 Démarrage du dashboard...${NC}"
echo ""

# Démarrer le dashboard
PORT=${PORT} FLASK_DEBUG=${MODE} python dashboard_app.py
