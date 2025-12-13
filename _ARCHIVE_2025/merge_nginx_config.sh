#!/bin/bash

###############################################################################
# Script de fusion configuration Nginx - Certbot + Security Headers
# Fusionne la config Certbot (avec certificats SSL) et la config complète
###############################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🔐 Fusion configuration Nginx complète${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "deployment/nginx/linkedin-bot.conf" ]; then
    echo -e "${RED}Erreur: Exécutez ce script depuis la racine du projet${NC}"
    exit 1
fi

# Vérifier que Certbot a bien configuré SSL
if [ ! -f "/etc/nginx/sites-available/linkedin-bot" ]; then
    echo -e "${RED}Erreur: Aucune configuration Nginx trouvée${NC}"
    exit 1
fi

echo -e "${YELLOW}Ce script va:${NC}"
echo "  1. Extraire les lignes SSL ajoutées par Certbot"
echo "  2. Copier la configuration complète avec security headers"
echo "  3. Insérer les certificats SSL au bon endroit"
echo "  4. Tester et recharger Nginx"
echo ""

# Extraire le domaine de la config actuelle
DOMAIN=$(grep -m1 "server_name" /etc/nginx/sites-available/linkedin-bot | awk '{print $2}' | sed 's/;//')

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Erreur: Impossible de détecter le domaine${NC}"
    exit 1
fi

echo -e "${BLUE}Domaine détecté: ${GREEN}$DOMAIN${NC}"
echo ""

# Extraire les lignes SSL de Certbot
echo -e "${YELLOW}[1/5] Extraction des certificats SSL...${NC}"

SSL_CERT=$(grep "ssl_certificate " /etc/nginx/sites-available/linkedin-bot | grep -v "ssl_certificate_key" | head -1 | sed 's/^[[:space:]]*//')
SSL_KEY=$(grep "ssl_certificate_key" /etc/nginx/sites-available/linkedin-bot | head -1 | sed 's/^[[:space:]]*//')
SSL_OPTIONS=$(grep "include.*options-ssl-nginx.conf" /etc/nginx/sites-available/linkedin-bot | head -1 | sed 's/^[[:space:]]*//')
SSL_DHPARAM=$(grep "ssl_dhparam" /etc/nginx/sites-available/linkedin-bot | head -1 | sed 's/^[[:space:]]*//')

if [ -z "$SSL_CERT" ] || [ -z "$SSL_KEY" ]; then
    echo -e "${RED}✗ Certificats SSL non trouvés${NC}"
    echo -e "${YELLOW}La configuration Certbot doit contenir les lignes ssl_certificate${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Certificats SSL extraits${NC}"
echo ""

# Sauvegarder la config actuelle
echo -e "${YELLOW}[2/5] Sauvegarde de la configuration actuelle...${NC}"
sudo cp /etc/nginx/sites-available/linkedin-bot \
    /etc/nginx/sites-available/linkedin-bot.before-merge.$(date +%Y%m%d_%H%M%S)
echo -e "${GREEN}✓ Sauvegarde créée${NC}"
echo ""

# Créer la config fusionnée dans un fichier temporaire
echo -e "${YELLOW}[3/5] Création de la configuration fusionnée...${NC}"

TEMP_CONFIG=$(mktemp)

# Copier la config complète et remplacer le domaine
sed "s/YOUR_DOMAIN.COM/$DOMAIN/g" deployment/nginx/linkedin-bot.conf > "$TEMP_CONFIG"

# Remplacer les lignes SSL commentées par les vraies lignes de Certbot
# On remplace la section entre "# CERTIFICATS SSL" et "# ssl_dhparam"
sed -i "/# CERTIFICATS SSL/,/# ssl_dhparam/c\\
    # ═══════════════════════════════════════════════════════════════\\
    # CERTIFICATS SSL (Let's Encrypt)\\
    # ═══════════════════════════════════════════════════════════════\\
    # Configuré automatiquement par Certbot\\
    $SSL_CERT\\
    $SSL_KEY\\
    $SSL_OPTIONS\\
    $SSL_DHPARAM" "$TEMP_CONFIG"

echo -e "${GREEN}✓ Configuration fusionnée créée${NC}"
echo ""

# Test de la configuration
echo -e "${YELLOW}[4/5] Test de la configuration...${NC}"

# Copier temporairement pour tester
sudo cp "$TEMP_CONFIG" /etc/nginx/sites-available/linkedin-bot

if sudo nginx -t; then
    echo ""
    echo -e "${GREEN}✓ Configuration valide !${NC}"
else
    echo ""
    echo -e "${RED}✗ Configuration invalide${NC}"
    echo -e "${YELLOW}Restauration de la configuration précédente...${NC}"

    # Restaurer la dernière sauvegarde
    LAST_BACKUP=$(ls -t /etc/nginx/sites-available/linkedin-bot.before-merge.* 2>/dev/null | head -1)
    if [ -n "$LAST_BACKUP" ]; then
        sudo cp "$LAST_BACKUP" /etc/nginx/sites-available/linkedin-bot
        echo -e "${GREEN}✓ Configuration restaurée${NC}"
    fi

    rm "$TEMP_CONFIG"
    exit 1
fi
echo ""

# Recharger Nginx
echo -e "${YELLOW}[5/5] Rechargement de Nginx...${NC}"
sudo systemctl reload nginx
echo -e "${GREEN}✓ Nginx rechargé${NC}"
echo ""

# Nettoyage
rm "$TEMP_CONFIG"

# Résumé
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✓ Configuration complète installée avec succès !${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Configuration active:${NC}"
echo "  • HTTPS avec certificat Let's Encrypt"
echo "  • Tous les security headers activés"
echo "  • Rate limiting configuré"
echo "  • Anti-indexation activée"
echo ""
echo -e "${BLUE}Vérifications:${NC}"
echo "  1. Tester HTTPS: ${GREEN}curl -I https://$DOMAIN${NC}"
echo "  2. Vérifier les headers: ${GREEN}curl -I https://$DOMAIN | grep -i 'x-frame\\|hsts\\|x-content'${NC}"
echo "  3. Score sécurité: ${GREEN}./scripts/verify_security.sh${NC}"
echo ""
echo -e "${BLUE}Certificats SSL:${NC}"
echo "  ${GREEN}$SSL_CERT${NC}"
echo "  ${GREEN}$SSL_KEY${NC}"
echo ""
