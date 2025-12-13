#!/bin/bash

###############################################################################
# Script pour corriger la syntaxe Nginx: décommenter les certificats SSL
# Les certificats existent et fonctionnent, il faut juste les décommenter
###############################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🔧 Correction syntaxe Nginx: Certificats SSL${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}Problème détecté:${NC}"
echo "  Les certificats SSL existent et fonctionnent,"
echo "  mais sont commentés dans la configuration."
echo ""
echo -e "${BLUE}Solution:${NC}"
echo "  Décommenter les 4 lignes SSL dans linkedin-bot.conf"
echo ""

# Vérifier que le fichier existe
if [ ! -f "/etc/nginx/sites-available/linkedin-bot" ]; then
    echo -e "${RED}Erreur: Configuration Nginx non trouvée${NC}"
    exit 1
fi

# Sauvegarder
echo -e "${YELLOW}[1/3] Sauvegarde de la configuration...${NC}"
sudo cp /etc/nginx/sites-available/linkedin-bot \
    /etc/nginx/sites-available/linkedin-bot.backup.$(date +%Y%m%d_%H%M%S)
echo -e "${GREEN}✓ Sauvegarde créée${NC}"
echo ""

# Décommenter les lignes SSL
echo -e "${YELLOW}[2/3] Décommenter les certificats SSL...${NC}"

sudo sed -i 's/^[[:space:]]*# ssl_certificate /    ssl_certificate /' /etc/nginx/sites-available/linkedin-bot
sudo sed -i 's/^[[:space:]]*# ssl_certificate_key /    ssl_certificate_key /' /etc/nginx/sites-available/linkedin-bot
sudo sed -i 's/^[[:space:]]*# include \/etc\/letsencrypt\/options-ssl-nginx.conf/    include \/etc\/letsencrypt\/options-ssl-nginx.conf/' /etc/nginx/sites-available/linkedin-bot
sudo sed -i 's/^[[:space:]]*# ssl_dhparam /    ssl_dhparam /' /etc/nginx/sites-available/linkedin-bot

echo -e "${GREEN}✓ Lignes SSL décommentées${NC}"
echo ""

# Tester
echo -e "${YELLOW}[3/3] Test de la configuration...${NC}"
if sudo nginx -t; then
    echo ""
    echo -e "${GREEN}✓ Configuration valide !${NC}"

    echo -e "${BLUE}Rechargement de Nginx...${NC}"
    sudo systemctl reload nginx
    echo -e "${GREEN}✓ Nginx rechargé${NC}"
    echo ""

    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✓ Correction réussie !${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}Vérifications:${NC}"
    echo "  1. Relancer la vérification: ${GREEN}./scripts/verify_security.sh${NC}"
    echo "  2. Tester HTTPS: ${GREEN}curl -I https://gaspardanoukolivier.freeboxos.fr${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}✗ Configuration invalide${NC}"
    echo -e "${YELLOW}Restauration de la sauvegarde...${NC}"

    LAST_BACKUP=$(ls -t /etc/nginx/sites-available/linkedin-bot.backup.* 2>/dev/null | head -1)
    if [ -n "$LAST_BACKUP" ]; then
        sudo cp "$LAST_BACKUP" /etc/nginx/sites-available/linkedin-bot
        echo -e "${GREEN}✓ Configuration restaurée${NC}"
    fi
    exit 1
fi
