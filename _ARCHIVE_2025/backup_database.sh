#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Script de backup automatisé pour LinkedIn Birthday Auto Bot
# ═══════════════════════════════════════════════════════════════════
#
# Ce script fait un backup sécurisé de la base SQLite vers la clé USB
# et maintient une rotation des 7 derniers backups.
#
# Usage:
#   ./backup_database.sh [--force]
#
# Cron (daily backup at 3am):
#   0 3 * * * /home/user/linkedin-birthday-auto/scripts/backup_database.sh >> /var/log/linkedin-backup.log 2>&1
#
# ═══════════════════════════════════════════════════════════════════

set -e

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Chemins des données (Docker volumes persistants)
DB_PATH="/app/data/linkedin.db"
BACKUP_DIR="/mnt/linkedin-data/backups"
RETENTION_DAYS=7

# Timestamp pour nommage unique
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="linkedin_backup_${TIMESTAMP}.db"
BACKUP_FULL_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Couleurs pour logs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

error_exit() {
    log_error "$1"
    exit 1
}

# ═══════════════════════════════════════════════════════════════════
# VÉRIFICATIONS PRÉLIMINAIRES
# ═══════════════════════════════════════════════════════════════════

log_info "🔍 Vérifications préliminaires"

# Vérifier si sqlite3 est installé
if ! command -v sqlite3 &> /dev/null; then
    error_exit "sqlite3 n'est pas installé. Installez-le avec: apt-get install sqlite3"
fi

# Vérifier si la base de données source existe
if [ ! -f "$DB_PATH" ]; then
    error_exit "Base de données source introuvable: $DB_PATH"
fi

# Vérifier si le répertoire de backup existe
if [ ! -d "$BACKUP_DIR" ]; then
    log_warn "Répertoire de backup inexistant, création..."
    mkdir -p "$BACKUP_DIR" || error_exit "Impossible de créer le répertoire de backup"
fi

# Vérifier que le répertoire de backup est sur la clé USB (pas sur SD card)
BACKUP_MOUNT=$(df "$BACKUP_DIR" | tail -1 | awk '{print $6}')
if [ "$BACKUP_MOUNT" = "/" ]; then
    log_warn "⚠️  ATTENTION: Le répertoire de backup est sur la carte SD, pas sur USB!"
    log_warn "   Cela peut user prématurément la carte SD."
    log_warn "   Montez une clé USB sur /mnt/linkedin-data ou utilisez un autre volume."
    if [ "$1" != "--force" ]; then
        error_exit "Backup annulé. Utilisez --force pour forcer."
    fi
fi

# Vérifier l'espace disque disponible (au moins 100MB requis)
AVAILABLE_SPACE=$(df "$BACKUP_DIR" | tail -1 | awk '{print $4}')
if [ "$AVAILABLE_SPACE" -lt 102400 ]; then
    log_warn "Espace disque faible: $(( AVAILABLE_SPACE / 1024 ))MB disponibles"
fi

log_info "✅ Toutes les vérifications sont passées"

# ═══════════════════════════════════════════════════════════════════
# BACKUP DE LA BASE DE DONNÉES
# ═══════════════════════════════════════════════════════════════════

log_info "💾 Début du backup de la base de données"

# Taille de la base source
DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
log_info "Taille de la base source: $DB_SIZE"

# Méthode 1 (préférée): Utiliser .backup de SQLite (garantit cohérence)
log_info "Utilisation de SQLite .backup (méthode sécurisée)"
sqlite3 "$DB_PATH" ".backup '$BACKUP_FULL_PATH'" || error_exit "Échec du backup SQLite"

# Vérifier l'intégrité du backup
log_info "🔍 Vérification de l'intégrité du backup"
sqlite3 "$BACKUP_FULL_PATH" "PRAGMA integrity_check;" > /tmp/integrity_check.txt 2>&1

if grep -q "ok" /tmp/integrity_check.txt; then
    log_info "✅ Intégrité du backup vérifiée (PRAGMA integrity_check: ok)"
else
    log_error "❌ Échec de la vérification d'intégrité"
    cat /tmp/integrity_check.txt
    rm -f "$BACKUP_FULL_PATH"
    error_exit "Backup corrompu, suppression du fichier"
fi

# Calculer le checksum du backup
CHECKSUM=$(sha256sum "$BACKUP_FULL_PATH" | cut -d' ' -f1)
echo "$CHECKSUM" > "${BACKUP_FULL_PATH}.sha256"
log_info "Checksum SHA256 sauvegardé: ${CHECKSUM:0:16}..."

# Compresser le backup (gzip)
log_info "🗜️  Compression du backup"
gzip -f "$BACKUP_FULL_PATH" || log_warn "Échec de la compression (non critique)"

if [ -f "${BACKUP_FULL_PATH}.gz" ]; then
    FINAL_SIZE=$(du -h "${BACKUP_FULL_PATH}.gz" | cut -f1)
    log_info "✅ Backup compressé: ${FINAL_SIZE}"
    BACKUP_FULL_PATH="${BACKUP_FULL_PATH}.gz"
else
    FINAL_SIZE=$(du -h "$BACKUP_FULL_PATH" | cut -f1)
    log_info "✅ Backup créé (non compressé): ${FINAL_SIZE}"
fi

# ═══════════════════════════════════════════════════════════════════
# ROTATION DES BACKUPS (Garder seulement les N derniers)
# ═══════════════════════════════════════════════════════════════════

log_info "🔄 Rotation des backups (rétention: ${RETENTION_DAYS} jours)"

# Compter le nombre de backups existants
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "linkedin_backup_*.db*" -type f | wc -l)
log_info "Nombre de backups existants: $BACKUP_COUNT"

# Supprimer les backups plus vieux que RETENTION_DAYS jours
OLD_BACKUPS=$(find "$BACKUP_DIR" -name "linkedin_backup_*.db*" -type f -mtime +${RETENTION_DAYS})

if [ -n "$OLD_BACKUPS" ]; then
    log_info "Suppression des backups obsolètes:"
    echo "$OLD_BACKUPS" | while read -r old_backup; do
        log_info "  - $(basename "$old_backup")"
        rm -f "$old_backup"
        rm -f "${old_backup}.sha256" 2>/dev/null || true
    done
else
    log_info "Aucun backup obsolète à supprimer"
fi

# ═══════════════════════════════════════════════════════════════════
# STATISTIQUES FINALES
# ═══════════════════════════════════════════════════════════════════

log_info "📊 Statistiques finales"

REMAINING_BACKUPS=$(find "$BACKUP_DIR" -name "linkedin_backup_*.db*" -type f | wc -l)
TOTAL_BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Backup terminé avec succès"
echo "═══════════════════════════════════════════════════════════════"
echo "📁 Fichier de backup : $(basename "$BACKUP_FULL_PATH")"
echo "📊 Taille           : $FINAL_SIZE (source: $DB_SIZE)"
echo "🗂️  Backups stockés  : $REMAINING_BACKUPS (max: $RETENTION_DAYS jours)"
echo "💾 Espace total     : $TOTAL_BACKUP_SIZE"
echo "📍 Répertoire       : $BACKUP_DIR"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Liste des backups disponibles
log_info "📋 Backups disponibles (triés par date):"
ls -lht "$BACKUP_DIR"/linkedin_backup_*.db* | head -n 10 | awk '{printf "  %s %s  %s\n", $6, $7, $9}'

echo ""
log_info "💡 Pour restaurer un backup:"
echo "  gunzip -c ${BACKUP_FULL_PATH} > /app/data/linkedin.db"
echo ""

exit 0
