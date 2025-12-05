#!/bin/bash

# =========================================================================
# Script d'installation de la configuration sudoers pour le contrôle API
# Ce script permet à l'API de contrôler les services systemd sans mot de passe
# =========================================================================

set -e

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Fonctions ---
print_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }

# Vérification des droits root
if [ "$EUID" -ne 0 ]; then
    print_error "Ce script doit être exécuté avec sudo"
    print_info "Usage: sudo ./scripts/install_sudoers.sh"
    exit 1
fi

print_header "🔐 Installation Configuration Sudoers"

SUDOERS_SOURCE="deployment/sudoers/linkedin-bot-api"
SUDOERS_TARGET="/etc/sudoers.d/linkedin-bot-api"

# Vérifier que le fichier source existe
if [ ! -f "$SUDOERS_SOURCE" ]; then
    print_error "Fichier source introuvable: $SUDOERS_SOURCE"
    exit 1
fi

# Vérifier la syntaxe du fichier sudoers
print_info "Vérification de la syntaxe du fichier sudoers..."
if ! visudo -c -f "$SUDOERS_SOURCE" &>/dev/null; then
    print_error "La syntaxe du fichier sudoers est invalide"
    exit 1
fi
print_success "Syntaxe valide"

# Copier le fichier
print_info "Installation du fichier sudoers..."
cp "$SUDOERS_SOURCE" "$SUDOERS_TARGET"
chmod 0440 "$SUDOERS_TARGET"
print_success "Fichier installé: $SUDOERS_TARGET"

# Vérifier l'installation
print_info "Vérification de l'installation..."
if visudo -c; then
    print_success "Configuration sudoers installée avec succès"
else
    print_error "Erreur de configuration sudoers"
    rm -f "$SUDOERS_TARGET"
    exit 1
fi

print_header "✅ Installation Terminée"
print_info "Les utilisateurs du groupe 'docker' peuvent maintenant contrôler les services systemd"
print_info "Les commandes suivantes sont disponibles sans mot de passe:"
echo "  - systemctl start/stop/restart/enable/disable [service]"
echo "  - systemctl is-active/is-enabled/status [service]"
echo ""
print_warning "Note: Cette configuration ne prend effet qu'après reconnexion"
