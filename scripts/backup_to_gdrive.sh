#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Script de backup automatique vers Google Drive
# LinkedIn Birthday Auto Bot - Fiabilisé & Robuste (2025)
# ═══════════════════════════════════════════════════════════════════
#
# Ce script sauvegarde la base SQLite vers Google Drive via rclone.
#
# Améliorations :
# - Logs horodatés et verbeux
# - Gestion d'erreur stricte (set -e)
# - Capture de stderr pour diagnostic
# - Vérifications pré-backup complètes
#
# Usage:
#   ./backup_to_gdrive.sh [--skip-local]
#
# ═══════════════════════════════════════════════════════════════════

set -o pipefail

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Détection racine projet
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Fichiers de log
LOG_FILE="${PROJECT_ROOT}/logs/backup_gdrive.log"
mkdir -p "${PROJECT_ROOT}/logs"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fonction de logging (Sortie Stdout + Fichier)
log() {
    local level=$1
    local msg=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local color=$NC

    case $level in
        INFO) color=$GREEN ;;
        WARN) color=$YELLOW ;;
        ERROR) color=$RED ;;
        DEBUG) color=$BLUE ;;
    esac

    echo -e "${color}[${timestamp}] [${level}] ${msg}${NC}" | tee -a "$LOG_FILE"
}

# Gestion d'erreur
handle_error() {
    local exit_code=$?
    local line_no=$1
    log ERROR "Échec à la ligne $line_no (Code: $exit_code)"
    log ERROR "Consultez $LOG_FILE pour les détails."
    exit $exit_code
}
trap 'handle_error $LINENO' ERR

log INFO "🚀 Démarrage du backup Google Drive..."
log INFO "Project Root: $PROJECT_ROOT"

# ═══════════════════════════════════════════════════════════════════
# PRÉ-CHECKS (VÉRIFICATIONS)
# ═══════════════════════════════════════════════════════════════════

# 1. Vérification rclone
if ! command -v rclone &> /dev/null; then
    log ERROR "rclone n'est pas installé. Abandon."
    exit 1
fi

# 2. Détection Remote
log INFO "🔍 Recherche du remote rclone..."
GDRIVE_REMOTE=$(rclone listremotes 2>/dev/null | head -n 1 | sed 's/://')

if [ -z "$GDRIVE_REMOTE" ]; then
    log ERROR "Aucun remote rclone configuré. Veuillez lancer 'rclone config'."
    exit 1
fi
log INFO "Remote détecté : '$GDRIVE_REMOTE'"

# 3. Vérification des fichiers sources
REQUIRED_FILES=(
    "$PROJECT_ROOT/data/linkedin.db"
    "$PROJECT_ROOT/config"
)

# .env est optionnel en dev, mais critique en prod. On check s'il existe.
if [ -f "$PROJECT_ROOT/.env" ]; then
    REQUIRED_FILES+=("$PROJECT_ROOT/.env")
else
    log WARN "Fichier .env non trouvé à la racine. Backup partiel possible."
fi

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -e "$file" ]; then
        log ERROR "Fichier requis manquant : $file"
        exit 1
    fi
done

# ═══════════════════════════════════════════════════════════════════
# BACKUP LOCAL
# ═══════════════════════════════════════════════════════════════════

BACKUP_DIR="${PROJECT_ROOT}/data/backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}.tar.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

log INFO "📦 Création de l'archive locale..."

# Utilisation de tar pour tout zipper (DB + Config + Env)
# On exclut les logs et node_modules pour alléger
tar -czf "$BACKUP_PATH" \
    -C "$PROJECT_ROOT" \
    data/linkedin.db \
    config \
    .env \
    2> >(while read line; do log ERROR "tar: $line"; done)

if [ ! -f "$BACKUP_PATH" ]; then
    log ERROR "L'archive n'a pas été créée."
    exit 1
fi

ARCHIVE_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
log INFO "Archive créée : $BACKUP_NAME ($ARCHIVE_SIZE)"

# ═══════════════════════════════════════════════════════════════════
# UPLOAD GOOGLE DRIVE
# ═══════════════════════════════════════════════════════════════════

REMOTE_DIR="LinkedInBot_Backups"
log INFO "☁️ Upload vers ${GDRIVE_REMOTE}:${REMOTE_DIR}..."

# Tentative d'upload avec retry et capture d'erreur
UPLOAD_OK=false
for i in {1..3}; do
    if rclone copy "$BACKUP_PATH" "${GDRIVE_REMOTE}:${REMOTE_DIR}/" --verbose 2>&1 | tee -a "$LOG_FILE"; then
        UPLOAD_OK=true
        break
    else
        log WARN "Échec upload (tentative $i/3)..."
        sleep 5
    fi
done

if [ "$UPLOAD_OK" = false ]; then
    log ERROR "Abandon après 3 échecs d'upload."
    exit 1
fi

log INFO "✅ Upload réussi."

# ═══════════════════════════════════════════════════════════════════
# NETTOYAGE
# ═══════════════════════════════════════════════════════════════════

RETENTION_DAYS=30
log INFO "🧹 Nettoyage des vieux backups (> $RETENTION_DAYS jours)..."

# Local
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
log INFO "Nettoyage local terminé."

# Distant
rclone delete "${GDRIVE_REMOTE}:${REMOTE_DIR}" --min-age ${RETENTION_DAYS}d --verbose 2>&1 | tee -a "$LOG_FILE"
log INFO "Nettoyage distant terminé."

# ═══════════════════════════════════════════════════════════════════
# NOTIFICATIONS SLACK (OPTIONNEL)
# ═══════════════════════════════════════════════════════════════════

SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
if [[ -n "$SLACK_WEBHOOK" ]]; then
    log INFO "📤 Envoi notification Slack..."

    SLACK_MESSAGE="{
        \"text\": \"✅ Backup LinkedIn Bot terminé avec succès\",
        \"attachments\": [{
            \"color\": \"good\",
            \"fields\": [
                {\"title\": \"Archive\", \"value\": \"$BACKUP_NAME ($ARCHIVE_SIZE)\", \"short\": true},
                {\"title\": \"Remote\", \"value\": \"${GDRIVE_REMOTE}:${REMOTE_DIR}\", \"short\": true},
                {\"title\": \"Timestamp\", \"value\": \"$(date '+%Y-%m-%d %H:%M:%S')\", \"short\": true},
                {\"title\": \"Rétention\", \"value\": \"${RETENTION_DAYS} jours\", \"short\": true}
            ]
        }]
    }"

    if curl -X POST -H 'Content-type: application/json' \
        --data "$SLACK_MESSAGE" \
        "$SLACK_WEBHOOK" 2>/dev/null; then
        log INFO "Notification Slack envoyée."
    else
        log WARN "Échec notification Slack."
    fi
fi

# ═══════════════════════════════════════════════════════════════════
# TEST RESTORE ALÉATOIRE (1er du mois)
# ═══════════════════════════════════════════════════════════════════

if [[ $(date +%d) == "01" ]]; then
    log INFO "🔄 Test restore mensuel..."

    RESTORE_TEST_DIR="/tmp/linkedin_restore_test_$$"
    mkdir -p "$RESTORE_TEST_DIR"

    LATEST_BACKUP=$(rclone ls "${GDRIVE_REMOTE}:${REMOTE_DIR}" 2>/dev/null | tail -1 | awk '{print $2}')

    if [[ -n "$LATEST_BACKUP" ]]; then
        if rclone copy "${GDRIVE_REMOTE}:${REMOTE_DIR}/${LATEST_BACKUP}" "$RESTORE_TEST_DIR/" 2>&1 | tee -a "$LOG_FILE"; then
            if tar -tzf "$RESTORE_TEST_DIR/$LATEST_BACKUP" &>/dev/null; then
                log INFO "✅ Test restore réussi pour $LATEST_BACKUP"
            else
                log ERROR "❌ Archive corrompue: $LATEST_BACKUP"
            fi
        else
            log ERROR "❌ Erreur download pour test restore"
        fi
    else
        log WARN "Aucun backup disponible pour test restore"
    fi

    rm -rf "$RESTORE_TEST_DIR"
fi

log INFO "🎉 Backup terminé avec succès."
exit 0
