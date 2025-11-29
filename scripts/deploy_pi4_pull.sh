#!/bin/bash

# =========================================================================
# Script de déploiement RAPIDE pour Raspberry Pi 4 (4GB)
# Architecture: Standalone (Bot + Dashboard + Redis + SQLite)
# Mode: Pull images pré-construites depuis GitHub Container Registry
#
# Avantages vs build local:
# - Déploiement en ~2-3 minutes (vs 25-30 minutes)
# - Zéro usure de la carte SD
# - Zéro consommation RAM pendant le déploiement
# - Images buildées par GitHub Actions avec optimisations
# =========================================================================

set -e  # Arrêt immédiat en cas d'erreur

# --- Configuration ---
COMPOSE_FILE="docker-compose.pi4-standalone.yml"
ENV_FILE=".env"
ENV_TEMPLATE=".env.pi4.example"
MIN_DISK_GB=3

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
    read -p "Continuer quand même ? [y/N] " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
else
    print_success "Espace disque OK (${DISK_AVAIL}GB)"
fi

# =========================================================================
# 2. Configuration Environnement & Fichiers
# =========================================================================
print_header "2. Configuration Environnement"

# Gestion .env avec création automatique intelligente
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_TEMPLATE" ]; then
        print_info "Création automatique du fichier .env..."
        cp "$ENV_TEMPLATE" "$ENV_FILE"

        # Génération automatique de valeurs
        SECRET_KEY=$(openssl rand -hex 32)
        LOCAL_IP=$(hostname -I | awk '{print $1}')

        # Ajout de la SECRET_KEY si le template l'utilise
        if grep -q "SECRET_KEY" "$ENV_FILE"; then
            sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" "$ENV_FILE"
        else
            echo "SECRET_KEY=$SECRET_KEY" >> "$ENV_FILE"
        fi

        # Génération API_KEY pour sécuriser la com API <-> Dashboard
        API_KEY=$(openssl rand -hex 32)
        if grep -q "API_KEY" "$ENV_FILE"; then
             sed -i "s/API_KEY=.*/API_KEY=$API_KEY/" "$ENV_FILE"
        else
             echo "API_KEY=$API_KEY" >> "$ENV_FILE"
        fi

        # Mise à jour de l'IP du Pi4 si présente dans le template
        if grep -q "# PI4_IP=" "$ENV_FILE"; then
            sed -i "s/# PI4_IP=.*/PI4_IP=$LOCAL_IP/" "$ENV_FILE"
        fi

        print_success "Fichier .env créé avec configuration automatique"
        print_info "IP locale détectée: $LOCAL_IP"
        print_info "SECRET_KEY générée automatiquement"
        print_warning "Vérifiez le fichier .env pour personnaliser la configuration si nécessaire"
    else
        print_error "Template $ENV_TEMPLATE introuvable !"
        exit 1
    fi
else
    print_success "Fichier .env existant détecté"

    # Vérifier si la SECRET_KEY existe et est définie
    if ! grep -q "^SECRET_KEY=.\+" "$ENV_FILE"; then
        print_warning "SECRET_KEY manquante ou vide dans .env"
        SECRET_KEY=$(openssl rand -hex 32)
        if grep -q "SECRET_KEY=" "$ENV_FILE"; then
            sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" "$ENV_FILE"
        else
            echo "SECRET_KEY=$SECRET_KEY" >> "$ENV_FILE"
        fi
        print_success "SECRET_KEY générée et ajoutée"
    fi
fi

# Création structure dossiers avec permissions appropriées
print_info "Création/vérification des dossiers requis..."
for dir in data logs config; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "Dossier $dir créé"
    fi
done

# Gestion des permissions CRITIQUE pour SQLite dans Docker
print_info "Application des permissions pour SQLite..."

# Vérifier et corriger les permissions des dossiers
for dir in data logs; do
    if [ -d "$dir" ]; then
        # Essayer de changer les permissions, sinon utiliser sudo
        if ! chmod 777 "$dir" 2>/dev/null; then
            print_warning "Permissions insuffisantes pour $dir, utilisation de sudo..."
            if command -v sudo &> /dev/null; then
                sudo chmod 777 "$dir" || print_error "Impossible de modifier les permissions de $dir"
            else
                print_error "sudo non disponible, les permissions de $dir ne peuvent pas être modifiées"
                print_info "Essayez manuellement : sudo chmod 777 $dir"
            fi
        fi
    fi
done

# Créer le fichier de base de données avec les bonnes permissions
if [ ! -f "data/linkedin.db" ]; then
    touch data/linkedin.db 2>/dev/null || true
fi
chmod 666 data/linkedin.db 2>/dev/null || sudo chmod 666 data/linkedin.db 2>/dev/null || true

# Vérification fichiers requis
for file in "auth_state.json" "config/config.yaml"; do
    if [ ! -f "$file" ]; then
        print_warning "Manquant: $file (Le bot en aura besoin au démarrage)"
        if [ "$file" == "auth_state.json" ]; then
            echo "{}" > "$file" # Crée un JSON valide vide
        else
            touch "$file" # Crée un fichier vide pour éviter que Docker ne crée un dossier
        fi
    fi
done

# =========================================================================
# 3. Authentification GitHub Container Registry (optionnel)
# =========================================================================
print_header "3. Configuration Registry"

print_info "Les images seront téléchargées depuis GitHub Container Registry (GHCR)"
print_info "Pour les repos publics, aucune authentification n'est requise."
print_info "Si vous rencontrez des erreurs 403/401, créez un token GitHub:"
print_info "  1. https://github.com/settings/tokens/new"
print_info "  2. Cochez 'read:packages'"
print_info "  3. docker login ghcr.io -u VOTRE_USERNAME"
echo ""

# =========================================================================
# 4. Nettoyage Préalable
# =========================================================================
print_header "4. Nettoyage"

print_info "Arrêt des conteneurs existants..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans || true

# =========================================================================
# 5. Pull des Images Pré-construites
# =========================================================================
print_header "5. Téléchargement Images (2-3 minutes)"

export DOCKER_BUILDKIT=1

print_info "Pull des images depuis GitHub Container Registry..."
if docker compose -f "$COMPOSE_FILE" pull; then
    print_success "Images téléchargées avec succès"
else
    print_error "Échec du téléchargement des images"
    print_warning "Vérifiez:"
    print_warning "  - Connexion internet active"
    print_warning "  - Images publiées sur GHCR (vérifiez GitHub Actions)"
    print_warning "  - Permissions du repo (public ou token configuré)"
    exit 1
fi

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
encore 1-2 minutes que Next.js finisse son premier démarrage.

⚡ \033[1mDéploiement rapide réussi!\033[0m
   Temps gagné vs build local: ~25 minutes
   Usure carte SD évitée: ✅
"
