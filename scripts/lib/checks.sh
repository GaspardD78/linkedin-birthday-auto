#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - CHECKS LIBRARY (v4.0)
# System prerequisite checks
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === CONSTANTS ===

readonly MIN_MEMORY_GB=3
readonly DISK_THRESHOLD_PERCENT=20
readonly HEALTH_TIMEOUT=300
readonly HEALTH_INTERVAL=10

# === MAIN CHECK FUNCTION ===

check_all_prerequisites() {
    local compose_file="$1"

    log_step "VÉRIFICATIONS PRÉ-DÉPLOIEMENT"

    # Vérifier les prérequis système
    if ! check_system_requirements; then
        return 1
    fi

    # Vérifier l'environnement Docker
    if ! check_docker_environment; then
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

    log_success "✓ Toutes les vérifications passées"
    return 0
}

# === SYSTEM REQUIREMENTS ===

check_system_requirements() {
    log_info "Vérification des prérequis système..."

    # Vérifier la mémoire
    local total_memory
    total_memory=$(get_total_memory_gb)
    if [[ $total_memory -lt $MIN_MEMORY_GB ]]; then
        log_error "Mémoire insuffisante: ${total_memory}GB (minimum: ${MIN_MEMORY_GB}GB)"
        return 1
    fi
    log_success "✓ Mémoire: ${total_memory}GB (OK)"

    # Vérifier curl
    if ! cmd_exists curl; then
        log_error "curl n'est pas installé"
        return 1
    fi
    log_success "✓ curl installé"

    # Vérifier openssl
    if ! cmd_exists openssl; then
        log_error "openssl n'est pas installé"
        return 1
    fi
    log_success "✓ openssl installé"

    return 0
}

# === DOCKER ENVIRONMENT ===

check_docker_environment() {
    log_info "Vérification de l'environnement Docker..."

    if ! cmd_exists docker; then
        log_error "Docker n'est pas installé"
        log_error "Installez Docker: curl -fsSL https://get.docker.com | sh"
        return 1
    fi
    log_success "✓ Docker installé"

    if ! docker info > /dev/null 2>&1; then
        log_error "Docker daemon n'est pas actif"
        log_error "Essayez: sudo systemctl start docker && sudo systemctl enable docker"
        return 1
    fi
    log_success "✓ Docker daemon actif"

    if ! docker compose version > /dev/null 2>&1; then
        log_error "docker compose n'est pas disponible"
        log_error "Docker Compose plugin est requis (installé avec Docker Engine v20.10+)"
        return 1
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
    if [[ ! -f "docker-compose.pi4-standalone.yml" ]]; then
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
