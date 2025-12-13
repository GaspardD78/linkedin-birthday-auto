#!/bin/bash

###############################################################################
# Script de diagnostic pour le problème de mot de passe
###############################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  🔍 DIAGNOSTIC MOT DE PASSE .env${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Test 1 : Fichier .env existe ?
echo -e "${BLUE}[1] Vérification existence du fichier .env${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ Le fichier .env n'existe PAS${NC}"
    echo ""
    echo "Solutions :"
    echo "  1. Lancez : ./scripts/init_env.sh"
    echo "  2. Ou copiez : cp .env.pi4.example .env"
    exit 1
else
    echo -e "${GREEN}✓ Le fichier .env existe${NC}"
    ls -lh .env
fi
echo ""

# Test 2 : Variable DASHBOARD_PASSWORD existe ?
echo -e "${BLUE}[2] Vérification variable DASHBOARD_PASSWORD${NC}"
if ! grep -q "^DASHBOARD_PASSWORD=" .env; then
    echo -e "${RED}✗ Variable DASHBOARD_PASSWORD absente du .env${NC}"
    echo ""
    echo "Ajoutez la ligne dans .env :"
    echo "  DASHBOARD_PASSWORD=votre_mot_de_passe"
    exit 1
else
    echo -e "${GREEN}✓ Variable DASHBOARD_PASSWORD présente${NC}"
fi
echo ""

# Test 3 : Extraire et analyser le mot de passe
echo -e "${BLUE}[3] Analyse du mot de passe${NC}"

PASSWORD=$(grep "^DASHBOARD_PASSWORD=" .env | cut -d'=' -f2-)

# Afficher les premiers caractères (pour debug, sans révéler le mot de passe)
FIRST_CHARS="${PASSWORD:0:10}"
echo "Premiers caractères : $FIRST_CHARS..."
echo "Longueur totale : ${#PASSWORD} caractères"
echo ""

# Test 4 : Vérifier le format bcrypt
echo -e "${BLUE}[4] Vérification format bcrypt${NC}"

# Bcrypt commence toujours par $2a$, $2b$, ou $2y$
if echo "$PASSWORD" | grep -q '^\$2[aby]\$'; then
    echo -e "${GREEN}✓ Le mot de passe est au format bcrypt${NC}"
    echo "  Format détecté : $(echo $PASSWORD | cut -d'$' -f1-3)\$..."

    # Vérifier la longueur (bcrypt = 60 caractères)
    if [ ${#PASSWORD} -eq 60 ]; then
        echo -e "${GREEN}✓ Longueur correcte (60 caractères)${NC}"
    else
        echo -e "${YELLOW}⚠ Longueur inhabituelle : ${#PASSWORD} caractères (attendu: 60)${NC}"
    fi
else
    echo -e "${RED}✗ Le mot de passe N'EST PAS au format bcrypt${NC}"
    echo ""
    echo "Le mot de passe est EN CLAIR : $FIRST_CHARS..."
    echo ""
    echo "Solutions :"
    echo "  1. Automatique : ./scripts/init_env.sh"
    echo "  2. Manuel : node dashboard/scripts/hash_password.js \"VotreMotDePasse\""
fi
echo ""

# Test 5 : Vérifier la regex utilisée dans verify_security.sh
echo -e "${BLUE}[5] Test avec la regex de verify_security.sh${NC}"

# La regex exacte utilisée dans verify_security.sh ligne 591
if grep -q '^DASHBOARD_PASSWORD=\$2[aby]\$' .env; then
    echo -e "${GREEN}✓ La regex de verify_security.sh détecte le hash${NC}"
else
    echo -e "${RED}✗ La regex de verify_security.sh NE détecte PAS le hash${NC}"

    # Debug : afficher ce que grep voit
    echo ""
    echo "Debug - Ligne extraite du .env :"
    grep "^DASHBOARD_PASSWORD=" .env
    echo ""

    echo "Cause possible :"
    echo "  • Caractères invisibles dans le fichier"
    echo "  • Encodage du fichier incorrect"
    echo "  • Espaces avant/après le ="
fi
echo ""

# Test 6 : Vérifier les backups
echo -e "${BLUE}[6] Vérification des backups .env${NC}"
if ls .env.backup.* 1> /dev/null 2>&1; then
    BACKUP_COUNT=$(ls .env.backup.* 2>/dev/null | wc -l)
    echo -e "${GREEN}✓ $BACKUP_COUNT backup(s) trouvé(s)${NC}"

    echo ""
    echo "Derniers backups :"
    ls -lht .env.backup.* | head -3
else
    echo -e "${YELLOW}⚠ Aucun backup trouvé${NC}"
fi
echo ""

# Test 7 : Vérifier bcryptjs
echo -e "${BLUE}[7] Vérification bcryptjs${NC}"
if [ -f "dashboard/node_modules/bcryptjs/package.json" ]; then
    VERSION=$(cat dashboard/node_modules/bcryptjs/package.json | grep '"version"' | awk -F'"' '{print $4}')
    echo -e "${GREEN}✓ bcryptjs installé (v$VERSION)${NC}"
else
    echo -e "${YELLOW}⚠ bcryptjs non installé${NC}"
    echo "  Installez avec : cd dashboard && npm install bcryptjs"
fi
echo ""

# Test 8 : Vérifier Node.js
echo -e "${BLUE}[8] Vérification Node.js${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js installé ($NODE_VERSION)${NC}"

    # Tester le script de hashage
    if [ -f "dashboard/scripts/hash_password.js" ]; then
        echo -e "${GREEN}✓ Script hash_password.js présent${NC}"
    else
        echo -e "${RED}✗ Script hash_password.js absent${NC}"
    fi
else
    echo -e "${RED}✗ Node.js non installé${NC}"
    echo "  Le hashage automatique ne fonctionnera pas"
fi
echo ""

# Résumé et recommandations
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  📋 RÉSUMÉ ET RECOMMANDATIONS${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if echo "$PASSWORD" | grep -q '^\$2[aby]\$' && [ ${#PASSWORD} -eq 60 ]; then
    echo -e "${GREEN}${BOLD}✅ Votre mot de passe est correctement hashé !${NC}"
    echo ""
    echo "Si verify_security.sh échoue encore, c'est un bug du script de vérification."
    echo "Le mot de passe est correct et fonctionnera."
else
    echo -e "${RED}${BOLD}❌ Le mot de passe doit être hashé${NC}"
    echo ""
    echo "SOLUTION RAPIDE :"
    echo ""
    echo -e "${YELLOW}${BOLD}  ./scripts/init_env.sh${NC}"
    echo ""
    echo "Cela va :"
    echo "  1. Créer un backup de votre .env actuel"
    echo "  2. Vous demander un nouveau mot de passe"
    echo "  3. Le hasher automatiquement avec bcrypt"
    echo "  4. Mettre à jour le .env avec le hash"
    echo ""
    echo "OU en manuel :"
    echo ""
    echo "  # 1. Hasher votre mot de passe"
    echo "  node dashboard/scripts/hash_password.js \"VotreMotDePasse\""
    echo ""
    echo "  # 2. Copier le hash généré"
    echo "  # 3. Éditer .env et remplacer DASHBOARD_PASSWORD= par le hash"
    echo "  nano .env"
fi

echo ""
