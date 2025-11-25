#!/bin/bash

# =========================================================================
# Script de déploiement OPTIMISÉ pour Raspberry Pi 4 (4GB)
# Architecture: Standalone (Bot + Dashboard + Redis + SQLite)
# =========================================================================

set -e  # Arrêt immédiat en cas d'erreur

# --- Configuration ---
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
ENV_FILE=".env"
ENV_TEMPLATE=".env.pi4"
MIN_RAM_MB=3500
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
# 1. Vérifications Système Approfondies
# =========================================================================
print_header "1. Vérifications Système"

# Vérification de l'emplacement
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "Fichier $COMPOSE_FILE introuvable !"
    print_info "Exécutez ce script à la racine du projet."
    exit 1
fi

# Vérification Docker & Compose V2
if docker compose version &> /dev/null; then
    print_success "Docker Compose V2 détecté"
else
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
    print_warning "Le build Docker risque d'échouer."
    read -p "Continuer quand même ? [y/N] " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
else
    print_success "Espace disque OK (${DISK_AVAIL}GB)"
fi

# Vérification & Gestion du SWAP (CRITIQUE pour Next.js build)
SWAP_TOTAL=$(free -m | awk '/Swap:/ {print $2}')
print_info "SWAP Actif: ${SWAP_TOTAL}MB"

if [ "$SWAP_TOTAL" -lt "$MIN_SWAP_MB" ]; then
    print_warning "SWAP Actif insuffisant (${SWAP_TOTAL}MB) pour compiler le Dashboard."

    SWAP_CONFIG_SIZE=$(grep -oP '^CONF_SWAPSIZE=\K\d+' /etc/dphys-swapfile || echo 0)

    if [ "$SWAP_CONFIG_SIZE" -lt "$MIN_SWAP_MB" ]; then
        print_error "Le SWAP est mal configuré (/etc/dphys-swapfile)."
        print_info "Veuillez le reconfigurer et l'activer avec les commandes suivantes :"
        echo "  sudo dphys-swapfile swapoff"
        echo "  sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile"
        echo "  sudo dphys-swapfile setup"
        echo "  sudo dphys-swapfile swapon"
        exit 1
    else
        print_error "Le SWAP est configuré mais pas actif."
        print_info "Veuillez l'activer avec la commande : sudo dphys-swapfile swapon"
        exit 1
    fi
else
    print_success "Swap suffisant pour la compilation."
fi

# =========================================================================
# 2. Configuration Environnement & Fichiers
# =========================================================================
print_header "2. Configuration Environnement"

# Gestion .env
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_TEMPLATE" ]; then
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        print_success "Fichier .env créé depuis le template"
        # Sécurisation basique d'une clé secrète si elle est vide
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 32)/" "$ENV_FILE"
    else
        print_error "Template .env.pi4 introuvable !"
        exit 1
    fi
fi

# Création structure dossiers
mkdir -p data logs config

# Gestion des permissions CRITIQUE pour SQLite dans Docker
print_info "Application des permissions pour SQLite..."
chmod 777 data logs
touch data/linkedin.db
chmod 666 data/linkedin.db 2>/dev/null || true

# Vérification fichiers requis
for file in "auth_state.json" "config/config.yaml"; do
    if [ ! -f "$file" ]; then
        print_warning "Manquant: $file (Le bot en aura besoin au démarrage)"
        touch "$file" # Crée un fichier vide pour éviter que Docker ne crée un dossier
    fi
done

# =========================================================================
# 3. Patching Automatique (Dashboard)
# =========================================================================
print_header "3. Vérification Code Source"

mkdir -p dashboard/lib

# Patch utils.ts
if [ ! -f "dashboard/lib/utils.ts" ]; then
    print_info "Création dashboard/lib/utils.ts..."
    cat > "dashboard/lib/utils.ts" << 'EOF'
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
EOF
fi

# Patch puppet-master.ts
if [ ! -f "dashboard/lib/puppet-master.ts" ]; then
    print_info "Création dashboard/lib/puppet-master.ts..."
    cat > "dashboard/lib/puppet-master.ts" << 'EOF'
export interface BotTask { id: string; type: string; payload: any; timestamp: number; }
export interface BotStatus { state: 'IDLE' | 'WORKING' | 'COOLDOWN' | 'ERROR' | 'STARTING' | 'STOPPING'; currentTask?: string; lastActive: number; }
class PuppetMaster {
  private status: BotStatus = { state: 'IDLE', lastActive: Date.now() };
  async getStatus(): Promise<BotStatus> { return this.status; }
  async killSwitch(): Promise<void> { this.status.state = 'STOPPING'; setTimeout(() => { this.status.state = 'IDLE'; }, 2000); }
  async startTask(task: BotTask): Promise<void> { this.status.state = 'WORKING'; this.status.currentTask = task.type; }
}
export const puppetMaster = new PuppetMaster();
EOF
fi

print_success "Dépendances du dashboard vérifiées"

# =========================================================================
# 4. Nettoyage Préalable
# =========================================================================
print_header "4. Nettoyage"

print_info "Arrêt des conteneurs existants..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans || true

# =========================================================================
# 5. Construction des Images (Build)
# =========================================================================
print_header "5. Construction (Patience... ~15-20 min)"

export DOCKER_BUILDKIT=1

print_info "[1/3] Pull des images de base..."
docker compose -f "$COMPOSE_FILE" pull

print_info "[2/3] Build Bot Worker..."
if docker compose -f "$COMPOSE_FILE" build bot-worker; then
    print_success "Bot Worker construit."
else
    print_error "Échec build Bot Worker."
    exit 1
fi

sleep 5

print_info "[3/3] Build Dashboard (C'est le plus long)..."
export NPM_CONFIG_TIMEOUT=600000
if docker compose -f "$COMPOSE_FILE" build dashboard; then
    print_success "Dashboard construit."
else
    print_error "Échec build Dashboard."
    print_warning "Vérifiez le SWAP si cela a échoué."
    exit 1
fi

print_info "Nettoyage des images intermédiaires..."
docker image prune -f > /dev/null 2>&1 || true

# =========================================================================
# 6. Démarrage
# =========================================================================
print_header "6. Démarrage des Services"

if docker compose -f "$COMPOSE_FILE" up -d; then
    print_success "Conteneurs lancés."
else
    print_error "Erreur au lancement."
    exit 1
fi

print_info "Attente de l'initialisation (30s)..."
for i in {1..30}; do echo -n "."; sleep 1; done
echo ""

# =========================================================================
# 7. Vérification Finale
# =========================================================================
print_header "7. Vérification État"

check_service() {
    local service_name=$1
    local container_id
    container_id=$(docker compose -f "$COMPOSE_FILE" ps -q "$service_name")

    if [ -n "$container_id" ]; then
        local state
        state=$(docker inspect --format='{{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "running")
        echo -e "  • $service_name: ${GREEN}UP${NC} (Health: $state)"
    else
        echo -e "  • $service_name: ${RED}DOWN${NC}"
        return 1
    fi
}

check_service "bot-worker"
check_service "dashboard"
check_service "redis-bot"
check_service "redis-dashboard"

LOCAL_IP=$(hostname -I | awk '{print $1}')

print_header "🚀 DÉPLOIEMENT TERMINÉ AVEC SUCCÈS"
echo -e "
📍 \033[1mAccès Dashboard :\033[0m http://${LOCAL_IP}:3000
📂 \033[1mBase de données :\033[0m ./data/linkedin.db
📄 \033[1mLogs :\033[0m           docker compose -f $COMPOSE_FILE logs -f

\033[1mNote :\033[0m Si le dashboard affiche une erreur 500 au début, attendez
encore 1-2 minutes que Next.js finisse son premier démarrage/compilation.
"
