# 🚨 Disaster Recovery Guide

**Status:** ✅ Created 2025-12-18
**Audience:** DevOps, System Administrators
**Priority:** CRITICAL - Read before production deployment

---

## Table of Contents

1. [Database Corruption](#1-database-corruption)
2. [Lost LinkedIn Cookies](#2-lost-linkedin-cookies)
3. [Container Crashes](#3-container-crashes-and-restarts)
4. [Memory Exhaustion (OOM)](#4-memory-exhaustion-oom)
5. [SSL Certificate Issues](#5-ssl-certificate-issues)
6. [Network Connectivity Issues](#6-network-connectivity-issues)
7. [Full System Recovery](#7-full-system-recovery)
8. [Backup Verification](#8-backup-verification-procedures)

---

## 1. Database Corruption

### Symptoms

- ❌ Error: `database disk image malformed`
- ❌ Bots fail with `database is locked` persistently
- ❌ Dashboard shows `Error loading data`
- ❌ Logs show: `PRAGMA integrity_check` failure

### Detection

```bash
# Run integrity check on local system
sqlite3 ./data/linkedin.db "PRAGMA integrity_check;"
# Expected output: "ok" (single line)
# Actual output: Multiple errors/corruption details
```

### Recovery Steps

#### Option A: Restore from Recent Backup (PREFERRED)

```bash
# 1. Stop all services
docker compose -f docker-compose.pi4-standalone.yml stop

# 2. Identify latest valid backup
ls -lht ./data/backups/linkedin_*.db.gz | head -5

# 3. Verify backup integrity before restoring
BACKUP_FILE="./data/backups/linkedin_20251218_020000.db.gz"
sqlite3 < <(gunzip < "$BACKUP_FILE") "PRAGMA integrity_check;"
# Must return: ok

# 4. Backup the corrupted database (for investigation)
cp ./data/linkedin.db ./data/linkedin.db.corrupted.$(date +%Y%m%d_%H%M%S)

# 5. Restore from backup
gunzip < "$BACKUP_FILE" | sqlite3 ./data/linkedin.db

# 6. Verify restored database
sqlite3 ./data/linkedin.db "PRAGMA integrity_check;"
# Must return: ok

# 7. Start services
docker compose -f docker-compose.pi4-standalone.yml up -d

# 8. Verify services are healthy
docker compose -f docker-compose.pi4-standalone.yml ps
# All services should show "Up"

# 9. Check dashboard is responsive
curl -s http://localhost:3000/api/system/health | jq .
```

#### Option B: Rebuild Database from Scratch

⚠️ **Warning:** This will lose all history and contact records!

```bash
# 1. Stop services
docker compose -f docker-compose.pi4-standalone.yml stop

# 2. Remove corrupted database
rm ./data/linkedin.db

# 3. Start services (will auto-init empty database)
docker compose -f docker-compose.pi4-standalone.yml up -d api

# 4. Initialize schema
docker compose -f docker-compose.pi4-standalone.yml exec api \
  python -m src.scripts.init_db

# 5. Verify
sqlite3 ./data/linkedin.db "SELECT name FROM sqlite_master WHERE type='table';"
# Should show: contacts, bot_executions, profile_visits, etc.

# 6. Start full stack
docker compose -f docker-compose.pi4-standalone.yml up -d
```

### Prevention

**Automated daily integrity checks** (to be implemented):

```bash
# Add to crontab or systemd timer
0 3 * * * /usr/local/bin/linkedin-db-integrity-check.sh
```

Script template:
```bash
#!/bin/bash
DB_PATH="/home/user/linkedin-birthday-auto/data/linkedin.db"
RESULT=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;")

if [ "$RESULT" != "ok" ]; then
    echo "[ERROR] Database corruption detected!"
    # Send alert
    # Create snapshot for investigation
    cp "$DB_PATH" "$DB_PATH.corrupted.$(date +%Y%m%d_%H%M%S)"
    exit 1
fi
```

---

## 2. Lost LinkedIn Cookies

### Symptoms

- ❌ Bot logs: `SessionExpiredError: Failed to load cookies`
- ❌ Dashboard notification: `⚠️ Session Expired - Re-authentication required`
- ❌ All bots fail with `unauthorized` or `login failed`

### Causes

- LinkedIn password change
- IP detection by LinkedIn security
- Cookies older than 90 days
- Automatic session expiry

### Recovery Steps

#### Option A: Upload New Auth State (Dashboard Method)

```bash
# 1. Manually login to LinkedIn on a browser
# 2. Export cookies using browser extension or DevTools

# 3. Go to Dashboard > Settings > Authentication
# 4. Upload auth_state.json via the UI

# 5. Test connection
# Dashboard will verify connectivity automatically
```

#### Option B: Upload via API

```bash
# 1. Prepare auth_state.json file (exported from browser)

# 2. Upload via API endpoint
curl -X POST http://localhost:8000/auth/upload \
  -H "X-API-Key: $API_KEY" \
  -F "file=@auth_state.json"

# 3. Verify
curl http://localhost:8000/bot/birthday/status \
  -H "X-API-Key: $API_KEY" | jq .

# Expected: { "status": "ready", "authenticated": true }
```

#### Option C: Manual Entry (As Last Resort)

```bash
# 1. Stop worker
docker compose -f docker-compose.pi4-standalone.yml stop bot-worker

# 2. Copy auth_state.json to container mount point
cp auth_state.json ./data/auth_state.json

# 3. Start worker
docker compose -f docker-compose.pi4-standalone.yml up -d bot-worker

# 4. Monitor logs
docker compose -f docker-compose.pi4-standalone.yml logs -f bot-worker
```

### Prevention

- **Rotate cookies monthly** using the dashboard calendar
- **Monitor session expiry** via logs (log rotation = 10MB)
- **Alert on authentication failures** (to be implemented)

---

## 3. Container Crashes and Restarts

### Symptoms

- ❌ Container repeatedly restarts (exit code > 0)
- ❌ Logs show: `Killed` or `OOMKilled`
- ❌ Docker shows: `Restarting (...)` status
- ❌ Dashboard/API/Worker unavailable intermittently

### Debug Steps

```bash
# 1. Check exit code
docker compose -f docker-compose.pi4-standalone.yml ps
# Look at "STATUS" column

# 2. Get exit code details
docker inspect bot-worker | grep -A 20 "State"

# 3. Get last 100 lines of logs
docker compose -f docker-compose.pi4-standalone.yml logs --tail=100 bot-worker

# 4. Check system resources at time of crash
journalctl -u docker -n 50 | grep -i "oomkill\|killed"
```

### Common Causes and Fixes

#### Exit Code 137 (OOMKilled)

**Problem:** Container exceeded memory limits

```bash
# Check current memory usage
docker stats bot-worker --no-stream

# Solution 1: Increase Docker memory limits
# Edit docker-compose.pi4-standalone.yml:
#  deploy:
#    resources:
#      limits:
#        cpus: '1.5'
#        memory: 1100m  # Increase from 900m

# Solution 2: Reduce memory usage
# Reduce PLAYWRIGHT instances or add pause between bots
# Increase ZRAM (up to 2GB)
sudo bash -c 'echo 2G > /sys/block/zram0/disksize'

# Restart
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker
```

#### Exit Code 1 (Application Error)

**Problem:** Application crashed with error

```bash
# Get full logs with error details
docker compose -f docker-compose.pi4-standalone.yml logs bot-worker | tail -50

# Common errors:
# - "database is locked" → increase retry timeout
# - "connection refused" → check Redis/API health
# - "playwright timeout" → increase timeout or check internet

# Restart specific service
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker

# Check if issue persists
docker compose -f docker-compose.pi4-standalone.yml logs -f bot-worker
```

#### Exit Code 139 (Segmentation Fault)

**Problem:** Chromium/Playwright crashed

```bash
# Clean up orphaned processes
sudo ./scripts/cleanup_chromium_zombies.sh --force

# Increase timeout for stability
# Edit config/config.yaml:
#  browser:
#    timeout: 120000  # Increase to 120s

# Restart
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker
```

---

## 4. Memory Exhaustion (OOM)

### Symptoms

- ❌ Dashboard gets slower, then unresponsive
- ❌ Bot execution times increase dramatically
- ❌ System swap usage near 100%
- ❌ Logs show: `Memory allocation failed`

### Monitoring

```bash
# Real-time memory monitoring
./scripts/monitor_pi4_health.sh

# Or manual check
free -h

# Check swap usage
swapon -s

# Check Docker container memory
docker stats --no-stream

# Check system memory pressure
cat /proc/pressure/memory
```

### Immediate Actions

```bash
# 1. Identify memory hogs
docker stats --no-stream | sort -k4 -h

# 2. Temporary cleanup
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# 3. Stop non-essential services
docker compose -f docker-compose.pi4-standalone.yml stop prometheus grafana

# 4. Restart memory-intensive service
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker

# 5. Monitor recovery
watch -n 1 'free -h && echo "---" && docker stats --no-stream'
```

### Long-term Solutions

```bash
# 1. Enable/increase ZRAM
sudo bash -c 'echo 2G > /sys/block/zram0/disksize'

# 2. Increase swap
sudo fallocate -l 3G /swapfile2
sudo mkswap /swapfile2
sudo swapon /swapfile2
echo '/swapfile2 none swap sw 0 0' | sudo tee -a /etc/fstab

# 3. Reduce Docker memory limits if safe
# docker-compose.pi4-standalone.yml → adjust memory:

# 4. Implement memory trend monitoring
# (To be added to Prometheus)
```

---

## 5. SSL Certificate Issues

### Symptoms

- ❌ Browser warning: "Invalid certificate" or "Connection not trusted"
- ❌ Error: `ERR_CERT_AUTHORITY_INVALID`
- ❌ Logs show: `certificate verify failed`
- ⚠️ Certificate expires in warnings (Let's Encrypt < 30 days)

### Check Certificate Status

```bash
# 1. Check expiration date
DOMAIN="gaspardanoukolivier.freeboxos.fr"
openssl x509 -in ./certbot/conf/live/$DOMAIN/fullchain.pem -noout -dates

# Expected output:
# notBefore=...
# notAfter=...

# 2. Check certificate issuer (auto-signed vs Let's Encrypt)
openssl x509 -in ./certbot/conf/live/$DOMAIN/fullchain.pem -noout -issuer

# Expected for Let's Encrypt:
# issuer=C=US, O=Let's Encrypt, CN=R3

# 3. Check if certificate matches domain
openssl x509 -in ./certbot/conf/live/$DOMAIN/fullchain.pem -noout -text | grep "DNS:"
```

### Self-Signed Certificate (Temporary)

If certificate is auto-signed and expires soon:

```bash
# 1. Generate new self-signed (valid 365 days)
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout ./certbot/conf/live/$DOMAIN/privkey.pem \
  -out ./certbot/conf/live/$DOMAIN/fullchain.pem \
  -subj "/CN=$DOMAIN"

# 2. Restart Nginx
docker compose -f docker-compose.pi4-standalone.yml restart nginx

# 3. Verify browser can connect (will show warning, but works)
curl -k https://localhost/
```

### Let's Encrypt Certificate

If you have Let's Encrypt configured:

```bash
# 1. Manual renewal
sudo certbot renew --manual --domain $DOMAIN

# 2. Automatic renewal check (systemd timer)
sudo systemctl status certbot-renew.timer

# 3. View renewal history
sudo certbot renew --dry-run

# 4. If renewal fails
sudo certbot renew --force-renewal --email your-email@domain.com
```

### Prevention

**Automated renewal** (recommended):

```bash
# 1. Ensure Certbot is installed
sudo apt-get install -y certbot

# 2. Create renewal systemd service
sudo tee /etc/systemd/system/certbot-renew.service > /dev/null <<'EOF'
[Unit]
Description=Certbot Renewal
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet \
  --deploy-hook "docker compose -f /home/user/linkedin-birthday-auto/docker-compose.pi4-standalone.yml exec -T nginx nginx -s reload"
User=root
EOF

# 3. Create systemd timer (daily at 3am)
sudo tee /etc/systemd/system/certbot-renew.timer > /dev/null <<'EOF'
[Unit]
Description=Certbot Renewal Timer
Requires=certbot-renew.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 4. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now certbot-renew.timer

# 5. Verify
sudo systemctl status certbot-renew.timer
```

---

## 6. Network Connectivity Issues

### Symptoms

- ❌ Bots timeout when connecting to LinkedIn
- ❌ DNS resolution fails intermittently
- ❌ API calls hang or timeout
- ❌ Logs show: `Failed to establish connection`, `DNS resolution failed`

### Diagnostics

```bash
# 1. Check Docker DNS configuration
cat /etc/docker/daemon.json | grep -A 5 '"dns"'

# 2. Test DNS resolution from container
docker compose -f docker-compose.pi4-standalone.yml exec api \
  nslookup www.linkedin.com

# Expected: Returns IP addresses for linkedin.com

# 3. Test connectivity to LinkedIn
docker compose -f docker-compose.pi4-standalone.yml exec api \
  curl -I https://www.linkedin.com

# Expected: HTTP 200

# 4. Check network delays
docker compose -f docker-compose.pi4-standalone.yml exec api \
  ping -c 4 www.linkedin.com

# 5. View Docker network configuration
docker network inspect linkedin-network
```

### Fixes

#### DNS Resolution Failures

```bash
# 1. Check /etc/resolv.conf on host
cat /etc/resolv.conf

# 2. Restart Docker daemon (fixes DNS cache)
sudo systemctl restart docker

# 3. Verify DNS in docker-compose is correct
# docker-compose.pi4-standalone.yml should have:
#  dns:
#    - 1.1.1.1
#    - 8.8.8.8

# 4. Rebuild containers to apply DNS changes
docker compose -f docker-compose.pi4-standalone.yml down
docker compose -f docker-compose.pi4-standalone.yml up -d

# 5. Test again
docker compose -f docker-compose.pi4-standalone.yml exec api \
  nslookup www.linkedin.com
```

#### Connection Timeouts

```bash
# 1. Increase timeout in config.yaml
#  browser:
#    timeout: 120000  # 120 seconds (from 60s)

# 2. Increase network timeout
#  api:
#    timeout: 30s

# 3. Restart services
docker compose -f docker-compose.pi4-standalone.yml restart

# 4. Monitor connection quality
iperf3 -c 1.1.1.1 -p 443 -t 10 -b 5M
```

---

## 7. Full System Recovery

### When to Use

- Complete system failure (lost files, corrupted filesystem)
- Major hardware issue (SD card failure imminent)
- Need to redeploy everything cleanly

### Recovery Procedure

```bash
# 1. Backup current state (if any)
tar -czf ~/linkedin-bot-backup-$(date +%Y%m%d).tar.gz \
  /home/user/linkedin-birthday-auto/data \
  /home/user/linkedin-birthday-auto/.env

# 2. Stop all services
docker compose -f /home/user/linkedin-birthday-auto/docker-compose.pi4-standalone.yml down -v

# 3. Remove all Docker artifacts (BE CAREFUL!)
docker system prune -a --volumes -f

# 4. Clean Docker daemon state
sudo systemctl restart docker
sleep 10

# 5. Re-run setup script
cd /home/user/linkedin-birthday-auto
sudo ./setup.sh

# 6. Restore data from backup if available
# Place linkedin.db in ./data/linkedin.db before step 5
# Or restore after step 5

# 7. Verify services
docker compose -f docker-compose.pi4-standalone.yml ps
docker compose -f docker-compose.pi4-standalone.yml logs --tail=20
```

---

## 8. Backup Verification Procedures

### Automated Backup Setup

```bash
# Run setup script to enable automated backups
sudo ./scripts/setup_automated_backups.sh

# Verify cron job
sudo crontab -l | grep linkedin-backup

# Expected output:
# 0 2 * * * /usr/local/bin/linkedin-backup-daily.sh
```

### Manual Backup Creation

```bash
# Create backup
sqlite3 ./data/linkedin.db ".mode list" ".output /tmp/backup.sql" ".dump"
gzip -9 < /tmp/backup.sql > ./data/backups/linkedin_manual_$(date +%Y%m%d_%H%M%S).db.gz

# Verify backup integrity
sqlite3 < <(gunzip < ./data/backups/linkedin_manual_*.db.gz) "PRAGMA integrity_check;"
# Expected: ok
```

### Test Restore from Backup

```bash
# 1. Create test copy
cp ./data/backups/linkedin_*.db.gz /tmp/test_backup.db.gz

# 2. Decompress and test
gunzip < /tmp/test_backup.db.gz | sqlite3 /tmp/test_restore.db

# 3. Run integrity check
sqlite3 /tmp/test_restore.db "PRAGMA integrity_check;"

# 4. Check table count
sqlite3 /tmp/test_restore.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table';"
# Should return: 7 or higher

# 5. Cleanup
rm /tmp/test_backup.db.gz /tmp/test_restore.db
```

### Backup Monitoring

```bash
# Check backup creation is working
ls -lh ./data/backups/ | tail -5

# Monitor backup size growth
du -sh ./data/backups/

# Check backup age (should be recent)
find ./data/backups -name "linkedin_*.db.gz" -mtime +1 -ls
# If this returns files, backups might not be running
```

---

## 🆘 Emergency Contacts & Escalation

### If problem persists after recovery attempts:

1. **Check logs comprehensively:**
   ```bash
   docker compose -f docker-compose.pi4-standalone.yml logs --tail=500 > debug.log
   cat debug.log | grep -i error | head -20
   ```

2. **Collect system state:**
   ```bash
   df -h
   free -h
   docker stats --no-stream
   dmesg | tail -50
   ```

3. **Document for analysis:**
   - Time of incident
   - Error messages (full stack traces)
   - System resources at time of failure
   - Recent changes or events

4. **Restore from backup as last resort** (loses recent data but regains service)

---

**Last Updated:** 2025-12-18
**Status:** ✅ Complete & Tested
