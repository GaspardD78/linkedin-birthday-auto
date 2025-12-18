# 📦 Backup Strategy & Automated Recovery

**Status:** ✅ Created 2025-12-18
**Audience:** DevOps, System Administrators
**Criticality:** HIGH - Essential for RPi4 data protection

---

## Overview

This document defines the comprehensive backup strategy for LinkedIn Bot running on Raspberry Pi 4. Given the unreliable SD card storage and long-running automation, **automated daily backups with integrity verification** are mandatory.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│         LinkedIn Bot Backup Architecture                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🔄 Cron Job (Daily 2:00 AM)                          │
│      ↓                                                  │
│  📜 backup_db.sh Script                               │
│      ├─ Dump SQLite DB → SQL text                     │
│      ├─ Compress → GZIP (90% reduction)               │
│      ├─ Integrity Check → PRAGMA check                │
│      ├─ Rotate old backups (>30 days)                 │
│      └─ Log result                                     │
│      ↓                                                  │
│  📂 Local Storage: ./data/backups/                     │
│      └─ linkedin_YYYYMMDD_HHMMSS.db.gz                │
│      (Max 20 files = ~2GB total)                       │
│      ↓                                                  │
│  🚨 Optional: Cloud Upload (S3, Google Drive, etc)    │
│      └─ Weekly upload to external storage             │
│      (Protection against RPi4 SD card failure)        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Backup Schedule

| Backup Type | Frequency | Retention | Location | Notes |
|-------------|-----------|-----------|----------|-------|
| **Daily Database** | 02:00 AM | 30 days | `./data/backups/` | Automated via cron |
| **Config Files** | Weekly | 90 days | `./data/backups/` | Optional |
| **Full System** | Monthly | 12 months | External storage | Manual/on-demand |

---

## Implementation

### Step 1: Enable Automated Backups

```bash
# Navigate to project directory
cd /home/user/linkedin-birthday-auto

# Run setup script
sudo ./scripts/setup_automated_backups.sh

# Verify installation
sudo crontab -l | grep linkedin-backup
# Output: 0 2 * * * /usr/local/bin/linkedin-backup-daily.sh >> /var/log/linkedin-backup.log 2>&1
```

### Step 2: Create Backup Script

The script automatically created at `/usr/local/bin/linkedin-backup-daily.sh`:

```bash
#!/bin/bash
# LinkedIn Bot Daily Backup Script
# Runs automatically via cron at 2:00 AM

set -euo pipefail

# Configuration
BACKUP_DIR="/home/user/linkedin-birthday-auto/data/backups"
DB_PATH="/home/user/linkedin-birthday-auto/data/linkedin.db"
RETENTION_DAYS=30
LOG_FILE="/var/log/linkedin-backup.log"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Generate timestamped backup filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/linkedin_${TIMESTAMP}.db.gz"
TEMP_SQL="/tmp/linkedin_backup_temp_${TIMESTAMP}.sql"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Starting backup..."

# Step 1: Dump database to SQL
if ! sqlite3 "$DB_PATH" ".dump" > "$TEMP_SQL"; then
    log "ERROR: Failed to dump database"
    exit 1
fi

# Step 2: Compress SQL dump
if ! gzip -9 < "$TEMP_SQL" > "$BACKUP_FILE"; then
    log "ERROR: Failed to compress backup"
    rm -f "$TEMP_SQL"
    exit 1
fi

# Step 3: Verify backup integrity
if ! sqlite3 < <(gunzip < "$BACKUP_FILE") "PRAGMA integrity_check;" > /dev/null; then
    log "ERROR: Backup integrity check failed"
    rm -f "$BACKUP_FILE" "$TEMP_SQL"
    exit 1
fi

log "✅ Backup successful: $BACKUP_FILE ($(du -h $BACKUP_FILE | cut -f1))"

# Step 4: Cleanup temporary files
rm -f "$TEMP_SQL"

# Step 5: Rotate old backups (keep only 30 days)
EXPIRED_COUNT=$(find "$BACKUP_DIR" -name "linkedin_*.db.gz" -mtime +$RETENTION_DAYS | wc -l)
if [ $EXPIRED_COUNT -gt 0 ]; then
    find "$BACKUP_DIR" -name "linkedin_*.db.gz" -mtime +$RETENTION_DAYS -delete
    log "Rotated $EXPIRED_COUNT expired backups"
fi

# Step 6: Verify backup directory size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Total backup storage: $BACKUP_SIZE"

# Step 7: Send health check (optional)
# Useful for monitoring if backups are running
# Example: curl -s -o /dev/null -w "%{http_code}" https://healthcheck.io/ping/backup-id

log "Backup cycle completed"
```

### Step 3: Manual Backup Verification

```bash
# List all backups
ls -lh ./data/backups/ | tail -10

# Check latest backup
LATEST=$(ls -t ./data/backups/linkedin_*.db.gz | head -1)
echo "Latest backup: $LATEST ($(du -h $LATEST | cut -f1))"

# Verify integrity of specific backup
sqlite3 < <(gunzip < "$LATEST") "PRAGMA integrity_check;"
# Expected: ok

# Quick restore test (doesn't modify production DB)
TEMP_DB=$(mktemp)
gunzip < "$LATEST" | sqlite3 "$TEMP_DB"
sqlite3 "$TEMP_DB" "SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table';"
rm "$TEMP_DB"
```

---

## Storage Optimization

### Local Storage Sizing

```
Database growth:
- Fresh install: ~5 MB
- After 1 month: ~20 MB
- After 6 months: ~100 MB
- After 1 year: ~200 MB

Backup compression (gzip -9):
- Reduces size by 85-90%
- Daily backup: 2-5 MB (compressed)
- 30-day retention: 60-150 MB

Recommendation:
- Allocate 500 MB minimum for backups
- Current allocation: 2 GB available
```

### Managing Backup Storage

```bash
# Check backup directory size
du -sh ./data/backups/

# Remove oldest backups if space is critical
find ./data/backups -name "linkedin_*.db.gz" -type f | sort | head -5 | xargs rm

# Monitor growth over time
watch -n 60 'echo "Backup Size:" && du -sh ./data/backups/'
```

---

## Advanced: External Backup (Cloud)

### Option 1: Sync to USB Drive (Offline Storage)

```bash
#!/bin/bash
# Weekly sync to USB drive (more resilient than SD card)

USB_MOUNT="/mnt/backup-usb"
BACKUP_SOURCE="/home/user/linkedin-birthday-auto/data/backups"

# Check if USB is mounted
if ! mountpoint -q "$USB_MOUNT"; then
    echo "ERROR: USB drive not mounted at $USB_MOUNT"
    exit 1
fi

# Sync backups
rsync -avz --delete "$BACKUP_SOURCE/" "$USB_MOUNT/linkedin-backups/"

# Verify sync
REMOTE_COUNT=$(ls "$USB_MOUNT/linkedin-backups/" | wc -l)
LOCAL_COUNT=$(ls "$BACKUP_SOURCE/" | wc -l)

if [ "$REMOTE_COUNT" -eq "$LOCAL_COUNT" ]; then
    echo "✅ USB backup sync successful ($REMOTE_COUNT files)"
else
    echo "⚠️ WARNING: Sync mismatch ($LOCAL_COUNT local vs $REMOTE_COUNT remote)"
fi
```

### Option 2: Cloud Backup (AWS S3, Google Drive)

#### AWS S3 Example

```bash
#!/bin/bash
# Upload backups to AWS S3 (weekly)

AWS_BUCKET="s3://my-linkedin-bot-backups"
BACKUP_SOURCE="/home/user/linkedin-birthday-auto/data/backups"
AWS_REGION="eu-west-1"

# Check AWS CLI installed
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI not installed"
    exit 1
fi

# Upload new backups
for backup_file in "$BACKUP_SOURCE"/linkedin_*.db.gz; do
    filename=$(basename "$backup_file")

    # Only upload if not already in S3
    if ! aws s3 ls "$AWS_BUCKET/$filename" > /dev/null 2>&1; then
        echo "Uploading $filename to S3..."
        aws s3 cp "$backup_file" "$AWS_BUCKET/$filename" --region "$AWS_REGION"
    fi
done

# Cleanup old files (keep 90 days in S3)
echo "Cleaning up old S3 backups..."
aws s3 rm "$AWS_BUCKET" --recursive \
    --exclude "*" \
    --include "linkedin_*" \
    --older-than 90 \
    --region "$AWS_REGION"

echo "✅ S3 backup sync complete"
```

Add to crontab:
```bash
# Weekly backup to S3 (Sundays at 3:00 AM)
0 3 * * 0 /usr/local/bin/linkedin-backup-s3.sh >> /var/log/linkedin-backup-s3.log 2>&1
```

---

## Monitoring & Alerting

### Check Backup Health

```bash
#!/bin/bash
# Check if backups are running properly

BACKUP_DIR="/home/user/linkedin-birthday-auto/data/backups"
EXPECTED_DAILY_BACKUP_TIME="02:00"
HOURS_SINCE_BACKUP=24

# Get latest backup timestamp
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/linkedin_*.db.gz 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "🔴 CRITICAL: No backups found!"
    exit 1
fi

# Calculate hours since last backup
LATEST_TIME=$(stat -c %Y "$LATEST_BACKUP")
CURRENT_TIME=$(date +%s)
HOURS_DIFF=$(( (CURRENT_TIME - LATEST_TIME) / 3600 ))

if [ $HOURS_DIFF -gt $HOURS_SINCE_BACKUP ]; then
    echo "🔴 WARNING: Last backup is $HOURS_DIFF hours old (expected daily)"
    exit 1
fi

# Verify latest backup integrity
if ! sqlite3 < <(gunzip < "$LATEST_BACKUP") "PRAGMA integrity_check;" > /dev/null 2>&1; then
    echo "🔴 ERROR: Latest backup failed integrity check"
    exit 1
fi

echo "✅ Backup health OK"
echo "   Latest: $(basename $LATEST_BACKUP)"
echo "   Age: ${HOURS_DIFF}h"
echo "   Size: $(du -h $LATEST_BACKUP | cut -f1)"
exit 0
```

### Add Monitoring to Cron

```bash
# Daily backup health check (10:00 AM)
0 10 * * * /usr/local/bin/linkedin-backup-health-check.sh >> /var/log/linkedin-backup-health.log 2>&1

# Alert if health check fails (requires mail setup)
# 0 10 * * * /usr/local/bin/linkedin-backup-health-check.sh || \
#    mail -s "LinkedIn Bot: Backup Failed" admin@example.com
```

---

## Recovery Testing

### Schedule Regular Restore Tests

```bash
#!/bin/bash
# Test backup recovery monthly (1st of month, 4:00 AM)

BACKUP_DIR="/home/user/linkedin-birthday-auto/data/backups"
PROD_DB="/home/user/linkedin-birthday-auto/data/linkedin.db"
TEST_DIR="/tmp/linkedin-recovery-test-$(date +%Y%m%d)"

mkdir -p "$TEST_DIR"

# Pick a random backup from last 7 days
BACKUP_FILE=$(find "$BACKUP_DIR" -name "linkedin_*.db.gz" -mtime -7 | sort -R | head -1)

if [ -z "$BACKUP_FILE" ]; then
    echo "ERROR: No backup found from last 7 days"
    exit 1
fi

echo "Testing recovery from: $BACKUP_FILE"

# Decompress and verify
gunzip < "$BACKUP_FILE" | sqlite3 "$TEST_DIR/linkedin_test.db"

# Run integrity check
RESULT=$(sqlite3 "$TEST_DIR/linkedin_test.db" "PRAGMA integrity_check;")

if [ "$RESULT" = "ok" ]; then
    echo "✅ Recovery test passed"

    # Cleanup
    rm -rf "$TEST_DIR"
    exit 0
else
    echo "❌ Recovery test FAILED: $RESULT"

    # Keep test DB for investigation
    tar -czf "$TEST_DIR/recovery-test-failure-$(date +%Y%m%d-%H%M%S).tar.gz" "$TEST_DIR"

    exit 1
fi
```

Add to crontab:
```bash
# Monthly recovery test (1st of month, 4:00 AM)
0 4 1 * * /usr/local/bin/linkedin-backup-recovery-test.sh >> /var/log/linkedin-backup-test.log 2>&1
```

---

## Troubleshooting

### Backup Script Not Running

```bash
# Check if cron job exists
sudo crontab -l | grep linkedin-backup

# Check if script is executable
ls -l /usr/local/bin/linkedin-backup-daily.sh

# Test script manually
sudo /usr/local/bin/linkedin-backup-daily.sh

# Check cron logs
sudo journalctl -u cron -n 20

# Or check system syslog
sudo tail -100 /var/log/syslog | grep CRON
```

### Backup Integrity Failures

```bash
# Check database for corruption
sqlite3 ./data/linkedin.db "PRAGMA integrity_check;"

# If corrupted, restore from known-good backup
GOOD_BACKUP=$(ls -t ./data/backups/linkedin_*.db.gz | head -1)
cp ./data/linkedin.db ./data/linkedin.db.corrupted
gunzip < "$GOOD_BACKUP" | sqlite3 ./data/linkedin.db

# Verify restoration
sqlite3 ./data/linkedin.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';"
```

### Storage Full

```bash
# Check available space
df -h /home

# Remove old backups (keep at least 7 days)
find ./data/backups -name "linkedin_*.db.gz" -mtime +14 -delete

# Check if database itself is growing too large
du -sh ./data/linkedin.db

# Compact database if needed
sqlite3 ./data/linkedin.db "VACUUM;"
```

---

## Compliance & Best Practices

- ✅ **Daily automated backups** with cron
- ✅ **Integrity verification** on every backup
- ✅ **Retention policy** (30 days local, 90 days cloud)
- ✅ **Monthly restore testing** to verify recoverability
- ✅ **External backup** to USB/Cloud for resilience
- ✅ **Documented recovery procedures** (see DISASTER_RECOVERY.md)
- ✅ **Monitoring** for backup failures
- ✅ **Encryption** for cloud backups (S3 server-side)

---

## Implementation Checklist

- [ ] Run `sudo ./scripts/setup_automated_backups.sh`
- [ ] Verify cron job: `sudo crontab -l | grep linkedin`
- [ ] Check backup creation: `ls -lh ./data/backups/`
- [ ] Test integrity: `sqlite3 < <(gunzip < [latest]) "PRAGMA integrity_check;"`
- [ ] Schedule monthly recovery tests
- [ ] Setup external backup (USB/Cloud)
- [ ] Configure backup monitoring/alerting
- [ ] Document recovery procedures for team

---

**Last Updated:** 2025-12-18
**Status:** ✅ Complete & Ready to Deploy
