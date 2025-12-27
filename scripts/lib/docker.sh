#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - DOCKER LIBRARY (v5.0)
# Docker operations with optimized image pulling
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === DOCKER CHECKS ===

docker_check_all_prerequisites() {
    log_info "Vérification des prérequis Docker..."

    if ! cmd_exists docker; then
        log_error "Docker n'est pas installé"
        return 1
    fi
    log_success "✓ Docker installé"

    if ! docker info > /dev/null 2>&1; then
        log_error "Docker daemon n'est pas actif"
        log_error "Essayez: sudo systemctl start docker"
        return 1
    fi
    log_success "✓ Docker daemon actif"

    if ! docker compose version > /dev/null 2>&1; then
        log_error "docker compose n'est pas disponible"
        log_error "Docker Compose plugin est requis (installé avec Docker Engine moderne)"
        return 1
    fi

    local compose_version
    compose_version=$(docker compose version --short 2>/dev/null || echo "unknown")
    log_success "✓ docker compose disponible (v${compose_version})"

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

# ═══════════════════════════════════════════════════════════════════════════════
# OPTIMIZED IMAGE PULLING (v5.0)
# ═══════════════════════════════════════════════════════════════════════════════

# Get image name for a service from compose file
_docker_get_service_image() {
    local compose_file="$1"
    local service="$2"
    docker compose -f "$compose_file" config --format json 2>/dev/null | \
        grep -o "\"$service\":{[^}]*\"image\":\"[^\"]*\"" | \
        sed -n 's/.*"image":"\([^"]*\)".*/\1/p' || \
        docker compose -f "$compose_file" config 2>/dev/null | \
        awk "/^  $service:$/,/^  [a-z]/" | grep "image:" | awk '{print $2}' | head -1
}

# Classify images into third-party (can parallel) vs custom (sequential)
_docker_classify_images() {
    local compose_file="$1"
    local -n _third_party=$2
    local -n _custom=$3

    local services
    services=$(docker compose -f "$compose_file" config --services 2>/dev/null)

    while IFS= read -r svc; do
        [[ -z "$svc" ]] && continue
        local image
        image=$(_docker_get_service_image "$compose_file" "$svc")

        # Third-party: Docker Hub official images (no registry prefix or docker.io)
        # Custom: ghcr.io, private registries
        if [[ "$image" == ghcr.io/* ]] || [[ "$image" == *".azurecr.io/"* ]] || [[ "$image" == *".ecr."* ]]; then
            _custom+=("$svc")
        else
            _third_party+=("$svc")
        fi
    done <<< "$services"
}

# Pull a single service with retry logic (no UI)
_docker_pull_single() {
    local compose_file="$1"
    local service="$2"
    local max_retries="${3:-4}"
    local retry=0

    while [[ $retry -lt $max_retries ]]; do
        if docker compose -f "$compose_file" pull --quiet "$service" 2>/dev/null; then
            return 0
        fi
        ((retry++))
        [[ $retry -lt $max_retries ]] && sleep $((2 ** retry))
    done
    return 1
}

# Track which services failed to pull (global array for docker_pull_parallel)
FAILED_PULL_SERVICES=()

# Pull third-party images in parallel (background jobs)
_docker_pull_parallel() {
    local compose_file="$1"
    shift
    local services=("$@")
    local pids=()
    local failed=0
    FAILED_PULL_SERVICES=()  # Reset global array

    [[ ${#services[@]} -eq 0 ]] && return 0

    log_info "Téléchargement images tierces en parallèle (${#services[@]} images)..."

    for svc in "${services[@]}"; do
        _docker_pull_single "$compose_file" "$svc" 4 &
        pids+=($!)
    done

    # Wait for all and collect failures
    local idx=0
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            log_warn "  ⚠ ${services[$idx]} - échec (non bloquant)"
            FAILED_PULL_SERVICES+=("${services[$idx]}")
            ((failed++))
        fi
        ((idx++))
    done

    if [[ $failed -eq 0 ]]; then
        log_success "✓ Images tierces synchronisées"
    else
        log_warn "  ${failed}/${#services[@]} images en échec (services concernés ne seront pas démarrés)"

        # Raspberry Pi 4 specific: Warn about critical ARM64 compatibility
        if [[ "$(uname -m)" == "aarch64" ]] || [[ "$(uname -m)" == "armv7l" ]]; then
            log_warn "  ℹ️  Architecture ARM détectée (Raspberry Pi)"
            log_warn "     Si nginx/api échouent au démarrage, vérifiez:"
            log_warn "     - Connexion Internet stable pour Docker Hub"
            log_warn "     - docker pull nginx:alpine (test manuel)"
            log_warn "     - docker images | grep 'arm' (architecture)"
        fi
    fi

    return 0
}

# Pull custom images sequentially with progress UI
_docker_pull_sequential_ui() {
    local compose_file="$1"
    shift
    local services=("$@")
    local total=${#services[@]}
    local current=0
    local max_retries=4

    [[ $total -eq 0 ]] && return 0

    log_info "Téléchargement images personnalisées (${total} images)..."

    for svc in "${services[@]}"; do
        ((current++))
        local retry=0
        local success=false

        printf "   [%d/%d] %-25s " "$current" "$total" "${svc:0:25}"

        while [[ $retry -lt $max_retries ]]; do
            if docker compose -f "$compose_file" pull --quiet "$svc" 2>/dev/null; then
                echo -e "${GREEN}✓${NC}"
                success=true
                break
            fi
            ((retry++))
            if [[ $retry -lt $max_retries ]]; then
                echo -ne "${YELLOW}retry ${retry}...${NC} "
                sleep $((2 ** retry))
            fi
        done

        if [[ "$success" != "true" ]]; then
            echo -e "${RED}✗ échec${NC}"
            log_error "Impossible de télécharger $svc après $max_retries tentatives"
            return 1
        fi
    done

    return 0
}

# Classify services as critical or optional
_docker_classify_services_criticality() {
    local -n _critical=$1
    local -n _optional=$2

    # Critical services required for basic functionality
    _critical=("redis-bot" "redis-dashboard" "api" "bot-worker" "dashboard" "nginx")

    # Optional services (monitoring, logging, utilities)
    _optional=("docker-socket-proxy" "dozzle" "prometheus" "grafana" "otel-collector")
}

# Verify if image exists locally for a service
_docker_check_image_exists() {
    local compose_file="$1"
    local service="$2"

    local image
    image=$(_docker_get_service_image "$compose_file" "$service")

    if [[ -z "$image" ]]; then
        return 1
    fi

    # Check if image exists locally
    if docker image inspect "$image" >/dev/null 2>&1; then
        return 0
    fi

    return 1
}

# Main optimized pull function - replaces docker_pull_with_retry
docker_pull_images_optimized() {
    local compose_file="$1"

    # Validate compose file
    if [[ ! -f "$compose_file" ]]; then
        log_error "Fichier compose introuvable: $compose_file"
        return 1
    fi

    if ! docker compose -f "$compose_file" config > /dev/null 2>&1; then
        log_error "Fichier docker-compose invalide"
        return 1
    fi

    # Classify images
    local third_party=()
    local custom=()
    _docker_classify_images "$compose_file" third_party custom

    local total=$((${#third_party[@]} + ${#custom[@]}))
    log_info "Synchronisation de ${total} images Docker..."
    echo "   • ${#third_party[@]} images tierces (parallèle)"
    echo "   • ${#custom[@]} images personnalisées (séquentiel)"
    echo ""

    # Phase 1: Pull third-party in parallel (non-blocking failures)
    _docker_pull_parallel "$compose_file" "${third_party[@]}"

    # Phase 2: Pull custom images sequentially (blocking failures)
    if ! _docker_pull_sequential_ui "$compose_file" "${custom[@]}"; then
        return 1
    fi

    # Phase 3: Verify critical services have their images
    log_info "Vérification des services critiques..."
    local critical_services=()
    local optional_services=()
    _docker_classify_services_criticality critical_services optional_services

    local missing_critical=()
    for svc in "${critical_services[@]}"; do
        if ! _docker_check_image_exists "$compose_file" "$svc"; then
            missing_critical+=("$svc")
        fi
    done

    if [[ ${#missing_critical[@]} -gt 0 ]]; then
        log_error "Services critiques sans image disponible:"
        for svc in "${missing_critical[@]}"; do
            log_error "  ✗ $svc"
        done
        log_error "Impossible de continuer sans ces services critiques"
        return 1
    fi

    log_success "✓ Tous les services critiques ont leurs images (${#critical_services[@]}/${#critical_services[@]})"

    # Phase 4: Report optional services without images
    if [[ ${#FAILED_PULL_SERVICES[@]} -gt 0 ]]; then
        log_warn "Services optionnels qui ne seront pas démarrés (images manquantes):"
        for svc in "${FAILED_PULL_SERVICES[@]}"; do
            log_warn "  ⊗ $svc"
        done
    fi

    echo ""
    log_success "✓ Images synchronisées (tous les services critiques OK)"
    return 0
}

# Get list of services with available images (excluding failed pulls)
docker_get_startable_services() {
    local compose_file="$1"
    local all_services
    all_services=$(docker compose -f "$compose_file" config --services 2>/dev/null)

    local startable_services=()
    while IFS= read -r svc; do
        [[ -z "$svc" ]] && continue

        # Skip services that failed to pull
        local skip=false
        for failed_svc in "${FAILED_PULL_SERVICES[@]}"; do
            if [[ "$svc" == "$failed_svc" ]]; then
                skip=true
                break
            fi
        done

        if [[ "$skip" == "false" ]] && _docker_check_image_exists "$compose_file" "$svc"; then
            startable_services+=("$svc")
        fi
    done <<< "$all_services"

    echo "${startable_services[@]}"
}

# Legacy function - kept for compatibility, delegates to optimized version
docker_pull_with_retry() {
    local compose_file="$1"
    docker_pull_images_optimized "$compose_file"
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONTAINER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

docker_compose_up() {
    local compose_file="$1"
    local detached="${2:-true}"
    local monitoring="${3:-false}"
    local cmd="docker compose -f $compose_file"
    local error_log="/tmp/setup_docker_up.err"

    if [[ "$monitoring" == "true" ]]; then
        log_info "Démarrage avec monitoring activé..."
        cmd="$cmd --profile monitoring"
    fi

    local services
    if [[ "$monitoring" == "true" ]]; then
        services=$(docker compose -f "$compose_file" --profile monitoring config --services 2>/dev/null)
    else
        services=$(docker compose -f "$compose_file" config --services 2>/dev/null)
    fi

    local total_services
    total_services=$(echo "$services" | wc -l)

    log_info "Démarrage de ${total_services} conteneurs Docker..."

    if [[ "$detached" == "true" ]]; then
        if ! $cmd up -d 2>"$error_log"; then
            log_error "Échec du démarrage des conteneurs"
            [[ -s "$error_log" ]] && cat "$error_log" | sed 's/^/  /'
            rm -f "$error_log"
            return 1
        fi
    else
        if ! $cmd up 2>"$error_log"; then
            log_error "Échec du démarrage des conteneurs"
            rm -f "$error_log"
            return 1
        fi
    fi
    rm -f "$error_log"

    # Progress display for each service
    local current=0
    local spinchars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

    echo -e "${BLUE}│${NC} Attente du démarrage des services..."

    while IFS= read -r service; do
        [[ -z "$service" ]] && continue
        current=$((current + 1))

        local max_wait=30
        local waited=0
        local spin_idx=0

        echo -ne "${BLUE}│${NC}   [${current}/${total_services}] ${service} "

        while [[ $waited -lt $max_wait ]]; do
            local status
            status=$(docker compose -f "$compose_file" ps "$service" --format "{{.Status}}" 2>/dev/null | head -1)

            if [[ "$status" == *"Up"* ]] || [[ "$status" == *"running"* ]]; then
                echo -e "\r${BLUE}│${NC}   [${current}/${total_services}] ${service} ${GREEN}✓ running${NC}    "
                break
            elif [[ "$status" == *"Exit"* ]] || [[ "$status" == *"exited"* ]]; then
                echo -e "\r${BLUE}│${NC}   [${current}/${total_services}] ${service} ${RED}✗ exited${NC}    "
                break
            fi

            spin_idx=$(( (spin_idx+1) % ${#spinchars} ))
            echo -ne "\r${BLUE}│${NC}   [${current}/${total_services}] ${service} ${YELLOW}${spinchars:$spin_idx:1}${NC} starting... "
            sleep 0.5
            waited=$((waited + 1))
        done

        [[ $waited -ge $max_wait ]] && echo -e "\r${BLUE}│${NC}   [${current}/${total_services}] ${service} ${YELLOW}⏳ timeout${NC}    "
    done <<< "$services"

    log_success "✓ Conteneurs démarrés"
    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# CLEANUP FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

docker_cleanup() {
    log_info "Nettoyage des ressources Docker (conteneurs et images uniquement)..."

    log_info "  - Nettoyage conteneurs arrêtés..."
    docker container prune -f --filter "label=com.docker.compose.project=linkedin-birthday-auto" 2>/dev/null || \
        docker container prune -f 2>/dev/null || true

    log_info "  - Nettoyage images sans tag..."
    docker image prune -f 2>/dev/null || true

    log_success "✓ Nettoyage Docker terminé (volumes préservés)"
    return 0
}

docker_cleanup_volumes() {
    log_warn "⚠️  Nettoyage des volumes Docker (ATTENTION: perte de données possible)"

    if prompt_yes_no "Êtes-vous sûr de vouloir supprimer les volumes non utilisés ?" "n"; then
        docker volume prune -f 2>/dev/null || true
        log_success "✓ Volumes nettoyés"
    else
        log_info "Nettoyage des volumes annulé"
    fi

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

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

        [[ $i -lt $max_retries ]] && echo -n "." && sleep "$retry_interval"
    done

    log_error "$service_name n'a pas démarré dans le délai imparti"
    return 1
}
