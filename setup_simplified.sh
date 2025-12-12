#!/bin/bash

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  LinkedIn Birthday Bot - Installation Simplifiée v4.0                    ║
# ║  Déploiement étape par étape avec hardening sécurité intégré             ║
# ║                                                                          ║
# ║  Images pré-construites via GitHub Actions (GHCR)                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
ENV_FILE=".env"
ENV_TEMPLATE=".env.pi4.example"
LOG_FILE="setup_$(date +%Y%m%d_%H%M%S).log"
DEBUG_MODE="${DEBUG:-false}"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ═══════════════════════════════════════════════════════════════════════════
# SYSTÈME DE LOGGING DEBUG
# ═══════════════════════════════════════════════════════════════════════════
log_init() {
    echo "═══════════════════════════════════════════════════════════════" > "$LOG_FILE"
    echo "LinkedIn Birthday Bot - Setup Log" >> "$LOG_FILE"
    echo "Date: $(date)" >> "$LOG_FILE"
    echo "User: $(whoami)" >> "$LOG_FILE"
    echo "PWD: $(pwd)" >> "$LOG_FILE"
    echo "═══════════════════════════════════════════════════════════════" >> "$LOG_FILE"
}

log_debug() {
    local msg="[DEBUG $(date +%H:%M:%S)] $1"
    echo "$msg" >> "$LOG_FILE"
    [[ "$DEBUG_MODE" == "true" ]] && echo -e "${DIM}$msg${NC}"
}

log_info() {
    local msg="[INFO  $(date +%H:%M:%S)] $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${CYAN}ℹ${NC}  $1"
}

log_success() {
    local msg="[OK    $(date +%H:%M:%S)] $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    local msg="[WARN  $(date +%H:%M:%S)] $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${YELLOW}⚠️${NC}  $1"
}

log_error() {
    local msg="[ERROR $(date +%H:%M:%S)] $1"
    echo "$msg" >> "$LOG_FILE"
    echo -e "${RED}❌${NC} $1"
}

log_step() {
    local step_num="$1"
    local step_name="$2"
    echo "" >> "$LOG_FILE"
    echo "═══ ÉTAPE $step_num: $step_name ═══" >> "$LOG_FILE"
    echo ""
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  ÉTAPE $step_num : $step_name${NC}"
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════
print_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   🚀 LinkedIn Birthday Bot - Installation Sécurisée v4.0                ║
║                                                                          ║
║   • Déploiement étape par étape                                         ║
║   • Hardening sécurité intégré                                          ║
║   • Logs debug détaillés                                                ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

ask_continue() {
    local prompt="${1:-Continuer ?}"
    echo -e -n "${CYAN}❓${NC} $prompt [O/n] "
    read -r response
    [[ -z "$response" || "$response" =~ ^[OoYy]$ ]]
}

generate_secure_key() {
    python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || \
    openssl rand -hex 32 2>/dev/null || \
    head -c 32 /dev/urandom | xxd -p | tr -d '\n'
}

validate_key() {
    local key="$1"
    local name="$2"

    # Liste des valeurs interdites
    local forbidden=("internal_secret_key" "CHANGE_ME" "CHANGEZ_MOI" "changeme" "secret" "password" "")

    for bad in "${forbidden[@]}"; do
        if [[ "$key" == "$bad"* ]]; then
            log_error "$name contient une valeur non sécurisée: '$bad...'"
            return 1
        fi
    done

    # Vérifier longueur minimum (32 caractères = 64 hex)
    if [[ ${#key} -lt 32 ]]; then
        log_error "$name est trop court (${#key} chars, minimum 32)"
        return 1
    fi

    log_debug "$name validé (${#key} chars)"
    return 0
}

wait_container_healthy() {
    local container="$1"
    local timeout="${2:-120}"
    local start_time=$(date +%s)

    log_debug "Attente de $container (timeout: ${timeout}s)"

    while true; do
        local elapsed=$(($(date +%s) - start_time))

        if [[ $elapsed -ge $timeout ]]; then
            log_error "Timeout: $container non healthy après ${timeout}s"
            log_debug "Logs de $container:"
            docker logs "$container" --tail 30 2>&1 | tee -a "$LOG_FILE"
            return 1
        fi

        local status=$(docker inspect "$container" --format='{{.State.Status}}' 2>/dev/null || echo "not_found")
        local health=$(docker inspect "$container" --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' 2>/dev/null || echo "unknown")

        log_debug "$container: status=$status health=$health (${elapsed}s)"

        case "$health" in
            "healthy")
                log_success "$container est healthy (${elapsed}s)"
                return 0
                ;;
            "no_healthcheck")
                if [[ "$status" == "running" ]]; then
                    log_success "$container est running (pas de healthcheck)"
                    return 0
                fi
                ;;
            "unhealthy")
                log_error "$container est unhealthy!"
                log_debug "Derniers logs:"
                docker logs "$container" --tail 20 2>&1 | tee -a "$LOG_FILE"
                return 1
                ;;
        esac

        if [[ "$status" == "exited" || "$status" == "dead" ]]; then
            log_error "$container a crashé (status: $status)"
            log_debug "Logs de crash:"
            docker logs "$container" --tail 50 2>&1 | tee -a "$LOG_FILE"
            return 1
        fi

        echo -n "."
        sleep 3
    done
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 0 : INITIALISATION
# ═══════════════════════════════════════════════════════════════════════════
step_0_init() {
    log_step "0" "INITIALISATION"

    log_info "Fichier de log: $LOG_FILE"
    log_info "Mode debug: $DEBUG_MODE"

    # Détection plateforme
    if [[ -f /proc/device-tree/model ]]; then
        local model=$(cat /proc/device-tree/model)
        log_success "Plateforme: $model"
    else
        log_info "Plateforme: $(uname -m) / $(uname -s)"
    fi

    # RAM
    if command -v free &>/dev/null; then
        local ram=$(free -m | awk '/^Mem:/{print $2}')
        log_info "RAM: ${ram}MB"
        log_debug "RAM détail: $(free -m | head -2)"
    fi

    # Disque
    local disk=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')
    log_info "Disque disponible: ${disk}GB"

    if [[ "$disk" -lt 3 ]]; then
        log_warning "Espace disque faible (<3GB)"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 1 : VÉRIFICATION PRÉREQUIS
# ═══════════════════════════════════════════════════════════════════════════
step_1_prerequisites() {
    log_step "1" "VÉRIFICATION DES PRÉREQUIS"

    local errors=0

    # Docker
    log_info "Vérification Docker..."
    if docker --version &>/dev/null; then
        local docker_ver=$(docker --version)
        log_success "Docker: $docker_ver"
        log_debug "Docker info: $(docker info 2>/dev/null | grep -E 'Server Version|Storage Driver' | head -2)"
    else
        log_error "Docker n'est pas installé!"
        log_info "Installation: curl -fsSL https://get.docker.com | sh"
        ((errors++))
    fi

    # Permissions Docker
    log_info "Vérification permissions Docker..."
    if docker ps &>/dev/null; then
        log_success "Permissions Docker OK"
    else
        log_error "Pas de permissions Docker pour $(whoami)"
        log_info "Exécutez: sudo usermod -aG docker $(whoami) && newgrp docker"
        ((errors++))
    fi

    # Docker Compose V2
    log_info "Vérification Docker Compose..."
    if docker compose version &>/dev/null; then
        local compose_ver=$(docker compose version --short)
        log_success "Docker Compose: $compose_ver"
    else
        log_error "Docker Compose V2 manquant!"
        log_info "Installation: sudo apt install docker-compose-plugin"
        ((errors++))
    fi

    # Fichier compose
    log_info "Vérification fichier compose..."
    if [[ -f "$COMPOSE_FILE" ]]; then
        log_success "Fichier compose: $COMPOSE_FILE"
        log_debug "Services définis: $(grep -E '^\s+\w+:$' "$COMPOSE_FILE" | head -10)"
    else
        log_error "Fichier $COMPOSE_FILE introuvable!"
        ((errors++))
    fi

    # Template .env
    log_info "Vérification template .env..."
    if [[ -f "$ENV_TEMPLATE" ]]; then
        log_success "Template: $ENV_TEMPLATE"
    else
        log_error "Template $ENV_TEMPLATE introuvable!"
        ((errors++))
    fi

    if [[ $errors -gt 0 ]]; then
        log_error "$errors erreur(s) de prérequis - Installation impossible"
        exit 1
    fi

    log_success "Tous les prérequis sont satisfaits"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 2 : CONFIGURATION SÉCURISÉE
# ═══════════════════════════════════════════════════════════════════════════
step_2_security_config() {
    log_step "2" "CONFIGURATION SÉCURISÉE (HARDENING)"

    # Création .env si absent
    if [[ ! -f "$ENV_FILE" ]]; then
        log_info "Création du fichier .env depuis le template..."
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        log_success "Fichier .env créé"
    else
        log_info "Fichier .env existant détecté"
        log_debug "Contenu .env (sans secrets): $(grep -E '^[A-Z_]+=' "$ENV_FILE" | grep -v -E 'PASSWORD|SECRET|KEY' | head -10)"
    fi

    # ─────────────────────────────────────────────────────────────────────
    # HARDENING: API_KEY
    # ─────────────────────────────────────────────────────────────────────
    log_info "Vérification API_KEY..."

    local current_api_key=$(grep -E "^API_KEY=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
    log_debug "API_KEY actuelle: ${current_api_key:0:10}..."

    if ! validate_key "$current_api_key" "API_KEY" 2>/dev/null; then
        log_warning "API_KEY invalide ou non sécurisée - Génération automatique"

        local new_api_key=$(generate_secure_key)
        log_debug "Nouvelle API_KEY générée: ${new_api_key:0:10}..."

        if grep -q "^API_KEY=" "$ENV_FILE"; then
            sed -i "s/^API_KEY=.*/API_KEY=$new_api_key/" "$ENV_FILE"
        else
            echo "API_KEY=$new_api_key" >> "$ENV_FILE"
        fi

        log_success "API_KEY sécurisée générée et enregistrée"
    else
        log_success "API_KEY valide"
    fi

    # ─────────────────────────────────────────────────────────────────────
    # HARDENING: JWT_SECRET
    # ─────────────────────────────────────────────────────────────────────
    log_info "Vérification JWT_SECRET..."

    local current_jwt=$(grep -E "^JWT_SECRET=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
    log_debug "JWT_SECRET actuel: ${current_jwt:0:10}..."

    if ! validate_key "$current_jwt" "JWT_SECRET" 2>/dev/null; then
        log_warning "JWT_SECRET invalide - Génération automatique"

        local new_jwt=$(generate_secure_key)

        if grep -q "^JWT_SECRET=" "$ENV_FILE"; then
            sed -i "s/^JWT_SECRET=.*/JWT_SECRET=$new_jwt/" "$ENV_FILE"
        else
            echo "JWT_SECRET=$new_jwt" >> "$ENV_FILE"
        fi

        log_success "JWT_SECRET sécurisé généré"
    else
        log_success "JWT_SECRET valide"
    fi

    # ─────────────────────────────────────────────────────────────────────
    # HARDENING: DASHBOARD CREDENTIALS
    # ─────────────────────────────────────────────────────────────────────
    log_info "Vérification credentials dashboard..."

    local dash_user=$(grep -E "^DASHBOARD_USER=" "$ENV_FILE" | cut -d'=' -f2-)
    local dash_pass=$(grep -E "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')

    if [[ -z "$dash_user" || "$dash_user" == "admin" ]]; then
        log_warning "DASHBOARD_USER non défini ou par défaut"
        echo -e -n "${CYAN}❓${NC} Nom d'utilisateur dashboard [admin]: "
        read -r new_user
        new_user="${new_user:-admin}"

        if grep -q "^DASHBOARD_USER=" "$ENV_FILE"; then
            sed -i "s/^DASHBOARD_USER=.*/DASHBOARD_USER=$new_user/" "$ENV_FILE"
        else
            echo "DASHBOARD_USER=$new_user" >> "$ENV_FILE"
        fi
        log_success "DASHBOARD_USER configuré: $new_user"
    fi

    if [[ -z "$dash_pass" || "$dash_pass" == "CHANGEZ_MOI"* || ${#dash_pass} -lt 8 ]]; then
        log_warning "DASHBOARD_PASSWORD non sécurisé"
        echo -e -n "${CYAN}❓${NC} Mot de passe dashboard (min 8 chars): "
        read -rs new_pass
        echo ""

        if [[ ${#new_pass} -lt 8 ]]; then
            log_error "Mot de passe trop court!"
            exit 1
        fi

        if grep -q "^DASHBOARD_PASSWORD=" "$ENV_FILE"; then
            sed -i "s/^DASHBOARD_PASSWORD=.*/DASHBOARD_PASSWORD=$new_pass/" "$ENV_FILE"
        else
            echo "DASHBOARD_PASSWORD=$new_pass" >> "$ENV_FILE"
        fi
        log_success "DASHBOARD_PASSWORD configuré"
    else
        log_success "DASHBOARD_PASSWORD valide"
    fi

    # Permissions sécurisées
    chmod 600 "$ENV_FILE"
    log_debug "Permissions .env: $(ls -la "$ENV_FILE")"

    log_success "Configuration sécurisée terminée"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 3 : PRÉPARATION DOSSIERS
# ═══════════════════════════════════════════════════════════════════════════
step_3_prepare_dirs() {
    log_step "3" "PRÉPARATION DES DOSSIERS"

    local dirs=("data" "logs" "config")

    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_success "Dossier créé: $dir/"
        else
            log_info "Dossier existant: $dir/"
        fi

        # Permissions pour Docker (UID 1000)
        chmod 755 "$dir" 2>/dev/null || true
        log_debug "Permissions $dir: $(ls -ld "$dir")"
    done

    # Config par défaut si manquant
    if [[ ! -f "config/config.yaml" ]]; then
        if [[ -f "config/config.yaml.example" ]]; then
            cp "config/config.yaml.example" "config/config.yaml"
            log_success "config.yaml copié depuis example"
        else
            log_warning "config/config.yaml absent - sera créé par le bot"
        fi
    else
        log_success "config/config.yaml présent"
    fi

    log_success "Dossiers préparés"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 4 : PULL DES IMAGES GHCR
# ═══════════════════════════════════════════════════════════════════════════
step_4_pull_images() {
    log_step "4" "TÉLÉCHARGEMENT DES IMAGES (GHCR)"

    log_info "Pull des images pré-construites depuis GitHub Container Registry..."
    log_debug "Compose file: $COMPOSE_FILE"

    # Arrêt des containers existants
    log_info "Arrêt des containers existants..."
    docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>&1 | tee -a "$LOG_FILE" || true

    # Pull des images
    log_info "Téléchargement des images (peut prendre quelques minutes)..."

    if docker compose -f "$COMPOSE_FILE" pull 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Images téléchargées avec succès"
    else
        log_error "Échec du téléchargement des images"
        log_info "Vérifiez votre connexion internet et les permissions GHCR"
        exit 1
    fi

    # Liste des images
    log_debug "Images Docker présentes:"
    docker images --format "{{.Repository}}:{{.Tag}} ({{.Size}})" | grep -E "linkedin|redis" | tee -a "$LOG_FILE" || true
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 5 : DÉMARRAGE SÉQUENTIEL
# ═══════════════════════════════════════════════════════════════════════════
step_5_start_services() {
    log_step "5" "DÉMARRAGE SÉQUENTIEL DES SERVICES"

    # ─────────────────────────────────────────────────────────────────────
    # 5.1 Redis Bot
    # ─────────────────────────────────────────────────────────────────────
    log_info "5.1 Démarrage redis-bot..."
    docker compose -f "$COMPOSE_FILE" up -d redis-bot 2>&1 | tee -a "$LOG_FILE"

    if wait_container_healthy "redis-bot" 60; then
        log_success "redis-bot démarré"
    else
        log_error "redis-bot n'a pas démarré correctement"
        exit 1
    fi

    # ─────────────────────────────────────────────────────────────────────
    # 5.2 Redis Dashboard
    # ─────────────────────────────────────────────────────────────────────
    log_info "5.2 Démarrage redis-dashboard..."
    docker compose -f "$COMPOSE_FILE" up -d redis-dashboard 2>&1 | tee -a "$LOG_FILE"

    if wait_container_healthy "redis-dashboard" 60; then
        log_success "redis-dashboard démarré"
    else
        log_error "redis-dashboard n'a pas démarré correctement"
        exit 1
    fi

    # ─────────────────────────────────────────────────────────────────────
    # 5.3 Bot API
    # ─────────────────────────────────────────────────────────────────────
    log_info "5.3 Démarrage bot-api..."
    log_debug "Vérification API_KEY avant démarrage..."

    # Vérification critique avant démarrage
    source "$ENV_FILE" 2>/dev/null || true
    if [[ "${API_KEY:-}" == "internal_secret_key" ]]; then
        log_error "CRITIQUE: API_KEY est toujours 'internal_secret_key'!"
        log_error "Le bot refusera de démarrer pour des raisons de sécurité."
        log_info "Exécutez: sed -i \"s/API_KEY=.*/API_KEY=\$(openssl rand -hex 32)/\" .env"
        exit 1
    fi

    docker compose -f "$COMPOSE_FILE" up -d api 2>&1 | tee -a "$LOG_FILE"

    echo -n "Attente bot-api "
    if wait_container_healthy "bot-api" 180; then
        echo ""
        log_success "bot-api démarré et healthy"
    else
        echo ""
        log_error "bot-api n'a pas démarré correctement"
        log_info "Diagnostic:"
        docker logs bot-api --tail 50 2>&1 | tee -a "$LOG_FILE"
        exit 1
    fi

    # ─────────────────────────────────────────────────────────────────────
    # 5.4 Bot Worker
    # ─────────────────────────────────────────────────────────────────────
    log_info "5.4 Démarrage bot-worker..."
    docker compose -f "$COMPOSE_FILE" up -d bot-worker 2>&1 | tee -a "$LOG_FILE"

    if wait_container_healthy "bot-worker" 120; then
        log_success "bot-worker démarré"
    else
        log_warning "bot-worker pas encore healthy (peut être normal)"
    fi

    # ─────────────────────────────────────────────────────────────────────
    # 5.5 Dashboard
    # ─────────────────────────────────────────────────────────────────────
    log_info "5.5 Démarrage dashboard..."
    docker compose -f "$COMPOSE_FILE" up -d dashboard 2>&1 | tee -a "$LOG_FILE"

    echo -n "Attente dashboard "
    if wait_container_healthy "dashboard" 180; then
        echo ""
        log_success "dashboard démarré"
    else
        echo ""
        log_warning "dashboard pas encore healthy - vérifiez les logs"
    fi

    log_success "Tous les services sont lancés"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 6 : VALIDATION FINALE
# ═══════════════════════════════════════════════════════════════════════════
step_6_validate() {
    log_step "6" "VALIDATION FINALE"

    echo ""
    log_info "État des containers:"
    docker compose -f "$COMPOSE_FILE" ps 2>&1 | tee -a "$LOG_FILE"

    echo ""
    log_info "Test de connectivité API..."

    # Test health endpoint
    local api_health=$(docker exec bot-api curl -sf http://localhost:8000/health 2>/dev/null || echo "FAIL")
    log_debug "API /health response: $api_health"

    if [[ "$api_health" != "FAIL" ]]; then
        log_success "API health check OK"
    else
        log_warning "API health check échoué - l'API peut encore démarrer"
    fi

    # Récupérer l'IP locale
    local local_ip=$(hostname -I | awk '{print $1}')
    local dashboard_port=$(grep -E "DASHBOARD_PORT=" "$ENV_FILE" | cut -d'=' -f2 || echo "3000")
    dashboard_port="${dashboard_port:-3000}"

    echo ""
    echo -e "${GREEN}${BOLD}"
    cat << EOF
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║                    ✅ INSTALLATION TERMINÉE                              ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    echo -e "📍 ${BOLD}Dashboard:${NC}      http://${local_ip}:${dashboard_port}"
    echo -e "📄 ${BOLD}Logs setup:${NC}     $LOG_FILE"
    echo -e "🔐 ${BOLD}Credentials:${NC}    Voir fichier .env"
    echo ""
    echo -e "${BOLD}Commandes utiles:${NC}"
    echo "  • Logs temps réel:   docker compose -f $COMPOSE_FILE logs -f"
    echo "  • Status:            docker compose -f $COMPOSE_FILE ps"
    echo "  • Redémarrer:        docker compose -f $COMPOSE_FILE restart"
    echo "  • Arrêter:           docker compose -f $COMPOSE_FILE down"
    echo ""

    log_success "Installation de base complète!"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 7 : HASHAGE BCRYPT DU MOT DE PASSE
# ═══════════════════════════════════════════════════════════════════════════
step_7_bcrypt_password() {
    log_step "7" "HASHAGE BCRYPT DU MOT DE PASSE"

    cat << 'EOF'
🔐 POURQUOI C'EST IMPORTANT ?
   Le mot de passe en clair dans .env peut être lu par quiconque accède au fichier.
   Avec bcrypt, le mot de passe est hashé de façon irréversible.

EOF

    # Vérifier si le mot de passe est déjà hashé
    local current_pass=$(grep -E "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')

    if [[ "$current_pass" =~ ^\$2[aby]\$ ]]; then
        log_success "Mot de passe déjà hashé avec bcrypt"
        return 0
    fi

    # Vérifier si Node.js est disponible
    if ! command -v node &>/dev/null; then
        log_warning "Node.js non disponible - hashage bcrypt ignoré"
        log_info "Pour hasher plus tard: cd dashboard && npm install bcryptjs && node scripts/hash_password.js"
        return 0
    fi

    # Vérifier si bcryptjs est installé
    if [[ ! -d "dashboard/node_modules/bcryptjs" ]]; then
        log_info "Installation de bcryptjs..."
        (cd dashboard && npm install bcryptjs --silent 2>/dev/null) || {
            log_warning "Impossible d'installer bcryptjs"
            return 0
        }
    fi

    # Vérifier si le script de hashage existe
    if [[ ! -f "dashboard/scripts/hash_password.js" ]]; then
        log_warning "Script hash_password.js non trouvé"
        return 0
    fi

    log_info "Hashage du mot de passe avec bcrypt..."

    # Générer le hash
    local password_hash
    password_hash=$(cd dashboard && node scripts/hash_password.js "$current_pass" --quiet 2>/dev/null) || {
        log_warning "Échec du hashage bcrypt"
        return 0
    }

    if [[ -z "$password_hash" || ! "$password_hash" =~ ^\$2 ]]; then
        log_warning "Hash invalide généré"
        return 0
    fi

    # Backup et mise à jour
    cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

    # Échapper le hash pour Docker Compose ($ -> $$)
    local escaped_hash="${password_hash//$/\$\$}"

    sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD='$escaped_hash'|" "$ENV_FILE"

    log_success "Mot de passe hashé avec bcrypt"
    log_debug "Hash: ${password_hash:0:20}..."

    # Redémarrer le dashboard pour appliquer
    log_info "Redémarrage du dashboard..."
    docker compose -f "$COMPOSE_FILE" restart dashboard 2>&1 | tee -a "$LOG_FILE" || true
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 8 : PROTECTION CORS
# ═══════════════════════════════════════════════════════════════════════════
step_8_cors_protection() {
    log_step "8" "PROTECTION CORS"

    cat << 'EOF'
🛡️ POURQUOI C'EST IMPORTANT ?
   CORS empêche des sites malveillants d'accéder à votre API.
   Sans CORS, n'importe quel site pourrait faire des requêtes à votre bot.

EOF

    # Vérifier si ALLOWED_ORIGINS est déjà configuré
    if grep -q "^ALLOWED_ORIGINS=" "$ENV_FILE" 2>/dev/null; then
        local current_origins=$(grep "^ALLOWED_ORIGINS=" "$ENV_FILE" | cut -d'=' -f2-)
        if [[ -n "$current_origins" && "$current_origins" != "http://localhost:3000" ]]; then
            log_success "CORS déjà configuré: $current_origins"
            return 0
        fi
    fi

    # Récupérer l'IP locale
    local local_ip=$(hostname -I | awk '{print $1}')
    local dashboard_port=$(grep -E "^DASHBOARD_PORT=" "$ENV_FILE" | cut -d'=' -f2 || echo "3000")
    dashboard_port="${dashboard_port:-3000}"

    echo -e -n "${CYAN}❓${NC} Domaine pour CORS (ex: https://monbot.com) [http://${local_ip}:${dashboard_port}]: "
    read -r cors_domain
    cors_domain="${cors_domain:-http://${local_ip}:${dashboard_port}}"

    # Mettre à jour .env
    if grep -q "^ALLOWED_ORIGINS=" "$ENV_FILE"; then
        sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=$cors_domain|" "$ENV_FILE"
    else
        echo "ALLOWED_ORIGINS=$cors_domain" >> "$ENV_FILE"
    fi

    log_success "CORS configuré: $cors_domain"

    # Redémarrer l'API
    log_info "Redémarrage de l'API..."
    docker compose -f "$COMPOSE_FILE" restart api 2>&1 | tee -a "$LOG_FILE" || true
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 9 : ANTI-INDEXATION
# ═══════════════════════════════════════════════════════════════════════════
step_9_anti_indexation() {
    log_step "9" "ANTI-INDEXATION GOOGLE"

    cat << 'EOF'
🚫 POURQUOI C'EST IMPORTANT ?
   Sans protection, Google peut indexer votre dashboard.
   N'importe qui pourrait trouver votre bot en cherchant sur Google.

EOF

    # Créer robots.txt si absent
    local robots_file="dashboard/public/robots.txt"

    if [[ -f "$robots_file" ]] && grep -q "Disallow: /" "$robots_file"; then
        log_success "robots.txt déjà configuré"
    else
        mkdir -p "dashboard/public"
        cat > "$robots_file" << 'ROBOTS'
# LinkedIn Birthday Bot - Anti-indexation
User-agent: *
Disallow: /
Disallow: /api/
Disallow: /login
Disallow: /dashboard

# Block all known bots
User-agent: Googlebot
Disallow: /

User-agent: Bingbot
Disallow: /

User-agent: Slurp
Disallow: /

User-agent: DuckDuckBot
Disallow: /

User-agent: Baiduspider
Disallow: /

User-agent: YandexBot
Disallow: /
ROBOTS
        log_success "robots.txt créé"
    fi

    # Vérifier les headers X-Robots-Tag dans next.config.js
    if [[ -f "dashboard/next.config.js" ]]; then
        if grep -q "X-Robots-Tag" "dashboard/next.config.js"; then
            log_success "Headers X-Robots-Tag déjà configurés dans Next.js"
        else
            log_info "Ajout recommandé: headers X-Robots-Tag dans next.config.js"
        fi
    fi

    log_success "Anti-indexation configurée"
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 10 : HTTPS AVEC LET'S ENCRYPT (OPTIONNEL)
# ═══════════════════════════════════════════════════════════════════════════
step_10_https_letsencrypt() {
    log_step "10" "HTTPS AVEC LET'S ENCRYPT"

    cat << 'EOF'
🔐 POURQUOI C'EST IMPORTANT ?
   Sans HTTPS, vos mots de passe circulent en CLAIR sur Internet.
   HTTPS chiffre toutes les communications.

⚠️  PRÉREQUIS :
   • Nom de domaine pointant vers votre IP publique
   • Ports 80 et 443 ouverts sur votre box/routeur
   • Accès root/sudo

EOF

    if ! ask_continue "Configurer HTTPS avec Let's Encrypt ?"; then
        log_info "Configuration HTTPS ignorée"
        return 0
    fi

    # Vérifier si Nginx est installé
    if ! command -v nginx &>/dev/null; then
        log_info "Installation de Nginx..."
        sudo apt update && sudo apt install -y nginx || {
            log_error "Impossible d'installer Nginx"
            return 1
        }
    fi
    log_success "Nginx installé"

    # Vérifier si Certbot est installé
    if ! command -v certbot &>/dev/null; then
        log_info "Installation de Certbot..."
        sudo apt install -y certbot python3-certbot-nginx || {
            log_error "Impossible d'installer Certbot"
            return 1
        }
    fi
    log_success "Certbot installé"

    # Demander le nom de domaine
    echo -e -n "${CYAN}❓${NC} Votre nom de domaine (ex: bot.exemple.com): "
    read -r domain_name

    if [[ -z "$domain_name" ]]; then
        log_error "Nom de domaine requis"
        return 1
    fi

    # Créer la configuration Nginx
    log_info "Configuration de Nginx pour $domain_name..."

    local nginx_conf="/etc/nginx/sites-available/linkedin-bot"
    sudo tee "$nginx_conf" > /dev/null << NGINX
# LinkedIn Birthday Bot - Nginx Configuration
# Generated by setup_simplified.sh

server {
    listen 80;
    server_name $domain_name;

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}

server {
    listen 443 ssl http2;
    server_name $domain_name;

    # SSL will be configured by Certbot

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Robots-Tag "noindex, nofollow" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Dashboard (Next.js)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

    # Activer le site
    sudo ln -sf "$nginx_conf" /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

    # Tester la configuration
    if ! sudo nginx -t; then
        log_error "Configuration Nginx invalide"
        return 1
    fi

    sudo systemctl reload nginx
    log_success "Nginx configuré"

    # Obtenir le certificat SSL
    log_info "Obtention du certificat SSL (Let's Encrypt)..."
    log_info "Assurez-vous que le port 80 est accessible depuis Internet"

    if sudo certbot --nginx -d "$domain_name" --non-interactive --agree-tos --register-unsafely-without-email; then
        log_success "Certificat SSL installé!"
        log_info "Accès sécurisé: https://$domain_name"

        # Mettre à jour ALLOWED_ORIGINS
        sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://$domain_name|" "$ENV_FILE"
        docker compose -f "$COMPOSE_FILE" restart api 2>&1 | tee -a "$LOG_FILE" || true
    else
        log_error "Échec de l'obtention du certificat"
        log_info "Vérifiez que:"
        log_info "  1. Le domaine $domain_name pointe vers votre IP"
        log_info "  2. Le port 80 est ouvert sur votre box"
        log_info "  3. Réessayez: sudo certbot --nginx -d $domain_name"
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE 11 : BACKUP GOOGLE DRIVE (OPTIONNEL)
# ═══════════════════════════════════════════════════════════════════════════
step_11_gdrive_backup() {
    log_step "11" "BACKUP AUTOMATIQUE GOOGLE DRIVE"

    cat << 'EOF'
💾 POURQUOI C'EST IMPORTANT ?
   Sans backup, si votre serveur plante, vous perdez TOUT.
   Le backup Google Drive sauvegarde automatiquement chaque nuit.

⚠️  PRÉREQUIS :
   • Compte Google
   • Possibilité d'ouvrir un navigateur (ou configuration headless)

EOF

    if ! ask_continue "Configurer le backup Google Drive ?"; then
        log_info "Configuration backup ignorée"
        return 0
    fi

    # Vérifier si rclone est installé
    if ! command -v rclone &>/dev/null; then
        log_info "Installation de rclone..."
        curl https://rclone.org/install.sh | sudo bash || {
            log_error "Impossible d'installer rclone"
            return 1
        }
    fi
    log_success "rclone installé"

    # Vérifier si Google Drive est déjà configuré
    if rclone listremotes 2>/dev/null | grep -q "gdrive:"; then
        log_success "Google Drive déjà configuré dans rclone"

        if ask_continue "Tester la connexion Google Drive ?"; then
            if rclone lsd gdrive: &>/dev/null; then
                log_success "Connexion Google Drive OK"
            else
                log_warning "Connexion échouée - reconfigurez avec: rclone config"
            fi
        fi
    else
        log_info "Configuration de Google Drive..."
        cat << 'INSTRUCTIONS'

📱 INSTRUCTIONS RCLONE :
   1. Tapez: gdrive (comme nom)
   2. Tapez: drive (comme storage)
   3. Appuyez Entrée pour client_id et client_secret (vide)
   4. Tapez: 1 pour scope (Full access)
   5. Appuyez Entrée pour service_account_file (vide)
   6. Tapez: n pour advanced config
   7. Tapez: y pour auto authenticate (si navigateur disponible)
   8. Autorisez dans le navigateur
   9. Tapez: n pour team drive
   10. Tapez: y pour confirmer

INSTRUCTIONS

        if ask_continue "Lancer la configuration rclone maintenant ?"; then
            rclone config

            if rclone listremotes | grep -q "gdrive:"; then
                log_success "Google Drive configuré!"
            else
                log_warning "Configuration incomplète"
                return 1
            fi
        fi
    fi

    # Vérifier le script de backup
    local backup_script="scripts/backup_to_gdrive.sh"

    if [[ ! -f "$backup_script" ]]; then
        log_info "Création du script de backup..."
        mkdir -p scripts
        cat > "$backup_script" << 'BACKUP'
#!/bin/bash
# Backup LinkedIn Bot vers Google Drive

set -e

BACKUP_DIR="LinkedInBot_Backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${DATE}"

echo "[$(date)] Démarrage du backup..."

# Créer le dossier distant si nécessaire
rclone mkdir "gdrive:${BACKUP_DIR}" 2>/dev/null || true

# Backup des données
rclone copy ./data "gdrive:${BACKUP_DIR}/${BACKUP_NAME}/data" --progress
rclone copy ./config "gdrive:${BACKUP_DIR}/${BACKUP_NAME}/config" --progress
rclone copy ./.env "gdrive:${BACKUP_DIR}/${BACKUP_NAME}/" --progress 2>/dev/null || true

# Nettoyer les backups > 30 jours
rclone delete "gdrive:${BACKUP_DIR}" --min-age 30d 2>/dev/null || true

echo "[$(date)] Backup terminé: ${BACKUP_NAME}"
BACKUP
        chmod +x "$backup_script"
        log_success "Script de backup créé"
    fi

    # Tester le backup
    if ask_continue "Tester le backup maintenant ?"; then
        log_info "Exécution du backup de test..."
        if bash "$backup_script"; then
            log_success "Backup de test réussi!"
        else
            log_warning "Backup échoué - vérifiez la configuration rclone"
        fi
    fi

    # Configurer le cron
    log_info "Configuration du backup automatique (cron)..."

    local cron_line="0 3 * * * $(pwd)/$backup_script >> /var/log/linkedin-bot-backup.log 2>&1"

    if crontab -l 2>/dev/null | grep -q "backup_to_gdrive.sh"; then
        log_success "Backup automatique déjà configuré"
    else
        if ask_continue "Activer le backup automatique quotidien (3h du matin) ?"; then
            (crontab -l 2>/dev/null; echo "$cron_line") | crontab -
            log_success "Backup automatique configuré"
            log_info "Logs: /var/log/linkedin-bot-backup.log"
        fi
    fi
}

# ═══════════════════════════════════════════════════════════════════════════
# ÉTAPE FINALE : RÉSUMÉ SÉCURITÉ
# ═══════════════════════════════════════════════════════════════════════════
step_final_security_summary() {
    log_step "✓" "RÉSUMÉ DE SÉCURITÉ"

    echo ""
    log_info "Vérification de la configuration sécurité..."
    echo ""

    local score=0
    local max_score=6

    # 1. API_KEY
    local api_key=$(grep -E "^API_KEY=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
    if [[ ${#api_key} -ge 32 && "$api_key" != "internal_secret_key"* ]]; then
        echo -e "  ${GREEN}✓${NC} API_KEY sécurisée"
        ((score++))
    else
        echo -e "  ${RED}✗${NC} API_KEY non sécurisée"
    fi

    # 2. JWT_SECRET
    local jwt=$(grep -E "^JWT_SECRET=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
    if [[ ${#jwt} -ge 32 ]]; then
        echo -e "  ${GREEN}✓${NC} JWT_SECRET sécurisé"
        ((score++))
    else
        echo -e "  ${RED}✗${NC} JWT_SECRET non sécurisé"
    fi

    # 3. Password hashé
    local pass=$(grep -E "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d'=' -f2- | tr -d "'" | tr -d '"')
    if [[ "$pass" =~ ^\$2 ]]; then
        echo -e "  ${GREEN}✓${NC} Mot de passe hashé (bcrypt)"
        ((score++))
    else
        echo -e "  ${YELLOW}~${NC} Mot de passe en clair"
    fi

    # 4. CORS
    local cors=$(grep -E "^ALLOWED_ORIGINS=" "$ENV_FILE" | cut -d'=' -f2-)
    if [[ -n "$cors" && "$cors" != "http://localhost:3000" ]]; then
        echo -e "  ${GREEN}✓${NC} CORS configuré: $cors"
        ((score++))
    else
        echo -e "  ${YELLOW}~${NC} CORS par défaut (localhost)"
    fi

    # 5. robots.txt
    if [[ -f "dashboard/public/robots.txt" ]] && grep -q "Disallow: /" "dashboard/public/robots.txt"; then
        echo -e "  ${GREEN}✓${NC} Anti-indexation (robots.txt)"
        ((score++))
    else
        echo -e "  ${YELLOW}~${NC} Anti-indexation non configurée"
    fi

    # 6. HTTPS
    if command -v certbot &>/dev/null && sudo certbot certificates 2>/dev/null | grep -q "Certificate Name:"; then
        echo -e "  ${GREEN}✓${NC} HTTPS (Let's Encrypt)"
        ((score++))
    else
        echo -e "  ${YELLOW}~${NC} HTTPS non configuré"
    fi

    echo ""
    echo -e "${BOLD}Score sécurité: ${score}/${max_score}${NC}"

    if [[ $score -ge 5 ]]; then
        echo -e "${GREEN}🔒 Excellent! Configuration très sécurisée.${NC}"
    elif [[ $score -ge 3 ]]; then
        echo -e "${YELLOW}🔓 Correct. Quelques améliorations possibles.${NC}"
    else
        echo -e "${RED}⚠️  Attention! Configuration à améliorer.${NC}"
    fi

    echo ""
    log_success "Consultez $LOG_FILE pour les détails complets."
}

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
main() {
    print_banner
    log_init

    log_info "Démarrage de l'installation..."
    log_info "Pour activer le mode debug: DEBUG=true ./setup_simplified.sh"
    echo ""

    if ! ask_continue "Démarrer l'installation ?"; then
        log_info "Installation annulée par l'utilisateur"
        exit 0
    fi

    # ─────────────────────────────────────────────────────────────────────
    # PHASE 1: Installation de base
    # ─────────────────────────────────────────────────────────────────────
    step_0_init
    step_1_prerequisites
    step_2_security_config
    step_3_prepare_dirs

    if ! ask_continue "Télécharger les images et démarrer les services ?"; then
        log_info "Déploiement annulé - Configuration sauvegardée"
        log_info "Pour reprendre: docker compose -f $COMPOSE_FILE up -d"
        exit 0
    fi

    step_4_pull_images
    step_5_start_services
    step_6_validate

    # ─────────────────────────────────────────────────────────────────────
    # PHASE 2: Sécurisation avancée (optionnel)
    # ─────────────────────────────────────────────────────────────────────
    echo ""
    echo -e "${MAGENTA}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}${BOLD}  PHASE 2 : SÉCURISATION AVANCÉE (Optionnel)${NC}"
    echo -e "${MAGENTA}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    cat << 'EOF'
La sécurisation avancée comprend :
  • Hashage bcrypt du mot de passe
  • Protection CORS
  • Anti-indexation Google
  • HTTPS avec Let's Encrypt
  • Backup automatique Google Drive

EOF

    if ask_continue "Continuer avec la sécurisation avancée ?"; then
        step_7_bcrypt_password
        step_8_cors_protection
        step_9_anti_indexation

        if ask_continue "Configurer HTTPS (nécessite un nom de domaine) ?"; then
            step_10_https_letsencrypt
        fi

        if ask_continue "Configurer le backup Google Drive ?"; then
            step_11_gdrive_backup
        fi

        step_final_security_summary
    else
        log_info "Sécurisation avancée ignorée"
        log_info "Pour la configurer plus tard: ./scripts/setup_security.sh"
    fi

    # ─────────────────────────────────────────────────────────────────────
    # FIN
    # ─────────────────────────────────────────────────────────────────────
    echo ""
    echo -e "${GREEN}${BOLD}"
    cat << EOF
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║                    🎉 INSTALLATION COMPLÈTE                              ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    local local_ip=$(hostname -I | awk '{print $1}')
    local dashboard_port=$(grep -E "^DASHBOARD_PORT=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "3000")

    echo -e "📍 ${BOLD}Dashboard:${NC}      http://${local_ip}:${dashboard_port:-3000}"
    echo -e "📄 ${BOLD}Logs setup:${NC}     $LOG_FILE"
    echo -e "🔐 ${BOLD}Credentials:${NC}    Fichier .env"
    echo ""
    echo -e "${BOLD}Commandes utiles:${NC}"
    echo "  • Logs:        docker compose -f $COMPOSE_FILE logs -f"
    echo "  • Status:      docker compose -f $COMPOSE_FILE ps"
    echo "  • Redémarrer:  docker compose -f $COMPOSE_FILE restart"
    echo "  • Arrêter:     docker compose -f $COMPOSE_FILE down"
    echo ""
}

# Lancer le script
main "$@"
