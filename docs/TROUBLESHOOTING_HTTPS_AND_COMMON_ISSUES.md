# Troubleshooting Guide - HTTPS & Common Issues

This guide addresses the most common issues found in the LinkedIn Birthday Auto deployment.

## Table of Contents

1. [HTTPS Certificate Warning (Temporary Certificate)](#1-https-certificate-warning)
2. [Let's Encrypt ACME Challenge Failure](#2-lets-encrypt-acme-challenge-failure)
3. [Login/Password Input Issues](#3-loginpassword-input-issues)
4. [API Health Check 404 Error](#4-api-health-check-404-error)
5. [HAProxy Timeout Warning](#5-haproxy-timeout-warning)
6. [OpenTelemetry Warning](#6-opentelemetry-warning)
7. [Docker Image Pull Failures (Raspberry Pi 4 / ARM64)](#7-docker-image-pull-failures-raspberry-pi-4--arm64)

---

## 1. HTTPS Certificate Warning

### Symptom

Browser shows "Non sécurisé" or "Not Secure" warning when accessing the dashboard. Certificate viewer shows:
- **Émetteur/Issuer**: Same as domain (e.g., `gaspardanoukolivier.freeboxos.fr`)
- **Organization**: `<Ne fait pas partie du certificat>` or `Development`
- **Type**: Temporary Certificate or Self-Signed

### Root Cause

The setup script claimed to obtain Let's Encrypt certificates but actually used/created self-signed certificates. This happens when:
1. Let's Encrypt challenge fails (domain not accessible from internet)
2. Ports 80/443 not properly forwarded
3. DNS not resolving correctly
4. Nginx configuration uses localhost certificates instead of domain certificates

### How to Identify

Check the certificate issuer:

```bash
openssl x509 -in certbot/conf/live/<your-domain>/fullchain.pem -noout -issuer
```

**Self-signed certificate** shows:
```
Issuer: CN = localhost
# or
Issuer: CN = gaspardanoukolivier.freeboxos.fr
```

**Let's Encrypt certificate** shows:
```
Issuer: C = US, O = Let's Encrypt, CN = R3
# or
Issuer: C = US, O = Let's Encrypt, CN = R10
```

### Solution

#### Quick Fix (Automated)

Run the certificate fix script:

```bash
cd /home/gaspard/linkedin-birthday-auto
sudo ./scripts/fix_https_certificates.sh
```

This script will:
1. Diagnose the current certificate status
2. Attempt to obtain Let's Encrypt certificates
3. Fall back to self-signed if Let's Encrypt fails
4. Generate proper HTTPS Nginx configuration
5. Restart services and validate

#### Manual Fix

**Step 1: Verify Domain Accessibility**

```bash
# From outside your network (or use online tools like https://check-host.net/)
curl -I http://gaspardanoukolivier.freeboxos.fr

# Should return HTTP 200 or 30x, not timeout
```

**Step 2: Check Port Forwarding**

Ensure your router/firewall forwards:
- Port 80 (HTTP) → Raspberry Pi IP:80
- Port 443 (HTTPS) → Raspberry Pi IP:443

**Step 3: Obtain Let's Encrypt Certificate**

```bash
cd /home/gaspard/linkedin-birthday-auto
sudo ./scripts/setup_letsencrypt.sh --force
```

**Step 4: Verify Certificate**

```bash
# Check certificate issuer
openssl x509 -in certbot/conf/live/gaspardanoukolivier.freeboxos.fr/fullchain.pem -noout -issuer

# Should show "O = Let's Encrypt"
```

**Step 5: Generate HTTPS Configuration**

```bash
export DOMAIN=gaspardanoukolivier.freeboxos.fr
envsubst '${DOMAIN}' < deployment/nginx/linkedin-bot-https.conf.template > deployment/nginx/linkedin-bot.conf
```

**Step 6: Restart Nginx**

```bash
docker compose restart nginx
```

**Step 7: Validate**

```bash
# Test HTTPS
curl -I https://gaspardanoukolivier.freeboxos.fr

# Check certificate in browser
# Should show valid Let's Encrypt certificate
```

### If Let's Encrypt Fails

If you cannot obtain Let's Encrypt certificates (domain not publicly accessible), you have two options:

**Option 1: Use Self-Signed Certificate (Development/Local)**

The current self-signed certificate will work but browsers will show warnings.

**Option 2: Use Cloudflare Tunnel (Recommended for NAT/CG-NAT)**

If behind CG-NAT or cannot forward ports, use Cloudflare Tunnel:
- Provides free HTTPS without port forwarding
- See: [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

---

## 2. Let's Encrypt ACME Challenge Failure

### Symptom

When running `setup.sh` or `scripts/setup_letsencrypt.sh`, you see:

```
[ERROR] ❌ Nginx ne peut PAS servir les fichiers ACME challenge
[ERROR] ❌ ÉCHEC CRITIQUE: Impossible d'obtenir un certificat Let's Encrypt
```

The diagnostic shows that port 80 is accessible and DNS resolves correctly, but the ACME challenge test fails.

### Root Cause

The Nginx configuration is not using the ACME bootstrap template, which includes the critical `location /.well-known/acme-challenge/` block needed for Let's Encrypt validation. This typically happens when:

1. The setup script was interrupted before Phase 5.1 completed
2. The Nginx configuration was manually overwritten with the wrong template
3. The `linkedin-bot.conf` file is using the default LAN template instead of ACME bootstrap

### How to Identify

Check the current Nginx configuration:

```bash
head -5 deployment/nginx/linkedin-bot.conf
```

**Incorrect (LAN mode)**:
```
# Configuration Nginx - LinkedIn Birthday Auto Bot (DEFAULT - LAN MODE)
```

**Correct (ACME bootstrap)**:
```
# Configuration Nginx - LinkedIn Birthday Auto Bot (MODE ACME BOOTSTRAP)
```

### Solution

#### Quick Fix

Regenerate the ACME bootstrap configuration:

```bash
cd /home/gaspard/linkedin-birthday-auto

# Generate ACME bootstrap config
DOMAIN=gaspardanoukolivier.freeboxos.fr
sed "s/\${DOMAIN}/$DOMAIN/g" deployment/nginx/linkedin-bot-acme-bootstrap.conf.template > deployment/nginx/linkedin-bot.conf

# For freeboxos.fr domains, remove www subdomain (not supported)
sed -i "s/ www\.${DOMAIN}//g" deployment/nginx/linkedin-bot.conf

# Create ACME challenge directory
mkdir -p certbot/www/.well-known/acme-challenge
chmod -R 755 certbot

# Restart Nginx
docker compose restart nginx

# Wait 5 seconds for Nginx to fully start
sleep 5

# Retry Let's Encrypt
./scripts/setup_letsencrypt.sh --force
```

#### Prevention

The issue has been fixed in the codebase (commits after this documentation). The `setup.sh` script now:
- Automatically selects the correct Nginx template based on certificate state
- Removes `www` subdomain for `.freeboxos.fr` domains automatically
- Validates Nginx can serve ACME challenges before attempting Let's Encrypt

If you still encounter this issue with the latest code, please report it.

### Additional Diagnostics

If the fix above doesn't work, verify these conditions:

**1. Check Nginx logs:**
```bash
docker compose logs nginx --tail 30
```

**2. Test ACME challenge serving manually:**
```bash
# Create test file
echo "test" > certbot/www/.well-known/acme-challenge/test
chmod 644 certbot/www/.well-known/acme-challenge/test

# Test from host
curl http://localhost/.well-known/acme-challenge/test

# Should return "test"
```

**3. Check Docker volume mounts:**
```bash
docker compose exec nginx ls -la /var/www/certbot/.well-known/acme-challenge/

# Should show the test file
```

**4. Verify Nginx config in container:**
```bash
docker compose exec nginx cat /etc/nginx/conf.d/default.conf | grep -A5 "acme-challenge"

# Should show:
#   location /.well-known/acme-challenge/ {
#       root /var/www/certbot;
#       allow all;
#   }
```

---

## 3. Login/Password Input Issues

### Symptom

Cannot enter text in login or password fields on the dashboard. Input fields reset automatically or don't accept text.

### Root Cause

This is typically caused by:
1. **HTTP instead of HTTPS**: Modern browsers restrict form inputs on non-HTTPS connections
2. **Content Security Policy (CSP) issues**: Nginx configuration may be blocking form functionality
3. **JavaScript errors**: Frontend issues related to security context

### Solution

**Fix 1: Enable HTTPS (Primary Solution)**

Follow the [HTTPS Certificate Warning](#1-https-certificate-warning) section above to enable proper HTTPS.

**Fix 2: Check Browser Console**

1. Open browser Developer Tools (F12)
2. Check Console tab for errors
3. Look for CSP or mixed content errors

**Fix 3: Temporary Workaround (Development Only)**

If you must use HTTP temporarily:

1. Use Chrome/Edge with special flags (NOT RECOMMENDED for production):
   ```bash
   # Launch Chrome with reduced security (TESTING ONLY)
   google-chrome --disable-web-security --user-data-dir=/tmp/chrome_dev
   ```

2. Or use Firefox with security warnings accepted

**Recommended**: Fix HTTPS properly instead of workarounds.

---

## 4. API Health Check 404 Error

### Symptom

API logs show:
```
INFO: 172.28.0.1:36308 - "GET /api/health HTTP/1.1" 404 Not Found
```

### Root Cause

The frontend or monitoring scripts call `/api/health`, but Nginx only has a route for `/health` (without `/api` prefix).

### Solution

**✅ FIXED** - The Nginx configuration has been updated to include both routes:

```nginx
# Original health check
location /health {
    proxy_pass http://api:8000/health;
}

# API health check (called by frontend/monitoring)
location /api/health {
    proxy_pass http://api:8000/health;
}
```

**To apply the fix**:

```bash
# Restart Nginx to apply updated configuration
docker compose restart nginx

# Verify the fix
curl http://localhost/api/health
# Should return: {"status": "healthy"}
```

### Verification

```bash
# Check logs - should no longer show 404 for /api/health
docker compose logs nginx --tail=50 | grep "api/health"
```

---

## 5. HAProxy Timeout Warning

### Symptom

Docker logs for `docker-socket-proxy` show:
```
[WARNING] (12) : missing timeouts for backend 'docker-events'.
| While not properly invalid, you will certainly encounter various problems
```

### Root Cause

HAProxy inside the `docker-socket-proxy` container lacks timeout configuration for long-lived connections (like Docker events streaming).

### Impact

- Low to Medium severity
- May cause connections to hang indefinitely
- Can lead to resource exhaustion over time
- Doesn't affect immediate functionality

### Solution

**✅ FIXED** - The `docker-compose.yml` has been updated with proper timeout configuration:

```yaml
docker-socket-proxy:
  environment:
    - TIMEOUT_CONNECT=50000
    - TIMEOUT_CLIENT=50000
    - TIMEOUT_SERVER=50000
    - TIMEOUT_TUNNEL=3600000  # ← NEW: For long-lived connections
```

**To apply the fix**:

```bash
# Recreate the docker-socket-proxy container
docker compose up -d --force-recreate docker-socket-proxy

# Verify - warning should be gone
docker compose logs docker-socket-proxy | grep -i warning
```

### Verification

```bash
# Check that container started without warnings
docker compose logs docker-socket-proxy --tail=20

# Should NOT show "missing timeouts" warning
```

---

## 6. OpenTelemetry Warning

### Symptom

Logs show:
```
opentelemetry_missing message=Tracing will be disabled
```

### Root Cause

The application tries to load OpenTelemetry tracing libraries but they're not configured or installed.

### Impact

- **Severity**: Low (informational only)
- Tracing is disabled but application works normally
- Only affects performance monitoring/debugging capabilities

### Solution

**Option 1: Ignore (Recommended)**

This warning is informational. The application works fine without tracing.

**Option 2: Enable OpenTelemetry (Advanced)**

If you want distributed tracing:

1. Install OpenTelemetry dependencies:
   ```bash
   # Add to requirements.txt or install in container
   pip install opentelemetry-api opentelemetry-sdk
   pip install opentelemetry-instrumentation-fastapi
   ```

2. Configure environment variables in `.env`:
   ```bash
   OTEL_SERVICE_NAME=linkedin-birthday-bot
   OTEL_EXPORTER_OTLP_ENDPOINT=http://your-collector:4317
   ENABLE_TELEMETRY=true
   ```

3. Rebuild containers:
   ```bash
   docker compose up -d --build
   ```

**Option 3: Disable the Warning**

Set environment variable:
```bash
# In .env or docker-compose.yml
ENABLE_TELEMETRY=false
```

---

## 7. Docker Image Pull Failures (Raspberry Pi 4 / ARM64)

### Symptom

During Phase 6 (Docker Deployment), the setup shows warnings:

```
⚠ [WARN]   ⚠ docker-socket-proxy - échec (non bloquant)
⚠ [WARN]   ⚠ nginx - échec (non bloquant)
⚠ [WARN]   ⚠ dozzle - échec (non bloquant)
⚠ [WARN]   3/8 images en échec (retry au démarrage)
```

And the progress bar shows:
```
└─ ⚠ Déploiement Docker incomplet (6/7)
```

### Root Cause

This issue has two components:

**1. Progress Bar Count Mismatch**
- The script was initialized with 7 steps but only 6 were implemented
- **Fixed in latest version**: Progress bar now correctly shows 6/6

**2. Image Pull Failures on ARM64**
- Raspberry Pi 4 uses ARM64 architecture (aarch64)
- Docker images must support ARM64/ARM architectures
- Temporary network issues or rate limiting from Docker Hub
- Images not being pulled from correct architecture variant

### Impact

- **Progress bar issue**: Cosmetic only - all steps complete successfully
- **Image pull failures**: Critical services (nginx, api) may fail to start if images weren't pulled

### Solution

#### For Progress Bar Issue

**Already Fixed** in the latest codebase. If you see "6/7" instead of "7/7":

```bash
git pull origin claude/letsencrypt-certificates-aNlS3
```

The fix changes `progress_init "Déploiement Docker" 7` to `6`.

#### For Image Pull Failures on Pi4

**Step 1: Verify Docker Architecture Support**

```bash
# Check current architecture
uname -m
# Should show: aarch64 (ARM64) or armv7l (ARM 32-bit)

# Check Docker version (must support ARM)
docker version | grep -i arch
```

**Step 2: Manually Pull Critical Images**

```bash
cd /home/gaspard/linkedin-birthday-auto

# Pull images manually with retry
docker pull nginx:alpine
docker pull tecnativa/docker-socket-proxy:latest
docker pull amir20/dozzle:latest

# Verify architecture
docker image inspect nginx:alpine | grep -i architecture
# Should show: "Architecture": "arm64" or "arm"
```

**Step 3: Check Running Containers**

```bash
docker compose ps

# If nginx or other services show "Exit" status, restart them:
docker compose restart nginx
docker compose restart api
docker compose restart dashboard
```

**Step 4: Check Container Logs for ARM-specific Issues**

```bash
# Check if containers are failing due to architecture mismatch
docker compose logs nginx --tail 20
docker compose logs api --tail 20

# Common ARM errors:
# - "exec format error" → wrong architecture
# - "no matching manifest" → image doesn't support ARM64
```

#### Prevention (Latest Code)

The fixes in this commit include:

1. **Automatic Critical Service Restart** (setup.sh:992-1004)
   - Detects ARM architecture
   - Automatically retries failed critical services (nginx, api, dashboard)

2. **ARM64 Warning Messages** (scripts/lib/docker.sh:147-154)
   - Displays helpful diagnostics when image pulls fail on ARM
   - Provides troubleshooting commands

3. **Correct Progress Bar** (setup.sh:937)
   - Shows accurate 6/6 step completion

### Verification

After applying fixes or manual intervention:

```bash
# All containers should show "Up"
docker compose ps

# Should show 8/8 containers running
docker compose ps --status running | wc -l

# Test nginx is serving requests
curl -I http://localhost

# Should return: HTTP/1.1 200 OK or 30x redirect
```

### Troubleshooting ARM-specific Issues

If images continue failing:

**1. Check Docker Hub Rate Limits**
```bash
# Docker Hub limits: 100 pulls/6h for anonymous users
# Solution: Login to Docker Hub
docker login

# Or use authenticated pulls
```

**2. Use ARM-specific Image Tags**
```bash
# Some images have explicit ARM tags
# Edit docker-compose.yml if needed:
nginx:alpine-arm64v8  # Explicit ARM tag
```

**3. Check Available Disk Space**
```bash
df -h /var/lib/docker
# Pi4 SD cards fill up quickly
# Clean old images: docker image prune -a
```

**4. Verify Network Stability**
```bash
# Test Docker Hub connectivity
curl -I https://registry-1.docker.io/v2/

# Should return: HTTP/2 200 or 401 (auth required)
```

### Additional Resources

- [Docker Hub Official Images ARM Support](https://www.docker.com/blog/multi-arch-images/)
- [Raspberry Pi Docker Guide](https://docs.docker.com/engine/install/debian/)

---

## Quick Reference Commands

### Check System Status

```bash
# Check all containers
docker compose ps

# Check Nginx logs
docker compose logs nginx --tail=50

# Check API logs
docker compose logs api --tail=50

# Check certificate
openssl x509 -in certbot/conf/live/<domain>/fullchain.pem -noout -text | grep -E "Issuer|Not After"

# Test HTTPS
curl -I https://your-domain.freeboxos.fr

# Test health endpoints
curl http://localhost/health
curl http://localhost/api/health
```

### Apply All Fixes

```bash
# 1. Fix HTTPS certificates
sudo ./scripts/fix_https_certificates.sh

# 2. Recreate docker-socket-proxy with timeout fix
docker compose up -d --force-recreate docker-socket-proxy

# 3. Restart Nginx with updated config
docker compose restart nginx

# 4. Verify all services
docker compose ps
docker compose logs --tail=20
```

### Rollback if Needed

```bash
# Restore from backup
cp .setup_backups/deployment-backup-*.tar.gz ./deployment-backup.tar.gz
tar -xzf deployment-backup.tar.gz

# Restart services
docker compose restart
```

---

## Getting Help

If issues persist:

1. **Check logs**: `docker compose logs --tail=100`
2. **Run diagnostics**: `./scripts/diagnose_https.sh`
3. **Check setup state**: `cat .setup.state | jq`
4. **Review setup logs**: `cat logs/setup_install_*.log`

For security-related issues, see: `docs/SECURITY_AUDIT.md`

For Raspberry Pi specific issues, see: `docs/RASPBERRY_PI_TROUBLESHOOTING.md`

---

**Last Updated**: 2025-12-26
**Version**: 1.0
**Status**: All fixes applied and tested
