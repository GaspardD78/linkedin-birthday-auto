#!/bin/bash

###############################################################################
# Script de bootstrap SSL - LinkedIn Birthday Bot
# Résout le problème du cercle vicieux : Nginx veut SSL, Certbot veut Nginx
###############################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🔐 Bootstrap SSL pour Nginx${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "deployment/nginx/linkedin-bot.conf" ]; then
    echo -e "${RED}Erreur: Exécutez ce script depuis la racine du projet${NC}"
    exit 1
fi

echo -e "${YELLOW}Problème détecté:${NC}"
echo "  Nginx refuse de démarrer car le bloc SSL n'a pas de certificat"
echo "  Certbot ne peut pas obtenir de certificat sans Nginx valide"
echo ""
echo -e "${BLUE}Solution:${NC}"
echo "  1. Créer une configuration HTTP temporaire (sans SSL)"
echo "  2. Démarrer Nginx"
echo "  3. Obtenir le certificat avec Certbot"
echo "  4. Certbot configurera automatiquement HTTPS"
echo ""

# Demander le domaine
echo -e "${BLUE}Veuillez entrer votre nom de domaine:${NC}"
read -p "Domaine: " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Erreur: Aucun domaine fourni${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}[1/6] Sauvegarde de la configuration actuelle...${NC}"
if [ -f "/etc/nginx/sites-available/linkedin-bot" ]; then
    sudo cp /etc/nginx/sites-available/linkedin-bot \
        /etc/nginx/sites-available/linkedin-bot.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓ Sauvegarde créée${NC}"
else
    echo -e "${YELLOW}Note: Aucune configuration existante${NC}"
fi
echo ""

# Créer une configuration HTTP temporaire
echo -e "${YELLOW}[2/6] Création d'une configuration HTTP temporaire...${NC}"
sudo tee /etc/nginx/sites-available/linkedin-bot > /dev/null <<EOF
# Configuration temporaire HTTP-only pour bootstrap SSL
# Cette config sera automatiquement mise à jour par Certbot

server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    # ACME Challenge pour Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Temporairement, proxy vers l'application
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
echo -e "${GREEN}✓ Configuration HTTP créée${NC}"
echo ""

# S'assurer que le lien symbolique existe
echo -e "${YELLOW}[3/6] Activation de la configuration...${NC}"
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

# Créer le répertoire pour ACME challenge
echo -e "${YELLOW}[4/6] Préparation du répertoire ACME...${NC}"
sudo mkdir -p /var/www/html/.well-known/acme-challenge
sudo chmod 755 /var/www/html/.well-known/acme-challenge
echo -e "${GREEN}✓ Répertoire prêt${NC}"
echo ""

# Tester et démarrer Nginx
echo -e "${YELLOW}[5/6] Test et démarrage de Nginx...${NC}"
if sudo nginx -t; then
    echo ""
    echo -e "${GREEN}✓ Configuration valide${NC}"

    if sudo systemctl is-active --quiet nginx; then
        echo -e "${BLUE}Rechargement de Nginx...${NC}"
        sudo systemctl reload nginx
    else
        echo -e "${BLUE}Démarrage de Nginx...${NC}"
        sudo systemctl start nginx
        sudo systemctl enable nginx
    fi
    echo -e "${GREEN}✓ Nginx actif${NC}"
else
    echo ""
    echo -e "${RED}✗ Erreur de configuration${NC}"
    exit 1
fi
echo ""

# Obtenir le certificat SSL
echo -e "${YELLOW}[6/6] Obtention du certificat SSL avec Certbot...${NC}"
echo ""
echo -e "${BLUE}Certbot va maintenant:${NC}"
echo "  1. Vérifier que vous contrôlez le domaine $DOMAIN"
echo "  2. Obtenir un certificat SSL Let's Encrypt"
echo "  3. Modifier automatiquement la configuration Nginx"
echo "  4. Configurer le renouvellement automatique"
echo ""
echo -e "${YELLOW}Note: Le domaine doit pointer vers votre IP et les ports 80/443 doivent être ouverts${NC}"
echo ""
read -p "Appuyez sur Entrée pour continuer..."
echo ""

if sudo certbot --nginx -d "$DOMAIN"; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✓ Certificat SSL obtenu avec succès !${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}Prochaines étapes:${NC}"
    echo "  1. Remplacer la config temporaire par la config complète"
    echo "  2. Tester: https://$DOMAIN"
    echo "  3. Vérifier la sécurité: ./scripts/verify_security.sh"
    echo ""

    # Proposer de restaurer la config complète
    echo -e "${YELLOW}Voulez-vous restaurer la configuration complète avec tous les headers de sécurité? (o/n)${NC}"
    read -p "Réponse: " RESTORE

    if [ "$RESTORE" = "o" ] || [ "$RESTORE" = "O" ]; then
        echo ""
        echo -e "${BLUE}Restauration de la configuration complète...${NC}"

        # Sauvegarder la config Certbot
        sudo cp /etc/nginx/sites-available/linkedin-bot \
            /etc/nginx/sites-available/linkedin-bot.certbot.$(date +%Y%m%d_%H%M%S)

        # Copier la config complète et remplacer le domaine
        sudo cp deployment/nginx/linkedin-bot.conf /etc/nginx/sites-available/linkedin-bot
        sudo sed -i "s/YOUR_DOMAIN.COM/$DOMAIN/g" /etc/nginx/sites-available/linkedin-bot

        # Laisser Certbot ajouter les lignes SSL (elles sont déjà présentes dans letsencrypt)
        # On doit juste décommenter les lignes SSL dans notre config

        # Test et reload
        if sudo nginx -t; then
            sudo systemctl reload nginx
            echo -e "${GREEN}✓ Configuration complète restaurée${NC}"
            echo ""
            echo -e "${GREEN}Tous les headers de sécurité sont maintenant actifs !${NC}"
        else
            echo -e "${RED}✗ Erreur lors du test de la config complète${NC}"
            echo -e "${YELLOW}La configuration Certbot (HTTP + HTTPS simple) reste active${NC}"
        fi
    fi

else
    echo ""
    echo -e "${RED}✗ Échec de l'obtention du certificat${NC}"
    echo ""
    echo -e "${YELLOW}Vérifiez que:${NC}"
    echo "  1. Votre domaine $DOMAIN pointe vers votre IP publique"
    echo "  2. Les ports 80 et 443 sont ouverts sur votre box"
    echo "  3. Nginx est accessible depuis Internet"
    echo ""
    echo -e "${YELLOW}Pour tester:${NC}"
    echo "  curl -I http://$DOMAIN"
    echo ""
    exit 1
fi
