#!/bin/bash
# Script de reconstruction propre du dashboard pour Raspberry Pi 4
# Force la reconstruction sans cache pour appliquer les correctifs de variables d'environnement

set -e  # Arrête le script en cas d'erreur

echo "🔧 Reconstruction propre du dashboard LinkedIn..."
echo ""

# Couleurs pour l'output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "docker-compose.pi4-standalone.yml" ]; then
    echo -e "${RED}❌ Erreur : docker-compose.pi4-standalone.yml non trouvé${NC}"
    echo "Exécutez ce script depuis la racine du projet"
    exit 1
fi

echo -e "${YELLOW}📋 Étape 1/5 : Arrêt du conteneur dashboard...${NC}"
docker compose -f docker-compose.pi4-standalone.yml stop dashboard

echo -e "${YELLOW}📋 Étape 2/5 : Suppression du conteneur dashboard...${NC}"
docker compose -f docker-compose.pi4-standalone.yml rm -f dashboard

echo -e "${YELLOW}📋 Étape 3/5 : Nettoyage des images Docker orphelines...${NC}"
docker image prune -f

echo -e "${YELLOW}📋 Étape 4/5 : Reconstruction sans cache (cela peut prendre 10-15 min sur Pi4)...${NC}"
docker compose -f docker-compose.pi4-standalone.yml build --no-cache dashboard

echo -e "${YELLOW}📋 Étape 5/5 : Redémarrage du dashboard...${NC}"
docker compose -f docker-compose.pi4-standalone.yml up -d dashboard

echo ""
echo -e "${GREEN}✅ Reconstruction terminée !${NC}"
echo ""
echo "📊 Vérification de l'état du conteneur :"
docker compose -f docker-compose.pi4-standalone.yml ps dashboard

echo ""
echo "📝 Pour voir les logs en temps réel :"
echo "   docker compose -f docker-compose.pi4-standalone.yml logs -f dashboard"
echo ""
echo "🌐 Dashboard accessible sur : http://localhost:3000"
echo ""
