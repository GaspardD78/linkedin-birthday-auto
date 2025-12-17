#!/bin/bash
# ==============================================================================
# LinkedIn Auto RPi4 - Fix Permissions Script
# ==============================================================================
# Ce script corrige les problèmes de permissions sur les fichiers critiques
# pour assurer le bon fonctionnement du bot et des scripts SSL.
#
# Problèmes résolus:
# - Propriété root sur .env bloquant setup_letsencrypt.sh
# - Permissions restrictives sur les dossiers data/, logs/, config/
# - Accès certbot/ pour Nginx
#
# Usage:
#   sudo ./scripts/fix_permissions.sh
#
# IMPORTANT: Ce script DOIT être exécuté avec sudo
# ==============================================================================

set -euo pipefail

# --- Couleurs ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# --- Logging ---
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${BLUE}  $1${NC}"; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"; }

# ==============================================================================
# VÉRIFICATIONS PRÉALABLES
# ==============================================================================

# Vérifier que le script est exécuté avec sudo
if [[ $EUID -ne 0 ]]; then
   log_error "Ce script doit être exécuté avec sudo"
   log_info "Usage: sudo ./scripts/fix_permissions.sh"
   exit 1
fi

# Récupérer le vrai utilisateur (celui qui a lancé sudo)
REAL_USER="${SUDO_USER:-$USER}"

if [[ "$REAL_USER" == "root" ]]; then
    log_error "Ne lancez pas ce script directement en tant que root."
    log_info "Connectez-vous avec un utilisateur normal et utilisez sudo."
    exit 1
fi

# Récupérer le groupe principal de l'utilisateur
REAL_GROUP=$(id -gn "$REAL_USER")

log_step "Fix Permissions - LinkedIn Auto RPi4"
log_info "Utilisateur détecté: $REAL_USER"
log_info "Groupe détecté: $REAL_GROUP"

# ==============================================================================
# CORRECTION DES PERMISSIONS
# ==============================================================================

log_step "1. Correction Propriétaire du Projet"

# Remettre l'utilisateur courant propriétaire du projet entier
log_info "Changement du propriétaire du projet vers $REAL_USER:$REAL_GROUP..."
chown -R "$REAL_USER:$REAL_GROUP" .

log_success "Propriété du projet restaurée"

# ==============================================================================

log_step "2. Sécurisation du Fichier .env"

# Fichier .env : lecture/écriture pour user uniquement (sécurité)
if [[ -f ".env" ]]; then
    log_info "Application des permissions sécurisées sur .env (600)..."
    chmod 600 .env
    chown "$REAL_USER:$REAL_GROUP" .env
    log_success "Fichier .env sécurisé (rw-------)"
else
    log_warn "Fichier .env non trouvé (sera créé par setup.sh)"
fi

# ==============================================================================

log_step "3. Permissions des Dossiers Critiques"

# Créer les dossiers s'ils n'existent pas et fixer les permissions
CRITICAL_DIRS=("data" "logs" "config" "certbot" "certbot/conf" "certbot/www")

for dir in "${CRITICAL_DIRS[@]}"; do
    if [[ ! -d "$dir" ]]; then
        log_info "Création du dossier $dir..."
        mkdir -p "$dir"
    fi

    log_info "Application des permissions sur $dir/ (775)..."
    chmod -R 775 "$dir"
    chown -R "$REAL_USER:$REAL_GROUP" "$dir"
done

log_success "Dossiers critiques configurés"

# ==============================================================================

log_step "4. Permissions Spéciales Certbot"

# Certbot a besoin d'écrire dans certbot/conf et certbot/www
if [[ -d "certbot" ]]; then
    log_info "Configuration accès Certbot/Nginx..."

    # S'assurer que Nginx (dans Docker) peut lire les certificats
    chmod -R 755 certbot/conf 2>/dev/null || true
    chmod -R 755 certbot/www 2>/dev/null || true

    log_success "Dossiers Certbot accessibles"
fi

# ==============================================================================

log_step "5. Permissions des Scripts"

# Tous les scripts doivent être exécutables
if [[ -d "scripts" ]]; then
    log_info "Rendre les scripts exécutables..."
    chmod +x scripts/*.sh 2>/dev/null || true
    log_success "Scripts exécutables"
fi

# ==============================================================================

log_step "6. Permissions des Fichiers de Messages"

# Les fichiers messages.txt et late_messages.txt doivent être modifiables
MESSAGE_FILES=("data/messages.txt" "data/late_messages.txt")

for file in "${MESSAGE_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        log_info "Configuration des permissions sur $file..."
        chmod 664 "$file"
        chown "$REAL_USER:$REAL_GROUP" "$file"
    else
        log_warn "Fichier $file non trouvé"
    fi
done

log_success "Fichiers de messages configurés"

# ==============================================================================
# VALIDATION
# ==============================================================================

log_step "Validation des Permissions"

# Vérifier que l'utilisateur peut lire .env
if [[ -f ".env" ]]; then
    if sudo -u "$REAL_USER" test -r .env; then
        log_success ".env lisible par $REAL_USER"
    else
        log_error ".env toujours non lisible"
        exit 1
    fi
fi

# Vérifier que l'utilisateur peut écrire dans data/
if sudo -u "$REAL_USER" test -w data/; then
    log_success "data/ accessible en écriture par $REAL_USER"
else
    log_error "data/ non accessible en écriture"
    exit 1
fi

# ==============================================================================
# RÉSUMÉ
# ==============================================================================

log_step "Permissions Corrigées avec Succès"

echo -e "
${BOLD}Résumé des Corrections :${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Propriétaire : $REAL_USER:$REAL_GROUP
✅ Fichier .env  : 600 (rw-------)
✅ Dossiers      : 775 (rwxrwxr-x)
✅ Scripts       : Exécutables
✅ Messages      : 664 (rw-rw-r--)

${BOLD}Prochaines Étapes :${NC}
━━━━━━━━━━━━━━━━━
1. Vous pouvez maintenant lancer setup_letsencrypt.sh sans sudo
2. L'API pourra lire/écrire les fichiers de messages
3. Les logs seront accessibles sans problème de permissions

${GREEN}🎉 Toutes les permissions sont maintenant correctes !${NC}
"
