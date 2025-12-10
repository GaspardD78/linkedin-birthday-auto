#!/bin/bash

###############################################################################
# Configuration Google Drive SANS NAVIGATEUR
# Pour serveurs headless (sans interface graphique)
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
echo -e "${BLUE}${BOLD}  📦 CONFIGURATION GOOGLE DRIVE - MODE HEADLESS${NC}"
echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Ce script configure rclone pour Google Drive sur un serveur"
echo "sans navigateur (headless), en utilisant un fichier rclone.conf"
echo "généré depuis un autre ordinateur."
echo ""

###############################################################################
# ÉTAPE 1 : VÉRIFIER RCLONE
###############################################################################

echo -e "${BLUE}${BOLD}[ÉTAPE 1/4] Vérification de rclone${NC}"
echo ""

if ! command -v rclone &> /dev/null; then
    echo -e "${YELLOW}rclone n'est pas installé. Installation...${NC}"

    # Détecter l'architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        RCLONE_ARCH="amd64"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        RCLONE_ARCH="arm64"
    else
        echo -e "${RED}Architecture non supportée: $ARCH${NC}"
        exit 1
    fi

    # Télécharger et installer rclone
    cd /tmp
    curl -O https://downloads.rclone.org/rclone-current-linux-${RCLONE_ARCH}.zip
    unzip -q rclone-current-linux-${RCLONE_ARCH}.zip
    cd rclone-*-linux-${RCLONE_ARCH}
    sudo cp rclone /usr/bin/
    sudo chown root:root /usr/bin/rclone
    sudo chmod 755 /usr/bin/rclone

    echo -e "${GREEN}✓ rclone installé avec succès${NC}"
else
    VERSION=$(rclone version | head -n 1 | awk '{print $2}')
    echo -e "${GREEN}✓ rclone déjà installé (version $VERSION)${NC}"
fi

echo ""

###############################################################################
# ÉTAPE 2 : INSTRUCTIONS POUR GÉNÉRER LE FICHIER
###############################################################################

echo -e "${BLUE}${BOLD}[ÉTAPE 2/4] Génération du fichier rclone.conf${NC}"
echo ""
echo "Vous devez générer un fichier rclone.conf depuis un ordinateur"
echo "avec un navigateur (Windows, Mac, ou Linux avec interface graphique)."
echo ""
echo -e "${YELLOW}${BOLD}Instructions pour votre PC local :${NC}"
echo ""
echo "1. Installez rclone sur votre PC local :"
echo "   • Windows : https://rclone.org/downloads/"
echo "   • Mac     : brew install rclone"
echo "   • Linux   : sudo apt install rclone"
echo ""
echo "2. Configurez Google Drive sur votre PC :"
echo "   ${BOLD}rclone config${NC}"
echo ""
echo "3. Suivez ces options :"
echo "   • n (New remote)"
echo "   • Nom: gdrive"
echo "   • Type: 15 (Google Drive)"
echo "   • client_id: [laissez vide]"
echo "   • client_secret: [laissez vide]"
echo "   • scope: 1 (Full access)"
echo "   • root_folder_id: [laissez vide]"
echo "   • service_account_file: [laissez vide]"
echo "   • Edit advanced config: n"
echo "   • Use auto config: y (autorise l'accès dans le navigateur)"
echo "   • Configure as team drive: n"
echo "   • Keep this remote: y"
echo ""
echo "4. Localisez le fichier rclone.conf :"
echo "   • Windows: %USERPROFILE%\\.config\\rclone\\rclone.conf"
echo "   • Mac/Linux: ~/.config/rclone/rclone.conf"
echo ""
echo "5. Transférez ce fichier sur votre serveur par SCP :"
echo "   ${BOLD}scp ~/.config/rclone/rclone.conf user@votre-serveur:/tmp/rclone.conf${NC}"
echo ""
echo -e "${YELLOW}${BOLD}OU copiez le contenu du fichier :${NC}"
echo "   cat ~/.config/rclone/rclone.conf"
echo "   (puis collez le contenu quand on vous le demandera)"
echo ""

read -p "Avez-vous déjà le fichier rclone.conf ? (o/n) : " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[OoYy]$ ]]; then
    echo ""
    echo -e "${YELLOW}Revenez lorsque vous aurez généré le fichier rclone.conf${NC}"
    exit 0
fi

###############################################################################
# ÉTAPE 3 : IMPORTER LE FICHIER
###############################################################################

echo ""
echo -e "${BLUE}${BOLD}[ÉTAPE 3/4] Import du fichier rclone.conf${NC}"
echo ""
echo "Choisissez votre méthode d'import :"
echo "  1) J'ai transféré le fichier en /tmp/rclone.conf"
echo "  2) Je vais coller le contenu du fichier"
echo "  3) Le fichier est dans un autre emplacement"
echo ""
read -p "Votre choix (1/2/3) : " -n 1 -r CHOICE
echo ""
echo ""

# Créer le répertoire de configuration
mkdir -p ~/.config/rclone

case $CHOICE in
    1)
        # Fichier en /tmp
        if [ ! -f "/tmp/rclone.conf" ]; then
            echo -e "${RED}✗ Fichier /tmp/rclone.conf introuvable${NC}"
            exit 1
        fi

        cp /tmp/rclone.conf ~/.config/rclone/rclone.conf
        chmod 600 ~/.config/rclone/rclone.conf
        echo -e "${GREEN}✓ Fichier importé depuis /tmp/rclone.conf${NC}"
        ;;

    2)
        # Coller le contenu
        echo "Collez le contenu de votre fichier rclone.conf ci-dessous."
        echo "Appuyez sur Ctrl+D quand vous avez terminé :"
        echo ""

        cat > ~/.config/rclone/rclone.conf
        chmod 600 ~/.config/rclone/rclone.conf

        echo ""
        echo -e "${GREEN}✓ Fichier importé depuis stdin${NC}"
        ;;

    3)
        # Autre emplacement
        read -p "Entrez le chemin complet du fichier : " FILE_PATH

        if [ ! -f "$FILE_PATH" ]; then
            echo -e "${RED}✗ Fichier introuvable: $FILE_PATH${NC}"
            exit 1
        fi

        cp "$FILE_PATH" ~/.config/rclone/rclone.conf
        chmod 600 ~/.config/rclone/rclone.conf
        echo -e "${GREEN}✓ Fichier importé depuis $FILE_PATH${NC}"
        ;;

    *)
        echo -e "${RED}✗ Choix invalide${NC}"
        exit 1
        ;;
esac

###############################################################################
# ÉTAPE 4 : VÉRIFIER LA CONNEXION
###############################################################################

echo ""
echo -e "${BLUE}${BOLD}[ÉTAPE 4/4] Vérification de la connexion${NC}"
echo ""

# Vérifier que le remote existe
if ! rclone listremotes | grep -q "gdrive:"; then
    echo -e "${RED}✗ Le remote 'gdrive:' n'a pas été trouvé dans le fichier${NC}"
    echo ""
    echo "Vérifiez que votre fichier rclone.conf contient bien une section [gdrive]"
    echo ""
    echo "Contenu actuel :"
    cat ~/.config/rclone/rclone.conf
    exit 1
fi

echo -e "${GREEN}✓ Remote 'gdrive' trouvé${NC}"
echo ""

# Tester la connexion
echo "Test de connexion à Google Drive..."
if rclone lsd gdrive: &> /dev/null; then
    echo -e "${GREEN}${BOLD}✓ CONNEXION RÉUSSIE !${NC}"
    echo ""
    echo "Contenu de votre Google Drive :"
    rclone lsd gdrive: | head -10
    echo ""
else
    echo -e "${RED}${BOLD}✗ ÉCHEC DE LA CONNEXION${NC}"
    echo ""
    echo -e "${YELLOW}Le token OAuth a peut-être expiré ou est invalide.${NC}"
    echo ""
    echo "Essayez de :"
    echo "  1. Re-générer le fichier rclone.conf sur votre PC"
    echo "  2. Vérifier que vous avez bien autorisé l'accès à Google Drive"
    echo "  3. Copier le NOUVEAU fichier sur le serveur"
    echo ""
    echo "Erreur détaillée :"
    rclone lsd gdrive: 2>&1
    exit 1
fi

###############################################################################
# FINALISATION
###############################################################################

echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  ✓ CONFIGURATION TERMINÉE AVEC SUCCÈS${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Votre serveur est maintenant connecté à Google Drive !"
echo ""
echo "Prochaines étapes :"
echo "  • Testez le backup : ./scripts/backup_to_gdrive.sh"
echo "  • Vérifiez la sécurité : ./scripts/verify_security.sh"
echo ""
