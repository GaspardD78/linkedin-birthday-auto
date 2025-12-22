#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# LINKEDIN AUTO - AUDIT LIBRARY (v4.0)
# Comprehensive security, services, routes, and database audit functions
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# === AUDIT REPORT STRUCTURE ===

declare -g AUDIT_TOTAL_CHECKS=0
declare -g AUDIT_PASSED=0
declare -g AUDIT_WARNINGS=0
declare -g AUDIT_FAILED=0
declare -a AUDIT_WARNINGS_LIST=()
declare -a AUDIT_FAILURES_LIST=()

# === HELPER FUNCTIONS ===

audit_check() {
    local check_name="$1"
    local check_result="$2"
    local message="$3"

    AUDIT_TOTAL_CHECKS=$((AUDIT_TOTAL_CHECKS + 1))

    if [[ "$check_result" == "0" ]]; then
        AUDIT_PASSED=$((AUDIT_PASSED + 1))
        log_success "✓ $check_name: $message"
    elif [[ "$check_result" == "1" ]]; then
        AUDIT_WARNINGS=$((AUDIT_WARNINGS + 1))
        AUDIT_WARNINGS_LIST+=("$check_name: $message")
        log_warn "⚠️  $check_name: $message"
    else
        AUDIT_FAILED=$((AUDIT_FAILED + 1))
        AUDIT_FAILURES_LIST+=("$check_name: $message")
        log_error "❌ $check_name: $message"
    fi
}

# === SECURITY AUDIT ===

audit_security() {
    local env_file="${1:-.env}"

    log_info "════════════════════════════════════════════════════════"
    log_info "🔒 AUDIT SÉCURITÉ"
    log_info "════════════════════════════════════════════════════════"

    if [[ ! -f "$env_file" ]]; then
        log_error "Fichier .env non trouvé: $env_file"
        audit_check ".env existant" 2 "Fichier introuvable"
        return 1
    fi

    # Vérifier permissions .env
    local perms
    perms=$(stat -c %a "$env_file" 2>/dev/null || stat -f %A "$env_file" 2>/dev/null || echo "unknown")

    if [[ "$perms" == "600" ]]; then
        audit_check "Permissions .env" 0 "600 (sécurisé)"
    else
        audit_check "Permissions .env" 1 "$perms au lieu de 600 - risque de sécurité"
        chmod 600 "$env_file" 2>/dev/null || true
    fi

    # Vérifier DASHBOARD_PASSWORD
    local pwd_status=0
    local pwd_msg=""
    # Regex améliorée pour accepter les guillemets optionnels ("..."), fréquents après setup.sh
    if grep -q "^DASHBOARD_PASSWORD=\"\?\$\$2[abxy]\$" "$env_file" 2>/dev/null; then
        pwd_status=0
        pwd_msg="Hash bcrypt détecté"
    elif grep -q "^DASHBOARD_PASSWORD=\"\?\\\$\\\$2[abxy]\\\$" "$env_file" 2>/dev/null; then
        pwd_status=0
        pwd_msg="Hash bcrypt détecté (échappé)"
    elif grep -q "^DASHBOARD_PASSWORD=\"\?\\\$\\\$6\\\$\\\$" "$env_file" 2>/dev/null; then
        pwd_status=1
        pwd_msg="SHA-512 (moins sécurisé que bcrypt)"
    elif grep -q "^DASHBOARD_PASSWORD=$\|CHANGEZ_MOI\|REPLACE_ME" "$env_file" 2>/dev/null; then
        pwd_status=2
        pwd_msg="Non configuré ou valeur par défaut détectée"
    else
        pwd_status=0
        pwd_msg="Configuré"
    fi
    audit_check "DASHBOARD_PASSWORD" "$pwd_status" "$pwd_msg"

    # Vérifier API_KEY
    if grep -q "^API_KEY=.*[a-zA-Z0-9/+=]\{32,\}" "$env_file" 2>/dev/null; then
        audit_check "API_KEY" 0 "Clé de 32+ caractères détectée"
    elif grep -q "^API_KEY=$\|^API_KEY=CHANGEZ_MOI\|^API_KEY=your_" "$env_file" 2>/dev/null; then
        audit_check "API_KEY" 2 "Non configurée ou valeur par défaut"
    else
        audit_check "API_KEY" 1 "Existante mais format incertain"
    fi

    # Vérifier JWT_SECRET
    if grep -q "^JWT_SECRET=.*[a-zA-Z0-9/+=]\{32,\}" "$env_file" 2>/dev/null; then
        audit_check "JWT_SECRET" 0 "Secret de 32+ caractères détecté"
    elif grep -q "^JWT_SECRET=$\|^JWT_SECRET=CHANGEZ_MOI\|^JWT_SECRET=your_" "$env_file" 2>/dev/null; then
        audit_check "JWT_SECRET" 2 "Non configuré ou valeur par défaut"
    else
        audit_check "JWT_SECRET" 1 "Existant mais format incertain"
    fi

    # Vérifier DOMAIN
    local domain
    domain=$(grep "^DOMAIN=" "$env_file" 2>/dev/null | cut -d'=' -f2 || echo "")
    if [[ -n "$domain" ]] && [[ "$domain" != "localhost" ]]; then
        audit_check "DOMAIN" 0 "$domain"
    else
        audit_check "DOMAIN" 1 "Non configuré ou localhost"
    fi

    # Vérifier absence de variables dangereuses
    if grep -q "^[A-Z_]*PASSWORD.*=.*plaintext\|^[A-Z_]*PASSWORD.*=.*clear" "$env_file" 2>/dev/null; then
        audit_check "Pas de mots de passe en clair" 2 "Mots de passe en clair détectés"
    else
        audit_check "Pas de mots de passe en clair" 0 "Aucun mot de passe en clair"
    fi

    log_info "════════════════════════════════════════════════════════"
}

# === SERVICES AUDIT ===

audit_services() {
    log_info "════════════════════════════════════════════════════════"
    log_info "🐳 AUDIT SERVICES DOCKER"
    log_info "════════════════════════════════════════════════════════"

    local compose_file="${1:-docker-compose.yml}"

    if [[ ! -f "$compose_file" ]]; then
        log_error "docker-compose.yml non trouvé: $compose_file"
        audit_check "docker-compose.yml existant" 2 "Fichier introuvable"
        return 1
    fi

    # Vérifier si Docker est disponible
    if ! command -v docker &>/dev/null; then
        audit_check "Docker disponible" 2 "Docker n'est pas installé ou accessible"
        return 1
    fi

    # Services essentiels
    local essential_services=("api" "dashboard" "redis-bot" "nginx" "redis-dashboard" "docker-socket-proxy" "bot-worker")

    for service in "${essential_services[@]}"; do
        local container_id
        container_id=$(docker compose -f "$compose_file" ps -q "$service" 2>/dev/null || echo "")

        if [[ -z "$container_id" ]]; then
            audit_check "Conteneur $service" 2 "Pas en cours d'exécution"
        else
            # Vérifier l'état du conteneur
            local container_state
            container_state=$(docker inspect -f '{{.State.Status}}' "$container_id" 2>/dev/null || echo "unknown")

            if [[ "$container_state" == "running" ]]; then
                audit_check "Conteneur $service" 0 "Actif (ID: ${container_id:0:12})"

                # Vérifier le healthcheck si dispo
                local health_status
                health_status=$(docker inspect -f '{{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "none")

                if [[ "$health_status" == "healthy" ]]; then
                    log_success "  └─ Santé: ✓ healthy"
                elif [[ "$health_status" == "unhealthy" ]]; then
                    audit_check "  Healthcheck $service" 2 "unhealthy"
                    # Afficher les logs pour debug
                    log_info "  Logs récents du conteneur:"
                    docker compose -f "$compose_file" logs "$service" --tail=5 2>/dev/null | sed 's/^/    /'
                elif [[ "$health_status" == "starting" ]]; then
                    log_warn "  └─ Santé: ⚠️  starting (attendre...)"
                fi
            else
                audit_check "Conteneur $service" 2 "État: $container_state (attendu: running)"
                log_warn "  Affichage des logs pour debug:"
                docker compose -f "$compose_file" logs "$service" --tail=10 2>/dev/null | sed 's/^/    /'
            fi
        fi
    done

    # Vérifier la validité du docker-compose.yml
    if docker compose -f "$compose_file" config >/dev/null 2>&1; then
        audit_check "docker-compose.yml syntaxe" 0 "Configuration valide"
    else
        audit_check "docker-compose.yml syntaxe" 2 "Configuration invalide"
    fi

    log_info "════════════════════════════════════════════════════════"
}

# === API ROUTES AUDIT ===

audit_api_routes() {
    log_info "════════════════════════════════════════════════════════"
    log_info "🌐 AUDIT ROUTES API"
    log_info "════════════════════════════════════════════════════════"

    local api_host="${1:-http://localhost:8000}"
    local dashboard_host="${2:-http://localhost:3000}"

    # Vérifier que curl est disponible
    if ! command -v curl &>/dev/null; then
        audit_check "curl disponible" 2 "curl n'est pas installé, vérifications API ignorées"
        return 0
    fi

    # Vérifier API health
    log_info "Vérification API: $api_host"
    if curl -sf "${api_host}/health" >/dev/null 2>&1; then
        audit_check "API /health endpoint" 0 "Accessible"
    else
        audit_check "API /health endpoint" 2 "Non accessible"
    fi

    # Vérifier endpoints critiques
    local api_endpoints=(
        "/api/health"
        "/docs"
    )

    for endpoint in "${api_endpoints[@]}"; do
        if curl -sf "${api_host}${endpoint}" >/dev/null 2>&1; then
            audit_check "API ${endpoint}" 0 "Accessible"
        else
            audit_check "API ${endpoint}" 1 "Non accessible (peut nécessiter authentification)"
        fi
    done

    # Vérifier Dashboard health
    log_info "Vérification Dashboard: $dashboard_host"
    if curl -sf "${dashboard_host}/api/system/health" >/dev/null 2>&1; then
        audit_check "Dashboard /api/system/health" 0 "Accessible"
    else
        audit_check "Dashboard /api/system/health" 2 "Non accessible"
    fi

    # Vérifier routes du dashboard
    local dashboard_routes=(
        "/api/config"
        "/api/tasks"
    )

    for route in "${dashboard_routes[@]}"; do
        if curl -sf -H "Authorization: Bearer test" "${dashboard_host}${route}" >/dev/null 2>&1; then
            audit_check "Dashboard ${route}" 0 "Accessible"
        elif curl -sI "${dashboard_host}${route}" 2>&1 | grep -q "401\|403"; then
            audit_check "Dashboard ${route}" 0 "Protégé par authentification (401/403)"
        else
            audit_check "Dashboard ${route}" 1 "Non accessible"
        fi
    done

    log_info "════════════════════════════════════════════════════════"
}

# === DATABASE AUDIT ===

audit_databases() {
    log_info "════════════════════════════════════════════════════════"
    log_info "💾 AUDIT BASES DE DONNÉES"
    log_info "════════════════════════════════════════════════════════"

    local data_dir="${1:-./data}"

    if [[ ! -d "$data_dir" ]]; then
        log_error "Répertoire data introuvable: $data_dir"
        audit_check "Répertoire data existant" 2 "Introuvable"
        return 1
    fi

    # Vérifier SQLite linkedin.db
    local db_file="$data_dir/linkedin.db"
    if [[ -f "$db_file" ]]; then
        local db_size
        db_size=$(ls -lh "$db_file" | awk '{print $5}')

        # Vérifier que c'est une DB valide avec sqlite3
        if command -v sqlite3 &>/dev/null; then
            if sqlite3 "$db_file" ".tables" >/dev/null 2>&1; then
                # Compter les tables
                local table_count
                table_count=$(sqlite3 "$db_file" ".tables" | wc -w)
                audit_check "SQLite database (linkedin.db)" 0 "Valide ($table_count tables, $db_size)"

                # Afficher les tables pour debug verbeux
                log_info "  Tables disponibles:"
                sqlite3 "$db_file" ".tables" | tr ' ' '\n' | while read -r table; do
                    if [[ -n "$table" ]]; then
                        local row_count
                        row_count=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM $table" 2>/dev/null || echo "?")
                        log_info "    - $table ($row_count rows)"
                    fi
                done
            else
                audit_check "SQLite database (linkedin.db)" 2 "Fichier corrompu ou format invalide"
            fi
        else
            if file "$db_file" 2>/dev/null | grep -q "SQLite"; then
                audit_check "SQLite database (linkedin.db)" 0 "Détecté ($db_size, sqlite3 non installé pour vérification)"
            else
                audit_check "SQLite database (linkedin.db)" 1 "Présent mais type incertain"
            fi
        fi
    else
        audit_check "SQLite database (linkedin.db)" 1 "Fichier non trouvé (sera créé au démarrage)"
    fi

    # Vérifier Redis
    if command -v redis-cli &>/dev/null; then
        # Redis bot
        if redis-cli -h localhost -p 6379 ping >/dev/null 2>&1; then
            local redis_info
            redis_info=$(redis-cli -h localhost -p 6379 info stats 2>/dev/null | grep -E "connected_clients|total_commands_processed" | tr '\n' ' ' || echo "")
            audit_check "Redis bot (localhost:6379)" 0 "Accessible $redis_info"
        else
            audit_check "Redis bot (localhost:6379)" 1 "Non accessible (peut être dans Docker)"
        fi
    else
        # Redis est probablement dans Docker, vérifier via Docker
        if docker exec redis-bot redis-cli ping >/dev/null 2>&1; then
            audit_check "Redis bot (Docker)" 0 "Conteneur actif et accessible"
        else
            audit_check "Redis bot (Docker)" 2 "Conteneur non accessible"
        fi
    fi

    # Vérifier autres fichiers de données
    if [[ -f "$data_dir/messages.txt" ]]; then
        local msg_count
        msg_count=$(wc -l < "$data_dir/messages.txt" || echo "0")
        log_info "  Messages file: $msg_count lignes"
    fi

    if [[ -f "$data_dir/auth_state.json" ]]; then
        log_info "  Auth state: ✓ Présent"
    else
        log_info "  Auth state: ⚠️  Non trouvé (optionnel)"
    fi

    log_info "════════════════════════════════════════════════════════"
}

# === VOLUMES & PERMISSIONS AUDIT ===

audit_volumes() {
    log_info "════════════════════════════════════════════════════════"
    log_info "📁 AUDIT VOLUMES ET PERMISSIONS"
    log_info "════════════════════════════════════════════════════════"

    local directories=("data" "logs" "config" "certbot" "deployment/nginx")

    for dir in "${directories[@]}"; do
        if [[ -d "$dir" ]]; then
            local perms
            local owner
            local size

            perms=$(stat -c %a "$dir" 2>/dev/null || stat -f %A "$dir" 2>/dev/null || echo "unknown")
            owner=$(stat -c %U:%G "$dir" 2>/dev/null || stat -f "%Su:%Sg" "$dir" 2>/dev/null || echo "unknown")
            size=$(du -sh "$dir" 2>/dev/null | awk '{print $1}' || echo "?")

            # Vérifier si le répertoire est writable
            if [[ -w "$dir" ]]; then
                audit_check "Répertoire $dir" 0 "RW ($perms, propriétaire: $owner, taille: $size)"
            else
                audit_check "Répertoire $dir" 1 "Non-writable ($perms, propriétaire: $owner)"
            fi
        else
            audit_check "Répertoire $dir" 1 "Introuvable"
        fi
    done

    # Vérifier les fichiers critiques
    local critical_files=(".env" "docker-compose.yml")

    for file in "${critical_files[@]}"; do
        if [[ -f "$file" ]]; then
            local perms
            perms=$(stat -c %a "$file" 2>/dev/null || stat -f %A "$file" 2>/dev/null || echo "unknown")
            audit_check "Fichier $file" 0 "Présent (permissions: $perms)"
        else
            audit_check "Fichier $file" 2 "Manquant"
        fi
    done

    log_info "════════════════════════════════════════════════════════"
}

# === SSL CERTIFICATES AUDIT ===

audit_ssl() {
    log_info "════════════════════════════════════════════════════════"
    log_info "🔐 AUDIT CERTIFICATS SSL/TLS"
    log_info "════════════════════════════════════════════════════════"

    local domain="${1:-gaspardanoukolivier.freeboxos.fr}"
    local cert_dir="certbot/conf/live/${domain}"

    if [[ ! -d "$cert_dir" ]]; then
        audit_check "Certificats $domain" 1 "Répertoire non trouvé (HTTP mode peut être utilisé)"
    else
        # Vérifier fullchain.pem
        if [[ -f "$cert_dir/fullchain.pem" ]]; then
            if command -v openssl &>/dev/null; then
                local expiry_date
                local days_left

                expiry_date=$(openssl x509 -enddate -noout -in "$cert_dir/fullchain.pem" 2>/dev/null | cut -d= -f2 || echo "unknown")

                if [[ "$expiry_date" != "unknown" ]]; then
                    days_left=$(( ($(date -d "$expiry_date" +%s 2>/dev/null || echo 0) - $(date +%s)) / 86400 ))

                    if [[ $days_left -gt 30 ]]; then
                        audit_check "Certificat fullchain.pem" 0 "Valide jusqu'à $expiry_date ($days_left jours)"
                    elif [[ $days_left -gt 0 ]]; then
                        audit_check "Certificat fullchain.pem" 1 "Expire bientôt: $expiry_date ($days_left jours)"
                    else
                        audit_check "Certificat fullchain.pem" 2 "EXPIRÉ depuis $expiry_date"
                    fi
                else
                    audit_check "Certificat fullchain.pem" 0 "Présent (format incertain)"
                fi
            else
                audit_check "Certificat fullchain.pem" 0 "Présent (openssl non disponible pour vérification)"
            fi
        else
            audit_check "Certificat fullchain.pem" 1 "Non trouvé"
        fi

        # Vérifier privkey.pem
        if [[ -f "$cert_dir/privkey.pem" ]]; then
            local key_perms
            key_perms=$(stat -c %a "$cert_dir/privkey.pem" 2>/dev/null || stat -f %A "$cert_dir/privkey.pem" 2>/dev/null || echo "unknown")

            if [[ "$key_perms" == "600" ]]; then
                audit_check "Clé privée privkey.pem" 0 "Présente avec permissions sécurisées (600)"
            else
                audit_check "Clé privée privkey.pem" 1 "Permissions non optimales ($key_perms au lieu de 600)"
                chmod 600 "$cert_dir/privkey.pem" 2>/dev/null || true
            fi
        else
            audit_check "Clé privée privkey.pem" 1 "Non trouvée"
        fi
    fi

    log_info "════════════════════════════════════════════════════════"
}

# === NETWORK AUDIT ===

audit_network() {
    log_info "════════════════════════════════════════════════════════"
    log_info "🌐 AUDIT RÉSEAU"
    log_info "════════════════════════════════════════════════════════"

    # Vérifier Docker network
    if docker network inspect linkedin-network >/dev/null 2>&1; then
        audit_check "Réseau Docker (linkedin-network)" 0 "Présent et fonctionnel"

        # Lister les conteneurs connectés
        local container_count
        container_count=$(docker network inspect linkedin-network | grep -c '"Name":' 2>/dev/null || echo "0")
        log_info "  Conteneurs connectés: $container_count"
    else
        audit_check "Réseau Docker (linkedin-network)" 2 "Non trouvé"
    fi

    # Vérifier connectivité DNS
    if docker run --rm --network linkedin-network alpine nslookup 8.8.8.8 >/dev/null 2>&1; then
        audit_check "DNS (Google 8.8.8.8)" 0 "Accessible depuis Docker"
    else
        audit_check "DNS (Google 8.8.8.8)" 1 "Non accessible depuis Docker"
    fi

    # Vérifier connectivité Cloudflare DNS
    if docker run --rm --network linkedin-network alpine nslookup 1.1.1.1 >/dev/null 2>&1; then
        audit_check "DNS (Cloudflare 1.1.1.1)" 0 "Accessible depuis Docker"
    else
        audit_check "DNS (Cloudflare 1.1.1.1)" 1 "Non accessible depuis Docker"
    fi

    log_info "════════════════════════════════════════════════════════"
}

# === LOGS AUDIT ===

audit_logs() {
    log_info "════════════════════════════════════════════════════════"
    log_info "📋 AUDIT LOGS"
    log_info "════════════════════════════════════════════════════════"

    local logs_dir="${1:-./logs}"

    if [[ ! -d "$logs_dir" ]]; then
        audit_check "Répertoire logs" 1 "Introuvable (sera créé)"
        return 0
    fi

    # Vérifier taille des logs
    local logs_size
    logs_size=$(du -sh "$logs_dir" 2>/dev/null | awk '{print $1}' || echo "?")

    audit_check "Répertoire logs" 0 "Présent (taille: $logs_size)"

    # Lister les fichiers de logs principaux
    for log_file in api.log dashboard.log worker.log; do
        if [[ -f "$logs_dir/$log_file" ]]; then
            local file_size
            file_size=$(ls -lh "$logs_dir/$log_file" | awk '{print $5}')

            local last_modified
            last_modified=$(date -r "$logs_dir/$log_file" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "?")

            # Vérifier les dernières lignes pour les erreurs
            local error_count
            error_count=$(grep -ic "error\|fatal\|critical" "$logs_dir/$log_file" 2>/dev/null | head -1 || echo "0")

            if [[ "$error_count" -gt 0 ]]; then
                audit_check "Log $log_file" 1 "$file_size (modifié: $last_modified, $error_count erreurs)"
            else
                audit_check "Log $log_file" 0 "$file_size (modifié: $last_modified)"
            fi
        fi
    done

    log_info "════════════════════════════════════════════════════════"
}

# === ATTENTE ACTIVE DES CONTENEURS HEALTHY ===

# Attendre que tous les conteneurs soient "healthy" ou "running"
# Usage: wait_for_containers_healthy &lt;compose_file&gt; &lt;max_wait_seconds&gt;
wait_for_containers_healthy() {
    local compose_file="${1:-docker-compose.yml}"
    local max_wait="${2:-120}" # 2 minutes par défaut
    local elapsed=0
    local check_interval=5

    log_info "════════════════════════════════════════════════════════"
    log_info "⏳ ATTENTE DES CONTENEURS (HEALTHY/RUNNING)"
    log_info "════════════════════════════════════════════════════════"

    # Récupérer la liste des services
    local services
    services=$(docker compose -f "$compose_file" config --services 2>/dev/null)

    if [[ -z "$services" ]]; then
        log_error "Impossible de lire les services depuis $compose_file"
        return 1
    fi

    local total_services
    total_services=$(echo "$services" | wc -l)

    log_info "Services à vérifier: $total_services"
    echo ""

    while [[ $elapsed -lt $max_wait ]]; do
        local all_healthy=true
        local healthy_count=0
        local starting_count=0
        local unhealthy_count=0

        while IFS= read -r service; do
            [[ -z "$service" ]] && continue

            local container_id
            container_id=$(docker compose -f "$compose_file" ps -q "$service" 2>/dev/null)

            if [[ -z "$container_id" ]]; then
                log_warn "  [$service] Conteneur non démarré"
                all_healthy=false
                continue
            fi

            # Vérifier le statut du conteneur
            local container_state
            container_state=$(docker inspect -f '{{.State.Status}}' "$container_id" 2>/dev/null || echo "unknown")

            if [[ "$container_state" != "running" ]]; then
                log_warn "  [$service] État: $container_state (attendu: running)"
                all_healthy=false
                continue
            fi

            # Vérifier le healthcheck si disponible
            local health_status
            health_status=$(docker inspect -f '{{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "none")

            case "$health_status" in
                healthy)
                    healthy_count=$((healthy_count + 1))
                    log_success "  [$service] ✓ healthy"
                    ;;
                starting)
                    starting_count=$((starting_count + 1))
                    log_info "  [$service] ⏳ starting... (${elapsed}s/${max_wait}s)"
                    all_healthy=false
                    ;;
                unhealthy)
                    unhealthy_count=$((unhealthy_count + 1))
                    log_error "  [$service] ✗ unhealthy"
                    all_healthy=false
                    ;;
                none)
                    # Pas de healthcheck, considérer comme OK si running
                    healthy_count=$((healthy_count + 1))
                    log_success "  [$service] ✓ running (no healthcheck)"
                    ;;
                *)
                    log_warn "  [$service] État inconnu: $health_status"
                    all_healthy=false
                    ;;
            esac

        done <<< "$services"

        if [[ "$all_healthy" == "true" ]]; then
            echo ""
            log_success "✓ Tous les conteneurs sont opérationnels ($healthy_count/$total_services)"
            log_info "════════════════════════════════════════════════════════"
            return 0
        fi

        # Afficher un résumé
        echo ""
        log_info "  Résumé: ${GREEN}$healthy_count healthy${NC} | ${YELLOW}$starting_count starting${NC} | ${RED}$unhealthy_count unhealthy${NC}"
        log_info "  ⏳ Attente... (${elapsed}s/${max_wait}s)"
        echo ""

        sleep "$check_interval"
        elapsed=$((elapsed + check_interval))
    done

    # Timeout atteint
    log_error "⏱ Timeout atteint (${max_wait}s) - Certains conteneurs ne sont pas healthy"
    log_info "════════════════════════════════════════════════════════"
    return 1
}

# Attendre qu'une URL API réponde avec un code HTTP 200
# Usage: wait_for_api_endpoint &lt;service_name&gt; &lt;url&gt; &lt;max_wait_seconds&gt;
wait_for_api_endpoint() {
    local service_name="$1"
    local url="$2"
    local max_wait="${3:-60}"
    local elapsed=0
    local check_interval=3

    log_info "Attente de $service_name sur $url..."

    while [[ $elapsed -lt $max_wait ]]; do
        # Utilisation de -L pour suivre les redirections (ex: 307 -> 200)
        # Utilisation de -f pour échouer sur 4xx/5xx (ex: 502 pendant le démarrage)
        if curl -sfL "$url" > /dev/null 2>&1; then
            log_success "✓ $service_name est accessible"
            return 0
        fi

        elapsed=$((elapsed + check_interval))
        echo -ne "\r  ⏳ Attente de $service_name... (${elapsed}s/${max_wait}s)"
        sleep "$check_interval"
    done

    echo ""
    log_error "✗ $service_name n'est pas accessible après ${max_wait}s"
    return 1
}

# === MAIN AUDIT FUNCTION ===

run_full_audit() {
    local env_file="${1:-.env}"
    local compose_file="${2:-docker-compose.yml}"
    local data_dir="${3:-./data}"
    local domain="${4:-gaspardanoukolivier.freeboxos.fr}"

    log_info ""
    log_info "${BOLD}${BLUE}╔═════════════════════════════════════════════════════════════════════════╗${NC}"
    log_info "${BOLD}${BLUE}║             🔍 AUDIT COMPLET - SÉCURITÉ, SERVICES, BDD                 ║${NC}"
    log_info "${BOLD}${BLUE}╚═════════════════════════════════════════════════════════════════════════╝${NC}"

    # Réinitialiser les compteurs
    AUDIT_TOTAL_CHECKS=0
    AUDIT_PASSED=0
    AUDIT_WARNINGS=0
    AUDIT_FAILED=0
    AUDIT_WARNINGS_LIST=()
    AUDIT_FAILURES_LIST=()

    # 1. Attendre que les conteneurs soient healthy (NOUVEAU)
    if ! wait_for_containers_healthy "$compose_file" 120; then
        log_warn "Certains conteneurs ne sont pas healthy, mais on continue l'audit..."
    fi

    # 2. Attendre que les API soient accessibles (NOUVEAU)
    echo ""
    log_info "Vérification des endpoints API..."
    wait_for_api_endpoint "API" "http://localhost:8000/health" 60 || true
    wait_for_api_endpoint "Dashboard" "http://localhost:3000/api/system/health" 60 || true
    echo ""

    # 3. Exécuter tous les audits
    audit_security "$env_file"
    audit_services "$compose_file"
    audit_api_routes
    audit_databases "$data_dir"
    audit_volumes
    audit_ssl "$domain"
    audit_network
    audit_logs "$data_dir/../logs"

    # === RAPPORT FINAL ===

    log_info ""
    log_info "${BOLD}${BLUE}╔═════════════════════════════════════════════════════════════════════════╗${NC}"
    log_info "${BOLD}${BLUE}║                      📊 RÉSUMÉ DE L'AUDIT                             ║${NC}"
    log_info "${BOLD}${BLUE}╚═════════════════════════════════════════════════════════════════════════╝${NC}"

    local summary_color="$GREEN"
    if [[ $AUDIT_FAILED -gt 0 ]]; then
        summary_color="$RED"
    elif [[ $AUDIT_WARNINGS -gt 0 ]]; then
        summary_color="$YELLOW"
    fi

    log_info ""
    log_info "  Résultats globaux:"
    log_info "    ${GREEN}✓ Réussis     : $AUDIT_PASSED/$AUDIT_TOTAL_CHECKS${NC}"
    log_info "    ${YELLOW}⚠️  Avertissements : $AUDIT_WARNINGS/$AUDIT_TOTAL_CHECKS${NC}"
    log_info "    ${RED}❌ Échoués     : $AUDIT_FAILED/$AUDIT_TOTAL_CHECKS${NC}"

    # Afficher les détails des avertissements
    if [[ $AUDIT_WARNINGS -gt 0 ]]; then
        log_info ""
        log_info "  ${YELLOW}Avertissements détectés:${NC}"
        for warning in "${AUDIT_WARNINGS_LIST[@]}"; do
            log_info "    ⚠️  $warning"
        done
    fi

    # Afficher les détails des échecs
    if [[ $AUDIT_FAILED -gt 0 ]]; then
        log_info ""
        log_info "  ${RED}Problèmes critiques détectés:${NC}"
        for failure in "${AUDIT_FAILURES_LIST[@]}"; do
            log_info "    ❌ $failure"
        done

        log_info ""
        log_warn "⚠️  ACTIONS RECOMMANDÉES:"
        log_info "  1. Vérifiez que tous les conteneurs Docker sont en cours d'exécution"
        log_info "  2. Consultez les logs pour plus de détails: docker compose logs [service]"
        log_info "  3. Vérifiez votre configuration .env"
        log_info "  4. Assurez-vous que les répertoires data/logs ont les bonnes permissions"
    fi

    # Statut final
    log_info ""
    if [[ $AUDIT_FAILED -eq 0 ]] && [[ $AUDIT_WARNINGS -eq 0 ]]; then
        log_success "${GREEN}✅ AUDIT COMPLÉTÉ AVEC SUCCÈS - Aucun problème détecté${NC}"
        log_info "════════════════════════════════════════════════════════"
        return 0
    elif [[ $AUDIT_FAILED -eq 0 ]]; then
        log_warn "${YELLOW}⚠️  AUDIT COMPLÉTÉ - $AUDIT_WARNINGS avertissement(s) detaillés au dessus${NC}"
        log_info "════════════════════════════════════════════════════════"
        return 0
    else
        log_error "${RED}❌ AUDIT ÉCHOUÉ - $AUDIT_FAILED problème(s) critique(s) détecté(s)${NC}"
        log_info "════════════════════════════════════════════════════════"
        return 1
    fi
}
