#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - INSTALLERS LIBRARY (v4.0)
# Installation functions for system dependencies
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === SYSTEM PACKAGES ===

install_system_packages() {
    log_info "Installation des dépendances système..."

    check_sudo

    log_info "Mise à jour des dépôts apt..."
    sudo apt-get update -qq

    local packages=("curl" "openssl" "git" "jq" "python3" "python3-pip" "python3-venv")
    local to_install=()

    for pkg in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $pkg "; then
            to_install+=("$pkg")
        fi
    done

    if [[ ${#to_install[@]} -gt 0 ]]; then
        log_info "Installation de: ${to_install[*]}"
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${to_install[@]}"
        log_success "✓ Dépendances système installées"
    else
        log_success "✓ Dépendances système déjà à jour"
    fi
}

# === DOCKER INSTALLATION ===

install_docker() {
    log_info "Installation de Docker..."

    if cmd_exists docker; then
        log_success "Docker est déjà installé"
        return 0
    fi

    check_sudo

    # Installation via le script officiel
    log_info "Téléchargement du script d'installation Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh

    log_info "Exécution du script d'installation..."
    sudo sh get-docker.sh

    rm get-docker.sh

    log_success "✓ Docker installé"

    # Configurer les permissions immédiatement après installation
    configure_docker_permissions
}

configure_docker_permissions() {
    log_info "Configuration des permissions Docker..."

    if groups "$USER" | grep -q "docker"; then
        log_success "✓ Utilisateur $USER déjà dans le groupe docker"
        return 0
    fi

    check_sudo
    sudo usermod -aG docker "$USER"
    log_success "✓ Utilisateur $USER ajouté au groupe docker"
    log_warn "⚠️  Vous devrez vous déconnecter/reconnecter pour que les changements prennent effet."
    log_warn "⚠️  Le script continuera, mais pourrait nécessiter sudo pour les commandes Docker."
}

# === PYTHON PACKAGES ===

install_python_packages() {
    log_info "Installation des paquets Python..."

    if ! cmd_exists pip3; then
        install_system_packages
    fi

    # Mettre à jour pip
    python3 -m pip install --upgrade pip --quiet 2>/dev/null || true

    # Installer bcrypt si manquant
    if ! python3 -c "import bcrypt" 2>/dev/null; then
        log_info "Installation de bcrypt..."
        if python3 -m pip install --user bcrypt --quiet 2>/dev/null; then
             log_success "✓ bcrypt installé"
        elif python3 -m pip install bcrypt --break-system-packages --quiet 2>/dev/null; then
             log_success "✓ bcrypt installé (--break-system-packages)"
        else
             log_warn "Échec installation bcrypt via pip. Tentative via apt..."
             check_sudo
             sudo apt-get install -y python3-bcrypt -qq
             log_success "✓ python3-bcrypt installé via apt"
        fi
    else
        log_success "✓ bcrypt déjà installé"
    fi
}

# === RCLONE INSTALLATION ===

install_rclone() {
    log_info "Installation de rclone pour sauvegardes Google Drive..."

    if cmd_exists rclone; then
        log_success "✓ rclone est déjà installé ($(rclone version | head -1))"
        return 0
    fi

    check_sudo

    # Installation via le dépôt officiel rclone
    log_info "Téléchargement de rclone..."
    curl -fsSL https://rclone.org/install.sh -o install-rclone.sh

    log_info "Exécution du script d'installation rclone..."
    sudo bash install-rclone.sh

    rm -f install-rclone.sh

    if cmd_exists rclone; then
        log_success "✓ rclone installé avec succès ($(rclone version | head -1))"
        return 0
    else
        log_error "Échec de l'installation de rclone"
        return 1
    fi
}
