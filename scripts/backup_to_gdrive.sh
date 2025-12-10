#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Script de backup automatique vers Google Drive
# LinkedIn Birthday Auto Bot - Audit Sécurité 2025
# ═══════════════════════════════════════════════════════════════════
#
# Ce script sauvegarde la base SQLite vers Google Drive via rclone.
# Il maintient une rotation de 30 jours de backups dans le cloud.
#
# Prérequis:
#   - rclone installé (curl https://rclone.org/install.sh | sudo bash)
#   - Configuration Google Drive : rclone config (nom: "gdrive")
#
# Usage:
#   ./backup_to_gdrive.sh [--skip-local]
#
# Cron (daily backup at 3am):
#   0 3 * * * /home/pi/linkedin-birthday-auto/scripts/backup_to_gdrive.sh >> /var/log/linkedin-backup-gdrive.log 2>&1
#
# ═══════════════════════════════════════════════════════════════════

set -e

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Chemins
DB_PATH="/app/data/linkedin.db"
LOCAL_BACKUP_DIR="/mnt/linkedin-data/backups"
GDRIVE_REMOTE="gdrive"  # Nom configuré dans rclone
GDRIVE_BACKUP_DIR="linkedin-bot-backups"
RETENTION_DAYS=30

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="linkedin_backup_${TIMESTAMP}.db"
BACKUP_FULL_PATH="${LOCAL_BACKUP_DIR}/${BACKUP_FILE}"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# ═══════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════

log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ℹ️  $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ⚠️  $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ❌ $1"
}

log_success() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ✅ $1"
}

error_exit() {
    log_error "$1"
    exit 1
}

# ═══════════════════════════════════════════════════════════════════
# VÉRIFICATIONS PRÉLIMINAIRES
# ═══════════════════════════════════════════════════════════════════

log_info "🔍 Vérifications préliminaires"

# Vérifier rclone
if ! command -v rclone &> /dev/null; then
    error_exit "rclone n'est pas installé. Installez-le avec: curl https://rclone.org/install.sh | sudo bash"
fi

# Vérifier sqlite3
if ! command -v sqlite3 &> /dev/null; then
    error_exit "sqlite3 n'est pas installé. Installez-le avec: apt-get install sqlite3"
fi

# Vérifier configuration Google Drive
if ! rclone listremotes | grep -q "^${GDRIVE_REMOTE}:$"; then
    error_exit "Google Drive non configuré dans rclone. Exécutez: rclone config"
fi

# Tester connexion Google Drive
log_info "Test de connexion à Google Drive..."
if ! rclone lsd "${GDRIVE_REMOTE}:" &> /dev/null; then
    error_exit "Impossible de se connecter à Google Drive. Vérifiez votre configuration rclone."
fi
log_success "Connexion Google Drive OK"

# Vérifier base de données source
if [ ! -f "$DB_PATH" ]; then
    error_exit "Base de données source introuvable: $DB_PATH"
fi

# Créer répertoire local backup si nécessaire
mkdir -p "$LOCAL_BACKUP_DIR" || error_exit "Impossible de créer $LOCAL_BACKUP_DIR"

# ═══════════════════════════════════════════════════════════════════
# BACKUP LOCAL DE LA BASE DE DONNÉES
# ═══════════════════════════════════════════════════════════════════

if [ "$1" != "--skip-local" ]; then
    log_info "💾 Backup local de la base de données"

    DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
    log_info "Taille de la base source: $DB_SIZE"

    # Backup SQLite sécurisé
    sqlite3 "$DB_PATH" ".backup '$BACKUP_FULL_PATH'" || error_exit "Échec du backup SQLite"

    # Vérification intégrité
    log_info "🔍 Vérification de l'intégrité"
    if ! sqlite3 "$BACKUP_FULL_PATH" "PRAGMA integrity_check;" | grep -q "ok"; then
        rm -f "$BACKUP_FULL_PATH"
        error_exit "Backup corrompu"
    fi
    log_success "Intégrité vérifiée"

    # Checksum
    CHECKSUM=$(sha256sum "$BACKUP_FULL_PATH" | cut -d' ' -f1)
    echo "$CHECKSUM" > "${BACKUP_FULL_PATH}.sha256"
    log_info "Checksum: ${CHECKSUM:0:16}..."

    # Compression
    log_info "🗜️  Compression du backup"
    gzip -f "$BACKUP_FULL_PATH" || log_warn "Échec compression (non critique)"

    if [ -f "${BACKUP_FULL_PATH}.gz" ]; then
        BACKUP_FULL_PATH="${BACKUP_FULL_PATH}.gz"
        FINAL_SIZE=$(du -h "$BACKUP_FULL_PATH" | cut -f1)
        log_success "Backup compressé: $FINAL_SIZE"
    else
        FINAL_SIZE=$(du -h "$BACKUP_FULL_PATH" | cut -f1)
        log_success "Backup créé: $FINAL_SIZE"
    fi
else
    log_info "⏭️  Skip backup local (utilisation backup existant)"
    # Trouver le backup le plus récent
    BACKUP_FULL_PATH=$(ls -t ${LOCAL_BACKUP_DIR}/linkedin_backup_*.db.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FULL_PATH" ]; then
        error_exit "Aucun backup local trouvé"
    fi
    FINAL_SIZE=$(du -h "$BACKUP_FULL_PATH" | cut -f1)
    log_info "Utilisation backup: $(basename $BACKUP_FULL_PATH) ($FINAL_SIZE)"
fi

# ═══════════════════════════════════════════════════════════════════
# UPLOAD VERS GOOGLE DRIVE
# ═══════════════════════════════════════════════════════════════════

log_info "☁️  Upload vers Google Drive"

# Créer le répertoire distant si nécessaire
rclone mkdir "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}" 2>/dev/null || true

# Upload avec retry (max 3 tentatives)
UPLOAD_SUCCESS=false
for attempt in {1..3}; do
    log_info "Tentative d'upload ${attempt}/3..."

    if rclone copy "$BACKUP_FULL_PATH" "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/" \
        --progress \
        --retries 3 \
        --low-level-retries 5 \
        --stats 10s; then
        UPLOAD_SUCCESS=true
        break
    else
        log_warn "Échec tentative ${attempt}"
        sleep 5
    fi
done

if [ "$UPLOAD_SUCCESS" = false ]; then
    error_exit "Échec upload vers Google Drive après 3 tentatives"
fi

# Upload du checksum aussi
if [ -f "${BACKUP_FULL_PATH}.sha256" ]; then
    rclone copy "${BACKUP_FULL_PATH}.sha256" "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/" --quiet
fi

log_success "Upload Google Drive terminé"

# Vérification upload
log_info "🔍 Vérification upload"
REMOTE_SIZE=$(rclone size "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/$(basename $BACKUP_FULL_PATH)" --json 2>/dev/null | grep -o '"bytes":[0-9]*' | cut -d: -f2)
LOCAL_SIZE=$(stat -f%z "$BACKUP_FULL_PATH" 2>/dev/null || stat -c%s "$BACKUP_FULL_PATH")

if [ "$REMOTE_SIZE" = "$LOCAL_SIZE" ]; then
    log_success "Tailles correspondent: $(numfmt --to=iec $LOCAL_SIZE)"
else
    log_warn "Différence de taille: local=$LOCAL_SIZE remote=$REMOTE_SIZE"
fi

# ═══════════════════════════════════════════════════════════════════
# ROTATION DES BACKUPS (Cloud + Local)
# ═══════════════════════════════════════════════════════════════════

log_info "🔄 Rotation des backups (rétention: ${RETENTION_DAYS} jours)"

# Rotation locale
OLD_LOCAL_BACKUPS=$(find "$LOCAL_BACKUP_DIR" -name "linkedin_backup_*.db*" -type f -mtime +${RETENTION_DAYS})
if [ -n "$OLD_LOCAL_BACKUPS" ]; then
    log_info "Suppression backups locaux obsolètes:"
    echo "$OLD_LOCAL_BACKUPS" | while read -r old_backup; do
        log_info "  - $(basename "$old_backup")"
        rm -f "$old_backup"
    done
fi

# Rotation Google Drive
log_info "Nettoyage Google Drive (backups > ${RETENTION_DAYS} jours)..."

# Lister tous les backups distants
rclone lsf "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/" | grep "linkedin_backup_" | while read -r remote_file; do
    # Extraire la date du nom de fichier (format: linkedin_backup_YYYYMMDD_HHMMSS.db.gz)
    FILE_DATE=$(echo "$remote_file" | grep -oP '\d{8}' | head -1)

    if [ -n "$FILE_DATE" ]; then
        # Calculer l'âge en jours
        FILE_TIMESTAMP=$(date -d "${FILE_DATE}" +%s 2>/dev/null || echo 0)
        CURRENT_TIMESTAMP=$(date +%s)
        AGE_DAYS=$(( (CURRENT_TIMESTAMP - FILE_TIMESTAMP) / 86400 ))

        if [ "$AGE_DAYS" -gt "$RETENTION_DAYS" ]; then
            log_info "Suppression Google Drive: $remote_file (${AGE_DAYS} jours)"
            rclone delete "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/${remote_file}" --quiet
        fi
    fi
done

# ═══════════════════════════════════════════════════════════════════
# STATISTIQUES FINALES
# ═══════════════════════════════════════════════════════════════════

log_info "📊 Statistiques finales"

# Backups locaux
LOCAL_COUNT=$(find "$LOCAL_BACKUP_DIR" -name "linkedin_backup_*.db*" -type f | wc -l)
LOCAL_TOTAL_SIZE=$(du -sh "$LOCAL_BACKUP_DIR" 2>/dev/null | cut -f1)

# Backups Google Drive
GDRIVE_COUNT=$(rclone lsf "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/" | grep "linkedin_backup_" | grep -v ".sha256" | wc -l)
GDRIVE_TOTAL_SIZE=$(rclone size "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/" --json 2>/dev/null | grep -o '"bytes":[0-9]*' | cut -d: -f2)
if [ -n "$GDRIVE_TOTAL_SIZE" ]; then
    GDRIVE_TOTAL_SIZE_HUMAN=$(numfmt --to=iec $GDRIVE_TOTAL_SIZE)
else
    GDRIVE_TOTAL_SIZE_HUMAN="N/A"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Backup Google Drive terminé avec succès"
echo "═══════════════════════════════════════════════════════════════"
echo "📁 Fichier             : $(basename "$BACKUP_FULL_PATH")"
echo "📊 Taille              : $FINAL_SIZE"
echo "☁️  Google Drive       : ${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/"
echo ""
echo "📂 Backups locaux      : $LOCAL_COUNT fichiers ($LOCAL_TOTAL_SIZE)"
echo "☁️  Backups cloud       : $GDRIVE_COUNT fichiers ($GDRIVE_TOTAL_SIZE_HUMAN)"
echo "🔄 Rétention           : $RETENTION_DAYS jours"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Liste des backups Google Drive
log_info "📋 Backups Google Drive (5 plus récents):"
rclone lsl "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/" | grep "linkedin_backup_" | grep -v ".sha256" | sort -r | head -5 | awk '{printf "  %s %s  %s  %s\n", $2, $3, $4, $5}'

echo ""
log_success "💡 Pour restaurer un backup depuis Google Drive:"
echo "  rclone copy ${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/$(basename $BACKUP_FULL_PATH) /tmp/"
echo "  gunzip -c /tmp/$(basename $BACKUP_FULL_PATH) > /app/data/linkedin.db"
echo ""

exit 0
