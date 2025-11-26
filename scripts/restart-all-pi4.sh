#!/bin/bash
# Script de redémarrage complet de l'architecture Pi4
# Utile pour appliquer les changements de configuration après un git pull

set -e

echo "🔄 Redémarrage complet de l'architecture LinkedIn Bot sur Pi4..."
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "docker-compose.pi4-standalone.yml" ]; then
    echo -e "${RED}❌ Erreur : docker-compose.pi4-standalone.yml non trouvé${NC}"
    echo "Exécutez ce script depuis la racine du projet"
    exit 1
fi

echo -e "${YELLOW}📋 Étape 1/4 : Arrêt de tous les services...${NC}"
docker compose -f docker-compose.pi4-standalone.yml down

echo -e "${YELLOW}📋 Étape 2/4 : Nettoyage des images et conteneurs orphelins...${NC}"
docker image prune -f
docker container prune -f

echo -e "${YELLOW}📋 Étape 3/4 : Reconstruction complète (15-20 min sur Pi4)...${NC}"
docker compose -f docker-compose.pi4-standalone.yml build --no-cache

echo -e "${YELLOW}📋 Étape 4/4 : Démarrage de tous les services...${NC}"
docker compose -f docker-compose.pi4-standalone.yml up -d

echo ""
echo -e "${GREEN}✅ Redémarrage complet terminé !${NC}"
echo ""
echo "📊 État des services :"
docker compose -f docker-compose.pi4-standalone.yml ps

echo ""
echo "📝 Pour voir les logs de tous les services :"
echo "   docker compose -f docker-compose.pi4-standalone.yml logs -f"
echo ""
echo "🌐 Dashboard accessible sur : http://localhost:3000"
echo ""
