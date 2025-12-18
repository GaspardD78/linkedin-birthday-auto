#!/bin/bash
# ==============================================================================
# SETUP AUTOMATED BACKUPS FOR LINKEDIN BOT
# ==============================================================================
# Creates daily automated database backups with rotation and integrity checks
# Runs: sudo ./scripts/setup_automated_backups.sh
# ==============================================================================

set -euo pipefail

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

# Logging functions
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${PROJECT_DIR}/data/backups"
DB_PATH="${PROJECT_DIR}/data/linkedin.db"
BACKUP_SCRIPT="/usr/local/bin/linkedin-backup-daily.sh"
LOG_FILE="/var/log/linkedin-backup.log"
RETENTION_DAYS=30

echo ""
echo -e "${BOLD}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║          AUTOMATED BACKUP SETUP FOR LINKEDIN BOT               ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running with sudo
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run with sudo"
    echo "Usage: sudo ./scripts/setup_automated_backups.sh"
    exit 1
fi

log_info "Project directory: $PROJECT_DIR"
log_info "Database path: $DB_PATH"
log_info "Backup directory: $BACKUP_DIR"
log_info "Retention: $RETENTION_DAYS days"

# ============================================================================
# PHASE 1: CREATE BACKUP DIRECTORY
# ============================================================================
log_info "Creating backup directory..."
mkdir -p "$BACKUP_DIR"
chmod 755 "$BACKUP_DIR"
log_success "Backup directory ready: $BACKUP_DIR"

# ============================================================================
# PHASE 2: CREATE DAILY BACKUP SCRIPT
# ============================================================================
log_info "Creating daily backup script..."

sudo tee "$BACKUP_SCRIPT" > /dev/null <<'BACKUP_SCRIPT_EOF'
#!/bin/bash
# LinkedIn Bot Daily Backup Script
# Auto-executed by cron at 2:00 AM daily
# Performs: Dump → Compress → Integrity Check → Rotate

set -euo pipefail

BACKUP_DIR="/home/user/linkedin-birthday-auto/data/backups"
DB_PATH="/home/user/linkedin-birthday-auto/data/linkedin.db"
RETENTION_DAYS=30
LOG_FILE="/var/log/linkedin-backup.log"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Generate timestamped filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/linkedin_${TIMESTAMP}.db.gz"
TEMP_SQL="/tmp/linkedin_backup_temp_${TIMESTAMP}.sql"

# Logging function
log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_msg "═══════════════════════════════════════════════════════════"
log_msg "🔄 Starting backup cycle..."

# ===== STEP 1: DUMP DATABASE =====
if ! sqlite3 "$DB_PATH" ".dump" > "$TEMP_SQL"; then
    log_msg "❌ ERROR: Failed to dump database"
    rm -f "$TEMP_SQL"
    exit 1
fi
log_msg "✅ Step 1: Database dumped to SQL"

# ===== STEP 2: COMPRESS =====
if ! gzip -9 < "$TEMP_SQL" > "$BACKUP_FILE"; then
    log_msg "❌ ERROR: Failed to compress backup"
    rm -f "$TEMP_SQL"
    exit 1
fi
log_msg "✅ Step 2: SQL compressed (gzip -9)"

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log_msg "   Backup size: $BACKUP_SIZE"

# ===== STEP 3: VERIFY INTEGRITY =====
if ! sqlite3 < <(gunzip < "$BACKUP_FILE") "PRAGMA integrity_check;" > /dev/null 2>&1; then
    log_msg "❌ ERROR: Backup integrity check FAILED"
    log_msg "   Backup file deleted: $BACKUP_FILE"
    rm -f "$BACKUP_FILE"
    rm -f "$TEMP_SQL"
    exit 1
fi
log_msg "✅ Step 3: Integrity check PASSED"

# ===== STEP 4: CLEANUP TEMP FILES =====
rm -f "$TEMP_SQL"
log_msg "✅ Step 4: Temporary files cleaned"

# ===== STEP 5: ROTATE OLD BACKUPS =====
EXPIRED_COUNT=$(find "$BACKUP_DIR" -name "linkedin_*.db.gz" -mtime +$RETENTION_DAYS | wc -l)
if [ $EXPIRED_COUNT -gt 0 ]; then
    find "$BACKUP_DIR" -name "linkedin_*.db.gz" -mtime +$RETENTION_DAYS -delete
    log_msg "✅ Step 5: Rotated $EXPIRED_COUNT expired backups (>$RETENTION_DAYS days)"
else
    log_msg "✅ Step 5: No expired backups to rotate"
fi

# ===== STEP 6: BACKUP STATS =====
BACKUP_SIZE_TOTAL=$(du -sh "$BACKUP_DIR" | cut -f1)
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "linkedin_*.db.gz" | wc -l)
log_msg "📊 Storage stats:"
log_msg "   Total backups: $BACKUP_COUNT"
log_msg "   Total storage: $BACKUP_SIZE_TOTAL"

log_msg "✅ Backup cycle completed successfully"
log_msg "═══════════════════════════════════════════════════════════"

exit 0
BACKUP_SCRIPT_EOF

chmod +x "$BACKUP_SCRIPT"
log_success "Backup script created: $BACKUP_SCRIPT"

# ============================================================================
# PHASE 3: CREATE LOG FILE
# ============================================================================
log_info "Creating log file..."
sudo touch "$LOG_FILE"
sudo chmod 666 "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup log initialized" >> "$LOG_FILE"
log_success "Log file ready: $LOG_FILE"

# ============================================================================
# PHASE 4: SETUP CRON JOB
# ============================================================================
log_info "Setting up cron job..."

# Check if cron job already exists
if sudo crontab -l 2>/dev/null | grep -q "linkedin-backup-daily.sh"; then
    log_warn "Cron job already exists, skipping creation"
else
    # Add cron job for 2:00 AM daily (02:00)
    (sudo crontab -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT >> $LOG_FILE 2>&1") | sudo crontab -
    log_success "Cron job installed (daily at 02:00 AM)"
fi

# Verify cron job
echo ""
log_info "Cron job verification:"
sudo crontab -l | grep linkedin-backup || log_warn "No cron job found (may need manual verification)"

# ============================================================================
# PHASE 5: PERFORM INITIAL BACKUP
# ============================================================================
log_info "Running initial backup..."
if sudo "$BACKUP_SCRIPT" >> "$LOG_FILE" 2>&1; then
    log_success "Initial backup completed successfully"
else
    log_warn "Initial backup failed - check log for details: $LOG_FILE"
fi

# ============================================================================
# PHASE 6: SUMMARY & INSTRUCTIONS
# ============================================================================
echo ""
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║           ✅ AUTOMATED BACKUPS CONFIGURED                      ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BOLD}📋 CONFIGURATION SUMMARY${NC}"
echo "  🗂️  Backup Directory: $BACKUP_DIR"
echo "  📜 Backup Script: $BACKUP_SCRIPT"
echo "  📅 Schedule: Daily at 02:00 AM"
echo "  🔄 Rotation: Keep $RETENTION_DAYS days of backups"
echo "  📝 Logs: $LOG_FILE"

echo ""
echo -e "${BOLD}✅ NEXT STEPS${NC}"
echo "  1. Verify backups are working:"
echo "     tail -f $LOG_FILE"
echo ""
echo "  2. Check backup directory:"
echo "     ls -lh $BACKUP_DIR/"
echo ""
echo "  3. Test restore procedure:"
echo "     # See docs/DISASTER_RECOVERY.md § Backup Verification"
echo ""
echo "  4. Optional: Setup cloud backup"
echo "     # See docs/BACKUP_STRATEGY.md § External Backup"
echo ""

echo -e "${BOLD}📖 DOCUMENTATION${NC}"
echo "  • Backup strategy: docs/BACKUP_STRATEGY.md"
echo "  • Disaster recovery: docs/DISASTER_RECOVERY.md"
echo "  • Backup verification: docs/DISASTER_RECOVERY.md § 8"
echo ""

log_success "Automated backup setup complete!"
exit 0
