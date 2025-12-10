#!/bin/bash

###############################################################################
# Script helper pour recréer le dashboard et recharger le .env
###############################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  🔄 RECRÉATION DU DASHBOARD${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "Ce script recrée le container dashboard pour recharger le fichier .env"
echo ""

# Déterminer le fichier docker-compose à utiliser
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="docker-compose.yml"
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo -e "${RED}✗ Aucun fichier docker-compose trouvé${NC}"
        exit 1
    fi
fi

echo -e "${BLUE}Fichier Docker Compose: ${NC}$COMPOSE_FILE"
echo ""

echo -e "${YELLOW}⚠️  IMPORTANT: ${NC}"
echo "   - restart ne recharge PAS les variables d'environnement du .env"
echo "   - --force-recreate détruit et recrée le container avec le nouveau .env"
echo ""

read -p "Continuer ? (o/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[OoYy]$ ]]; then
    echo "Opération annulée"
    exit 0
fi
echo ""

echo -e "${BLUE}[1] Vérification du .env${NC}"
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ Fichier .env trouvé${NC}"

    # Vérifier les variables importantes
    if grep -q "^DASHBOARD_PASSWORD=\$\$2[aby]\$\$" .env; then
        echo -e "${GREEN}✓ DASHBOARD_PASSWORD correctement échappé ($$)${NC}"
    elif grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" .env; then
        echo -e "${RED}✗ DASHBOARD_PASSWORD mal échappé ($ au lieu de $$)${NC}"
        echo ""
        echo "Corrigez avec : ./scripts/fix_env_password.sh"
        exit 1
    fi
else
    echo -e "${RED}✗ Fichier .env manquant${NC}"
    echo ""
    echo "Créez-le avec : ./scripts/init_env.sh"
    exit 1
fi
echo ""

echo -e "${BLUE}[2] Recréation du container dashboard${NC}"
echo "Commande: docker compose -f $COMPOSE_FILE up -d dashboard --force-recreate"
echo ""

docker compose -f "$COMPOSE_FILE" up -d dashboard --force-recreate

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Dashboard recréé avec succès${NC}"
else
    echo ""
    echo -e "${RED}✗ Échec de la recréation${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}[3] Attente du démarrage (10 secondes)${NC}"
sleep 10
echo ""

echo -e "${BLUE}[4] Vérification${NC}"

if docker ps | grep -q "dashboard"; then
    echo -e "${GREEN}✓ Le container dashboard est en cours d'exécution${NC}"

    # Vérifier que les variables sont chargées
    CONTAINER_PASSWORD=$(docker exec dashboard env 2>/dev/null | grep "^DASHBOARD_PASSWORD=" | cut -d'=' -f2- || echo "")

    if [ -n "$CONTAINER_PASSWORD" ]; then
        echo -e "${GREEN}✓ DASHBOARD_PASSWORD chargé dans le container${NC}"
        echo "  Hash: ${CONTAINER_PASSWORD:0:30}..."
    else
        echo -e "${RED}✗ DASHBOARD_PASSWORD non trouvé dans le container${NC}"
    fi
else
    echo -e "${RED}✗ Le container dashboard n'est pas démarré${NC}"
    echo ""
    echo "Vérifiez les logs:"
    echo "  docker compose -f $COMPOSE_FILE logs dashboard"
fi
echo ""

echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  ✅ TERMINÉ${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

DASHBOARD_USER=$(grep "^DASHBOARD_USER=" .env 2>/dev/null | cut -d'=' -f2- || echo "admin")

echo "Vous pouvez maintenant vous connecter au dashboard:"
echo ""
echo "  URL: http://$(hostname -I | awk '{print $1}'):3000"
echo "  Utilisateur: $DASHBOARD_USER"
echo "  Mot de passe: Votre mot de passe en clair (pas le hash du .env)"
echo ""

echo "Pour voir les logs:"
echo "  docker compose -f $COMPOSE_FILE logs -f dashboard"
echo ""
