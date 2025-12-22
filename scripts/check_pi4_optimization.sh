#!/bin/bash

# =========================================================================
# Script de vérification des optimisations pour Raspberry Pi 4
# =========================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. Vérification du SWAP
print_header "Vérification de la mémoire SWAP"
SWAP_TOTAL=$(free -m | awk '/Swap/ {print $2}')
if [ "$SWAP_TOTAL" -lt 2000 ]; then
    print_warning "Swap détecté : ${SWAP_TOTAL}MB"
    print_warning "Attention : Une utilisation excessive du Swap peut user la carte SD."
    print_warning "Assurez-vous que peu d'applications tournent en parallèle."
else
    print_success "Swap OK : ${SWAP_TOTAL}MB"
fi

# 2. Vérification de Next.js Standalone
print_header "Vérification Next.js Standalone"
if grep -q "output: 'standalone'" dashboard/next.config.js; then
    print_success "Next.js configuré en mode 'standalone'"
else
    print_error "Next.js NON configuré en mode 'standalone'. Modifiez dashboard/next.config.js"
fi

# 3. Vérification de la rotation des logs Docker
print_header "Vérification de la rotation des logs Docker"
if grep -q "max-size" docker-compose.yml; then
    print_success "Rotation des logs Docker configurée"
else
    print_warning "Rotation des logs Docker absente dans docker-compose.yml"
fi

# 4. Vérification des limites de ressources
print_header "Vérification des limites de ressources"
if grep -q "deploy:" docker-compose.yml; then
    print_success "Limites de ressources (CPU/RAM) définies"
else
    print_warning "Limites de ressources non définies dans docker-compose.yml"
fi

# 5. Vérification ZRAM (Optionnel mais recommandé)
print_header "Vérification ZRAM (Compression RAM)"
if lsmod | grep -q zram; then
    print_success "Module ZRAM chargé"
else
    print_warning "ZRAM non activé. Recommandé pour Pi 4 avec beaucoup de containers."
    print_warning "Installation : sudo apt install zram-tools"
fi
