#!/bin/bash
# Script de rotation de la clé API
# Génère une nouvelle clé sécurisée et redémarre les services

set -e

echo "🔐 Rotation de la clé API"
echo "========================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "docker-compose.pi4-standalone.yml" ]; then
    echo -e "${RED}❌ Erreur : docker-compose.pi4-standalone.yml non trouvé${NC}"
    echo "Exécutez ce script depuis la racine du projet"
    exit 1
fi

# Vérifier que le fichier .env existe
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Fichier .env non trouvé${NC}"
    echo "Création depuis .env.pi4.example..."
    cp .env.pi4.example .env
    echo -e "${GREEN}✅ Fichier .env créé${NC}"
    echo ""
fi

# Générer la nouvelle clé
echo -e "${BLUE}🔑 Génération d'une nouvelle clé API sécurisée...${NC}"

# Tenter plusieurs méthodes de génération
if command -v openssl &> /dev/null; then
    NEW_KEY=$(openssl rand -hex 32)
    METHOD="OpenSSL"
elif command -v python3 &> /dev/null; then
    NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    METHOD="Python3"
else
    NEW_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
    METHOD="/dev/urandom"
fi

echo -e "${GREEN}✅ Nouvelle clé générée (via $METHOD)${NC}"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Nouvelle clé API :${NC}"
echo -e "${GREEN}$NEW_KEY${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT : Sauvegardez cette clé dans un endroit sûr !${NC}"
echo "   - Gestionnaire de mots de passe recommandé"
echo "   - Ne la partagez jamais par email ou messagerie"
echo ""

# Demander confirmation
read -p "Appuyez sur Entrée pour continuer (ou Ctrl+C pour annuler)..."

# Backup de l'ancien .env
BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
cp .env "$BACKUP_FILE"
echo -e "${GREEN}📋 Backup créé : $BACKUP_FILE${NC}"

# Afficher l'ancienne clé (pour référence)
OLD_KEY=$(grep "^API_KEY=" .env | cut -d'=' -f2)
echo -e "${BLUE}Ancienne clé : ${NC}${OLD_KEY}"
echo ""

# Remplacer la clé dans .env
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS (BSD sed)
    sed -i '' "s|^API_KEY=.*|API_KEY=$NEW_KEY|" .env
else
    # Linux (GNU sed)
    sed -i "s|^API_KEY=.*|API_KEY=$NEW_KEY|" .env
fi

echo -e "${GREEN}✅ Clé mise à jour dans .env${NC}"
echo ""

# Vérifier que le remplacement a fonctionné
UPDATED_KEY=$(grep "^API_KEY=" .env | cut -d'=' -f2)
if [ "$UPDATED_KEY" = "$NEW_KEY" ]; then
    echo -e "${GREEN}✅ Vérification : clé correctement mise à jour${NC}"
else
    echo -e "${RED}❌ Erreur : la clé n'a pas été correctement mise à jour${NC}"
    echo "Restauration du backup..."
    cp "$BACKUP_FILE" .env
    exit 1
fi

echo ""
echo -e "${YELLOW}🔄 Redémarrage des services Docker...${NC}"
echo ""

# Arrêter les services
echo -e "${BLUE}📋 Étape 1/3 : Arrêt des services...${NC}"
docker compose -f docker-compose.pi4-standalone.yml down

# Redémarrer avec la nouvelle configuration
echo -e "${BLUE}📋 Étape 2/3 : Démarrage avec la nouvelle clé...${NC}"
docker compose -f docker-compose.pi4-standalone.yml up -d

# Attendre que les services démarrent
echo -e "${BLUE}📋 Étape 3/3 : Vérification des services...${NC}"
sleep 5

# Afficher le statut
echo ""
docker compose -f docker-compose.pi4-standalone.yml ps
echo ""

# Vérifier les logs pour des erreurs d'API key
echo -e "${BLUE}🔍 Vérification des logs de l'API (5 dernières secondes)...${NC}"
sleep 2
API_LOGS=$(docker logs bot-api --since 5s 2>&1 | grep -i "api_key" || echo "Aucune erreur de clé API détectée")

if echo "$API_LOGS" | grep -q "no_api_key_configured"; then
    echo -e "${RED}❌ Attention : l'API n'a pas chargé la nouvelle clé${NC}"
    echo "$API_LOGS"
elif echo "$API_LOGS" | grep -q "invalid_api_key"; then
    echo -e "${RED}❌ Attention : erreur de clé API détectée${NC}"
    echo "$API_LOGS"
else
    echo -e "${GREEN}✅ Aucune erreur de clé API détectée${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Rotation de la clé API terminée avec succès !${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📝 Informations :${NC}"
echo "   • Backup de l'ancien .env : $BACKUP_FILE"
echo "   • Nouvelle clé : $NEW_KEY"
echo ""
echo -e "${BLUE}🔍 Commandes utiles :${NC}"
echo "   • Logs API    : docker logs bot-api -f"
echo "   • Logs Dashboard : docker logs dashboard -f"
echo "   • Statut      : docker compose -f docker-compose.pi4-standalone.yml ps"
echo ""
echo -e "${BLUE}🌐 Dashboard :${NC}"
echo "   http://localhost:3000"
echo ""
echo -e "${YELLOW}💡 Conseil : Si le dashboard affiche toujours une erreur 403, attendez${NC}"
echo -e "${YELLOW}   quelques secondes que les services se synchronisent complètement.${NC}"
echo ""
