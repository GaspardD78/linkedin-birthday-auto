#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - CHECKS LIBRARY (v4.0)
# System prerequisite checks and installation hooks
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === CONSTANTS ===

readonly MIN_MEMORY_GB=3
readonly DISK_THRESHOLD_PERCENT=20
readonly HEALTH_TIMEOUT=300
readonly HEALTH_INTERVAL=10

# === MAIN CHECK FUNCTION ===

ensure_prerequisites() {
    local compose_file="$1"
    local check_only_mode="${CHECK_ONLY:-false}"

    log_step "VÉRIFICATIONS & INSTALLATIONS"

    # Vérifier les prérequis système
    if ! ensure_system_requirements "$check_only_mode"; then
        return 1
    fi

    # Vérifier l'environnement Docker
    if ! ensure_docker_environment "$check_only_mode"; then
        return 1
    fi

    # Vérifier les fichiers de configuration
    if ! check_config_files; then
        return 1
    fi

    # Vérifier l'espace disque
    if ! check_disk_space; then
        return 1
    fi

    log_success "✓ Tous les prérequis sont satisfaits"
    return 0
}

# === SYSTEM REQUIREMENTS ===

ensure_system_requirements() {
    local check_only="$1"
    log_info "Vérification des prérequis système..."

    # Vérifier la mémoire
    local total_memory
    total_memory=$(get_total_memory_gb)
    if [[ $total_memory -lt $MIN_MEMORY_GB ]]; then
        log_error "Mémoire insuffisante: ${total_memory}GB (minimum: ${MIN_MEMORY_GB}GB)"
        # La mémoire physique ne peut pas être "installée", donc échec
        return 1
    fi
    log_success "✓ Mémoire: ${total_memory}GB (OK)"

    # Vérifier dépendances manquantes
    local missing_deps=false
    for cmd in curl openssl git jq python3; do
        if ! cmd_exists "$cmd"; then
            missing_deps=true
            break
        fi
    done

    if [[ "$missing_deps" == "true" ]]; then
        if [[ "$check_only" == "true" ]]; then
             log_error "Dépendances système manquantes (curl, openssl, git, jq, python3)."
             return 1
        fi

        # Installer les dépendances
        install_system_packages
        install_python_packages
    else
        log_success "✓ Outils système installés (curl, openssl, git, jq, python3)"

        # Vérifier paquets python même si python3 existe
        if [[ "$check_only" != "true" ]]; then
            install_python_packages
        fi
    fi

    return 0
}

# === DOCKER ENVIRONMENT ===

ensure_docker_environment() {
    local check_only="$1"
    log_info "Vérification de l'environnement Docker..."

    if ! cmd_exists docker; then
        if [[ "$check_only" == "true" ]]; then
            log_error "Docker n'est pas installé"
            return 1
        fi
        install_docker
    fi
    log_success "✓ Docker installé"

    # Vérifier si l'utilisateur est dans le groupe docker
    if ! groups "$USER" | grep -q "docker"; then
        if [[ "$check_only" == "true" ]]; then
             log_warn "L'utilisateur $USER n'est pas dans le groupe docker."
        else
             configure_docker_permissions
        fi
    fi

    if ! docker info > /dev/null 2>&1; then
        # Essayer avec sudo si nécessaire (si le groupe vient d'être ajouté)
        if sudo docker info > /dev/null 2>&1; then
             log_warn "Docker accessible via sudo uniquement (re-login nécessaire)."
        else
             log_error "Docker daemon n'est pas actif."
             if [[ "$check_only" != "true" ]]; then
                  log_info "Tentative de démarrage de Docker..."
                  check_sudo
                  sudo systemctl start docker && sudo systemctl enable docker
                  sleep 3
             else
                  return 1
             fi
        fi
    fi
    log_success "✓ Docker daemon actif"

    if ! docker compose version > /dev/null 2>&1; then
        log_error "docker compose n'est pas disponible"
        if [[ "$check_only" != "true" ]]; then
             log_info "Tentative d'installation du plugin Docker Compose..."
             check_sudo
             sudo apt-get install -y docker-compose-plugin -qq || true
             if ! docker compose version > /dev/null 2>&1; then
                 log_error "Impossible d'installer Docker Compose."
                 return 1
             fi
             log_success "✓ Docker Compose installé"
        else
             return 1
        fi
    fi
    log_success "✓ docker compose disponible"

    return 0
}

# === CONFIG FILES ===

check_config_files() {
    log_info "Vérification des fichiers de configuration..."

    # Le fichier .env peut être créé pendant le setup, donc on ne le vérifie pas ici
    # mais on vérifie le template
    if [[ ! -f ".env.pi4.example" ]]; then
        log_error "Template .env (.env.pi4.example) non trouvé"
        return 1
    fi
    log_success "✓ Template .env trouvé"

    # Vérifier docker-compose
    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "Fichier docker-compose introuvable"
        return 1
    fi
    log_success "✓ Fichier docker-compose trouvé"

    return 0
}

# === DISK SPACE ===

check_disk_space() {
    log_info "Vérification de l'espace disque..."

    local usage
    usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')

    if [[ $usage -gt $((100 - DISK_THRESHOLD_PERCENT)) ]]; then
        log_warn "Espace disque faible: ${usage}% utilisé"
        # Ne pas échouer, juste avertir
    else
        log_success "✓ Espace disque OK: ${usage}% utilisé"
    fi

    return 0
}
