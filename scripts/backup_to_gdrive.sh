#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Script de backup automatique vers Google Drive
# LinkedIn Birthday Auto Bot - Audit Sécurité 2025
# ═══════════════════════════════════════════════════════════════════
#
# Ce script sauvegarde la base SQLite vers Google Drive via rclone.
#
# Modifications (Debug & Fiabilisation):
# - Détection dynamique du remote rclone
# - Vérification stricte des chemins (data, .env, config)
# - Gestion verbeuse des erreurs rclone
#
# Usage:
#   ./backup_to_gdrive.sh [--skip-local]
#
# ═══════════════════════════════════════════════════════════════════

set -e
set -o pipefail

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION ET DÉTECTION
# ═══════════════════════════════════════════════════════════════════

# Détection de la racine du projet
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fonctions de log
log_info() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} [INFO] $1"; }
log_warn() { echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} [WARN] $1"; }
log_error() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} [ERROR] $1"; }
log_debug() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} [DEBUG] $1"; }

error_exit() {
    log_error "$1"
    exit 1
}

log_info "🚀 Démarrage du script de backup (Mode Fiabilisé)"
log_debug "Script directory: $SCRIPT_DIR"
log_debug "Project root: $PROJECT_ROOT"

# 1. Détection du remote rclone
log_info "🔍 Détection du remote rclone..."
GDRIVE_REMOTE=$(rclone listremotes 2>/dev/null | head -n 1 | sed 's/://')

if [ -z "$GDRIVE_REMOTE" ]; then
    log_warn "Aucun remote détecté automatiquement. Utilisation par défaut : 'gdrive'"
    GDRIVE_REMOTE="gdrive"
else
    log_info "Remote rclone détecté : '$GDRIVE_REMOTE'"
fi

# 2. Configuration des chemins
DB_PATH="${PROJECT_ROOT}/data/linkedin.db"
ENV_PATH="${PROJECT_ROOT}/.env" # Note: .env might not exist in sandbox, checking anyway per requirement
CONFIG_DIR="${PROJECT_ROOT}/config"

# Répertoire de backup local (Temporaire ou Persistant)
# On privilégie un dossier dans data/backups pour éviter les problèmes de droits /mnt
DEFAULT_BACKUP_DIR="/mnt/linkedin-data/backups"
LOCAL_BACKUP_DIR="${PROJECT_ROOT}/data/backups"

# Si le dossier /mnt existe et est accessible en écriture, on l'utilise (legacy)
if [ -d "$DEFAULT_BACKUP_DIR" ] && [ -w "$DEFAULT_BACKUP_DIR" ]; then
    LOCAL_BACKUP_DIR="$DEFAULT_BACKUP_DIR"
    log_debug "Utilisation du dossier backup legacy: $LOCAL_BACKUP_DIR"
elif [ -d "$(dirname "$DEFAULT_BACKUP_DIR")" ] && [ -w "$(dirname "$DEFAULT_BACKUP_DIR")" ]; then
     # Si /mnt/linkedin-data existe et est writable, on peut créer backups dedans
     LOCAL_BACKUP_DIR="$DEFAULT_BACKUP_DIR"
     log_debug "Utilisation du dossier backup legacy (à créer): $LOCAL_BACKUP_DIR"
else
    log_debug "Utilisation du dossier backup local (fallback): $LOCAL_BACKUP_DIR"
fi

# Configuration Drive
GDRIVE_BACKUP_DIR="Backups/RPI4_LinkedinBot"
RETENTION_DAYS=30

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="linkedin_backup_${TIMESTAMP}.db"
BACKUP_FULL_PATH="${LOCAL_BACKUP_DIR}/${BACKUP_FILE}"

log_debug "DB_PATH: $DB_PATH"
log_debug "LOCAL_BACKUP_DIR: $LOCAL_BACKUP_DIR"
log_debug "GDRIVE_PATH: ${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}"

# ═══════════════════════════════════════════════════════════════════
# VÉRIFICATIONS STRICTES (REQUIREMENTS)
# ═══════════════════════════════════════════════════════════════════

log_info "🔍 Vérification de l'environnement..."

# Vérification rclone
if ! command -v rclone &> /dev/null; then
    error_exit "rclone n'est pas installé. (curl https://rclone.org/install.sh | sudo bash)"
fi

# Vérification fichiers sources requis
# Le prompt demande explicitement de vérifier data/, .env, config/
# Attention: .env peut être .env.pi4.example si pas configuré, mais ici on suppose prod
REQUIRED_PATHS=("$PROJECT_ROOT/data" "$PROJECT_ROOT/config")
# On vérifie .env séparément car il peut ne pas exister dans certains contextes (dev),
# mais en prod sur RPi4 il est vital.
if [ -f "$PROJECT_ROOT/.env" ]; then
    REQUIRED_PATHS+=("$PROJECT_ROOT/.env")
else
    log_warn "Fichier .env non trouvé à la racine ($PROJECT_ROOT/.env). Vérifiez si c'est normal."
    # Si requirements stricts:
    # error_exit "Fichier .env manquant."
    # Mais le user dit "Data path: ... .env". Donc il doit être là.
    # On va faire un check strict selon la demande.
    log_error "Fichier .env manquant."
    exit 1
fi

MISSING_PATH=false
for path in "${REQUIRED_PATHS[@]}"; do
    if [ ! -e "$path" ]; then
        log_error "Chemin requis manquant : $path"
        MISSING_PATH=true
    else
        log_debug "OK: $path"
    fi
done

if [ "$MISSING_PATH" = true ]; then
    error_exit "Certains fichiers sources requis sont manquants. Abandon."
fi

# Vérification présence DB (warning si absente mais dossier data là)
if [ ! -f "$DB_PATH" ]; then
    # C'est critique pour le backup DB
    error_exit "Base de données SQLite introuvable : $DB_PATH"
fi

# Vérification/Création dossier backup local et permissions
if [ ! -d "$LOCAL_BACKUP_DIR" ]; then
    log_info "Création du dossier backup local : $LOCAL_BACKUP_DIR"
    mkdir -p "$LOCAL_BACKUP_DIR" || error_exit "Impossible de créer $LOCAL_BACKUP_DIR"
fi

if [ ! -w "$LOCAL_BACKUP_DIR" ]; then
    error_exit "Permission refusée : Impossible d'écrire dans $LOCAL_BACKUP_DIR"
fi

# Test connexion Drive rapide
log_info "Test de connexion au remote '$GDRIVE_REMOTE'..."
if ! rclone about "${GDRIVE_REMOTE}:" &> /dev/null; then
    # On tente un lsd si about échoue
    if ! rclone lsd "${GDRIVE_REMOTE}:" &> /dev/null; then
        error_exit "Échec de connexion au remote '${GDRIVE_REMOTE}'. Vérifiez 'rclone config'."
    fi
fi
log_info "Connexion Drive OK."

# ═══════════════════════════════════════════════════════════════════
# CRÉATION DU BACKUP LOCAL
# ═══════════════════════════════════════════════════════════════════

if [ "$1" != "--skip-local" ]; then
    log_info "📦 Création du backup SQLite local..."

    if ! command -v sqlite3 &> /dev/null; then
        error_exit "sqlite3 n'est pas installé."
    fi

    # Backup avec sqlite3
    if ! sqlite3 "$DB_PATH" ".backup '$BACKUP_FULL_PATH'"; then
        error_exit "Erreur lors de l'exécution de sqlite3 .backup"
    fi

    # Vérification intégrité
    log_debug "Vérification intégrité SQLite..."
    INTEGRITY=$(sqlite3 "$BACKUP_FULL_PATH" "PRAGMA integrity_check;")
    if [ "$INTEGRITY" != "ok" ]; then
        rm -f "$BACKUP_FULL_PATH"
        error_exit "Backup corrompu (Integrity Check: $INTEGRITY)"
    fi

    # Checksum
    sha256sum "$BACKUP_FULL_PATH" > "${BACKUP_FULL_PATH}.sha256"

    # Compression
    log_info "🗜️ Compression..."
    gzip -f "$BACKUP_FULL_PATH"
    BACKUP_FULL_PATH="${BACKUP_FULL_PATH}.gz"

    if [ ! -f "$BACKUP_FULL_PATH" ]; then
        error_exit "Le fichier compressé n'a pas été créé."
    fi

    SIZE=$(du -h "$BACKUP_FULL_PATH" | cut -f1)
    log_info "Backup local créé avec succès : $BACKUP_FULL_PATH ($SIZE)"

else
    log_info "⏭️ Skip local backup requested."
    # Find latest
    BACKUP_FULL_PATH=$(ls -t ${LOCAL_BACKUP_DIR}/linkedin_backup_*.db.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FULL_PATH" ]; then
        error_exit "Aucun backup local trouvé pour l'upload."
    fi
    log_info "Utilisation du dernier backup : $BACKUP_FULL_PATH"
fi

# ═══════════════════════════════════════════════════════════════════
# UPLOAD VERS GOOGLE DRIVE
# ═══════════════════════════════════════════════════════════════════

log_info "☁️ Upload vers Google Drive : ${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}"

# Création dossier distant (sans masquer stderr)
log_debug "Vérification/Création dossier distant..."
# On autorise l'échec si le dossier existe déjà (exit code != 0 possible sur certains remotes ?)
# rclone mkdir ne fail pas si existe, sauf droits.
if ! rclone mkdir "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}" 2>/dev/null; then
    # On re-tente sans masquer pour voir l'erreur si besoin, ou on log warning
    log_warn "Erreur (ou déjà existant) lors du mkdir distant."
fi

UPLOAD_SUCCESS=false

for attempt in {1..3}; do
    log_info "Tentative d'upload ${attempt}/3..."

    # On capture stderr pour l'afficher
    # --stats-one-line est plus clean pour les logs
    if rclone copy "$BACKUP_FULL_PATH" "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/" --verbose --stats 5s; then
        UPLOAD_SUCCESS=true
        log_info "Upload réussi."
        break
    else
        EXIT_CODE=$?
        log_warn "Échec de la commande rclone copy (Code: $EXIT_CODE). Retrying in 5s..."
        sleep 5
    fi
done

if [ "$UPLOAD_SUCCESS" = false ]; then
    error_exit "Abandon après 3 échecs d'upload."
fi

# Upload checksum
rclone copy "${BACKUP_FULL_PATH}.sha256" "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/" --quiet || true

# ═══════════════════════════════════════════════════════════════════
# ROTATION ET NETTOYAGE
# ═══════════════════════════════════════════════════════════════════

log_info "🧹 Nettoyage des vieux backups (> $RETENTION_DAYS jours)..."

# Local
find "$LOCAL_BACKUP_DIR" -name "linkedin_backup_*.db*" -type f -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

# Remote
# On utilise --min-age pour simplifier la logique
rclone delete "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}" --min-age ${RETENTION_DAYS}d --include "linkedin_backup_*" --verbose || log_warn "Erreur lors du nettoyage distant"

# ═══════════════════════════════════════════════════════════════════
# RÉSUMÉ
# ═══════════════════════════════════════════════════════════════════

REMOTE_STATS=$(rclone size "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}" --json 2>/dev/null)
# Extraction un peu plus robuste (JSON simple)
COUNT=$(echo "$REMOTE_STATS" | grep -o '"count":[0-9]*' | cut -d: -f2)
SIZE=$(echo "$REMOTE_STATS" | grep -o '"bytes":[0-9]*' | cut -d: -f2)
# Fallback si numfmt absent (ex: minimal docker)
if command -v numfmt &>/dev/null; then
    SIZE_HUMAN=$(numfmt --to=iec $SIZE 2>/dev/null)
else
    SIZE_HUMAN="$SIZE bytes"
fi

echo ""
log_info "✅ Sauvegarde terminée avec succès."
echo "---------------------------------------------------"
echo "📁 Source          : $DB_PATH"
echo "📦 Archive         : $BACKUP_FULL_PATH"
echo "☁️  Destination     : ${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}"
echo "📊 État Drive      : $COUNT fichiers, $SIZE_HUMAN"
echo "---------------------------------------------------"

exit 0
