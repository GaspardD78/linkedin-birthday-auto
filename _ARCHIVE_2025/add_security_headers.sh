#!/bin/bash

###############################################################################
# Script d'ajout des security headers - LinkedIn Birthday Bot
# Ajoute tous les security headers à la configuration Nginx existante
###############################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  🛡️  Ajout des Security Headers Nginx${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier que la config existe
if [ ! -f "/etc/nginx/sites-available/linkedin-bot" ]; then
    echo -e "${RED}Erreur: Configuration Nginx non trouvée${NC}"
    exit 1
fi

echo -e "${YELLOW}Ce script va ajouter les security headers suivants:${NC}"
echo "  • HSTS (Strict-Transport-Security)"
echo "  • X-Frame-Options"
echo "  • X-Content-Type-Options"
echo "  • X-XSS-Protection"
echo "  • Referrer-Policy"
echo "  • Content-Security-Policy"
echo "  • Permissions-Policy"
echo "  • X-Robots-Tag (anti-indexation)"
echo ""

# Sauvegarder
echo -e "${YELLOW}[1/3] Sauvegarde de la configuration...${NC}"
sudo cp /etc/nginx/sites-available/linkedin-bot \
    /etc/nginx/sites-available/linkedin-bot.backup.$(date +%Y%m%d_%H%M%S)
echo -e "${GREEN}✓ Sauvegarde créée${NC}"
echo ""

# Vérifier si les headers existent déjà
if sudo grep -q "Strict-Transport-Security" /etc/nginx/sites-available/linkedin-bot; then
    echo -e "${YELLOW}⚠️  Les security headers semblent déjà présents${NC}"
    echo -e "${YELLOW}Voulez-vous les remplacer? (o/n)${NC}"
    read -p "Réponse: " REPLACE
    if [ "$REPLACE" != "o" ] && [ "$REPLACE" != "O" ]; then
        echo -e "${BLUE}Opération annulée${NC}"
        exit 0
    fi
fi

# Créer un fichier avec les headers
HEADERS_FILE=$(mktemp)
cat > "$HEADERS_FILE" <<'EOF'

    # ═══════════════════════════════════════════════════════════════
    # SECURITY HEADERS (Protection XSS, Clickjacking, etc.)
    # ═══════════════════════════════════════════════════════════════

    # HSTS: Force HTTPS pendant 1 an
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Protection clickjacking
    add_header X-Frame-Options "DENY" always;

    # Désactiver MIME sniffing
    add_header X-Content-Type-Options "nosniff" always;

    # Protection XSS navigateur
    add_header X-XSS-Protection "1; mode=block" always;

    # Referrer policy
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Content Security Policy (CSP)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';" always;

    # Permissions Policy (anciennement Feature-Policy)
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Protection anti-indexation moteurs de recherche
    add_header X-Robots-Tag "noindex, nofollow, noarchive, nosnippet, noimageindex, nocache" always;

EOF

echo -e "${YELLOW}[2/3] Ajout des security headers...${NC}"

# Créer un script Python pour insérer les headers au bon endroit
PYTHON_SCRIPT=$(mktemp)
cat > "$PYTHON_SCRIPT" <<'PYTHON_EOF'
import sys
import re

# Lire la config existante
with open('/etc/nginx/sites-available/linkedin-bot', 'r') as f:
    config = f.read()

# Lire les headers à ajouter
with open(sys.argv[1], 'r') as f:
    headers = f.read()

# Supprimer les anciens headers s'ils existent
config = re.sub(r'\n\s*# ═+\n\s*# SECURITY HEADERS.*?\n\s*add_header X-Robots-Tag.*?\n', '', config, flags=re.DOTALL)
config = re.sub(r'\n\s*add_header Strict-Transport-Security.*?\n', '', config)
config = re.sub(r'\n\s*add_header X-Frame-Options.*?\n', '', config)
config = re.sub(r'\n\s*add_header X-Content-Type-Options.*?\n', '', config)
config = re.sub(r'\n\s*add_header X-XSS-Protection.*?\n', '', config)
config = re.sub(r'\n\s*add_header Referrer-Policy.*?\n', '', config)
config = re.sub(r'\n\s*add_header Content-Security-Policy.*?\n', '', config)
config = re.sub(r'\n\s*add_header Permissions-Policy.*?\n', '', config)
config = re.sub(r'\n\s*add_header X-Robots-Tag.*?\n', '', config)

# Trouver le bloc server HTTPS (celui avec ssl)
# On cherche après "listen 443 ssl" et avant le premier "location"
pattern = r'(listen 443 ssl[^\n]*\n.*?server_name[^\n]*\n)'
match = re.search(pattern, config, re.DOTALL)

if match:
    # Insérer les headers après server_name
    insert_pos = match.end()
    config = config[:insert_pos] + headers + config[insert_pos:]
    print("✓ Headers insérés dans le bloc HTTPS")
else:
    print("✗ Bloc HTTPS non trouvé")
    sys.exit(1)

# Écrire la nouvelle config
with open('/tmp/nginx-config-with-headers.tmp', 'w') as f:
    f.write(config)

print("✓ Configuration générée")
PYTHON_EOF

# Exécuter le script Python
if python3 "$PYTHON_SCRIPT" "$HEADERS_FILE"; then
    # Copier la nouvelle config
    sudo cp /tmp/nginx-config-with-headers.tmp /etc/nginx/sites-available/linkedin-bot
    rm /tmp/nginx-config-with-headers.tmp
    echo -e "${GREEN}✓ Security headers ajoutés${NC}"
else
    echo -e "${RED}✗ Erreur lors de l'ajout des headers${NC}"
    rm "$PYTHON_SCRIPT" "$HEADERS_FILE"
    exit 1
fi

rm "$PYTHON_SCRIPT" "$HEADERS_FILE"
echo ""

# Test de la configuration
echo -e "${YELLOW}[3/3] Test de la configuration...${NC}"
if sudo nginx -t; then
    echo ""
    echo -e "${GREEN}✓ Configuration valide !${NC}"

    # Recharger Nginx
    echo -e "${BLUE}Rechargement de Nginx...${NC}"
    sudo systemctl reload nginx
    echo -e "${GREEN}✓ Nginx rechargé${NC}"
    echo ""

    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✓ Security headers installés avec succès !${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}Vérifications:${NC}"

    # Extraire le domaine
    DOMAIN=$(sudo grep -m1 "server_name" /etc/nginx/sites-available/linkedin-bot | awk '{print $2}' | sed 's/;//')

    echo "  1. Tester les headers: ${GREEN}curl -I https://$DOMAIN${NC}"
    echo "  2. Vérifier HSTS: ${GREEN}curl -I https://$DOMAIN | grep -i hsts${NC}"
    echo "  3. Score sécurité: ${GREEN}./scripts/verify_security.sh${NC}"
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
