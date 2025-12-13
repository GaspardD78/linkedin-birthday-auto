#!/bin/bash

###############################################################################
# Initialisation du fichier .env avec configuration sécurisée
###############################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

clear

echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}${BOLD}  🔐 INITIALISATION FICHIER .env SÉCURISÉ${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier qu'on est dans le bon répertoire
if [ ! -f ".env.pi4.example" ]; then
    echo -e "${RED}Erreur: Fichier .env.pi4.example introuvable${NC}"
    echo "Exécutez ce script depuis la racine du projet"
    exit 1
fi

# Vérifier si .env existe déjà
if [ -f ".env" ]; then
    echo -e "${YELLOW}⚠️  Le fichier .env existe déjà !${NC}"
    echo ""
    ls -lh .env
    echo ""
    read -p "Voulez-vous le REMPLACER ? (o/n) : " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[OoYy]$ ]]; then
        echo -e "${YELLOW}Opération annulée${NC}"
        exit 0
    fi

    # Créer un backup
    BACKUP_FILE=".env.backup.$(date +%Y%m%d_%H%M%S)"
    cp .env "$BACKUP_FILE"
    echo -e "${GREEN}✓ Backup créé: $BACKUP_FILE${NC}"
    echo ""
fi

###############################################################################
# ÉTAPE 1 : Copier le fichier exemple
###############################################################################

echo -e "${BLUE}${BOLD}[ÉTAPE 1/4] Copie du fichier exemple${NC}"
echo ""

cp .env.pi4.example .env
chmod 600 .env

echo -e "${GREEN}✓ Fichier .env créé avec les permissions 600${NC}"
echo ""

###############################################################################
# ÉTAPE 2 : Générer les clés secrètes
###############################################################################

echo -e "${BLUE}${BOLD}[ÉTAPE 2/4] Génération des clés secrètes${NC}"
echo ""

# Générer API_KEY (64 caractères)
API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo -e "${GREEN}✓ API_KEY générée (64 caractères)${NC}"

# Générer JWT_SECRET (64 caractères)
JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
echo -e "${GREEN}✓ JWT_SECRET généré (64 caractères)${NC}"

# Remplacer dans .env
sed -i "s|API_KEY=CHANGEZ_MOI_PAR_CLE_FORTE_GENERER_AVEC_COMMANDE_CI_DESSUS|API_KEY=$API_KEY|" .env
sed -i "s|JWT_SECRET=CHANGEZ_MOI_PAR_SECRET_JWT_GENERER_AVEC_OPENSSL|JWT_SECRET=$JWT_SECRET|" .env

echo ""

###############################################################################
# ÉTAPE 3 : Configurer le mot de passe Dashboard
###############################################################################

echo -e "${BLUE}${BOLD}[ÉTAPE 3/4] Configuration du mot de passe Dashboard${NC}"
echo ""

# Demander le nom d'utilisateur
echo -e "${YELLOW}Nom d'utilisateur pour le dashboard (défaut: admin) :${NC}"
read -p "> " DASHBOARD_USER
DASHBOARD_USER=${DASHBOARD_USER:-admin}

sed -i "s|DASHBOARD_USER=admin|DASHBOARD_USER=$DASHBOARD_USER|" .env
echo -e "${GREEN}✓ Utilisateur: $DASHBOARD_USER${NC}"
echo ""

# Demander le mot de passe
while true; do
    echo -e "${YELLOW}Mot de passe pour le dashboard (minimum 8 caractères) :${NC}"
    read -s -p "> " DASHBOARD_PASSWORD
    echo ""

    if [ ${#DASHBOARD_PASSWORD} -lt 8 ]; then
        echo -e "${RED}✗ Le mot de passe doit contenir au moins 8 caractères${NC}"
        echo ""
        continue
    fi

    echo -e "${YELLOW}Confirmez le mot de passe :${NC}"
    read -s -p "> " DASHBOARD_PASSWORD_CONFIRM
    echo ""

    if [ "$DASHBOARD_PASSWORD" != "$DASHBOARD_PASSWORD_CONFIRM" ]; then
        echo -e "${RED}✗ Les mots de passe ne correspondent pas${NC}"
        echo ""
        continue
    fi

    break
done

# Vérifier que Node.js est installé pour hasher
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠️  Node.js n'est pas installé${NC}"
    echo "Le mot de passe sera stocké en clair pour l'instant"
    echo "Installez Node.js puis lancez: node dashboard/scripts/hash_password.js"

    sed -i "s|DASHBOARD_PASSWORD=CHANGEZ_MOI_PAR_MOT_DE_PASSE_FORT|DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD|" .env
else
    # Vérifier que bcryptjs est installé
    if [ ! -f "dashboard/node_modules/bcryptjs/package.json" ]; then
        echo -e "${YELLOW}Installation de bcryptjs...${NC}"
        cd dashboard
        npm install bcryptjs --silent
        cd ..
        echo -e "${GREEN}✓ bcryptjs installé${NC}"
    fi

    # Hasher le mot de passe
    echo "Hashage du mot de passe avec bcrypt..."
    HASHED_PASSWORD=$(node dashboard/scripts/hash_password.js --quiet "$DASHBOARD_PASSWORD" 2>/dev/null)

    if [ -n "$HASHED_PASSWORD" ]; then
        # Le hash est déjà échappé pour Docker Compose ($$) par hash_password.js
        # Échapper uniquement pour sed (doubler les backslashes si présents)
        ESCAPED_HASH=$(echo "$HASHED_PASSWORD" | sed 's/\\/\\\\/g')
        sed -i "s|DASHBOARD_PASSWORD=CHANGEZ_MOI_PAR_MOT_DE_PASSE_FORT|DASHBOARD_PASSWORD=$ESCAPED_HASH|" .env
        echo -e "${GREEN}✓ Mot de passe hashé avec bcrypt (échappé pour Docker Compose)${NC}"
    else
        echo -e "${RED}✗ Échec du hashage${NC}"
        sed -i "s|DASHBOARD_PASSWORD=CHANGEZ_MOI_PAR_MOT_DE_PASSE_FORT|DASHBOARD_PASSWORD=$DASHBOARD_PASSWORD|" .env
        echo -e "${YELLOW}⚠️  Mot de passe stocké en clair${NC}"
    fi
fi

echo ""

###############################################################################
# ÉTAPE 4 : Configuration optionnelle
###############################################################################

echo -e "${BLUE}${BOLD}[ÉTAPE 4/4] Configuration optionnelle${NC}"
echo ""

# Demander le domaine pour ALLOWED_ORIGINS
echo -e "${YELLOW}Domaine pour CORS (ex: https://votredomaine.com)${NC}"
echo "Laisser vide pour utiliser localhost uniquement"
read -p "> " ALLOWED_ORIGINS

if [ -n "$ALLOWED_ORIGINS" ]; then
    # Ajouter ALLOWED_ORIGINS si pas déjà présent
    if ! grep -q "^ALLOWED_ORIGINS=" .env; then
        echo "" >> .env
        echo "# CORS Configuration" >> .env
        echo "ALLOWED_ORIGINS=$ALLOWED_ORIGINS" >> .env
        echo -e "${GREEN}✓ ALLOWED_ORIGINS configuré${NC}"
    fi
else
    echo -e "${YELLOW}→ CORS non configuré (localhost uniquement)${NC}"
fi

echo ""

###############################################################################
# RÉSUMÉ
###############################################################################

echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  ✓ FICHIER .env INITIALISÉ AVEC SUCCÈS${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BOLD}Récapitulatif :${NC}"
echo "  • Fichier créé avec permissions 600"
echo "  • API_KEY générée automatiquement"
echo "  • JWT_SECRET généré automatiquement"
echo "  • Utilisateur Dashboard: $DASHBOARD_USER"
if [ -n "$HASHED_PASSWORD" ]; then
    echo "  • Mot de passe Dashboard: hashé avec bcrypt ✓"
else
    echo "  • Mot de passe Dashboard: EN CLAIR ⚠️"
fi
echo ""

echo -e "${YELLOW}${BOLD}⚠️  IMPORTANT :${NC}"
echo "  • Conservez votre mot de passe dans un gestionnaire sécurisé"
echo "  • NE JAMAIS commiter le fichier .env dans git"
echo "  • Le fichier .env est déjà dans .gitignore"
echo ""

echo -e "${BLUE}Prochaines étapes :${NC}"
echo "  1. Vérifier la configuration : cat .env"
echo "  2. Configurer Google Drive : ./scripts/setup_gdrive_headless.sh"
echo "  3. Vérifier la sécurité : ./scripts/verify_security.sh"
echo "  4. Démarrer l'application : docker compose up -d"
echo ""
