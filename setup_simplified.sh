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

    log_success "Installation complète! Consultez $LOG_FILE pour les détails."
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
}

# Lancer le script
main "$@"
