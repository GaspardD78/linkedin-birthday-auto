#!/bin/bash

# =========================================================================
# 🚀 LinkedIn Birthday Bot - Installation Simplifiée Tout-en-Un
# =========================================================================
# Ce script orchestre l'installation complète du bot de manière interactive
# et optimisée pour Raspberry Pi 4 (et autres environnements Linux).
#
# USAGE:
#   ./setup.sh                    # Installation interactive complète
#   ./setup.sh --quick            # Installation rapide (skip les vérifications)
#   ./setup.sh --config-only      # Configuration uniquement (sans installation)
#   ./setup.sh --help             # Afficher l'aide
# =========================================================================

set -e

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="full"  # full, quick, config-only

# --- Parse arguments ---
for arg in "$@"; do
    case "$arg" in
        --quick)
            MODE="quick"
            ;;
        --config-only)
            MODE="config-only"
            ;;
        --help|-h)
            cat << EOF
LinkedIn Birthday Bot - Installation Simplifiée

USAGE:
  ./setup.sh [OPTIONS]

OPTIONS:
  (aucun)           Installation interactive complète
  --quick           Installation rapide (saute les vérifications détaillées)
  --config-only     Configure .env et auth_state.json uniquement (sans installation)
  --help, -h        Affiche cette aide

DESCRIPTION:
  Ce script orchestre l'installation complète du LinkedIn Birthday Bot
  de manière interactive et optimisée pour Raspberry Pi 4.

  Il guide l'utilisateur à travers:
  1. La détection de l'environnement
  2. L'installation des prérequis (Docker, Compose)
  3. La configuration de l'authentification LinkedIn
  4. Le déploiement des services
  5. La configuration de l'automatisation (sur Pi4)

EOF
            exit 0
            ;;
    esac
done

# --- Fonctions ---

print_banner() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║  ${BOLD}🚀 LinkedIn Birthday Bot - Installation Simplifiée${NC}${CYAN}      ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}║  ${BOLD}Version 2.0 - Installation Tout-en-Un${NC}${CYAN}                   ║${NC}"
    echo -e "${CYAN}║                                                              ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}═══ $1 ═══${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}${BOLD}➤ $1${NC}"
}

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }

ask_yes_no() {
    local question="$1"
    local default="${2:-n}"
    local response

    if [ "$default" = "y" ]; then
        read -p "$(echo -e ${YELLOW}❓ ${question} ${BOLD}[O/n]${NC} ) " response
        response=${response:-y}
    else
        read -p "$(echo -e ${YELLOW}❓ ${question} ${BOLD}[o/N]${NC} ) " response
        response=${response:-n}
    fi

    [[ "$response" =~ ^[OoYy]$ ]]
}

ask_input() {
    local question="$1"
    local default="$2"
    local response

    if [ -n "$default" ]; then
        read -p "$(echo -e ${CYAN}❓ ${question} ${BOLD}[${default}]${NC} ) " response
        echo "${response:-$default}"
    else
        read -p "$(echo -e ${CYAN}❓ ${question}: ${NC}) " response
        echo "$response"
    fi
}

# Fonction pour détecter la plateforme
detect_platform() {
    if [ -f "/proc/device-tree/model" ] && grep -q "Raspberry Pi" /proc/device-tree/model; then
        echo "raspberry-pi"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

# Fonction pour vérifier les permissions Docker
has_docker_access() {
    docker ps > /dev/null 2>&1
    return $?
}

# Fonction pour vérifier si l'utilisateur est dans le groupe docker
is_in_docker_group() {
    id -nG "$USER" | grep -qw "docker"
    return $?
}

# =========================================================================
# MAIN - Orchestration de l'installation
# =========================================================================

cd "$SCRIPT_DIR"

print_banner

print_info "Bienvenue dans l'assistant d'installation du LinkedIn Birthday Bot !"
print_info "Ce script va vous guider pas à pas dans l'installation et la configuration."
echo ""

# =========================================================================
# ÉTAPE 0 : Détection de l'environnement
# =========================================================================

print_header "ÉTAPE 0 : Détection de l'environnement"

PLATFORM=$(detect_platform)
IS_RASPBERRY_PI=false

case "$PLATFORM" in
    raspberry-pi)
        print_success "Plateforme détectée : Raspberry Pi"
        IS_RASPBERRY_PI=true
        ;;
    linux)
        print_success "Plateforme détectée : Linux"
        ;;
    macos)
        print_success "Plateforme détectée : macOS"
        ;;
    *)
        print_warning "Plateforme non reconnue, installation générique Linux"
        ;;
esac

# Vérifier les ressources disponibles
if [ "$MODE" != "quick" ]; then
    TOTAL_RAM=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}' || echo "0")
    DISK_AVAIL=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')

    print_info "Mémoire RAM : ${TOTAL_RAM}MB"
    print_info "Espace disque disponible : ${DISK_AVAIL}GB"

    if [ "$TOTAL_RAM" -lt 3500 ] && [ "$IS_RASPBERRY_PI" = true ]; then
        print_warning "Mémoire RAM faible pour un Raspberry Pi 4"
        print_info "Le SWAP sera configuré automatiquement"
    fi

    if [ "$DISK_AVAIL" -lt 10 ]; then
        print_warning "Espace disque faible (recommandé: 10GB+)"
        if ! ask_yes_no "Continuer quand même ?"; then
            print_error "Installation annulée"
            exit 1
        fi
    fi
fi

# =========================================================================
# MODE : Configuration uniquement
# =========================================================================

if [ "$MODE" = "config-only" ]; then
    print_header "MODE : Configuration uniquement"

    print_step "Configuration de l'authentification LinkedIn"
    echo ""
    print_info "Pour configurer l'authentification LinkedIn, vous avez 2 options :"
    echo ""
    echo -e "${BOLD}Option 1 : Exporter les cookies depuis votre navigateur (RECOMMANDÉ)${NC}"
    echo "  1. Installez l'extension 'Cookie-Editor' ou 'EditThisCookie'"
    echo "  2. Connectez-vous à LinkedIn"
    echo "  3. Exportez les cookies au format JSON"
    echo "  4. Sauvegardez le fichier exporté en tant que 'auth_state.json' dans ce dossier"
    echo ""
    echo -e "${BOLD}Option 2 : Variable d'environnement (pour les utilisateurs avancés)${NC}"
    echo "  Encodez votre fichier JSON en base64 et ajoutez-le dans le fichier .env"
    echo ""

    if ask_yes_no "Avez-vous déjà un fichier auth_state.json à importer ?" "n"; then
        AUTH_FILE_PATH=$(ask_input "Chemin vers votre fichier auth_state.json" "./auth_state.json")
        if [ -f "$AUTH_FILE_PATH" ]; then
            cp "$AUTH_FILE_PATH" "$SCRIPT_DIR/auth_state.json"
            print_success "Fichier auth_state.json copié"
        else
            print_error "Fichier non trouvé : $AUTH_FILE_PATH"
            print_info "Veuillez le copier manuellement dans : $SCRIPT_DIR/auth_state.json"
        fi
    else
        print_info "Créez le fichier auth_state.json et placez-le dans : $SCRIPT_DIR/auth_state.json"
        print_info "Exemple de structure :"
        cat << 'EOF'
{
  "cookies": [
    {
      "name": "li_at",
      "value": "VOTRE_TOKEN_ICI",
      "domain": ".linkedin.com",
      "path": "/",
      "expires": 1234567890,
      "httpOnly": true,
      "secure": true,
      "sameSite": "None"
    }
  ],
  "origins": []
}
EOF
    fi

    echo ""
    print_step "Configuration du fichier .env"
    echo ""

    if [ ! -f ".env" ]; then
        if [ -f ".env.pi4.example" ]; then
            cp ".env.pi4.example" ".env"
            print_success "Fichier .env créé depuis le template"
        else
            print_error "Template .env.pi4.example introuvable"
            exit 1
        fi
    else
        print_info "Fichier .env existant détecté"
    fi

    # Demander les paramètres de base
    echo ""
    print_info "Configuration de base :"

    DRY_RUN=$(ask_input "Mode DRY RUN (test sans envoyer de messages)" "true")
    BOT_MODE=$(ask_input "Mode du bot (standard/unlimited)" "standard")
    HEADLESS=$(ask_input "Mode headless (navigateur invisible)" "true")
    WEEKLY_LIMIT=$(ask_input "Limite hebdomadaire de messages" "80")

    # Mettre à jour le .env
    sed -i "s/^LINKEDIN_BOT_DRY_RUN=.*/LINKEDIN_BOT_DRY_RUN=$DRY_RUN/" .env
    sed -i "s/^LINKEDIN_BOT_MODE=.*/LINKEDIN_BOT_MODE=$BOT_MODE/" .env
    sed -i "s/^LINKEDIN_BOT_BROWSER_HEADLESS=.*/LINKEDIN_BOT_BROWSER_HEADLESS=$HEADLESS/" .env

    # Ajouter WEEKLY_LIMIT si elle n'existe pas
    if ! grep -q "LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT" .env; then
        echo "LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT=$WEEKLY_LIMIT" >> .env
    else
        sed -i "s/^LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT=.*/LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT=$WEEKLY_LIMIT/" .env
    fi

    print_success "Configuration .env mise à jour !"
    echo ""
    print_info "Fichier .env configuré : $SCRIPT_DIR/.env"
    print_info "Vous pouvez l'éditer manuellement pour des options avancées : nano .env"
    echo ""
    print_success "Configuration terminée !"
    print_info "Pour déployer, exécutez : ./setup.sh"
    exit 0
fi

# =========================================================================
# ÉTAPE 1 : Vérification et installation des prérequis
# =========================================================================

print_header "ÉTAPE 1 : Vérification des prérequis"

# Docker
print_step "Vérification de Docker..."
NEED_SG_DOCKER=false

if ! command -v docker &> /dev/null; then
    print_warning "Docker n'est pas installé"

    if ask_yes_no "Voulez-vous installer Docker automatiquement ?" "y"; then
        print_info "Installation de Docker..."

        if [ "$EUID" -ne 0 ]; then
            print_info "L'installation de Docker nécessite les droits sudo"
            sudo curl -fsSL https://get.docker.com | sudo sh
            sudo usermod -aG docker $USER
        else
            curl -fsSL https://get.docker.com | sh
            usermod -aG docker $USER
        fi

        print_success "Docker installé"
        print_warning "⚠️  Vous devrez vous déconnecter et reconnecter pour utiliser Docker sans sudo"
        NEED_SG_DOCKER=true
    else
        print_error "Docker est requis pour continuer"
        print_info "Installez Docker et relancez ce script"
        exit 1
    fi
else
    print_success "Docker est installé"

    # Vérification des permissions
    if ! has_docker_access; then
        print_warning "L'utilisateur actuel n'a pas les droits pour exécuter des commandes Docker"

        if is_in_docker_group; then
            print_info "✅ L'utilisateur est DÉJÀ dans le groupe 'docker' mais la session actuelle ne le reflète pas."
            print_info "Le script tentera d'utiliser 'sg docker' pour le déploiement."
            NEED_SG_DOCKER=true
        else
            if ask_yes_no "Voulez-vous ajouter l'utilisateur $USER au groupe docker ?" "y"; then
                sudo usermod -aG docker $USER
                print_success "Utilisateur ajouté au groupe docker"
                print_info "Le script tentera d'utiliser 'sg docker' pour le déploiement sans redémarrage."
                NEED_SG_DOCKER=true
            else
                print_error "Les permissions Docker sont requises."
                print_info "Exécutez manuellement: sudo usermod -aG docker $USER (puis redémarrez)"
                exit 1
            fi
        fi
    else
        print_success "Permissions Docker OK"
    fi
fi

# Docker Compose V2
print_step "Vérification de Docker Compose V2..."
if ! docker compose version &> /dev/null; then
    print_warning "Docker Compose V2 n'est pas installé"

    if ask_yes_no "Voulez-vous installer Docker Compose V2 automatiquement ?" "y"; then
        print_info "Installation de Docker Compose V2..."

        if [ "$EUID" -ne 0 ]; then
            sudo apt-get update
            sudo apt-get install -y docker-compose-plugin
        else
            apt-get update
            apt-get install -y docker-compose-plugin
        fi

        print_success "Docker Compose V2 installé"
    else
        print_error "Docker Compose V2 est requis pour continuer"
        exit 1
    fi
else
    print_success "Docker Compose V2 est installé"
fi

# =========================================================================
# ÉTAPE 2 : Configuration
# =========================================================================

print_header "ÉTAPE 2 : Configuration"

# Vérifier si auth_state.json existe
if [ -f "$SCRIPT_DIR/auth_state.json" ]; then
    print_success "✅ Fichier auth_state.json détecté localement."
    # Pas besoin de copier si on est déjà dans le bon répertoire, mais au cas où :
    if [ ! -f "auth_state.json" ]; then
        cp "$SCRIPT_DIR/auth_state.json" "auth_state.json"
    fi
else
    print_warning "Fichier auth_state.json non trouvé"
    echo ""
    print_info "Pour configurer l'authentification LinkedIn :"
    echo "  1. Installez l'extension 'Cookie-Editor' dans votre navigateur"
    echo "  2. Connectez-vous à LinkedIn"
    echo "  3. Exportez les cookies au format JSON"
    echo "  4. Sauvegardez le fichier exporté en tant que 'auth_state.json' dans ce dossier"
    echo ""

    if ask_yes_no "Souhaitez-vous configurer l'authentification maintenant ?" "n"; then
        echo ""
        echo -e "${BOLD}Choisissez une option :${NC}"
        echo "  1. J'ai déjà un fichier auth_state.json ailleurs (je vais le copier)"
        echo "  2. Je vais exporter mes cookies maintenant (pause de l'installation)"
        echo "  3. Continuer sans authentification (je le ferai plus tard)"
        echo ""

        read -p "Votre choix [1-3]: " auth_choice

        case "$auth_choice" in
            1)
                AUTH_FILE_PATH=$(ask_input "Chemin vers votre fichier auth_state.json" "~/Downloads/auth_state.json")
                AUTH_FILE_PATH="${AUTH_FILE_PATH/#\~/$HOME}"  # Expand ~

                if [ -f "$AUTH_FILE_PATH" ]; then
                    cp "$AUTH_FILE_PATH" "$SCRIPT_DIR/auth_state.json"
                    print_success "Fichier auth_state.json copié"
                else
                    print_error "Fichier non trouvé : $AUTH_FILE_PATH"
                    echo "{}" > auth_state.json
                    print_warning "Fichier vide créé - vous devrez le configurer plus tard"
                fi
                ;;
            2)
                echo ""
                print_info "📋 Instructions détaillées :"
                echo "  1. Ouvrez votre navigateur"
                echo "  2. Installez l'extension 'Cookie-Editor' ou 'EditThisCookie'"
                echo "  3. Allez sur https://www.linkedin.com et connectez-vous"
                echo "  4. Cliquez sur l'icône de l'extension"
                echo "  5. Cliquez sur 'Export' et choisissez 'JSON'"
                echo "  6. Copiez le contenu et créez le fichier auth_state.json"
                echo ""
                print_warning "L'installation est en pause. Appuyez sur ENTRÉE une fois le fichier créé..."
                read

                if [ -f "auth_state.json" ]; then
                    print_success "Fichier auth_state.json détecté !"
                else
                    print_warning "Fichier non détecté, création d'un fichier vide"
                    echo "{}" > auth_state.json
                fi
                ;;
            3)
                print_warning "Création d'un fichier auth_state.json vide"
                echo "{}" > auth_state.json
                print_info "Vous devrez le configurer avant d'utiliser le bot"
                ;;
            *)
                print_error "Choix invalide"
                echo "{}" > auth_state.json
                ;;
        esac
    else
        echo "{}" > auth_state.json
        print_warning "Fichier auth_state.json vide créé - à configurer plus tard"
    fi
fi

# Configuration du .env
echo ""
print_step "Configuration du fichier .env"

if [ ! -f ".env" ]; then
    if [ -f ".env.pi4.example" ]; then
        print_info "Création du fichier .env depuis le template..."
        cp ".env.pi4.example" ".env"

        # Générer des clés sécurisées
        SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)

        # Mettre à jour le .env pour SECRET_KEY
        if grep -q "SECRET_KEY=" .env; then
            sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
        else
            echo "SECRET_KEY=$SECRET_KEY" >> .env
        fi

        # 1. Générer une clé unique et sécurisée pour l'API
        GENERATED_KEY=$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)

        # 2. Définir ou Mettre à jour API_KEY
        if grep -q "^API_KEY=" .env; then
            sed -i "s|^API_KEY=.*|API_KEY=$GENERATED_KEY|" .env
        else
            echo "API_KEY=$GENERATED_KEY" >> .env
        fi

        # 3. Définir ou Mettre à jour BOT_API_KEY (DOIT être identique à API_KEY)
        if grep -q "^BOT_API_KEY=" .env; then
            sed -i "s|^BOT_API_KEY=.*|BOT_API_KEY=$GENERATED_KEY|" .env
        else
            echo "BOT_API_KEY=$GENERATED_KEY" >> .env
        fi

        print_success "Clés API synchronisées (API_KEY et BOT_API_KEY) dans .env"
    else
        print_error "Template .env.pi4.example introuvable"
        exit 1
    fi
else
    print_success "Fichier .env existant détecté"
fi

# Demander la configuration de base si mode interactif
if [ "$MODE" != "quick" ]; then
    echo ""
    if ask_yes_no "Voulez-vous configurer les paramètres de base maintenant ?" "y"; then
        echo ""
        print_info "${BOLD}Configuration de base :${NC}"

        DRY_RUN=$(ask_input "Mode DRY RUN (test sans envoyer)" "true")
        BOT_MODE=$(ask_input "Mode du bot (standard/unlimited)" "standard")
        HEADLESS=$(ask_input "Mode headless (navigateur invisible)" "true")
        WEEKLY_LIMIT=$(ask_input "Limite hebdomadaire de messages" "80")

        # Mettre à jour le .env
        sed -i "s/^LINKEDIN_BOT_DRY_RUN=.*/LINKEDIN_BOT_DRY_RUN=$DRY_RUN/" .env 2>/dev/null || echo "LINKEDIN_BOT_DRY_RUN=$DRY_RUN" >> .env
        sed -i "s/^LINKEDIN_BOT_MODE=.*/LINKEDIN_BOT_MODE=$BOT_MODE/" .env 2>/dev/null || echo "LINKEDIN_BOT_MODE=$BOT_MODE" >> .env
        sed -i "s/^LINKEDIN_BOT_BROWSER_HEADLESS=.*/LINKEDIN_BOT_BROWSER_HEADLESS=$HEADLESS/" .env 2>/dev/null || echo "LINKEDIN_BOT_BROWSER_HEADLESS=$HEADLESS" >> .env

        if ! grep -q "LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT" .env; then
            echo "LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT=$WEEKLY_LIMIT" >> .env
        else
            sed -i "s/^LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT=.*/LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT=$WEEKLY_LIMIT/" .env
        fi

        print_success "Configuration .env mise à jour"
    fi
fi

# =========================================================================
# ÉTAPE 3 : Déploiement
# =========================================================================

print_header "ÉTAPE 3 : Déploiement"

print_info "Le déploiement va maintenant commencer."
print_info "Cette étape peut prendre 15-20 minutes (compilation Next.js)."
echo ""

if ask_yes_no "Voulez-vous continuer avec le déploiement ?" "y"; then
    # Utiliser le script de déploiement RAPIDE (Pull) au lieu du rebuild
    DEPLOY_SCRIPT="./scripts/deploy_pi4_pull.sh"

    if [ -f "$DEPLOY_SCRIPT" ]; then
        chmod +x "$DEPLOY_SCRIPT"
        print_info "Lancement du déploiement optimisé via $(basename "$DEPLOY_SCRIPT")..."
        print_info "Cela permet d'utiliser les images pré-compilées (gain de ~20 minutes)."
        echo ""

        if [ "$NEED_SG_DOCKER" = true ]; then
            print_info "⚠️  Exécution du déploiement avec le groupe 'docker' actif (via sg)..."
            if command -v sg >/dev/null 2>&1; then
                sg docker -c "$DEPLOY_SCRIPT"
                DEPLOY_EXIT_CODE=$?
            else
                print_warning "Commande 'sg' introuvable. Tentative d'exécution standard..."
                "$DEPLOY_SCRIPT"
                DEPLOY_EXIT_CODE=$?
            fi
        else
            "$DEPLOY_SCRIPT"
            DEPLOY_EXIT_CODE=$?
        fi

        if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
            print_success "Déploiement réussi !"
        else
            print_error "Le déploiement a rencontré des problèmes"
            echo ""
            print_warning "Problèmes courants et solutions :"
            echo ""
            echo "  ${BOLD}1. Timeout réseau (TLS handshake timeout)${NC}"
            echo "     → Connexion internet lente ou instable"
            echo "     → Le script a déjà réessayé 5 fois avec backoff exponentiel"
            echo "     → ${CYAN}Solution${NC}: Vérifiez votre connexion et relancez : $DEPLOY_SCRIPT"
            echo ""
            echo "  ${BOLD}2. Erreur 403/401 (GitHub Container Registry)${NC}"
            echo "     → Images privées nécessitant authentification"
            echo "     → ${CYAN}Solution${NC}: docker login ghcr.io -u VOTRE_USERNAME"
            echo ""
            echo "  ${BOLD}3. Espace disque insuffisant${NC}"
            echo "     → Images Docker volumineuses (500MB-1GB chacune)"
            echo "     → ${CYAN}Solution${NC}: Libérez de l'espace : docker system prune -a"
            echo ""
            print_info "💡 Pour réessayer uniquement le déploiement, lancez :"
            echo "   ${CYAN}$DEPLOY_SCRIPT${NC}"
            echo ""

            if ask_yes_no "Voulez-vous réessayer le déploiement maintenant ?" "n"; then
                echo ""
                print_info "Nouvelle tentative de déploiement..."

                if [ "$NEED_SG_DOCKER" = true ]; then
                    sg docker -c "$DEPLOY_SCRIPT"
                    DEPLOY_EXIT_CODE=$?
                else
                    "$DEPLOY_SCRIPT"
                    DEPLOY_EXIT_CODE=$?
                fi

                if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
                    print_success "Déploiement réussi à la seconde tentative !"
                else
                    print_error "Le déploiement a échoué à nouveau"
                    exit 1
                fi
            else
                exit 1
            fi
        fi
    else
        print_error "Script $DEPLOY_SCRIPT introuvable"
        exit 1
    fi
else
    print_warning "Déploiement ignoré"
    print_info "Vous pouvez le lancer plus tard avec : ./scripts/deploy_pi4_pull.sh"
    exit 0
fi

# =========================================================================
# ÉTAPE 4 : Configuration de l'automatisation (Raspberry Pi uniquement)
# =========================================================================

if [ "$IS_RASPBERRY_PI" = true ]; then
    print_header "ÉTAPE 4 : Configuration de l'automatisation (Raspberry Pi)"

    echo ""
    print_info "Sur Raspberry Pi, vous pouvez configurer :"
    echo "  • Démarrage automatique au boot"
    echo "  • Monitoring horaire des ressources"
    echo "  • Backups quotidiens de la base de données"
    echo "  • Nettoyage hebdomadaire automatique"
    echo ""

    if ask_yes_no "Voulez-vous installer l'automatisation (services systemd) ?" "y"; then
        if [ -f "scripts/install_automation_pi4.sh" ]; then
            chmod +x scripts/install_automation_pi4.sh
            print_info "Lancement de l'installation de l'automatisation..."
            print_warning "Cette étape nécessite les droits sudo"
            echo ""

            sudo ./scripts/install_automation_pi4.sh

            print_success "Automatisation configurée !"
            print_info "Le bot démarrera automatiquement au prochain redémarrage"
        else
            print_error "Script scripts/install_automation_pi4.sh introuvable"
        fi
    else
        print_warning "Automatisation ignorée"
        print_info "Vous pouvez l'installer plus tard avec : sudo ./scripts/install_automation_pi4.sh"
    fi
else
    print_header "ÉTAPE 4 : Automatisation"
    print_info "L'automatisation via systemd est uniquement disponible sur Raspberry Pi"
    print_info "Sur votre plateforme, configurez un cron job manuellement si besoin"
fi

# =========================================================================
# RÉSUMÉ FINAL
# =========================================================================

print_header "🎉 INSTALLATION TERMINÉE !"

LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}║  ${BOLD}${GREEN}✅ INSTALLATION RÉUSSIE !${NC}${CYAN}                                  ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BOLD}📍 Accès :${NC}"
echo -e "  • Dashboard : ${GREEN}http://${LOCAL_IP}:3000${NC}"
echo -e "  • API : ${GREEN}http://${LOCAL_IP}:8000${NC}"
echo ""

echo -e "${BOLD}📁 Fichiers de configuration :${NC}"
echo -e "  • Configuration : ${CYAN}.env${NC}"
echo -e "  • Authentification : ${CYAN}auth_state.json${NC}"
echo -e "  • Config avancée : ${CYAN}config/config.yaml${NC}"
echo ""

echo -e "${BOLD}🔧 Commandes utiles :${NC}"
echo -e "  • Voir les logs :        ${CYAN}docker compose -f docker-compose.pi4-standalone.yml logs -f${NC}"
echo -e "  • Redémarrer :           ${CYAN}docker compose -f docker-compose.pi4-standalone.yml restart${NC}"
echo -e "  • Arrêter :              ${CYAN}docker compose -f docker-compose.pi4-standalone.yml down${NC}"
echo -e "  • Vérifier l'état :      ${CYAN}./scripts/verify_rpi_docker.sh${NC}"

if [ "$IS_RASPBERRY_PI" = true ]; then
    echo -e "  • Statut du service :    ${CYAN}sudo systemctl status linkedin-bot${NC}"
    echo -e "  • Logs du service :      ${CYAN}sudo journalctl -u linkedin-bot -f${NC}"
fi

echo ""

echo -e "${BOLD}📚 Documentation :${NC}"
echo -e "  • Guide complet : ${CYAN}README.md${NC}"
echo -e "  • Troubleshooting : ${CYAN}docs/RASPBERRY_PI_TROUBLESHOOTING.md${NC}"
echo ""

if [ "$IS_RASPBERRY_PI" = true ]; then
    echo -e "${YELLOW}ℹ️  Note :${NC} Pour activer les permissions Docker sans sudo, redémarrez votre Pi :"
    echo -e "  ${CYAN}sudo reboot${NC}"
    echo ""
fi

print_success "L'installation est terminée ! Bon usage du bot 🎂"
echo ""
