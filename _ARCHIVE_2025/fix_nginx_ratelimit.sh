#!/bin/bash

###############################################################################
# Script de correction rapide Nginx Rate Limiting
# Corrige l'erreur: invalid rate "rate=5r/15m"
###############################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🔧 Correction rapide: Nginx Rate Limiting${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "deployment/nginx/rate-limit-zones.conf" ]; then
    echo -e "${RED}Erreur: Exécutez ce script depuis la racine du projet${NC}"
    exit 1
fi

echo -e "${YELLOW}Problème détecté:${NC}"
echo "  Le fichier /etc/nginx/conf.d/rate-limit-zones.conf contient une syntaxe invalide:"
echo "  ${RED}rate=5r/15m${NC} (Nginx n'accepte pas les périodes de 15 minutes)"
echo ""
echo -e "${BLUE}Solution:${NC}"
echo "  Remplacer par ${GREEN}rate=1r/m${NC} avec ${GREEN}burst=5${NC}"
echo "  Cela permet ~5 tentatives par 5 minutes (limitation Nginx)"
echo ""

# Sauvegarder l'ancien fichier si il existe
if [ -f "/etc/nginx/conf.d/rate-limit-zones.conf" ]; then
    echo -e "${YELLOW}[1/4] Sauvegarde de l'ancienne configuration...${NC}"
    sudo cp /etc/nginx/conf.d/rate-limit-zones.conf \
        /etc/nginx/conf.d/rate-limit-zones.conf.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓ Sauvegarde créée${NC}"
    echo ""
fi

# Créer le répertoire si nécessaire
echo -e "${YELLOW}[2/4] Vérification du répertoire...${NC}"
sudo mkdir -p /etc/nginx/conf.d
echo -e "${GREEN}✓ Répertoire prêt${NC}"
echo ""

# Copier le fichier corrigé
echo -e "${YELLOW}[3/4] Installation du fichier corrigé...${NC}"
sudo cp deployment/nginx/rate-limit-zones.conf /etc/nginx/conf.d/
echo -e "${GREEN}✓ Fichier installé${NC}"
echo ""

# Vérifier la configuration
echo -e "${YELLOW}[4/4] Test de la configuration Nginx...${NC}"
echo ""

if sudo nginx -t; then
    echo ""
    echo -e "${GREEN}✓ Configuration Nginx valide !${NC}"
    echo ""

    # Recharger Nginx si il est actif
    if sudo systemctl is-active --quiet nginx; then
        echo -e "${BLUE}Rechargement de Nginx...${NC}"
        sudo systemctl reload nginx
        echo -e "${GREEN}✓ Nginx rechargé avec succès${NC}"
    else
        echo -e "${YELLOW}Note: Nginx n'est pas actif. Démarrez-le avec:${NC}"
        echo "  sudo systemctl start nginx"
    fi

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✓ Correction réussie !${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}Prochaines étapes:${NC}"
    echo "  1. Démarrez Nginx si nécessaire: sudo systemctl start nginx"
    echo "  2. Relancez la vérification: ./scripts/verify_security.sh"
    echo ""

else
    echo ""
    echo -e "${RED}✗ Erreur de configuration Nginx${NC}"
    echo ""
    echo -e "${YELLOW}D'autres erreurs persistent. Consultez les messages ci-dessus.${NC}"
    echo -e "${YELLOW}Pour une réparation complète, utilisez:${NC}"
    echo "  ./scripts/fix_nginx.sh"
    echo ""
    exit 1
fi
