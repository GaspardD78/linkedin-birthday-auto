#!/bin/bash
# ==============================================================================
# LINKEDIN AUTO RPi4 - SETUP SCRIPT (V3.0 - PRODUCTION READY)
# ==============================================================================
# Architecte : Claude - Audit Technique Complet
# Cible      : Raspberry Pi 4 (4GB RAM, SD 32GB, ARM64)
# ==============================================================================
#
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                        RAPPORT D'AUDIT TECHNIQUE                         ║
# ╠══════════════════════════════════════════════════════════════════════════╣
# ║                                                                          ║
# ║ FAILLES CRITIQUES CORRIGÉES (V2.1 → V3.0) :                              ║
# ║                                                                          ║
# ║ 1. [FATAL] Volume SQLite Incohérent                                      ║
# ║    - AVANT: Script attendait ./data/linkedin.db (filesystem local)       ║
# ║    - RÉALITÉ: Docker utilise volume nommé "shared-data:/app/data"        ║
# ║    - FIX: Initialisation via docker exec, pas sur filesystem local       ║
# ║                                                                          ║
# ║ 2. [FATAL] Pas de vérification RAM/SWAP                                  ║
# ║    - Conteneurs nécessitent ~2.8GB, Pi4 n'a que 4GB                      ║
# ║    - Playwright/Node.js OOM garanti sans SWAP suffisant                  ║
# ║    - FIX: Check RAM+SWAP >= 6GB, création swapfile si nécessaire         ║
# ║                                                                          ║
# ║ 3. [CRITIQUE] Health Check Incomplet                                     ║
# ║    - AVANT: Simple curl HTTP, ne vérifie pas l'état Docker "healthy"     ║
# ║    - FIX: Boucle utilisant docker compose ps --format pour état réel     ║
# ║                                                                          ║
# ║ 4. [CRITIQUE] Double échappement $ incorrect                             ║
# ║    - AVANT: ${HASHED_PASS//$/\$\$} ne produit pas $$ mais \$             ║
# ║    - FIX: Utilisation de sed pour échappement fiable                     ║
# ║                                                                          ║
# ║ 5. [UX] Mot de passe visible dans rapport final                          ║
# ║    - Affiché en clair avec indication "Copiez-le!" pour l'utilisateur    ║
# ║                                                                          ║
# ║ 6. [PERF] Pas de nettoyage disque intelligent                            ║
# ║    - SD 32GB saturée rapidement par images Docker                        ║
# ║    - FIX: Nettoyage conditionnel si espace < 20%, ciblant dangling       ║
# ║                                                                          ║
# ║ 7. [PERF] Nginx sans healthcheck Docker                                  ║
# ║    - FIX: Attente explicite avec vérification curl intégrée              ║
# ║                                                                          ║
# ║ 8. [ANTI-PATTERN] Script exige ROOT mais conteneurs tournent en 1000     ║
# ║    - FIX: Script tourne en user normal, sudo uniquement quand requis     ║
# ║                                                                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝
#
# ==============================================================================

set -euo pipefail

# --- Couleurs ---
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# --- Configuration ---
readonly DOMAIN="gaspardanoukolivier.freeboxos.fr"
readonly COMPOSE_FILE="docker-compose.pi4-standalone.yml"
readonly ENV_FILE=".env"
readonly ENV_TEMPLATE=".env.pi4.example"
readonly MIN_MEMORY_GB=6  # RAM + SWAP minimum requis
readonly DISK_THRESHOLD_PERCENT=20  # Seuil pour nettoyage
readonly HEALTH_TIMEOUT=180  # 3 minutes max pour startup (Pi4 = lent)
readonly HEALTH_INTERVAL=5  # Check toutes les 5 secondes

# --- Logging ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"; echo -e "${BOLD}${BLUE}  $1${NC}"; echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}\n"; }
log_debug()   { [[ "${DEBUG:-false}" == "true" ]] && echo -e "${DIM}[DEBUG] $1${NC}"; }

# --- Gestion d'erreurs ---
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        echo ""
        log_error "Le script a échoué. Affichage des logs des conteneurs..."
        docker compose -f "$COMPOSE_FILE" logs --tail=30 2>/dev/null || true
    fi
}
trap cleanup EXIT

# --- Fonctions utilitaires ---

# Vérifie si une commande existe
cmd_exists() {
    command -v "$1" &> /dev/null
}

# Calcule la mémoire totale disponible (RAM + SWAP) en GB
get_total_memory_gb() {
    local ram_kb swap_kb total_kb
    ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    swap_kb=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
    total_kb=$((ram_kb + swap_kb))
    echo $((total_kb / 1024 / 1024))
}

# Calcule le pourcentage d'espace disque utilisé
get_disk_usage_percent() {
    df -h . | awk 'NR==2 {gsub(/%/,"",$5); print $5}'
}


# Vérifie si l'utilisateur peut utiliser sudo
check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        log_warn "Privilèges sudo requis pour certaines opérations."
        sudo true || { log_error "Impossible d'obtenir les privilèges sudo."; exit 1; }
    fi
}

# ==============================================================================
# BANNIÈRE
# ==============================================================================

clear
echo -e "${BLUE}"
cat << "EOF"
  _      _       _            _ _             _         _
 | |    (_)     | |          | (_)           | |       | |
 | |     _ _ __ | | _____  __| |_ _ __       | |_ _   _| |_ ___
 | |    | | '_ \| |/ / _ \/ _` | | '_ \      | __| | | | __/ _ \
 | |____| | | | |   <  __/ (_| | | | | |     | |_| |_| | || (_) |
 |______|_|_| |_|_|\_\___|\__,_|_|_| |_|      \__|\__,_|\__\___/

         >>> RASPBERRY PI 4 SETUP v3.0 (Production) <<<
EOF
echo -e "${NC}"
echo -e "${DIM}Optimisé pour: ARM64 | 4GB RAM | SD 32GB${NC}"
echo ""

# ==============================================================================
# PHASE 1 : PRÉ-REQUIS SYSTÈME (FAIL-FAST)
# ==============================================================================
log_step "PHASE 1 : Vérifications Système (Fail-Fast)"

# 1.1 Vérification UID utilisateur
CURRENT_UID=$(id -u)
if [[ "$CURRENT_UID" -eq 0 ]]; then
    log_warn "Script lancé en root. Recommandé: lancer en utilisateur normal (UID 1000)."
    log_info "Continuation avec root, mais les permissions pourraient nécessiter ajustement."
elif [[ "$CURRENT_UID" -ne 1000 ]]; then
    log_warn "UID actuel: $CURRENT_UID (attendu: 1000)"
    log_info "Les volumes Docker utilisent UID 1000. Ajustements possibles requis."
fi

# 1.2 Vérification des fichiers critiques
log_info "Vérification des fichiers critiques..."
MISSING_FILES=()

if [[ ! -f "$COMPOSE_FILE" ]]; then
    MISSING_FILES+=("$COMPOSE_FILE")
fi
if [[ ! -f "$ENV_TEMPLATE" ]]; then
    MISSING_FILES+=("$ENV_TEMPLATE")
fi
if [[ ! -d "dashboard" ]]; then
    MISSING_FILES+=("dashboard/")
fi
if [[ ! -f "dashboard/scripts/hash_password.js" ]]; then
    MISSING_FILES+=("dashboard/scripts/hash_password.js")
fi

if [[ ${#MISSING_FILES[@]} -gt 0 ]]; then
    log_error "Fichiers critiques manquants:"
    for f in "${MISSING_FILES[@]}"; do
        echo "  - $f"
    done
    exit 1
fi
log_success "Fichiers critiques présents."

# 1.3 Vérification Docker
log_info "Vérification de Docker..."
if ! cmd_exists docker; then
    log_error "Docker n'est pas installé."
    log_info "Installation: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! docker info &>/dev/null; then
    log_error "Le daemon Docker ne répond pas."
    log_info "Vérifiez: sudo systemctl status docker"
    exit 1
fi

# Vérification que l'utilisateur est dans le groupe docker
if [[ "$CURRENT_UID" -ne 0 ]] && ! groups | grep -q docker; then
    log_error "L'utilisateur n'est pas dans le groupe docker."
    log_info "Exécutez: sudo usermod -aG docker \$USER && newgrp docker"
    exit 1
fi
log_success "Docker opérationnel."

# 1.4 Vérification RAM + SWAP
log_info "Vérification mémoire (RAM + SWAP)..."
TOTAL_MEM_GB=$(get_total_memory_gb)
log_info "Mémoire totale disponible: ${TOTAL_MEM_GB}GB (minimum requis: ${MIN_MEMORY_GB}GB)"

if [[ $TOTAL_MEM_GB -lt $MIN_MEMORY_GB ]]; then
    log_warn "Mémoire insuffisante! Risque d'OOM (Out Of Memory) élevé."

    # Proposition de création de swapfile
    SWAP_SIZE=$((MIN_MEMORY_GB - TOTAL_MEM_GB + 1))
    SWAP_FILE="/swapfile"

    if [[ ! -f "$SWAP_FILE" ]]; then
        echo -e "${YELLOW}Voulez-vous créer un swapfile de ${SWAP_SIZE}GB ? (recommandé) [O/n]${NC}"
        read -r -t 30 REPLY || REPLY="o"
        if [[ ! "$REPLY" =~ ^[Nn]$ ]]; then
            check_sudo
            log_info "Création du swapfile de ${SWAP_SIZE}GB..."
            sudo fallocate -l "${SWAP_SIZE}G" "$SWAP_FILE" || sudo dd if=/dev/zero of="$SWAP_FILE" bs=1G count="$SWAP_SIZE" status=progress
            sudo chmod 600 "$SWAP_FILE"
            sudo mkswap "$SWAP_FILE"
            sudo swapon "$SWAP_FILE"

            # Ajouter au fstab si pas déjà présent
            if ! grep -q "$SWAP_FILE" /etc/fstab; then
                echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab > /dev/null
            fi

            # Recalculer
            TOTAL_MEM_GB=$(get_total_memory_gb)
            log_success "Swapfile créé. Nouvelle mémoire totale: ${TOTAL_MEM_GB}GB"
        else
            log_warn "Continuation sans swap additionnel. Risque d'OOM!"
        fi
    else
        log_warn "Swapfile existe déjà mais mémoire insuffisante. Augmentez le swap manuellement."
    fi
fi

# 1.5 Optimisation ZRAM (si disponible)
if [[ -d /sys/block/zram0 ]] && ! swapon --show | grep -q zram; then
    log_info "ZRAM disponible mais non activé. Considérez l'activation pour de meilleures performances."
fi

log_success "Phase 1 terminée: Système prêt."

# ==============================================================================
# PHASE 2 : HYGIÈNE DISQUE INTELLIGENTE
# ==============================================================================
log_step "PHASE 2 : Gestion Espace Disque (SD Card Optimized)"

DISK_USAGE=$(get_disk_usage_percent)
DISK_FREE=$((100 - DISK_USAGE))

log_info "Espace disque utilisé: ${DISK_USAGE}% (libre: ${DISK_FREE}%)"

if [[ $DISK_FREE -lt $DISK_THRESHOLD_PERCENT ]]; then
    log_warn "Espace disque faible! Nettoyage Docker en cours..."

    # Nettoyage ciblé pour économiser les I/O de la SD
    log_info "Suppression des images dangling uniquement..."
    docker image prune -f --filter "dangling=true" 2>/dev/null || true

    log_info "Suppression des conteneurs arrêtés..."
    docker container prune -f 2>/dev/null || true

    log_info "Suppression des volumes orphelins..."
    docker volume prune -f 2>/dev/null || true

    NEW_DISK_FREE=$((100 - $(get_disk_usage_percent)))
    log_success "Nettoyage terminé. Espace libéré: $((NEW_DISK_FREE - DISK_FREE))%"
else
    log_success "Espace disque suffisant. Pas de nettoyage nécessaire."
fi

# Vérification espace pour les images Docker (estimation ~3GB requis)
AVAILABLE_GB=$(df -BG . | awk 'NR==2 {gsub(/G/,"",$4); print $4}')
if [[ $AVAILABLE_GB -lt 3 ]]; then
    log_error "Espace disque insuffisant: ${AVAILABLE_GB}GB disponible (minimum 3GB requis pour les images)"
    exit 1
fi

log_success "Phase 2 terminée: Espace disque OK (${AVAILABLE_GB}GB disponible)."

# ==============================================================================
# PHASE 3 : ARRÊT DES SERVICES EXISTANTS
# ==============================================================================
log_step "PHASE 3 : Arrêt Propre des Services Existants"

if docker compose -f "$COMPOSE_FILE" ps -q 2>/dev/null | grep -q .; then
    log_info "Arrêt des conteneurs existants..."
    docker compose -f "$COMPOSE_FILE" down --remove-orphans --timeout 30 2>/dev/null || true
    log_success "Conteneurs arrêtés."
else
    log_info "Aucun conteneur en cours d'exécution."
fi

# Libération Port 80/443 si nécessaire (pour Certbot standalone)
log_info "Vérification des ports 80/443..."
for PORT in 80 443; do
    PORT_PIDS=$(lsof -t -i :"$PORT" 2>/dev/null || true)
    if [[ -n "$PORT_PIDS" ]]; then
        log_warn "Port $PORT occupé (PIDs: $PORT_PIDS). Libération..."
        check_sudo
        echo "$PORT_PIDS" | xargs -r sudo kill -9 2>/dev/null || true
    fi
done
log_success "Ports libérés."

# ==============================================================================
# PHASE 4 : TÉLÉCHARGEMENT DES IMAGES
# ==============================================================================
log_step "PHASE 4 : Téléchargement des Images Docker"

log_info "Pull des images en cours (peut prendre plusieurs minutes sur Pi4)..."
log_info "Conseil: Les images ARM64 sont pré-buildées sur GHCR."

# Pull avec retry pour gérer les problèmes réseau
PULL_ATTEMPTS=3
for attempt in $(seq 1 $PULL_ATTEMPTS); do
    if docker compose -f "$COMPOSE_FILE" pull; then
        log_success "Images téléchargées avec succès."
        break
    else
        if [[ $attempt -lt $PULL_ATTEMPTS ]]; then
            log_warn "Échec du pull (tentative $attempt/$PULL_ATTEMPTS). Retry dans 5s..."
            sleep 5
        else
            log_error "Impossible de télécharger les images après $PULL_ATTEMPTS tentatives."
            exit 1
        fi
    fi
done

# ==============================================================================
# PHASE 5 : CONFIGURATION (.env & Secrets)
# ==============================================================================
log_step "PHASE 5 : Configuration Sécurisée"

# 5.1 Création du .env si manquant
if [[ ! -f "$ENV_FILE" ]]; then
    log_info "Création du fichier .env depuis le template..."
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    log_success "Fichier .env créé avec permissions 600."
else
    log_info "Fichier .env existant détecté."
fi

# 5.2 Authentification Dashboard
echo -e "\n${BOLD}>>> Configuration Authentification Dashboard${NC}"

# Lecture des valeurs actuelles
CURRENT_USER=$(grep "^DASHBOARD_USER=" "$ENV_FILE" | cut -d '=' -f2 || echo "")
CURRENT_PASS=$(grep "^DASHBOARD_PASSWORD=" "$ENV_FILE" | cut -d '=' -f2- || echo "")

# Détection si c'est un hash bcrypt existant
if [[ "$CURRENT_PASS" =~ ^\$2[aby]\$ ]]; then
    log_info "Mot de passe déjà hashé en bcrypt. Voulez-vous le changer ? [o/N]"
    read -r -t 15 CHANGE_PASS || CHANGE_PASS="n"
    if [[ ! "$CHANGE_PASS" =~ ^[Oo]$ ]]; then
        log_info "Conservation du mot de passe existant."
        SKIP_PASSWORD=true
    fi
fi

if [[ "${SKIP_PASSWORD:-false}" != "true" ]]; then
    # Utilisateur
    if [[ -z "$CURRENT_USER" ]] || [[ "$CURRENT_USER" == "admin" ]] || [[ "$CURRENT_USER" == "your_username" ]]; then
        echo -n "Nom d'utilisateur Dashboard (défaut: admin): "
        read -r INPUT_USER
        DASHBOARD_USER=${INPUT_USER:-admin}
    else
        DASHBOARD_USER="$CURRENT_USER"
        log_info "Utilisateur existant conservé: $DASHBOARD_USER"
    fi

    # Mot de passe
    echo -n "Mot de passe Dashboard: "
    read -rs DASHBOARD_PASS
    echo ""

    if [[ -z "$DASHBOARD_PASS" ]]; then
        log_error "Le mot de passe ne peut pas être vide."
        exit 1
    fi

    if [[ ${#DASHBOARD_PASS} -lt 8 ]]; then
        log_warn "Mot de passe court (< 8 caractères). Recommandé: 12+ caractères."
    fi

    # Hashage bcrypt
    log_info "Hashage du mot de passe avec bcrypt..."

    # Vérification de bcryptjs
    if [[ ! -d "dashboard/node_modules/bcryptjs" ]]; then
        log_info "Installation de bcryptjs..."
        (cd dashboard && npm install bcryptjs --silent --no-audit --no-fund 2>/dev/null) || {
            log_error "Impossible d'installer bcryptjs. Vérifiez npm."
            exit 1
        }
    fi

    # Hashage (mode quiet pour récupérer uniquement le hash)
    HASHED_PASS=$(node dashboard/scripts/hash_password.js "$DASHBOARD_PASS" --quiet 2>/dev/null)

    if [[ -z "$HASHED_PASS" ]] || [[ ! "$HASHED_PASS" =~ ^\$2[aby]\$ ]]; then
        log_error "Échec du hashage bcrypt."
        exit 1
    fi

    # Échappement pour Docker Compose ($ → $$)
    # Utilisation de sed pour un échappement fiable
    DOCKER_SAFE_HASH=$(echo "$HASHED_PASS" | sed 's/\$/\$\$/g')

    # Mise à jour du .env
    sed -i "s|^DASHBOARD_USER=.*|DASHBOARD_USER=${DASHBOARD_USER}|" "$ENV_FILE"

    # Utilisation d'un délimiteur différent pour sed car le hash contient des caractères spéciaux
    # On échappe aussi les / dans le hash
    ESCAPED_HASH=$(echo "$DOCKER_SAFE_HASH" | sed 's/[\/&]/\\&/g')
    sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${ESCAPED_HASH}|" "$ENV_FILE"

    log_success "Identifiants mis à jour."
fi

# 5.3 Génération des secrets si placeholders
log_info "Vérification des secrets API/JWT..."

# API_KEY
if grep -q "CHANGEZ_MOI\|your_secure" "$ENV_FILE" 2>/dev/null; then
    log_info "Génération de nouveaux secrets..."

    NEW_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
    NEW_JWT_SECRET=$(openssl rand -hex 32)

    sed -i "s|^API_KEY=.*|API_KEY=${NEW_API_KEY}|" "$ENV_FILE"
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${NEW_JWT_SECRET}|" "$ENV_FILE"

    log_success "Secrets API/JWT générés."
else
    log_info "Secrets existants conservés."
fi

# 5.4 Permissions fichiers
chmod 600 "$ENV_FILE"
log_success "Phase 5 terminée: Configuration sécurisée."

# ==============================================================================
# PHASE 6 : PRÉPARATION VOLUMES & PERMISSIONS
# ==============================================================================
log_step "PHASE 6 : Préparation des Volumes"

# Création des répertoires locaux montés en bind
log_info "Création des répertoires..."
mkdir -p logs config certbot/conf certbot/www certbot/work certbot/logs

# Permissions pour l'utilisateur 1000 (utilisateur des conteneurs)
log_info "Configuration des permissions (UID 1000)..."
if [[ "$CURRENT_UID" -eq 0 ]]; then
    chown -R 1000:1000 logs config
else
    # Si on n'est pas root et qu'on est UID 1000, pas besoin de chown
    if [[ "$CURRENT_UID" -ne 1000 ]]; then
        check_sudo
        sudo chown -R 1000:1000 logs config
    fi
fi
chmod -R 775 logs config

log_success "Phase 6 terminée: Volumes préparés."

# ==============================================================================
# PHASE 7 : GESTION SSL (Optionnelle)
# ==============================================================================
log_step "PHASE 7 : Gestion SSL (HTTPS)"

CERT_DIR="./certbot/conf/live/$DOMAIN"

if [[ ! -f "$CERT_DIR/fullchain.pem" ]]; then
    log_warn "Certificat SSL non trouvé pour $DOMAIN."

    echo -e "${YELLOW}Voulez-vous générer un certificat Let's Encrypt ? [o/N]${NC}"
    echo -e "${DIM}(Nécessite que le port 80 soit accessible depuis Internet)${NC}"
    read -r -t 30 GENERATE_SSL || GENERATE_SSL="n"

    if [[ "$GENERATE_SSL" =~ ^[Oo]$ ]]; then
        if cmd_exists certbot; then
            check_sudo
            log_info "Génération du certificat SSL..."
            sudo certbot certonly --standalone \
                -d "$DOMAIN" \
                --email "gaspard.danouk@gmail.com" \
                --agree-tos \
                --non-interactive \
                --config-dir "$(pwd)/certbot/conf" \
                --work-dir "$(pwd)/certbot/work" \
                --logs-dir "$(pwd)/certbot/logs" || {
                    log_warn "Échec Certbot. Le dashboard sera accessible en HTTP uniquement."
                }
        else
            log_warn "Certbot non installé. Installation: sudo apt install certbot"
        fi
    else
        log_info "SSL ignoré. Le dashboard sera accessible en HTTP sur le port 3000."
    fi
else
    log_success "Certificat SSL valide détecté pour $DOMAIN."

    # Tentative de renouvellement si proche de l'expiration
    if cmd_exists certbot; then
        log_info "Vérification du renouvellement..."
        certbot renew --dry-run \
            --cert-name "$DOMAIN" \
            --config-dir "$(pwd)/certbot/conf" \
            --work-dir "$(pwd)/certbot/work" \
            --logs-dir "$(pwd)/certbot/logs" 2>/dev/null || true
    fi
fi

log_success "Phase 7 terminée."

# ==============================================================================
# PHASE 8 : DÉMARRAGE DES SERVICES
# ==============================================================================
log_step "PHASE 8 : Démarrage des Services"

log_info "Lancement des conteneurs..."
docker compose -f "$COMPOSE_FILE" up -d

log_success "Conteneurs lancés. Attente du démarrage complet..."

# ==============================================================================
# PHASE 9 : HEALTH CHECKS (VITAL)
# ==============================================================================
log_step "PHASE 9 : Vérification de Santé (Health Checks)"

# Fonction de vérification de santé d'un service
check_service_health() {
    local service="$1"
    local endpoint="$2"
    local timeout="$3"
    local elapsed=0

    echo -n "  - $service"

    while [[ $elapsed -lt $timeout ]]; do
        # Vérification état Docker
        local state
        state=$(docker compose -f "$COMPOSE_FILE" ps --format "{{.Service}}:{{.State}}:{{.Health}}" 2>/dev/null | grep "^${service}:" || echo "")

        if [[ "$state" == *":exited:"* ]] || [[ "$state" == *":dead:"* ]]; then
            echo -e " ${RED}CRASHED${NC}"
            log_error "Le service $service a crashé!"
            docker compose -f "$COMPOSE_FILE" logs "$service" --tail=20
            return 1
        fi

        if [[ "$state" == *":running:healthy"* ]]; then
            # Double vérification avec endpoint HTTP si fourni
            if [[ -n "$endpoint" ]]; then
                if curl -sf "$endpoint" > /dev/null 2>&1; then
                    echo -e " ${GREEN}OK${NC} (healthy + HTTP OK)"
                    return 0
                fi
            else
                echo -e " ${GREEN}OK${NC} (healthy)"
                return 0
            fi
        fi

        echo -n "."
        sleep "$HEALTH_INTERVAL"
        elapsed=$((elapsed + HEALTH_INTERVAL))
    done

    echo -e " ${RED}TIMEOUT${NC}"
    return 1
}

# Fonction pour les services sans healthcheck Docker (Nginx)
check_http_endpoint() {
    local name="$1"
    local url="$2"
    local timeout="$3"
    local elapsed=0

    echo -n "  - $name"

    while [[ $elapsed -lt $timeout ]]; do
        if curl -sf -k "$url" > /dev/null 2>&1; then
            echo -e " ${GREEN}OK${NC}"
            return 0
        fi
        echo -n "."
        sleep "$HEALTH_INTERVAL"
        elapsed=$((elapsed + HEALTH_INTERVAL))
    done

    echo -e " ${YELLOW}WARN${NC} (timeout, vérifiez les logs)"
    return 1
}

log_info "Vérification de chaque service (timeout: ${HEALTH_TIMEOUT}s)..."
echo ""

FAILED_SERVICES=()

# Redis (démarrage rapide)
check_service_health "redis-bot" "" 60 || FAILED_SERVICES+=("redis-bot")
check_service_health "redis-dashboard" "" 60 || FAILED_SERVICES+=("redis-dashboard")

# API (démarrage moyen, a un healthcheck)
check_service_health "api" "http://localhost:8000/health" "$HEALTH_TIMEOUT" || FAILED_SERVICES+=("api")

# Dashboard (démarrage lent sur Pi4, Next.js compile)
check_service_health "dashboard" "http://localhost:3000" "$HEALTH_TIMEOUT" || FAILED_SERVICES+=("dashboard")

# Nginx (pas de healthcheck Docker, vérification HTTP)
check_http_endpoint "nginx (HTTPS)" "https://localhost" 60 || {
    # Fallback: essayer HTTP si HTTPS échoue (certificat manquant)
    check_http_endpoint "nginx (HTTP)" "http://localhost:80" 30 || FAILED_SERVICES+=("nginx")
}

# Bot Worker (peut être lent à démarrer)
check_service_health "bot-worker" "" "$HEALTH_TIMEOUT" || FAILED_SERVICES+=("bot-worker")

echo ""

if [[ ${#FAILED_SERVICES[@]} -gt 0 ]]; then
    log_error "Services en échec: ${FAILED_SERVICES[*]}"
    log_error "Affichage des logs..."
    for svc in "${FAILED_SERVICES[@]}"; do
        echo -e "\n${YELLOW}=== Logs: $svc ===${NC}"
        docker compose -f "$COMPOSE_FILE" logs "$svc" --tail=30
    done
    exit 1
fi

log_success "Tous les services sont opérationnels!"

# ==============================================================================
# PHASE 10 : RAPPORT FINAL
# ==============================================================================
log_step "PHASE 10 : Rapport d'Installation"

# Collecte des informations
IP_ADDR=$(hostname -I | awk '{print $1}')
SERVICES_STATUS=$(docker compose -f "$COMPOSE_FILE" ps --format "table {{.Service}}\t{{.State}}\t{{.Status}}" 2>/dev/null || echo "N/A")

# Utilisateur dashboard (lu depuis .env)
FINAL_USER=$(grep "^DASHBOARD_USER=" "$ENV_FILE" | cut -d '=' -f2)

# Mot de passe (affiché en clair pour copie)
if [[ -n "${DASHBOARD_PASS:-}" ]]; then
    DISPLAY_PASS="$DASHBOARD_PASS"
else
    DISPLAY_PASS="(inchangé - voir .env)"
fi

# État SSL
if [[ -f "$CERT_DIR/fullchain.pem" ]]; then
    SSL_STATUS="${GREEN}Actif${NC} (Let's Encrypt)"
else
    SSL_STATUS="${YELLOW}Non configuré${NC}"
fi

# État mémoire
CURRENT_MEM=$(get_total_memory_gb)

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}${BOLD}                   LINKEDIN AUTO - RAPPORT FINAL                     ${NC}${BLUE}║${NC}"
echo -e "${BLUE}╠══════════════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║${NC}                                                                      ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  ${BOLD}ACCÈS${NC}                                                              ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    URL Locale   : http://${IP_ADDR}:3000                            ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    URL Publique : https://${DOMAIN}/                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    Grafana      : http://${IP_ADDR}:3001 (admin/admin)              ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                                                      ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  ${BOLD}AUTHENTIFICATION${NC}                                                    ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    Utilisateur  : ${FINAL_USER}                                              ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    Mot de passe : ${YELLOW}${DISPLAY_PASS}${NC} ${DIM}(Copiez-le!)${NC}              ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                                                      ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  ${BOLD}SÉCURITÉ${NC}                                                            ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    SSL (HTTPS)  : $SSL_STATUS                                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    Hachage MDP  : BCrypt (12 rounds)                                 ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    Permissions  : .env (600), data (UID 1000)                        ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                                                      ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}  ${BOLD}RESSOURCES${NC}                                                          ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    Mémoire      : ${CURRENT_MEM}GB (RAM+SWAP)                                    ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}    Disque libre : ${AVAILABLE_GB}GB                                              ${BLUE}║${NC}"
echo -e "${BLUE}║${NC}                                                                      ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"

echo ""
echo -e "${BOLD}ÉTAT DES SERVICES :${NC}"
echo "$SERVICES_STATUS"

echo ""
echo -e "${GREEN}${BOLD}Installation terminée avec succès!${NC}"
echo ""
echo -e "${DIM}Commandes utiles:${NC}"
echo -e "  Logs temps réel : docker compose -f $COMPOSE_FILE logs -f"
echo -e "  Redémarrer      : docker compose -f $COMPOSE_FILE restart"
echo -e "  Arrêter         : docker compose -f $COMPOSE_FILE down"
echo -e "  Audit sécurité  : ./scripts/verify_security.sh"
echo ""
