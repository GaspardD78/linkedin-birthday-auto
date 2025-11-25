#!/bin/bash

# =========================================================================
# Script de nettoyage périodique pour Raspberry Pi 4
# Économise l'espace sur la carte SD (32GB)
# =========================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "ℹ️  $1"; }

# Vérifier espace avant nettoyage
print_header "📊 Espace Disque AVANT Nettoyage"
df -h / | awk 'NR==1 || NR==2'
SPACE_BEFORE=$(df / | awk 'NR==2 {print $4}')

print_header "🧹 Nettoyage Raspberry Pi 4"

# 1. Nettoyage Docker
print_info "Nettoyage des images, conteneurs et volumes Docker inutilisés..."
if docker system prune -af --filter "until=168h" --volumes 2>/dev/null; then
    print_success "Images Docker > 7 jours supprimées"
else
    print_warning "Échec nettoyage Docker (déjà clean ?)"
fi

# 2. Logs applicatifs anciens
print_info "Suppression logs applicatifs > 30 jours..."
if [ -d "logs/" ]; then
    DELETED_LOGS=$(find logs/ -name "*.log" -mtime +30 -delete -print | wc -l)
    if [ "$DELETED_LOGS" -gt 0 ]; then
        print_success "Logs supprimés: $DELETED_LOGS fichiers"
    else
        print_info "Aucun log ancien à supprimer"
    fi
else
    print_info "Dossier logs/ introuvable"
fi

# 3. Screenshots anciens
print_info "Suppression screenshots > 7 jours..."
if [ -d "screenshots/" ]; then
    DELETED_SCREENSHOTS=$(find screenshots/ -name "*.png" -mtime +7 -delete -print | wc -l)
    if [ "$DELETED_SCREENSHOTS" -gt 0 ]; then
        print_success "Screenshots supprimés: $DELETED_SCREENSHOTS fichiers"
    else
        print_info "Aucun screenshot ancien à supprimer"
    fi
else
    print_info "Dossier screenshots/ introuvable"
fi

# 4. Fichiers temporaires du projet
print_info "Nettoyage fichiers temporaires Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
print_success "Cache Python nettoyé"

# 5. Cache APT (nécessite sudo)
if [ "$EUID" -eq 0 ]; then
    print_info "Nettoyage cache APT..."
    apt-get clean 2>/dev/null || true
    print_success "Cache APT nettoyé"
else
    print_warning "Cache APT non nettoyé (nécessite sudo)"
fi

# 6. Journaux système (nécessite sudo)
if [ "$EUID" -eq 0 ]; then
    print_info "Nettoyage journaux système > 7 jours..."
    journalctl --vacuum-time=7d 2>/dev/null || true
    print_success "Journaux système nettoyés"
else
    print_warning "Journaux système non nettoyés (nécessite sudo)"
fi

# Vérifier espace après nettoyage
print_header "📊 Espace Disque APRÈS Nettoyage"
df -h / | awk 'NR==1 || NR==2'
SPACE_AFTER=$(df / | awk 'NR==2 {print $4}')

# Calcul espace libéré
SPACE_FREED=$((SPACE_AFTER - SPACE_BEFORE))
SPACE_FREED_MB=$((SPACE_FREED / 1024))

print_header "✅ Nettoyage Terminé"
if [ $SPACE_FREED_MB -gt 0 ]; then
    print_success "Espace libéré: ~${SPACE_FREED_MB}MB"
else
    print_info "Peu d'espace libéré (système déjà propre)"
fi
