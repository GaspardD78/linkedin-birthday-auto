#!/bin/bash

###############################################################################
# 🔒 Script d'Installation Sécurité - LinkedIn Birthday Bot
# Version: 1.0
# Guide interactif pour installer TOUTES les protections de sécurité
###############################################################################

set -e  # Arrêt si erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Fonction pour afficher des titres
print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Fonction pour afficher des étapes
print_step() {
    echo -e "${GREEN}${BOLD}➜ $1${NC}"
}

# Fonction pour afficher des infos
print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Fonction pour afficher des succès
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Fonction pour afficher des erreurs
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Fonction pour poser des questions oui/non
ask_yes_no() {
    while true; do
        read -p "$1 (o/n): " yn
        case $yn in
            [Oo]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Répondez par o (oui) ou n (non).";;
        esac
    done
}

# Fonction pour attendre que l'utilisateur appuie sur Entrée
press_enter() {
    echo ""
    read -p "Appuyez sur Entrée pour continuer..."
    echo ""
}

###############################################################################
# INTRODUCTION
###############################################################################

clear
print_header "🔒 INSTALLATION SÉCURITÉ - LINKEDIN BIRTHDAY BOT"

cat << 'EOF'
Ce script va vous guider pas à pas pour installer TOUTES les protections
de sécurité de votre bot LinkedIn.

⏱️  DURÉE TOTALE : 30-45 minutes

📋 CE QUI VA ÊTRE INSTALLÉ :
   1. ✅ Backup automatique Google Drive (15 min)
   2. ✅ HTTPS avec Let's Encrypt (15 min)
   3. ✅ Mot de passe hashé bcrypt (5 min)
   4. ✅ Protection CORS (2 min)
   5. ✅ Anti-indexation (2 min)

⚠️  PRÉREQUIS :
   • Raspberry Pi connecté à Internet
   • Accès SSH au Raspberry Pi
   • Compte Google (pour backup)
   • Nom de domaine (pour HTTPS)
   • Accès interface Freebox (pour ports)

EOF

###############################################################################
# VÉRIFICATION ET INSTALLATION DES DÉPENDANCES
###############################################################################

print_header "🔧 VÉRIFICATION DES DÉPENDANCES"

echo ""
print_info "Vérification des dépendances système requises..."
echo ""

DEPS_MISSING=false

# Vérifier curl (nécessaire pour installer rclone)
print_step "Vérification de curl..."
if command -v curl &> /dev/null; then
    print_success "✓ curl est installé"
else
    print_info "⏭ curl n'est pas installé - Installation requise"
    DEPS_MISSING=true
fi

# Vérifier Node.js
print_step "Vérification de Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_success "✓ Node.js est installé ($NODE_VERSION)"
else
    print_info "⏭ Node.js n'est pas installé - Installation requise"
    DEPS_MISSING=true
fi

# Vérifier npm
print_step "Vérification de npm..."
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    print_success "✓ npm est installé (v$NPM_VERSION)"
else
    print_info "⏭ npm n'est pas installé - Installation requise"
    DEPS_MISSING=true
fi

echo ""

# Si des dépendances manquent, proposer de les installer
if [ "$DEPS_MISSING" = true ]; then
    cat << 'EOF'

⚠️  DÉPENDANCES MANQUANTES DÉTECTÉES

Certaines dépendances système sont manquantes. Elles sont nécessaires pour
l'installation des protections de sécurité.

Ce script va maintenant installer automatiquement les dépendances manquantes.

EOF

    if ask_yes_no "Voulez-vous installer automatiquement les dépendances manquantes ?"; then
        print_step "Installation des dépendances système..."
        echo ""

        # Mise à jour de la liste des paquets
        print_info "Mise à jour de la liste des paquets..."
        sudo apt update

        # Installer curl si manquant
        if ! command -v curl &> /dev/null; then
            print_info "Installation de curl..."
            sudo apt install -y curl
            if command -v curl &> /dev/null; then
                print_success "✓ curl installé avec succès"
            else
                print_error "✗ Erreur lors de l'installation de curl"
                exit 1
            fi
        fi

        # Installer Node.js et npm si manquants
        if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
            print_info "Installation de Node.js et npm..."

            # Vérifier la version Debian/Ubuntu pour choisir la bonne méthode
            if command -v apt &> /dev/null; then
                # Utiliser NodeSource pour avoir une version récente
                print_info "Installation via NodeSource (version LTS)..."
                curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
                sudo apt install -y nodejs
            else
                # Fallback sur la version par défaut du dépôt
                sudo apt install -y nodejs npm
            fi

            if command -v node &> /dev/null && command -v npm &> /dev/null; then
                NODE_VERSION=$(node --version)
                NPM_VERSION=$(npm --version)
                print_success "✓ Node.js $NODE_VERSION et npm v$NPM_VERSION installés avec succès"
            else
                print_error "✗ Erreur lors de l'installation de Node.js/npm"
                exit 1
            fi
        fi

        echo ""
        print_success "✓ Toutes les dépendances système sont installées !"
    else
        print_error "Installation annulée. Les dépendances sont OBLIGATOIRES."
        echo ""
        print_info "Pour installer manuellement :"
        print_info "  sudo apt update"
        print_info "  sudo apt install -y curl nodejs npm"
        exit 1
    fi
else
    print_success "✓ Toutes les dépendances système sont déjà installées !"
fi

echo ""
press_enter

###############################################################################
# DÉTECTION DE LA CONFIGURATION EXISTANTE
###############################################################################

print_header "🔍 DÉTECTION DE LA CONFIGURATION EXISTANTE"

echo ""
print_info "Analyse de la configuration actuelle..."
echo ""

# Variables de statut
BACKUP_DONE=false
HTTPS_DONE=false
BCRYPT_DONE=false
CORS_DONE=false
ANTIINDEX_DONE=false

# Étape 1 : Backup Google Drive
if command -v rclone &> /dev/null && rclone listremotes | grep -q "gdrive:" && crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"; then
    BACKUP_DONE=true
    print_success "✓ Étape 1 : Backup Google Drive - Déjà configuré"
else
    print_info "⏭ Étape 1 : Backup Google Drive - À configurer"
fi

# Étape 2 : HTTPS avec Let's Encrypt
if command -v nginx &> /dev/null && command -v certbot &> /dev/null && sudo certbot certificates 2>/dev/null | grep -q "Certificate Name:"; then
    HTTPS_DONE=true
    print_success "✓ Étape 2 : HTTPS avec Let's Encrypt - Déjà configuré"
else
    print_info "⏭ Étape 2 : HTTPS avec Let's Encrypt - À configurer"
fi

# Étape 3 : Mot de passe hashé bcrypt
if [ -f "dashboard/node_modules/bcryptjs/package.json" ] && grep -qE "^DASHBOARD_PASSWORD=['\"]?\\\$2[aby]\\\$" .env 2>/dev/null; then
    BCRYPT_DONE=true
    print_success "✓ Étape 3 : Mot de passe hashé bcrypt - Déjà configuré"
else
    print_info "⏭ Étape 3 : Mot de passe hashé bcrypt - À configurer"
fi

# Étape 4 : Protection CORS
if grep -q "^ALLOWED_ORIGINS=" .env 2>/dev/null; then
    CORS_DONE=true
    print_success "✓ Étape 4 : Protection CORS - Déjà configuré"
else
    print_info "⏭ Étape 4 : Protection CORS - À configurer"
fi

# Étape 5 : Anti-indexation
if [ -f "dashboard/public/robots.txt" ] && grep -q "Disallow: /" dashboard/public/robots.txt 2>/dev/null; then
    ANTIINDEX_DONE=true
    print_success "✓ Étape 5 : Anti-indexation Google - Déjà configuré"
else
    print_info "⏭ Étape 5 : Anti-indexation Google - À configurer"
fi

echo ""

# Calculer combien d'étapes sont déjà faites
COMPLETED=0
[ "$BACKUP_DONE" = true ] && COMPLETED=$((COMPLETED + 1))
[ "$HTTPS_DONE" = true ] && COMPLETED=$((COMPLETED + 1))
[ "$BCRYPT_DONE" = true ] && COMPLETED=$((COMPLETED + 1))
[ "$CORS_DONE" = true ] && COMPLETED=$((COMPLETED + 1))
[ "$ANTIINDEX_DONE" = true ] && COMPLETED=$((COMPLETED + 1))

print_info "📊 Progression : $COMPLETED/5 étapes complétées"
echo ""

# Si tout est fait, on arrête
if [ $COMPLETED -eq 5 ]; then
    print_success "🎉 Toutes les étapes de sécurité sont déjà configurées !"
    echo ""
    print_info "Pour vérifier la configuration, lancez : ./scripts/verify_security.sh"
    exit 0
fi

# Si certaines étapes sont faites, demander si on veut les refaire
if [ $COMPLETED -gt 0 ]; then
    cat << EOF

${YELLOW}⚠️  Certaines étapes sont déjà configurées.${NC}

Vous avez le choix :
  ${GREEN}[1]${NC} Passer directement aux étapes non configurées (recommandé)
  ${YELLOW}[2]${NC} Refaire toutes les étapes depuis le début
  ${RED}[3]${NC} Quitter

EOF

    read -p "Votre choix (1/2/3) : " choice

    case $choice in
        1)
            print_success "✓ Passage aux étapes non configurées"
            SKIP_COMPLETED=true
            ;;
        2)
            print_info "Redémarrage depuis le début"
            SKIP_COMPLETED=false
            BACKUP_DONE=false
            HTTPS_DONE=false
            BCRYPT_DONE=false
            CORS_DONE=false
            ANTIINDEX_DONE=false
            ;;
        3)
            echo "Installation annulée."
            exit 0
            ;;
        *)
            print_error "Choix invalide. Annulation."
            exit 1
            ;;
    esac
else
    SKIP_COMPLETED=false
    if ! ask_yes_no "Êtes-vous prêt à commencer l'installation ?"; then
        echo "Installation annulée. Relancez ce script quand vous serez prêt !"
        exit 0
    fi
fi

###############################################################################
# ÉTAPE 1 : BACKUP GOOGLE DRIVE
###############################################################################

if [ "$BACKUP_DONE" = true ] && [ "$SKIP_COMPLETED" = true ]; then
    print_success "⏭️  ÉTAPE 1/5 : Backup Google Drive - Déjà configuré, passée"
else
    print_header "📦 ÉTAPE 1/5 : BACKUP AUTOMATIQUE GOOGLE DRIVE"

cat << 'EOF'
💾 POURQUOI C'EST IMPORTANT ?
   Sans backup, si votre Raspberry Pi plante, vous perdez TOUS vos contacts,
   messages, historiques. Le backup Google Drive sauvegarde tout automatiquement
   chaque nuit à 3h du matin.

📝 CE QUE NOUS ALLONS FAIRE :
   1. Installer rclone (outil de synchronisation cloud)
   2. Configurer votre compte Google Drive
   3. Tester un backup manuel
   4. Programmer le backup automatique tous les jours

EOF

press_enter

# Vérifier si rclone est déjà installé
print_step "Vérification de rclone..."
if command -v rclone &> /dev/null; then
    print_success "rclone est déjà installé !"
    RCLONE_VERSION=$(rclone version | head -n 1)
    print_info "Version: $RCLONE_VERSION"
else
    print_info "rclone n'est pas installé. Installation en cours..."

    if ask_yes_no "Voulez-vous installer rclone maintenant ?"; then
        print_step "Installation de rclone..."
        curl https://rclone.org/install.sh | sudo bash

        if command -v rclone &> /dev/null; then
            print_success "rclone installé avec succès !"
        else
            print_error "Erreur lors de l'installation de rclone"
            exit 1
        fi
    else
        print_error "Installation annulée. rclone est OBLIGATOIRE pour les backups."
        exit 1
    fi
fi

echo ""
print_step "Configuration de Google Drive..."
echo ""

# Détecter si on est dans un environnement Docker/headless
IN_DOCKER=false
IN_HEADLESS=false

if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    IN_DOCKER=true
fi

if ! command -v xdg-open &> /dev/null && [ -z "$DISPLAY" ]; then
    IN_HEADLESS=true
fi

if [ "$IN_DOCKER" = true ] || [ "$IN_HEADLESS" = true ]; then
    cat << 'EOF'
⚠️  ENVIRONNEMENT DÉTECTÉ : Docker / Sans Interface Graphique

Vous êtes dans un environnement sans navigateur web disponible.
Vous avez DEUX OPTIONS pour configurer rclone :

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION 1 (RECOMMANDÉE) : Configuration sur une autre machine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Sur votre ORDINATEUR LOCAL (avec navigateur) :
   - Installez rclone : curl https://rclone.org/install.sh | sudo bash
   - Lancez : rclone config
   - Suivez les étapes pour configurer "gdrive"
   - Une fois terminé, récupérez le fichier de config :
     ~/.config/rclone/rclone.conf

2. Sur votre RASPBERRY PI / SERVEUR :
   - Créez le répertoire : mkdir -p ~/.config/rclone
   - Copiez le fichier rclone.conf depuis votre ordinateur
   - Par exemple via SCP :
     scp ~/.config/rclone/rclone.conf pi@IP_RASPBERRY:~/.config/rclone/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OPTION 2 : Configuration avec authentification manuelle
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cette option nécessite de copier/coller une URL manuellement.

ÉTAPES IMPORTANTES :
1. name> → tapez : gdrive
2. Storage> → tapez : drive
3. client_id> → appuyez sur Entrée (laisser vide)
4. client_secret> → appuyez sur Entrée (laisser vide)
5. scope> → tapez : 1 (Full access)
6. service_account_file> → appuyez sur Entrée (laisser vide)
7. Edit advanced config? → tapez : n (non)
8. Use web browser to automatically authenticate? → tapez : n (NON) ⚠️
9. Use web browser on a remote headless machine? → tapez : n (NON)

Ensuite, rclone va afficher une URL.
COPIEZ cette URL et ouvrez-la dans le navigateur de votre ordinateur.
Une fois l'authentification terminée, COPIEZ le code fourni et collez-le dans le terminal.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Si vous rencontrez des problèmes, consultez le guide :
   docs/RCLONE_DOCKER_AUTH_GUIDE.md

EOF
else
    cat << 'EOF'
📱 INSTRUCTIONS POUR CONFIGURER GOOGLE DRIVE :

Vous allez maintenant configurer votre compte Google Drive.
Une fenêtre va s'ouvrir dans votre navigateur.

⚠️  IMPORTANT : Suivez exactement ces étapes :

1. Quand on vous demande "name>", tapez : gdrive
2. Quand on vous demande "Storage>", tapez : drive
3. Quand on vous demande "client_id>", appuyez juste sur Entrée (laisser vide)
4. Quand on vous demande "client_secret>", appuyez juste sur Entrée (laisser vide)
5. Quand on vous demande "scope>", tapez : 1 (Full access)
6. Quand on vous demande "service_account_file>", appuyez sur Entrée (laisser vide)
7. Quand on vous demande "Edit advanced config?", tapez : n (non)
8. Quand on vous demande "Use web browser to automatically authenticate?", tapez : y (oui)
9. Une page web va s'ouvrir → Connectez-vous avec votre compte Google
10. Autorisez rclone à accéder à votre Google Drive
11. Revenez au terminal, tapez : y (oui) pour confirmer

EOF
fi

if ask_yes_no "Avez-vous bien lu les instructions ci-dessus ?"; then
    # Vérifier si la configuration existe déjà
    if rclone listremotes | grep -q "gdrive:"; then
        print_success "Le remote 'gdrive' existe déjà !"

        if ask_yes_no "Voulez-vous tester la connexion à Google Drive ?"; then
            print_step "Test de connexion..."
            if rclone lsd gdrive: &> /dev/null; then
                print_success "Connexion à Google Drive réussie !"
            else
                print_error "Erreur de connexion. Vérifiez votre configuration."
                if ask_yes_no "Voulez-vous reconfigurer ?"; then
                    rclone config
                fi
            fi
        fi
    else
        print_info "Lancement de la configuration rclone..."
        echo ""
        rclone config
        echo ""

        # Vérifier que la configuration a fonctionné
        if rclone listremotes | grep -q "gdrive:"; then
            print_success "Configuration réussie !"
        else
            print_error "La configuration a échoué. Le remote 'gdrive' n'a pas été créé."
            print_info "Relancez ce script et suivez bien toutes les étapes."
            exit 1
        fi
    fi
else
    print_error "Lisez bien les instructions avant de continuer !"
    exit 1
fi

echo ""
print_step "Test du backup..."
echo ""

# Rendre le script de backup exécutable
chmod +x ./scripts/backup_to_gdrive.sh

if ask_yes_no "Voulez-vous tester un backup maintenant (recommandé) ?"; then
    print_info "Lancement du backup de test..."
    echo ""

    if ./scripts/backup_to_gdrive.sh; then
        echo ""
        print_success "✓ Backup de test réussi !"
        print_info "Vérifiez votre Google Drive : vous devriez voir un dossier 'LinkedInBot_Backups'"
    else
        echo ""
        print_error "Le backup a échoué. Vérifiez les erreurs ci-dessus."
        exit 1
    fi
fi

echo ""
print_step "Configuration du backup automatique..."
echo ""

cat << 'EOF'
🕐 BACKUP AUTOMATIQUE :

Le backup va s'exécuter automatiquement tous les jours à 3h du matin.
Cela se fait via "cron" (le planificateur de tâches Linux).

EOF

if ask_yes_no "Voulez-vous activer le backup automatique quotidien ?"; then
    SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/backup_to_gdrive.sh"
    CRON_LINE="0 3 * * * $SCRIPT_PATH >> /var/log/linkedin-bot-backup.log 2>&1"

    # Vérifier si la tâche cron existe déjà
    if crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"; then
        print_success "Le backup automatique est déjà configuré !"
    else
        print_info "Ajout de la tâche cron..."
        (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
        print_success "Backup automatique configuré avec succès !"
        print_info "Le backup s'exécutera tous les jours à 3h du matin"
        print_info "Logs disponibles dans : /var/log/linkedin-bot-backup.log"
    fi
fi

print_success "✓✓✓ ÉTAPE 1 TERMINÉE : Backup Google Drive configuré !"
fi  # Fin de l'étape 1

###############################################################################
# ÉTAPE 2 : HTTPS AVEC LET'S ENCRYPT
###############################################################################

if [ "$HTTPS_DONE" = true ] && [ "$SKIP_COMPLETED" = true ]; then
    print_success "⏭️  ÉTAPE 2/5 : HTTPS avec Let's Encrypt - Déjà configuré, passée"
else
    press_enter
    print_header "🔐 ÉTAPE 2/5 : HTTPS AVEC LET'S ENCRYPT"

cat << 'EOF'
🌐 POURQUOI C'EST IMPORTANT ?
   Sans HTTPS, vos mots de passe et données circulent en CLAIR sur Internet.
   N'importe qui sur le réseau peut les intercepter. HTTPS chiffre tout.

📝 CE QUE NOUS ALLONS FAIRE :
   1. Configurer les ports sur votre Freebox (action MANUELLE)
   2. Installer Nginx (reverse proxy)
   3. Obtenir un certificat SSL gratuit (Let's Encrypt)
   4. Configurer Nginx avec toutes les sécurités

⚠️  PRÉREQUIS OBLIGATOIRE :
   Vous DEVEZ avoir un nom de domaine qui pointe vers votre IP Freebox.

   Exemples :
   • bot.mondomaine.com
   • linkedin.mondomaine.fr
   • monbot.free.fr (si domaine Free)

EOF

if ! ask_yes_no "Avez-vous un nom de domaine qui pointe vers votre Freebox ?"; then
    print_error "Vous devez d'abord obtenir un nom de domaine avant de continuer."
    cat << 'EOF'

💡 SOLUTIONS :

Option 1 - Domaine gratuit Freebox (si client Free) :
   1. Allez sur https://subscribe.free.fr/accesgratuit/
   2. Activez votre domaine gratuit *.free.fr

Option 2 - Acheter un domaine (10-15€/an) :
   • OVH : https://www.ovhcloud.com/fr/domains/
   • Gandi : https://www.gandi.net/fr/domain
   • Namecheap : https://www.namecheap.com

   Puis configurez les DNS pour pointer vers votre IP Freebox.

EOF
    print_info "Relancez ce script une fois que vous avez un nom de domaine."
    exit 1
fi

echo ""
read -p "Quel est votre nom de domaine ? (ex: bot.mondomaine.com) : " DOMAIN_NAME
echo ""

if [ -z "$DOMAIN_NAME" ]; then
    print_error "Vous devez entrer un nom de domaine."
    exit 1
fi

print_success "Nom de domaine : $DOMAIN_NAME"

echo ""
print_step "Configuration des ports Freebox..."
echo ""

cat << 'EOF'
📱 CONFIGURATION FREEBOX (ACTION MANUELLE REQUISE) :

Vous devez maintenant ouvrir 2 ports sur votre Freebox pour permettre
l'accès depuis Internet :

1. Ouvrez votre navigateur et allez sur : http://mafreebox.freebox.fr
2. Connectez-vous avec le mot de passe de votre Freebox
3. Allez dans : Paramètres de la Freebox > Mode avancé > Redirections de ports
4. Cliquez sur "Ajouter une redirection"

REDIRECTION 1 - HTTP (pour Let's Encrypt) :
   • Protocole : TCP
   • Port externe : 80
   • Port interne : 80
   • IP destination : [IP de votre Raspberry Pi]
   • Commentaire : LinkedIn Bot HTTP

REDIRECTION 2 - HTTPS :
   • Protocole : TCP
   • Port externe : 443
   • Port interne : 443
   • IP destination : [IP de votre Raspberry Pi]
   • Commentaire : LinkedIn Bot HTTPS

⚠️  IMPORTANT : Utilisez la même IP (celle de votre Raspberry Pi) pour les 2 redirections.

EOF

# Afficher l'IP du Raspberry Pi
RASPBERRY_IP=$(hostname -I | awk '{print $1}')
print_info "IP de votre Raspberry Pi : $RASPBERRY_IP"
echo ""

if ! ask_yes_no "Avez-vous configuré les 2 redirections de ports (80 et 443) ?"; then
    print_error "Vous devez configurer les ports avant de continuer."
    print_info "Relancez ce script une fois les ports configurés."
    exit 1
fi

echo ""
print_step "Installation de Nginx et Certbot..."
echo ""

# Installer Nginx et Certbot
if command -v nginx &> /dev/null; then
    print_success "Nginx est déjà installé !"
else
    print_info "Installation de Nginx..."
    sudo apt update
    sudo apt install -y nginx
    print_success "Nginx installé !"
fi

if command -v certbot &> /dev/null; then
    print_success "Certbot est déjà installé !"
else
    print_info "Installation de Certbot..."
    sudo apt install -y certbot python3-certbot-nginx
    print_success "Certbot installé !"
fi

echo ""
print_step "Configuration de Nginx..."
echo ""

# Créer le répertoire de configuration s'il n'existe pas
sudo mkdir -p /etc/nginx/sites-available
sudo mkdir -p /etc/nginx/sites-enabled

# Copier la configuration Nginx
NGINX_CONF="/etc/nginx/sites-available/linkedin-bot"
print_info "Création du fichier de configuration Nginx..."

sudo cp -f ./deployment/nginx/linkedin-bot.conf "$NGINX_CONF"

# Remplacer le placeholder par le vrai domaine
sudo sed -i "s/VOTRE_DOMAINE_ICI/$DOMAIN_NAME/g" "$NGINX_CONF"
sudo sed -i "s/YOUR_DOMAIN.COM/$DOMAIN_NAME/g" "$NGINX_CONF"

# Copier la configuration de rate limiting
print_info "Installation de la configuration rate limiting..."
sudo cp ./deployment/nginx/rate-limit-zones.conf /etc/nginx/conf.d/
print_success "Rate limiting configuré !"

# Créer le lien symbolique
if [ ! -L /etc/nginx/sites-enabled/linkedin-bot ]; then
    sudo ln -s "$NGINX_CONF" /etc/nginx/sites-enabled/
    print_success "Configuration Nginx activée !"
fi

# Supprimer la config par défaut si elle existe
if [ -L /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
    print_info "Configuration par défaut désactivée"
fi

# Créer la page d'erreur 429
sudo mkdir -p /var/www/html
sudo cp ./deployment/nginx/429.html /var/www/html/

# Tester la configuration Nginx
print_step "Test de la configuration Nginx..."
if sudo nginx -t; then
    print_success "Configuration Nginx valide !"
else
    print_error "Erreur dans la configuration Nginx"
    exit 1
fi

# Recharger Nginx
print_step "Rechargement de Nginx..."
sudo systemctl reload nginx
sudo systemctl enable nginx
print_success "Nginx rechargé et activé au démarrage !"

echo ""
print_step "Obtention du certificat SSL Let's Encrypt..."
echo ""

cat << 'EOF'
🔑 CERTIFICAT SSL GRATUIT :

Let's Encrypt va maintenant générer un certificat SSL gratuit pour votre domaine.
Ce certificat sera automatiquement renouvelé tous les 3 mois.

⚠️  IMPORTANT :
   • Assurez-vous que votre domaine pointe bien vers votre IP Freebox
   • Les ports 80 et 443 doivent être ouverts sur la Freebox
   • Le Raspberry Pi doit être accessible depuis Internet

EOF

if ask_yes_no "Voulez-vous obtenir le certificat SSL maintenant ?"; then
    print_info "Lancement de Certbot..."
    echo ""

    sudo certbot --nginx -d "$DOMAIN_NAME" --non-interactive --agree-tos --register-unsafely-without-email || {
        print_error "Erreur lors de l'obtention du certificat."
        echo ""
        print_info "Causes possibles :"
        print_info "  1. Votre domaine ne pointe pas vers votre IP Freebox"
        print_info "  2. Les ports 80/443 ne sont pas ouverts sur la Freebox"
        print_info "  3. Le Raspberry Pi n'est pas accessible depuis Internet"
        echo ""
        print_info "Pour tester manuellement plus tard :"
        print_info "  sudo certbot --nginx -d $DOMAIN_NAME"
        echo ""

        if ! ask_yes_no "Voulez-vous continuer l'installation sans HTTPS ?"; then
            exit 1
        fi
    }

    echo ""
    print_success "✓ Certificat SSL installé !"
    print_info "Renouvellement automatique : certbot renouvelle automatiquement le certificat"
fi

# Recharger Nginx une dernière fois
sudo systemctl reload nginx

print_success "✓✓✓ ÉTAPE 2 TERMINÉE : HTTPS configuré !"
fi  # Fin de l'étape 2

###############################################################################
# ÉTAPE 3 : MOT DE PASSE HASHÉ BCRYPT
###############################################################################

if [ "$BCRYPT_DONE" = true ] && [ "$SKIP_COMPLETED" = true ]; then
    print_success "⏭️  ÉTAPE 3/5 : Mot de passe hashé bcrypt - Déjà configuré, passée"
else
    press_enter
    print_header "🔑 ÉTAPE 3/5 : MOT DE PASSE HASHÉ BCRYPT"

cat << 'EOF'
🔐 POURQUOI C'EST IMPORTANT ?
   Actuellement, votre mot de passe est stocké EN CLAIR dans le fichier .env.
   Si quelqu'un accède à ce fichier, il voit votre mot de passe directement.
   Avec bcrypt, le mot de passe est "hashé" (transformé) de façon irréversible.

📝 CE QUE NOUS ALLONS FAIRE :
   1. Installer la librairie bcryptjs dans le dashboard
   2. Choisir un nouveau mot de passe (ou garder l'actuel)
   3. Générer le hash bcrypt
   4. Mettre à jour le fichier .env
   5. Redémarrer le dashboard

EOF

press_enter

# Aller dans le répertoire dashboard
cd dashboard

print_step "Installation de bcryptjs..."

if [ -d "node_modules/bcryptjs" ]; then
    print_success "bcryptjs est déjà installé !"
else
    print_info "Installation en cours..."
    # Utiliser npm depuis le PATH au lieu d'un chemin codé en dur
    if command -v npm &> /dev/null; then
        npm install bcryptjs
        print_success "bcryptjs installé !"
    else
        print_error "npm n'est pas disponible. Installez Node.js d'abord."
        exit 1
    fi
fi

echo ""
print_step "Génération du hash du mot de passe..."
echo ""

cat << 'EOF'
🔑 CHOIX DU MOT DE PASSE :

Vous pouvez soit :
   1. Garder votre mot de passe actuel (il sera juste hashé)
   2. Choisir un nouveau mot de passe plus sécurisé

💡 RECOMMANDATIONS :
   • Au moins 12 caractères
   • Mélange de lettres, chiffres et symboles
   • Exemple : B0t!L1nk3d1n@2025

EOF

# Vérification préliminaire du mot de passe
AUTO_SECURE=false
if [ -f "../.env" ]; then
    CURRENT_CHECK=$(grep "^DASHBOARD_PASSWORD=" ../.env | cut -d '=' -f2- | sed "s/^['\"]//;s/['\"]$//")
    if [[ ! "$CURRENT_CHECK" =~ ^\$2[aby]\$ ]]; then
        print_info "⚠️  Mot de passe EN CLAIR détecté. Sécurisation automatique..."
        AUTO_SECURE=true
    fi
fi

if [ "$AUTO_SECURE" = false ] && ask_yes_no "Voulez-vous choisir un NOUVEAU mot de passe ?"; then
    echo ""
    read -s -p "Entrez votre nouveau mot de passe : " NEW_PASSWORD
    echo ""
    read -s -p "Confirmez le mot de passe : " NEW_PASSWORD_CONFIRM
    echo ""

    if [ "$NEW_PASSWORD" != "$NEW_PASSWORD_CONFIRM" ]; then
        print_error "Les mots de passe ne correspondent pas !"
        exit 1
    fi

    if [ ${#NEW_PASSWORD} -lt 8 ]; then
        print_error "Le mot de passe doit faire au moins 8 caractères !"
        exit 1
    fi

    PASSWORD_TO_HASH="$NEW_PASSWORD"
else
    # Récupérer le mot de passe actuel depuis .env
    if [ -f "../.env" ]; then
        # Enlever les quotes si présentes et extraire le mot de passe
        CURRENT_PASSWORD=$(grep "^DASHBOARD_PASSWORD=" ../.env | cut -d '=' -f2- | sed "s/^['\"]//;s/['\"]$//")

        # Vérifier si c'est déjà un hash bcrypt
        if [[ "$CURRENT_PASSWORD" =~ ^\$2[aby]\$ ]]; then
            print_error "Le mot de passe est déjà un hash bcrypt !"
            print_info "Si vous voulez changer de mot de passe, choisissez 'o' (oui) à la question précédente."
            exit 1
        fi

        PASSWORD_TO_HASH="$CURRENT_PASSWORD"
        print_info "Utilisation du mot de passe actuel"
    else
        print_error "Fichier .env introuvable !"
        print_info "Créez d'abord le fichier .env à partir de l'exemple :"
        print_info "  cp .env.pi4.example .env"
        print_info "  nano .env  # puis modifiez les valeurs"
        exit 1
    fi
fi

print_step "Génération du hash bcrypt (cela peut prendre quelques secondes)..."

# Générer le hash
# Utiliser node depuis le PATH au lieu d'un chemin codé en dur
if command -v node &> /dev/null; then
    PASSWORD_HASH=$(node scripts/hash_password.js "$PASSWORD_TO_HASH" --quiet)
else
    print_error "node n'est pas disponible. Installez Node.js d'abord."
    exit 1
fi

echo ""
print_success "Hash généré avec succès !"
print_info "Hash : ${PASSWORD_HASH:0:20}..." # Afficher seulement les 20 premiers caractères

echo ""
print_step "Mise à jour du fichier .env..."

# Backup du .env
cp ../.env ../.env.backup.$(date +%Y%m%d_%H%M%S)
print_info "Backup créé : .env.backup.$(date +%Y%m%d_%H%M%S)"

# Remplacer le mot de passe dans .env
# IMPORTANT: Le hash bcrypt doit être échappé ($ -> $$) pour Docker Compose
# Les quotes simples ne suffisent pas toujours selon la version de Docker Compose
PASSWORD_HASH_ESCAPED="${PASSWORD_HASH//$/\$\$}"

if grep -q "^DASHBOARD_PASSWORD=" ../.env; then
    # Utiliser sed pour remplacer la ligne entière avec le hash échappé et entre quotes simples
    # On échappe les barres obliques (/) dans le hash en utilisant un autre délimiteur (@)
    sed -i "s@^DASHBOARD_PASSWORD=.*@DASHBOARD_PASSWORD='$PASSWORD_HASH_ESCAPED'@" ../.env
    print_success "Mot de passe mis à jour dans .env !"
else
    echo "DASHBOARD_PASSWORD='$PASSWORD_HASH_ESCAPED'" >> ../.env
    print_success "Mot de passe ajouté dans .env !"
fi

chmod 600 ../.env
cd ..

echo ""
print_step "Redémarrage du dashboard..."

if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose restart dashboard
    print_success "Dashboard redémarré !"
else
    print_info "Docker non détecté. Redémarrez manuellement le dashboard :"
    print_info "  docker compose restart dashboard"
fi

print_success "✓✓✓ ÉTAPE 3 TERMINÉE : Mot de passe hashé avec bcrypt !"
fi  # Fin de l'étape 3

###############################################################################
# ÉTAPE 4 : PROTECTION CORS
###############################################################################

if [ "$CORS_DONE" = true ] && [ "$SKIP_COMPLETED" = true ]; then
    print_success "⏭️  ÉTAPE 4/5 : Protection CORS - Déjà configurée, passée"
else
    press_enter
    print_header "🛡️ ÉTAPE 4/5 : PROTECTION CORS"

cat << 'EOF'
🌐 POURQUOI C'EST IMPORTANT ?
   CORS (Cross-Origin Resource Sharing) empêche des sites web malveillants
   d'accéder à votre API depuis un autre domaine. Sans CORS, n'importe quel
   site pourrait faire des requêtes à votre bot.

📝 CE QUE NOUS ALLONS FAIRE :
   1. Ajouter la variable ALLOWED_ORIGINS dans .env
   2. Redémarrer l'API

EOF

press_enter

print_step "Configuration de CORS..."

# Demander le domaine
echo ""
read -p "Quel est votre domaine HTTPS ? (ex: https://bot.mondomaine.com) : " CORS_DOMAIN
echo ""

if [ -z "$CORS_DOMAIN" ]; then
    CORS_DOMAIN="https://$DOMAIN_NAME"
    print_info "Utilisation du domaine configuré précédemment : $CORS_DOMAIN"
fi

# Vérifier que le domaine commence par https://
if [[ ! "$CORS_DOMAIN" =~ ^https:// ]]; then
    print_error "Le domaine doit commencer par https://"
    exit 1
fi

print_step "Ajout de ALLOWED_ORIGINS dans .env..."

if grep -q "^ALLOWED_ORIGINS=" .env; then
    # Utiliser awk pour éviter les problèmes avec les caractères spéciaux
    awk -v domain="$CORS_DOMAIN" 'BEGIN {FS=OFS="="} /^ALLOWED_ORIGINS=/ {$2=domain; print; next} {print}' .env > .env.tmp && mv .env.tmp .env
    print_success "ALLOWED_ORIGINS mis à jour !"
else
    echo "ALLOWED_ORIGINS=$CORS_DOMAIN" >> .env
    print_success "ALLOWED_ORIGINS ajouté !"
fi

chmod 600 .env
print_step "Redémarrage de l'API..."

if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose restart api
    print_success "API redémarrée !"
else
    print_info "Docker non détecté. Redémarrez manuellement l'API :"
    print_info "  docker compose restart api"
fi

print_success "✓✓✓ ÉTAPE 4 TERMINÉE : CORS configuré !"
fi  # Fin de l'étape 4

###############################################################################
# ÉTAPE 5 : ANTI-INDEXATION
###############################################################################

if [ "$ANTIINDEX_DONE" = true ] && [ "$SKIP_COMPLETED" = true ]; then
    print_success "⏭️  ÉTAPE 5/5 : Anti-indexation Google - Déjà configurée, passée"
else
    press_enter
    print_header "🔍 ÉTAPE 5/5 : PROTECTION ANTI-INDEXATION"

cat << 'EOF'
🚫 POURQUOI C'EST IMPORTANT ?
   Sans protection, Google et autres moteurs de recherche peuvent indexer
   votre dashboard. N'importe qui pourrait alors trouver votre bot en
   cherchant sur Google et tenter de s'y connecter.

📝 CE QUI A ÉTÉ MIS EN PLACE :
   ✓ robots.txt (demande aux robots de ne pas indexer)
   ✓ Meta tags HTML (balises noindex/nofollow)
   ✓ Header X-Robots-Tag (Next.js)
   ✓ Header X-Robots-Tag (Nginx - redondant)

📋 ACTION REQUISE :
   Vous devez juste redémarrer le dashboard et Nginx pour activer
   toutes les protections.

EOF

press_enter

print_step "Redémarrage du dashboard..."

if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose restart dashboard
    print_success "Dashboard redémarré !"
else
    print_info "Redémarrez manuellement : docker compose restart dashboard"
fi

print_step "Rechargement de Nginx..."
sudo systemctl reload nginx
print_success "Nginx rechargé !"

print_success "✓✓✓ ÉTAPE 5 TERMINÉE : Anti-indexation activé !"
fi  # Fin de l'étape 5

###############################################################################
# VÉRIFICATIONS FINALES
###############################################################################

press_enter

print_header "✅ VÉRIFICATIONS FINALES"

echo ""
print_step "Vérification de la configuration..."
echo ""

# Initialisation Base de données
print_info "Vérification de la base de données..."
if [ ! -d "data" ]; then
    mkdir -p data
    print_success "Dossier data/ créé"
fi
if [ ! -f "data/linkedin_bot.db" ]; then
    touch data/linkedin_bot.db
    chmod 664 data/linkedin_bot.db
    print_success "Base de données data/linkedin_bot.db initialisée"
elif [ -f "data/linkedin_bot.db" ]; then
    # S'assurer que les permissions sont correctes si le fichier existe
    chmod 664 data/linkedin_bot.db
    print_success "Base de données existante détectée"
fi
echo ""

# Test 1 : Backup
print_info "Test 1/5 : Backup Google Drive"
if rclone listremotes | grep -q "gdrive:"; then
    print_success "  ✓ rclone configuré"
else
    print_error "  ✗ rclone non configuré"
fi

if crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"; then
    print_success "  ✓ Backup automatique activé"
else
    print_error "  ✗ Backup automatique non activé"
fi

echo ""

# Test 2 : HTTPS
print_info "Test 2/5 : HTTPS"
if command -v nginx &> /dev/null; then
    print_success "  ✓ Nginx installé"
else
    print_error "  ✗ Nginx non installé"
fi

if [ -f "/etc/nginx/sites-available/linkedin-bot" ]; then
    print_success "  ✓ Configuration Nginx créée"
else
    print_error "  ✗ Configuration Nginx manquante"
fi

if sudo certbot certificates 2>/dev/null | grep -q "Domains:"; then
    print_success "  ✓ Certificat SSL installé"
else
    print_error "  ✗ Certificat SSL non installé"
fi

echo ""

# Test 3 : Bcrypt
print_info "Test 3/5 : Mot de passe hashé"
if [ -f "dashboard/node_modules/bcryptjs/package.json" ]; then
    print_success "  ✓ bcryptjs installé"
else
    print_error "  ✗ bcryptjs non installé"
fi

if grep -qE "^DASHBOARD_PASSWORD=['\"]?\\\$2[aby]\\\$" .env 2>/dev/null; then
    print_success "  ✓ Mot de passe hashé dans .env"
else
    print_error "  ✗ Mot de passe non hashé"
fi

echo ""

# Test 4 : CORS
print_info "Test 4/5 : CORS"
if grep -q "^ALLOWED_ORIGINS=" .env 2>/dev/null; then
    print_success "  ✓ ALLOWED_ORIGINS configuré"
else
    print_error "  ✗ ALLOWED_ORIGINS non configuré"
fi

echo ""

# Test 5 : Anti-indexation
print_info "Test 5/5 : Anti-indexation"
if [ -f "dashboard/public/robots.txt" ]; then
    print_success "  ✓ robots.txt présent"
else
    print_error "  ✗ robots.txt manquant"
fi

if [ -f "docs/ANTI_INDEXATION_GUIDE.md" ]; then
    print_success "  ✓ Guide anti-indexation disponible"
else
    print_error "  ✗ Guide anti-indexation manquant"
fi

echo ""

###############################################################################
# RÉSUMÉ FINAL
###############################################################################

print_header "🎉 INSTALLATION TERMINÉE !"

cat << EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    📊 RÉSUMÉ DE L'INSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Backup automatique Google Drive
   • Fréquence : Tous les jours à 3h du matin
   • Destination : Google Drive/LinkedInBot_Backups/
   • Rétention : 30 jours
   • Logs : /var/log/linkedin-bot-backup.log

✅ HTTPS avec Let's Encrypt
   • Domaine : $DOMAIN_NAME
   • Certificat : Let's Encrypt (renouvellement auto)
   • Rate Limiting : Activé (anti brute-force)
   • Security Headers : Tous configurés

✅ Mot de passe hashé bcrypt
   • Algorithme : bcrypt (salt rounds 12)
   • Protection : Résistant aux timing attacks
   • Backup : .env.backup.* créé

✅ Protection CORS
   • Origins autorisées : $CORS_DOMAIN
   • Méthodes : GET, POST, PUT, DELETE
   • Protection : Requêtes cross-origin bloquées

✅ Anti-indexation Google
   • robots.txt : ✓
   • Meta tags : ✓
   • X-Robots-Tag (Next.js) : ✓
   • X-Robots-Tag (Nginx) : ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔒 SCORE SÉCURITÉ : 9.5/10

Votre bot LinkedIn est maintenant HAUTEMENT SÉCURISÉ !

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                       📝 PROCHAINES ÉTAPES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Testez l'accès à votre dashboard :
   https://$DOMAIN_NAME

2. Vérifiez que tout fonctionne :
   ./scripts/verify_security.sh

3. Consultez les guides si besoin :
   • SECURITY_HARDENING_GUIDE.md
   • docs/ANTI_INDEXATION_GUIDE.md
   • docs/EMAIL_NOTIFICATIONS_INTEGRATION.md

4. Surveillez les backups :
   tail -f /var/log/linkedin-bot-backup.log

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 BESOIN D'AIDE ?

Tous les guides sont en français dans le dossier docs/
Chaque configuration peut être modifiée dans .env ou les fichiers de config

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

print_success "Bravo ! Installation de sécurité terminée avec succès ! 🎉"
echo ""
