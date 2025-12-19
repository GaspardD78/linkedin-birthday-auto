#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - DOCKER LIBRARY (v4.0)
# Docker operations and health checks
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === DOCKER CHECKS ===

docker_check_all_prerequisites() {
    log_info "Vérification des prérequis Docker..."

    # Vérifier que docker est installé
    if ! cmd_exists docker; then
        log_error "Docker n'est pas installé"
        return 1
    fi
    log_success "✓ Docker installé"

    # Vérifier que le daemon Docker est actif
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker daemon n'est pas actif"
        return 1
    fi
    log_success "✓ Docker daemon actif"

    # Vérifier que docker-compose est installé
    if ! cmd_exists docker; then
        log_error "docker-compose n'est pas disponible"
        return 1
    fi
    log_success "✓ docker-compose disponible"

    return 0
}

docker_compose_validate() {
    local compose_file="$1"

    log_info "Validation du fichier docker-compose..."

    if [[ ! -f "$compose_file" ]]; then
        log_error "Fichier docker-compose introuvable: $compose_file"
        return 1
    fi

    if ! docker compose -f "$compose_file" config > /dev/null 2>&1; then
        log_error "Fichier docker-compose invalide (YAML malformé)"
        return 1
    fi

    log_success "✓ Docker-compose valide"
    return 0
}

docker_pull_with_retry() {
    local compose_file="$1"
    local max_retries=4
    local base_delay=2
    local services
    local error_log="/tmp/setup_docker_services.err"

    log_info "Vérification du fichier docker-compose..."

    if [[ ! -f "$compose_file" ]]; then
        log_error "Fichier docker-compose introuvable: $(cd . && pwd)/$compose_file"
        return 1
    fi
    log_info "✓ Fichier trouvé: $compose_file"

    log_info "Validation YAML du fichier docker-compose..."
    if ! docker compose -f "$compose_file" config > /dev/null 2>"$error_log"; then
        log_error "Le fichier $compose_file est invalide (YAML malformé)"
        log_error "Détails de l'erreur :"
        cat "$error_log" | sed 's/^/  /'
        rm -f "$error_log"
        return 1
    fi
    log_info "✓ YAML valide"

    log_info "Lecture de la liste des services..."
    services=$(docker compose -f "$compose_file" config --services 2>"$error_log")
    local docker_exit_code=$?

    if [[ $docker_exit_code -ne 0 ]] || [[ -z "$services" ]]; then
        log_error "Impossible de lire la liste des services depuis $compose_file"
        if [[ -s "$error_log" ]]; then
            log_error "Message d'erreur Docker :"
            cat "$error_log" | sed 's/^/  /'
        fi
        rm -f "$error_log"
        return 1
    fi
    rm -f "$error_log"

    log_info "Téléchargement des images Docker..."

    local total_services
    total_services=$(echo "$services" | wc -l)
    local current=0

    while IFS= read -r service; do
        [[ -z "$service" ]] && continue

        current=$((current + 1))
        echo -n "[${current}/${total_services}] Pull de l'image pour '${service}' "
        local retry_count=0
        local success=false

        while [[ $retry_count -lt $max_retries ]]; do
            if docker compose -f "$compose_file" pull --quiet "$service" 2>"$error_log"; then
                echo -e "${GREEN}✓${NC}"
                success=true
                rm -f "$error_log"
                break
            else
                retry_count=$((retry_count + 1))
                if [[ $retry_count -lt $max_retries ]]; then
                    local delay=$((base_delay ** retry_count))
                    echo -n "${YELLOW}✗${NC} (retry dans ${delay}s) "
                    sleep "$delay"
                else
                    echo -e "${RED}✗ ÉCHEC${NC}"
                fi
            fi
        done

        if [[ "$success" != "true" ]]; then
            log_error "Échec du pull pour le service '$service'."
            if [[ -s "$error_log" ]]; then
                log_error "Détails :"
                cat "$error_log" | sed 's/^/  /'
            fi
            rm -f "$error_log"
            return 1
        fi
    done <<< "$services"

    log_success "Toutes les images ont été téléchargées avec succès."
    return 0
}

docker_compose_up() {
    local compose_file="$1"
    local detached="${2:-true}"

    log_info "Démarrage des conteneurs Docker..."

    if [[ "$detached" == "true" ]]; then
        docker compose -f "$compose_file" up -d
    else
        docker compose -f "$compose_file" up
    fi

    log_success "✓ Conteneurs démarrés"
    return 0
}

docker_cleanup() {
    log_info "Nettoyage des ressources Docker..."

    # Supprimer les conteneurs arrêtés
    docker container prune -f 2>/dev/null || true

    # Supprimer les images sans tag
    docker image prune -f 2>/dev/null || true

    # Supprimer les volumes non utilisés
    docker volume prune -f 2>/dev/null || true

    log_success "✓ Nettoyage Docker terminé"
    return 0
}

wait_for_service() {
    local service_name="$1"
    local health_url="$2"
    local max_retries=30
    local retry_interval=2

    log_info "Attente du démarrage de $service_name..."

    for ((i = 1; i <= max_retries; i++)); do
        if curl -sf "$health_url" > /dev/null 2>&1; then
            log_success "✓ $service_name est opérationnel"
            return 0
        fi

        if [[ $i -lt $max_retries ]]; then
            echo -n "."
            sleep "$retry_interval"
        fi
    done

    log_error "$service_name n'a pas démarré dans le délai imparti"
    return 1
}
