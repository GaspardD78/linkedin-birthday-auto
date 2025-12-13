#!/bin/bash

# =========================================================================
# Script de déploiement pour Raspberry Pi 4 (Production)
# Architecture: Standalone (Bot + Dashboard + Redis + SQLite)
# =========================================================================

set -e  # Arrêt immédiat en cas d'erreur

# --- Configuration ---
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"
ENV_TEMPLATE=".env.pi4.example"
MIN_SWAP_MB=2000
MIN_DISK_GB=5

# --- Couleurs ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Fonctions ---

print_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }

# =========================================================================
# 1. Vérifications Système
# =========================================================================
print_header "1. Vérifications Système"

# Vérification Docker & Compose V2
if ! docker compose version &> /dev/null; then
    print_error "Docker Compose V2 non trouvé. (Essayez: sudo apt install docker-compose-plugin)"
    exit 1
fi

# Vérification Permissions Docker
if ! docker ps &> /dev/null; then
    print_error "L'utilisateur actuel n'a pas les droits Docker."
    print_info "Exécutez: sudo usermod -aG docker $USER (puis redémarrez)"
    exit 1
fi

# Vérification Espace Disque
DISK_AVAIL=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')
if [ "$DISK_AVAIL" -lt "$MIN_DISK_GB" ]; then
    print_warning "Espace disque faible: ${DISK_AVAIL}GB (Recommandé: ${MIN_DISK_GB}GB+)"
fi

# Vérification & Gestion du SWAP (Next.js runtime sur Pi4 peut être gourmand)
SWAP_TOTAL=$(free -m | awk '/Swap:/ {print $2}')
print_info "SWAP Actif: ${SWAP_TOTAL}MB"

if [ "$SWAP_TOTAL" -lt "$MIN_SWAP_MB" ]; then
    print_warning "SWAP Actif faible (${SWAP_TOTAL}MB). Recommandé: 2048MB+"
    print_info "Pour augmenter le swap sur Pi4:"
    echo "  sudo dphys-swapfile swapoff"
    echo "  sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile"
    echo "  sudo dphys-swapfile setup && sudo dphys-swapfile swapon"
    # On ne bloque pas le déploiement car on ne build plus, on pull juste
else
    print_success "Swap OK."
fi

# =========================================================================
# 2. Configuration Environnement (.env)
# =========================================================================
print_header "2. Configuration Environnement"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_TEMPLATE" ]; then
        print_info "Création automatique du fichier .env..."
        cp "$ENV_TEMPLATE" "$ENV_FILE"

        # Génération automatique de valeurs sécurisées
        SECRET_KEY=$(openssl rand -hex 32)
        API_KEY=$(openssl rand -hex 32)
        JWT_SECRET=$(openssl rand -hex 32)

        # IP Locale pour info
        LOCAL_IP=$(hostname -I | awk '{print $1}')

        # Remplacement / Ajout des clés
        # Note: on utilise sed avec séparateur | pour éviter les soucis avec les /

        # SECRET_KEY (Flask/Django legacy or internal)
        if grep -q "SECRET_KEY" "$ENV_FILE"; then
            sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" "$ENV_FILE"
        else
            echo "SECRET_KEY=$SECRET_KEY" >> "$ENV_FILE"
        fi

        # API_KEY (Communication Bot <-> Dashboard)
        if grep -q "API_KEY" "$ENV_FILE"; then
             sed -i "s|^API_KEY=.*|API_KEY=$API_KEY|" "$ENV_FILE"
        else
             echo "API_KEY=$API_KEY" >> "$ENV_FILE"
        fi

        # JWT_SECRET (Auth Dashboard)
        if grep -q "JWT_SECRET" "$ENV_FILE"; then
             sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$JWT_SECRET|" "$ENV_FILE"
        else
             echo "JWT_SECRET=$JWT_SECRET" >> "$ENV_FILE"
        fi

        print_success "Fichier .env créé."
        print_info "IP locale détectée: $LOCAL_IP"
        print_warning "Vérifiez .env pour configurer DASHBOARD_USER/PASSWORD"
    else
        print_error "Template $ENV_TEMPLATE introuvable !"
        exit 1
    fi
else
    print_success "Fichier .env existant détecté"
fi

# =========================================================================
# 3. Préparation Dossiers & Permissions
# =========================================================================
print_header "3. Préparation Dossiers"

# Création dossiers requis
for dir in data logs config; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "Dossier $dir créé"
    fi
done

# Permissions (Critique pour SQLite/Logs dans Docker)
# On tente chmod sans sudo, sinon on prévient
print_info "Application permissions (777 sur data/ logs/ pour Docker)..."
chmod 777 data logs config 2>/dev/null || print_warning "Impossible de faire chmod 777 (non-root?). Assurez-vous que l'utilisateur Docker peut écrire dans data/ et logs/"

# Fichier DB vide si inexistant (pour éviter que Docker le crée en tant que dossier)
if [ ! -f "data/linkedin.db" ]; then
    touch data/linkedin.db 2>/dev/null || true
    chmod 666 data/linkedin.db 2>/dev/null || true
fi

# Création fichiers vides pour volumes (évite erreurs de montage)
for file in "auth_state.json" "config/config.yaml"; do
    if [ ! -f "$file" ]; then
        if [ "$file" == "auth_state.json" ]; then
            echo "{}" > "$file"
        else
            touch "$file"
        fi
        chmod 666 "$file" 2>/dev/null || true
    fi
done

# =========================================================================
# 4. Déploiement (Pull & Up)
# =========================================================================
print_header "4. Déploiement (Pull & Start)"

if [ ! -f "$COMPOSE_FILE" ]; then
    # Fallback si le fichier a été renommé mais le script pas à jour
    if [ -f "docker-compose.pi4-standalone.yml" ]; then
        COMPOSE_FILE="docker-compose.pi4-standalone.yml"
    else
        print_error "Fichier Compose introuvable ($COMPOSE_FILE)"
        exit 1
    fi
fi

print_info "Fichier Compose utilisé: $COMPOSE_FILE"

print_info "Arrêt des conteneurs existants..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans || true

print_info "Téléchargement des images (Pull)..."
docker compose -f "$COMPOSE_FILE" pull

print_info "Démarrage des services..."
docker compose -f "$COMPOSE_FILE" up -d

# =========================================================================
# 5. Vérification Santé (Wait Loop)
# =========================================================================
print_header "5. Vérification Santé"

wait_for_service() {
    local service=$1
    local max_retries=30 # 30 * 2s = 60s max
    local count=0

    echo -n "Attente de $service..."
    while [ $count -lt $max_retries ]; do
        status=$(docker compose -f "$COMPOSE_FILE" ps -q "$service" | xargs docker inspect -f '{{.State.Health.Status}}' 2>/dev/null || echo "starting")
        if [ "$status" == "healthy" ]; then
            echo -e " ${GREEN}OK${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        count=$((count+1))
    done
    echo -e " ${RED}TIMEOUT${NC}"
    return 1
}

# On attend Redis d'abord
wait_for_service "redis-bot"
wait_for_service "redis-dashboard"
# Puis l'API
wait_for_service "api"
# Le worker et le dashboard peuvent prendre plus de temps
print_info "Vérification des autres services (asynchrone)..."

docker compose -f "$COMPOSE_FILE" ps

LOCAL_IP=$(hostname -I | awk '{print $1}')
echo -e "
🚀 \033[1mDÉPLOIEMENT TERMINÉ\033[0m

📍 \033[1mDashboard :\033[0m      http://${LOCAL_IP}:3000
📂 \033[1mLogs :\033[0m           docker compose -f $COMPOSE_FILE logs -f
"
