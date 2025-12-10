#!/bin/bash

###############################################################################
# Script de réparation Nginx - LinkedIn Birthday Bot
# Installe et configure Nginx avec tous les paramètres de sécurité
###############################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  🔧 Réparation et installation de Nginx${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier si on est dans le bon répertoire
if [ ! -f "deployment/nginx/linkedin-bot.conf" ]; then
    echo -e "${RED}Erreur: Exécutez ce script depuis la racine du projet${NC}"
    exit 1
fi

# 1. Installer Nginx si nécessaire
echo -e "${YELLOW}[1/7] Vérification de Nginx...${NC}"
if ! command -v nginx &> /dev/null; then
    echo -e "${BLUE}Installation de Nginx...${NC}"
    sudo apt update
    sudo apt install -y nginx
    echo -e "${GREEN}✓ Nginx installé${NC}"
else
    echo -e "${GREEN}✓ Nginx déjà installé${NC}"
fi
echo ""

# 2. Créer les répertoires nécessaires
echo -e "${YELLOW}[2/7] Création des répertoires...${NC}"
sudo mkdir -p /etc/nginx/sites-available
sudo mkdir -p /etc/nginx/sites-enabled
sudo mkdir -p /etc/nginx/conf.d
sudo mkdir -p /var/www/html
echo -e "${GREEN}✓ Répertoires créés${NC}"
echo ""

# 3. Copier le fichier de zones de rate limiting
echo -e "${YELLOW}[3/7] Configuration des zones de rate limiting...${NC}"
if [ -f "/etc/nginx/conf.d/rate-limit-zones.conf" ]; then
    echo -e "${YELLOW}Sauvegarde de l'ancien fichier...${NC}"
    sudo cp /etc/nginx/conf.d/rate-limit-zones.conf /etc/nginx/conf.d/rate-limit-zones.conf.backup.$(date +%Y%m%d_%H%M%S)
fi
sudo cp deployment/nginx/rate-limit-zones.conf /etc/nginx/conf.d/
echo -e "${GREEN}✓ Zones de rate limiting configurées${NC}"
echo ""

# 4. Vérifier que nginx.conf inclut conf.d
echo -e "${YELLOW}[4/7] Vérification de nginx.conf...${NC}"
if ! sudo grep -q "include /etc/nginx/conf.d/\*.conf" /etc/nginx/nginx.conf; then
    echo -e "${BLUE}Ajout de l'inclusion de conf.d dans nginx.conf...${NC}"
    sudo sed -i '/http {/a\    include /etc/nginx/conf.d/*.conf;' /etc/nginx/nginx.conf
    echo -e "${GREEN}✓ Inclusion ajoutée${NC}"
else
    echo -e "${GREEN}✓ Inclusion déjà présente${NC}"
fi
echo ""

# 5. Copier la configuration linkedin-bot
echo -e "${YELLOW}[5/7] Installation de la configuration linkedin-bot...${NC}"

# Demander le domaine à l'utilisateur
echo -e "${BLUE}Veuillez entrer votre nom de domaine (ex: gaspardanoukolivier.freeboxos.fr)${NC}"
read -p "Domaine: " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Erreur: Aucun domaine fourni${NC}"
    exit 1
fi

# Sauvegarder l'ancienne config si elle existe
if [ -f "/etc/nginx/sites-available/linkedin-bot" ]; then
    sudo cp /etc/nginx/sites-available/linkedin-bot /etc/nginx/sites-available/linkedin-bot.backup.$(date +%Y%m%d_%H%M%S)
fi

# Copier et remplacer le domaine
sudo cp deployment/nginx/linkedin-bot.conf /etc/nginx/sites-available/linkedin-bot
sudo sed -i "s/YOUR_DOMAIN.COM/$DOMAIN/g" /etc/nginx/sites-available/linkedin-bot

echo -e "${GREEN}✓ Configuration installée pour le domaine: $DOMAIN${NC}"
echo ""

# 6. Activer la configuration
echo -e "${YELLOW}[6/7] Activation de la configuration...${NC}"
if [ -L "/etc/nginx/sites-enabled/linkedin-bot" ]; then
    sudo rm /etc/nginx/sites-enabled/linkedin-bot
fi
sudo ln -s /etc/nginx/sites-available/linkedin-bot /etc/nginx/sites-enabled/
echo -e "${GREEN}✓ Configuration activée${NC}"
echo ""

# Désactiver la config par défaut si elle existe
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    echo -e "${BLUE}Désactivation de la configuration par défaut...${NC}"
    sudo rm /etc/nginx/sites-enabled/default
fi

# 7. Copier les pages d'erreur
echo -e "${YELLOW}[7/7] Installation des pages d'erreur...${NC}"
if [ -f "deployment/nginx/429.html" ]; then
    sudo cp deployment/nginx/429.html /var/www/html/
    echo -e "${GREEN}✓ Page 429.html installée${NC}"
fi
echo ""

# Test de la configuration
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Test de la configuration Nginx...${NC}"
echo ""

if sudo nginx -t; then
    echo ""
    echo -e "${GREEN}✓ Configuration Nginx valide${NC}"
    echo ""

    # Démarrer ou recharger Nginx
    if sudo systemctl is-active --quiet nginx; then
        echo -e "${BLUE}Rechargement de Nginx...${NC}"
        sudo systemctl reload nginx
        echo -e "${GREEN}✓ Nginx rechargé avec succès${NC}"
    else
        echo -e "${BLUE}Démarrage de Nginx...${NC}"
        sudo systemctl start nginx
        sudo systemctl enable nginx
        echo -e "${GREEN}✓ Nginx démarré avec succès${NC}"
    fi

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  ✓ Installation et configuration réussies !${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}Prochaines étapes:${NC}"
    echo "  1. Vérifiez que votre DNS pointe vers ce serveur"
    echo "  2. Obtenez un certificat SSL avec: sudo certbot --nginx -d $DOMAIN"
    echo "  3. Relancez le script de vérification: ./scripts/verify_security.sh"
    echo ""

else
    echo ""
    echo -e "${RED}✗ Erreur de configuration Nginx${NC}"
    echo ""
    echo -e "${YELLOW}Consultez les erreurs ci-dessus pour corriger la configuration${NC}"
    exit 1
fi
