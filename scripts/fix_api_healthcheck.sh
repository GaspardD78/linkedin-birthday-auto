#!/bin/bash

# =========================================================================
# Script de correction du healthcheck bot-api
# Ce script modifie le healthcheck pour ne pas dépendre de curl
# =========================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }

COMPOSE_FILE="docker-compose.pi4-standalone.yml"
BACKUP_FILE="${COMPOSE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

print_header "Correction du healthcheck bot-api"

# 1. Sauvegarde
print_info "Création d'une sauvegarde: $BACKUP_FILE"
cp "$COMPOSE_FILE" "$BACKUP_FILE"
print_success "Sauvegarde créée"

# 2. Remplacement du healthcheck par une version Python (toujours disponible)
print_info "Modification du healthcheck pour utiliser Python au lieu de curl..."

# Utiliser Python pour remplacer le healthcheck
python3 << 'EOF'
import re

with open('docker-compose.pi4-standalone.yml', 'r') as f:
    content = f.read()

# Remplacer le healthcheck de l'API pour utiliser Python au lieu de curl
old_healthcheck = r'''    healthcheck:
      test: \["CMD", "curl", "-f", "http://localhost:8000/health"\]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s'''

new_healthcheck = '''    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s'''

content = re.sub(old_healthcheck, new_healthcheck, content)

with open('docker-compose.pi4-standalone.yml', 'w') as f:
    f.write(content)

print("✓ Healthcheck modifié avec succès")
EOF

print_success "Healthcheck corrigé (utilise Python au lieu de curl)"
print_info "start_period augmenté à 60s pour laisser plus de temps au démarrage"
print_info "retries augmenté à 5 pour plus de résilience"

# 3. Redéploiement
print_header "Redéploiement"
print_info "Arrêt des conteneurs..."
docker compose -f "$COMPOSE_FILE" down

print_info "Redémarrage avec la nouvelle configuration..."
docker compose -f "$COMPOSE_FILE" up -d

print_success "Redéploiement terminé"

print_header "Vérification"
print_info "Attente de 60 secondes pour le démarrage..."
sleep 60

docker compose -f "$COMPOSE_FILE" ps

print_info "Pour suivre les logs de l'API:"
echo "  docker logs -f bot-api"

print_info "Pour restaurer la sauvegarde si nécessaire:"
echo "  cp $BACKUP_FILE $COMPOSE_FILE"
echo "  docker compose -f $COMPOSE_FILE up -d --force-recreate"
