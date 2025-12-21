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
        log_error "Essayez: sudo systemctl start docker"
        return 1
    fi
    log_success "✓ Docker daemon actif"

    # Vérifier que docker compose est disponible (plugin intégré)
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

# Enhanced Interactive Pull with Dashboard
docker_pull_with_retry() {
    local compose_file="$1"
    local max_retries=4
    local base_delay=2
    local error_log
    error_log=$(mktemp)
    local pull_log
    pull_log=$(mktemp)

    # --- 1. Validation Phase ---
    if [[ ! -f "$compose_file" ]]; then
        log_error "Compose file not found: $compose_file"
        return 1
    fi

    # Validate YAML
    if ! docker compose -f "$compose_file" config > /dev/null 2>"$error_log"; then
        log_error "Invalid Docker Compose file:"
        cat "$error_log" | sed 's/^/  /' && rm -f "$error_log"
        return 1
    fi

    # Get Services
    local services_raw
    services_raw=$(docker compose -f "$compose_file" config --services 2>"$error_log")
    if [[ $? -ne 0 ]] || [[ -z "$services_raw" ]]; then
        log_error "Failed to list services."
        cat "$error_log" && rm -f "$error_log"
        return 1
    fi
    rm -f "$error_log"

    # Read into array
    local service_list=()
    while IFS= read -r s; do [[ -n "$s" ]] && service_list+=("$s"); done <<< "$services_raw"
    local total=${#service_list[@]}

    # --- 2. Mode Selection ---
    local use_ui=false
    if has_smart_tty; then use_ui=true; fi

    # Disable UI if terminal height is too small to fit the dashboard
    if [[ "$use_ui" == "true" ]]; then
        local term_lines
        term_lines=$(get_term_lines)
        if [[ $((total + 5)) -gt "$term_lines" ]]; then
            use_ui=false
            log_warn "Terminal too small for dashboard UI ($total services vs $term_lines lines). Falling back to log mode."
        fi
    fi

    log_info "Synchronizing ${total} Docker images... (Sequential pull for UI stability)"

    # --- 3. UI Execution ---
    if [[ "$use_ui" == "true" ]]; then
        # Trap to clean up cursor and logs
        trap 'ui_cursor_show; rm -f "$pull_log" "$error_log"; [[ -n "${pid:-}" ]] && kill "$pid" 2>/dev/null' EXIT INT TERM

        ui_cursor_hide
        echo ""

        # Draw Initial Dashboard
        # Header is already printed by log_info above, let's print the list

        for svc in "${service_list[@]}"; do
            printf "   ${DIM}• %-25s${NC} ${DIM}Waiting...${NC}\n" "${svc:0:25}"
        done
        echo "" # Spacer
        echo "" # Global Bar placeholder

        # Calculate cursor jumps
        local total_rows=$((total + 2)) # Services + Spacer + Bar

        # We start at the bottom of the printed block.

        local current=0
        for svc in "${service_list[@]}"; do
            ((current++))
            local retry=0
            local success=false

            # --- PREPARE CURSOR ---
            # Lines are:
            # 1. Service 1
            # ...
            # N. Service N
            # N+1. Spacer
            # N+2. Global Bar
            # We are at N+3.

            # Calculate lines UP to reach the current service line
            local lines_up=$((total_rows - (current - 1)))

            # START PULL LOOP
            while [[ $retry -lt $max_retries ]]; do
                # Update line to "Pulling"
                echo -ne "\r"
                ui_move_up_n "$lines_up"
                ui_line_clear
                printf "   ${BLUE}➤ %-25s${NC} ${YELLOW}Starting...${NC}" "${svc:0:25}"

                # Move back down to update Global Bar
                tput cud "$lines_up"

                # Update Global Bar
                ui_move_up_n 1 # Go to Bar line
                ui_line_clear
                local p_current=$((current - 1)) # Completed count
                local cols
                cols=$(get_term_cols)
                local bar_width=$((cols - 35)) # Subtract label and percentage length
                [[ $bar_width -lt 10 ]] && bar_width=10 # Minimum width
                printf "   ${BLUE}Total Progress:${NC} "
                ui_render_progress_bar "$p_current" "$total" "$bar_width" "$BLUE"
                tput cud 1 # Back to bottom

                # START BACKGROUND PULL
                > "$pull_log"
                # Using --progress=plain to parse logs
                docker compose -f "$compose_file" pull --progress=plain "$svc" > "$pull_log" 2>&1 &
                local pid=$!

                local spin_chars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
                if [[ "${LANG:-}" != *"UTF-8"* ]]; then
                    spin_chars='|/-\'
                fi
                local idx=0
                local spin_len=${#spin_chars}

                # SPINNER LOOP
                while kill -0 "$pid" 2>/dev/null; do
                    idx=$(( (idx+1) % spin_len ))
                    local char="${spin_chars:$idx:1}"

                    # Parse status from log
                    local status_msg="Downloading..."
                    local last_line
                    # Grab last non-empty line
                    last_line=$(grep -v "^$" "$pull_log" | tail -n 1 | tr -d '\r' | tr -s ' ' || true)

                    # Heuristics for status
                    if [[ "$last_line" == *"Downloading"* ]]; then
                        status_msg="Downloading layers..."
                        # Try to find a percentage like "12MB/50MB" or similar if present
                        # Usually plain output is "layer: Downloading [===>   ] 10MB/50MB"
                        if [[ "$last_line" =~ ([0-9]+(\.[0-9]+)?[KMGT]B/[0-9]+(\.[0-9]+)?[KMGT]B) ]]; then
                            status_msg="Downloading (${BASH_REMATCH[1]})"
                        fi
                    elif [[ "$last_line" == *"Waiting"* ]]; then
                        status_msg="Waiting for layers..."
                    elif [[ "$last_line" == *"Verifying"* ]]; then
                        status_msg="Verifying Checksum..."
                    elif [[ "$last_line" == *"Pull complete"* ]]; then
                        status_msg="Extracting..."
                    elif [[ "$last_line" == *"Pulled"* ]]; then
                        status_msg="Finalizing..."
                    elif [[ -n "$last_line" ]]; then
                        # Strip service name if present at start "service_1 The..."
                         local clean_line=${last_line#* }
                         status_msg=$(ui_truncate_text "${clean_line}" 35)
                    fi

                    # Update Service Line
                    echo -ne "\r"
                    ui_move_up_n "$lines_up"
                    ui_line_clear
                    printf "   ${BLUE}➤ %-25s${NC} ${CYAN}%s${NC} %s" "${svc:0:25}" "$char" "$status_msg"
                    tput cud "$lines_up"

                    sleep 0.1
                done

                wait "$pid"
                local exit_code=$?

                if [[ $exit_code -eq 0 ]]; then
                    success=true
                    # Mark DONE
                    echo -ne "\r"
                    ui_move_up_n "$lines_up"
                    ui_line_clear
                    printf "   ${GREEN}✓ %-25s${NC} ${DIM}Ready${NC}" "${svc:0:25}"
                    tput cud "$lines_up"
                    break
                else
                    ((retry++))
                    local delay=$((base_delay ** retry))
                    # Mark ERROR/RETRY
                    echo -ne "\r"
                    ui_move_up_n "$lines_up"
                    ui_line_clear
                    printf "   ${YELLOW}⚠ %-25s${NC} ${RED}Retry ${retry}/${max_retries} in ${delay}s...${NC}" "${svc:0:25}"
                    tput cud "$lines_up"
                    sleep "$delay"
                fi
            done

            if [[ "$success" != "true" ]]; then
                ui_cursor_show
                # Move below the dashboard block
                echo ""
                log_error "Failed to pull $svc after retries."
                return 1
            fi
        done

        # Final Global Bar Update
        ui_move_up_n 1
        ui_line_clear
        local cols
        cols=$(get_term_cols)
        local bar_width=$((cols - 35))
        [[ $bar_width -lt 10 ]] && bar_width=10
        printf "   ${BLUE}Total Progress:${NC} "
        ui_render_progress_bar "$total" "$total" "$bar_width" "$GREEN"
        tput cud 1

        ui_cursor_show
        echo -e "\n\n${GREEN}✓ All images synchronized.${NC}\n"
        rm -f "$pull_log"
        return 0

    else
        # --- 4. Fallback Mode (No UI) ---
        # Simple linear log
        local current=0
        for svc in "${service_list[@]}"; do
            ((current++))
            echo -n "   [${current}/${total}] Pulling $svc... "
            local retry=0
            local success=false
            while [[ $retry -lt $max_retries ]]; do
                if docker compose -f "$compose_file" pull --quiet "$svc" 2>/dev/null; then
                    echo "OK"
                    success=true
                    break
                else
                     ((retry++))
                     if [[ $retry -lt $max_retries ]]; then
                        echo -n "Retry $retry... "
                        sleep 2
                     else
                        echo "Failed."
                     fi
                fi
            done
            if [[ "$success" == "false" ]]; then
                return 1
            fi
        done
        log_success "Images pulled."
        return 0
    fi
}

docker_compose_up() {
    local compose_file="$1"
    local detached="${2:-true}"
    local monitoring="${3:-false}"
    local cmd="docker compose -f $compose_file"
    local error_log="/tmp/setup_docker_up.err"

    # Ajouter le profil monitoring si activé
    if [[ "$monitoring" == "true" ]]; then
        log_info "Démarrage avec monitoring activé..."
        cmd="$cmd --profile monitoring"
    fi

    # Récupérer la liste des services à démarrer
    local services
    if [[ "$monitoring" == "true" ]]; then
        services=$(docker compose -f "$compose_file" --profile monitoring config --services 2>/dev/null)
    else
        services=$(docker compose -f "$compose_file" config --services 2>/dev/null)
    fi

    local total_services
    total_services=$(echo "$services" | wc -l)

    log_info "Démarrage de ${total_services} conteneurs Docker..."

    # Démarrer les conteneurs
    if [[ "$detached" == "true" ]]; then
        if ! $cmd up -d 2>"$error_log"; then
            log_error "Échec du démarrage des conteneurs"
            if [[ -s "$error_log" ]]; then
                cat "$error_log" | sed 's/^/  /'
            fi
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

    # Afficher la progression du démarrage de chaque service
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
            # Vérifier si le conteneur est running
            local status
            status=$(docker compose -f "$compose_file" ps "$service" --format "{{.Status}}" 2>/dev/null | head -1)

            if [[ "$status" == *"Up"* ]] || [[ "$status" == *"running"* ]]; then
                echo -e "\r${BLUE}│${NC}   [${current}/${total_services}] ${service} ${GREEN}✓ running${NC}    "
                break
            elif [[ "$status" == *"Exit"* ]] || [[ "$status" == *"exited"* ]]; then
                echo -e "\r${BLUE}│${NC}   [${current}/${total_services}] ${service} ${RED}✗ exited${NC}    "
                break
            fi

            # Afficher le spinner
            spin_idx=$(( (spin_idx+1) % ${#spinchars} ))
            echo -ne "\r${BLUE}│${NC}   [${current}/${total_services}] ${service} ${YELLOW}${spinchars:$spin_idx:1}${NC} starting... "
            sleep 0.5
            waited=$((waited + 1))
        done

        if [[ $waited -ge $max_wait ]]; then
            echo -e "\r${BLUE}│${NC}   [${current}/${total_services}] ${service} ${YELLOW}⏳ timeout${NC}    "
        fi
    done <<< "$services"

    log_success "✓ Conteneurs démarrés"
    return 0
}

docker_cleanup() {
    log_info "Nettoyage des ressources Docker (conteneurs et images uniquement)..."

    # Supprimer les conteneurs arrêtés de ce projet uniquement
    log_info "  - Nettoyage conteneurs arrêtés..."
    docker container prune -f --filter "label=com.docker.compose.project=linkedin-birthday-auto" 2>/dev/null || \
        docker container prune -f 2>/dev/null || true

    # Supprimer les images sans tag (dangereuses uniquement)
    log_info "  - Nettoyage images sans tag..."
    docker image prune -f 2>/dev/null || true

    # NE PAS supprimer les volumes automatiquement pour éviter perte de données
    # Les utilisateurs peuvent le faire manuellement avec:
    #   docker volume prune -f

    log_success "✓ Nettoyage Docker terminé (volumes préservés)"
    return 0
}

docker_cleanup_volumes() {
    # Fonction séparée pour nettoyer les volumes (non appelée automatiquement)
    log_warn "⚠️  Nettoyage des volumes Docker (ATTENTION: perte de données possible)"

    if prompt_yes_no "Êtes-vous sûr de vouloir supprimer les volumes non utilisés ?" "n"; then
        docker volume prune -f 2>/dev/null || true
        log_success "✓ Volumes nettoyés"
    else
        log_info "Nettoyage des volumes annulé"
    fi

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
