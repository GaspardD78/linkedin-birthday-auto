#!/bin/bash

###############################################################################
# Script de test pour vérifier les variables d'environnement dans le container
###############################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  🔍 TEST VARIABLES D'ENVIRONNEMENT DASHBOARD${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${BLUE}[1] Variables dans le fichier .env local${NC}"
echo "─────────────────────────────────────────────"
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ Fichier .env existe${NC}"
    echo ""
    echo "DASHBOARD_USER:"
    grep "^DASHBOARD_USER=" .env || echo -e "${RED}  Non trouvé${NC}"
    echo ""
    echo "DASHBOARD_PASSWORD (premiers caractères):"
    PASSWORD=$(grep "^DASHBOARD_PASSWORD=" .env | cut -d'=' -f2-)
    echo "  ${PASSWORD:0:20}..."
    echo "  Longueur totale: ${#PASSWORD} caractères"
    echo ""
    echo "JWT_SECRET (premiers caractères):"
    JWT=$(grep "^JWT_SECRET=" .env | cut -d'=' -f2-)
    echo "  ${JWT:0:20}..."
    echo "  Longueur totale: ${#JWT} caractères"
else
    echo -e "${RED}✗ Fichier .env n'existe pas !${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}[2] Container dashboard en cours d'exécution ?${NC}"
echo "─────────────────────────────────────────────"
if docker ps --format '{{.Names}}' | grep -q "^dashboard$"; then
    echo -e "${GREEN}✓ Container dashboard est en cours d'exécution${NC}"

    CONTAINER_ID=$(docker ps -qf "name=^dashboard$")
    echo "  Container ID: $CONTAINER_ID"
else
    echo -e "${RED}✗ Container dashboard n'est PAS en cours d'exécution${NC}"
    echo ""
    echo "Démarrez-le avec:"
    echo "  docker compose -f docker-compose.pi4-standalone.yml up -d dashboard"
    exit 1
fi
echo ""

echo -e "${BLUE}[3] Variables d'environnement DANS le container${NC}"
echo "─────────────────────────────────────────────"
echo "DASHBOARD_USER:"
docker exec dashboard env | grep "^DASHBOARD_USER=" || echo -e "${RED}  Non défini dans le container !${NC}"
echo ""
echo "DASHBOARD_PASSWORD (premiers caractères):"
CONTAINER_PASSWORD=$(docker exec dashboard env | grep "^DASHBOARD_PASSWORD=" | cut -d'=' -f2-)
if [ -n "$CONTAINER_PASSWORD" ]; then
    echo "  ${CONTAINER_PASSWORD:0:20}..."
    echo "  Longueur: ${#CONTAINER_PASSWORD} caractères"
else
    echo -e "${RED}  Non défini dans le container !${NC}"
fi
echo ""
echo "JWT_SECRET (premiers caractères):"
CONTAINER_JWT=$(docker exec dashboard env | grep "^JWT_SECRET=" | cut -d'=' -f2-)
if [ -n "$CONTAINER_JWT" ]; then
    echo "  ${CONTAINER_JWT:0:20}..."
    echo "  Longueur: ${#CONTAINER_JWT} caractères"
else
    echo -e "${RED}  Non défini dans le container !${NC}"
fi
echo ""

echo -e "${BLUE}[4] Comparaison .env vs container${NC}"
echo "─────────────────────────────────────────────"

# Comparer DASHBOARD_PASSWORD
LOCAL_PASSWORD=$(grep "^DASHBOARD_PASSWORD=" .env | cut -d'=' -f2-)
CONTAINER_PASSWORD=$(docker exec dashboard env | grep "^DASHBOARD_PASSWORD=" | cut -d'=' -f2-)

if [ "$LOCAL_PASSWORD" = "$CONTAINER_PASSWORD" ]; then
    echo -e "${GREEN}✓ DASHBOARD_PASSWORD correspond${NC}"
else
    echo -e "${RED}✗ DASHBOARD_PASSWORD NE CORRESPOND PAS !${NC}"
    echo ""
    echo "Local (.env):     ${LOCAL_PASSWORD:0:30}..."
    echo "Container:        ${CONTAINER_PASSWORD:0:30}..."
    echo ""
    echo -e "${YELLOW}⚠️  Le container n'a pas chargé le nouveau .env !${NC}"
    echo "   Vous devez redémarrer le container:"
    echo "   docker compose -f docker-compose.pi4-standalone.yml restart dashboard"
fi
echo ""

echo -e "${BLUE}[5] Test de hash bcrypt${NC}"
echo "─────────────────────────────────────────────"

# Vérifier que le hash commence bien par $$2
if echo "$LOCAL_PASSWORD" | grep -q '^\$\$2[aby]\$\$'; then
    echo -e "${GREEN}✓ Le hash local commence par \$\$2... (correct pour Docker Compose)${NC}"
elif echo "$LOCAL_PASSWORD" | grep -q '^\$2[aby]\$'; then
    echo -e "${RED}✗ Le hash local commence par \$2... (INCORRECT pour Docker Compose)${NC}"
    echo ""
    echo "   Docker Compose nécessite \$\$ au lieu de \$"
    echo "   Régénérez le hash avec:"
    echo "   node dashboard/scripts/hash_password.js \"VotreMotDePasse\""
else
    echo -e "${YELLOW}⚠️  Le mot de passe ne semble pas être un hash bcrypt${NC}"
fi
echo ""

echo -e "${BLUE}[6] Logs récents du dashboard${NC}"
echo "─────────────────────────────────────────────"
echo "Recherche d'erreurs d'authentification..."
docker logs dashboard --tail 30 2>&1 | grep -i -E "(auth|login|password|jwt|error|warn)" | tail -10 || echo "Aucune erreur trouvée"
echo ""

echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  📋 RÉSUMÉ${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$LOCAL_PASSWORD" != "$CONTAINER_PASSWORD" ]; then
    echo -e "${RED}${BOLD}❌ PROBLÈME DÉTECTÉ${NC}"
    echo ""
    echo "Le container n'a pas la même configuration que votre .env local"
    echo ""
    echo "SOLUTION:"
    echo "  1. Redémarrez le container:"
    echo "     ${YELLOW}docker compose -f docker-compose.pi4-standalone.yml restart dashboard${NC}"
    echo ""
    echo "  2. Relancez ce script pour vérifier"
    echo ""
elif ! echo "$LOCAL_PASSWORD" | grep -q '^\$\$2[aby]\$\$'; then
    echo -e "${RED}${BOLD}❌ FORMAT DE HASH INCORRECT${NC}"
    echo ""
    echo "Le hash n'est pas au bon format pour Docker Compose"
    echo ""
    echo "SOLUTION:"
    echo "  1. Régénérez le hash:"
    echo "     ${YELLOW}node dashboard/scripts/hash_password.js \"VotreMotDePasse\"${NC}"
    echo ""
    echo "  2. Copiez le résultat dans votre .env"
    echo ""
    echo "  3. Redémarrez le dashboard:"
    echo "     ${YELLOW}docker compose -f docker-compose.pi4-standalone.yml restart dashboard${NC}"
    echo ""
else
    echo -e "${GREEN}${BOLD}✅ CONFIGURATION OK${NC}"
    echo ""
    echo "Vos identifiants de connexion:"
    echo "  Utilisateur: ${GREEN}$(grep "^DASHBOARD_USER=" .env | cut -d'=' -f2-)${NC}"
    echo "  Mot de passe: ${GREEN}Le mot de passe que vous avez utilisé pour générer le hash${NC}"
    echo ""
    echo "Si vous ne pouvez toujours pas vous connecter:"
    echo "  1. Vérifiez que vous utilisez le mot de passe EN CLAIR (pas le hash)"
    echo "  2. Vérifiez les logs: docker logs dashboard -f"
    echo "  3. Essayez de créer un nouveau hash avec un mot de passe simple pour tester"
    echo ""
fi
