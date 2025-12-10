#!/bin/bash

###############################################################################
# Script de réparation rapide pour hasher le mot de passe
###############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  🔧 RÉPARATION RAPIDE - HASHAGE MOT DE PASSE${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier que .env existe
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ Le fichier .env n'existe pas${NC}"
    echo ""
    echo "Utilisez plutôt : ./scripts/init_env.sh"
    exit 1
fi

# Vérifier que DASHBOARD_PASSWORD existe
if ! grep -q "^DASHBOARD_PASSWORD=" .env; then
    echo -e "${RED}✗ Variable DASHBOARD_PASSWORD absente du .env${NC}"
    exit 1
fi

# Extraire le mot de passe actuel
CURRENT_PASSWORD=$(grep "^DASHBOARD_PASSWORD=" .env | cut -d'=' -f2-)

# Vérifier s'il est déjà hashé
if echo "$CURRENT_PASSWORD" | grep -q "^\$2[aby]\$"; then
    echo -e "${GREEN}✓ Le mot de passe est DÉJÀ hashé${NC}"
    echo ""
    echo "Premiers caractères : ${CURRENT_PASSWORD:0:20}..."
    echo "Longueur : ${#CURRENT_PASSWORD} caractères"
    echo ""

    if [ ${#CURRENT_PASSWORD} -eq 60 ]; then
        echo -e "${GREEN}${BOLD}Le mot de passe est correct !${NC}"
        echo ""
        echo "Si verify_security.sh échoue, il y a peut-être des caractères"
        echo "invisibles ou un problème d'encodage."
        echo ""
        read -p "Voulez-vous ré-hasher quand même ? (o/n) : " -n 1 -r
        echo ""

        if [[ ! $REPLY =~ ^[OoYy]$ ]]; then
            echo "Opération annulée"
            exit 0
        fi
    else
        echo -e "${YELLOW}⚠ Longueur inhabituelle${NC}"
        echo "On va re-hasher pour corriger."
        echo ""
    fi
else
    echo -e "${YELLOW}⚠ Le mot de passe est en CLAIR${NC}"
    echo ""
fi

# Vérifier Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js n'est pas installé${NC}"
    echo ""
    echo "Installez Node.js puis relancez ce script"
    exit 1
fi

# Vérifier bcryptjs
if [ ! -f "dashboard/node_modules/bcryptjs/package.json" ]; then
    echo -e "${YELLOW}Installation de bcryptjs...${NC}"
    cd dashboard
    npm install bcryptjs --silent
    cd ..
    echo -e "${GREEN}✓ bcryptjs installé${NC}"
    echo ""
fi

# Vérifier le script de hashage
if [ ! -f "dashboard/scripts/hash_password.js" ]; then
    echo -e "${RED}✗ Script hash_password.js introuvable${NC}"
    exit 1
fi

# Créer un backup
BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
cp .env "$BACKUP_FILE"
echo -e "${GREEN}✓ Backup créé : $BACKUP_FILE${NC}"
echo ""

# Deux options : hasher le mot de passe actuel OU demander un nouveau
echo "Options :"
echo "  1) Hasher le mot de passe actuel (si en clair)"
echo "  2) Saisir un nouveau mot de passe"
echo ""
read -p "Votre choix (1/2) : " -n 1 -r CHOICE
echo ""
echo ""

if [ "$CHOICE" = "2" ]; then
    # Demander un nouveau mot de passe
    while true; do
        echo -e "${YELLOW}Nouveau mot de passe (minimum 8 caractères) :${NC}"
        read -s -p "> " NEW_PASSWORD
        echo ""

        if [ ${#NEW_PASSWORD} -lt 8 ]; then
            echo -e "${RED}✗ Le mot de passe doit contenir au moins 8 caractères${NC}"
            echo ""
            continue
        fi

        echo -e "${YELLOW}Confirmez le mot de passe :${NC}"
        read -s -p "> " NEW_PASSWORD_CONFIRM
        echo ""

        if [ "$NEW_PASSWORD" != "$NEW_PASSWORD_CONFIRM" ]; then
            echo -e "${RED}✗ Les mots de passe ne correspondent pas${NC}"
            echo ""
            continue
        fi

        CURRENT_PASSWORD="$NEW_PASSWORD"
        break
    done
    echo ""
fi

# Hasher le mot de passe
echo "Hashage du mot de passe avec bcrypt..."

HASHED_PASSWORD=$(node dashboard/scripts/hash_password.js --quiet "$CURRENT_PASSWORD" 2>/dev/null)

if [ -z "$HASHED_PASSWORD" ]; then
    echo -e "${RED}✗ Échec du hashage${NC}"
    echo ""
    echo "Essayez manuellement :"
    echo "  node dashboard/scripts/hash_password.js"
    exit 1
fi

echo -e "${GREEN}✓ Mot de passe hashé avec succès${NC}"
echo ""

# Vérifier le hash généré
echo "Hash généré :"
echo "  Premiers caractères : ${HASHED_PASSWORD:0:20}..."
echo "  Longueur : ${#HASHED_PASSWORD} caractères"

if [ ${#HASHED_PASSWORD} -ne 60 ]; then
    echo -e "${RED}✗ Le hash ne fait pas 60 caractères !${NC}"
    exit 1
fi

if ! echo "$HASHED_PASSWORD" | grep -q "^\$2[aby]\$"; then
    echo -e "${RED}✗ Le hash ne commence pas par \$2a\$, \$2b\$ ou \$2y\$${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Hash valide${NC}"
echo ""

# Remplacer dans .env
echo "Mise à jour du fichier .env..."

# Méthode plus robuste : échapper tous les caractères spéciaux
# On utilise une approche différente pour éviter les problèmes avec sed
TEMP_FILE=$(mktemp)

while IFS= read -r line; do
    if [[ $line =~ ^DASHBOARD_PASSWORD= ]]; then
        echo "DASHBOARD_PASSWORD=$HASHED_PASSWORD"
    else
        echo "$line"
    fi
done < .env > "$TEMP_FILE"

# Remplacer le fichier
mv "$TEMP_FILE" .env
chmod 600 .env

echo -e "${GREEN}✓ Fichier .env mis à jour${NC}"
echo ""

# Vérifier que ça a fonctionné
echo "Vérification finale..."
NEW_HASH=$(grep "^DASHBOARD_PASSWORD=" .env | cut -d'=' -f2-)

if [ "$NEW_HASH" = "$HASHED_PASSWORD" ]; then
    echo -e "${GREEN}✓ Le hash a été correctement enregistré${NC}"
else
    echo -e "${RED}✗ Problème lors de l'enregistrement${NC}"
    echo ""
    echo "Hash attendu : ${HASHED_PASSWORD:0:20}..."
    echo "Hash enregistré : ${NEW_HASH:0:20}..."
    exit 1
fi

echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  ✅ MOT DE PASSE HASHÉ AVEC SUCCÈS${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "Vérification avec la regex de verify_security.sh :"
if grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" .env; then
    echo -e "${GREEN}✓ La regex détecte correctement le hash${NC}"
else
    echo -e "${YELLOW}⚠ La regex ne détecte pas le hash${NC}"
    echo ""
    echo "Cela peut être un bug dans verify_security.sh"
    echo "Mais votre mot de passe EST hashé correctement."
fi

echo ""
echo "Prochaines étapes :"
echo "  1. Testez : ./scripts/verify_security.sh"
echo "  2. Si le test [22] échoue encore, envoyez-moi le diagnostic :"
echo "     ./scripts/diagnose_password.sh"
echo ""
