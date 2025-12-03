# 🔧 Raspberry Pi Troubleshooting Guide

Complete troubleshooting guide for running the LinkedIn Birthday Bot on Raspberry Pi with Docker.

______________________________________________________________________

## 📋 Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
1. [Docker Issues](#docker-issues)
1. [Container Issues](#container-issues)
1. [Memory Issues](#memory-issues)
1. [Network Issues](#network-issues)
1. [Authentication Issues](#authentication-issues)
1. [Performance Issues](#performance-issues)
1. [System Issues](#system-issues)
1. [Expected Warnings](#expected-warnings)

______________________________________________________________________

## 🔍 Quick Diagnostics

Before diving into specific issues, run these commands to gather diagnostic information:

```bash
# 1. Run the verification script
cd ~/linkedin-birthday-auto
./scripts/verify_rpi_docker.sh

# 2. Check system resources
echo "=== System Info ==="
uname -a
free -h
df -h

# 3. Check Docker status
echo "=== Docker Info ==="
docker --version
docker compose version
sudo systemctl status docker

# 4. Check containers
echo "=== Container Status ==="
docker-compose -f docker-compose.pi4-standalone.yml ps

# 5. Check recent logs
echo "=== Recent Logs ==="
docker-compose -f docker-compose.pi4-standalone.yml logs --tail 50

# 6. Check temperatures
echo "=== System Temperature ==="
vcgencmd measure_temp
```

Save this output when reporting issues.

______________________________________________________________________

## 🐳 Docker Issues

### Issue: Docker command not found

**Error:**

```
bash: docker: command not found
```

**Solution:**

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Apply group membership
newgrp docker

# Verify
docker --version
```

### Issue: Permission denied while trying to connect to Docker daemon

**Error:**

```
Got permission denied while trying to connect to the Docker daemon socket
```

**Solution:**

```bash
# Add your user to the docker group
sudo usermod -aG docker $USER

# Log out and back in, OR use:
newgrp docker

# Verify
docker run hello-world
```

### Issue: Docker daemon not running

**Error:**

```
Cannot connect to the Docker daemon. Is the docker daemon running?
```

**Solution:**

```bash
# Start Docker service
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Check status
sudo systemctl status docker
```

### Issue: Docker Compose not found

**Error:**

```
docker-compose: command not found
```

**Solution:**

```bash
# Check if Docker Compose plugin is available
docker compose version

# If not, install it
sudo apt update
sudo apt install docker-compose-plugin

# Verify
docker compose version
```

______________________________________________________________________

## 📦 Container Issues

### Issue: Containers fail to start

**Error:**

```
Error response from daemon: failed to create shim task
```

**Diagnosis:**

```bash
# Check Docker logs
sudo journalctl -u docker -n 50 --no-pager

# Check if containers exist
docker ps -a

# Check specific container
docker logs linkedin-bot-redis
docker logs linkedin-bot-worker
```

**Solution 1: Clean restart**

```bash
# Stop and remove containers
docker-compose -f docker-compose.pi4-standalone.yml down

# Remove any orphaned volumes
docker volume prune -f

# Start fresh
docker-compose -f docker-compose.pi4-standalone.yml up -d
```

**Solution 2: Rebuild containers**

```bash
# Stop containers
docker-compose -f docker-compose.pi4-standalone.yml down

# Remove images
docker rmi $(docker images 'linkedin*' -q) 2>/dev/null || true

# Rebuild from scratch
docker-compose -f docker-compose.pi4-standalone.yml build --no-cache
docker-compose -f docker-compose.pi4-standalone.yml up -d
```

### Issue: Container keeps restarting

**Diagnosis:**

```bash
# Check restart count
docker ps -a | grep linkedin

# Check why it's restarting
docker logs linkedin-bot-worker --tail 100
docker logs linkedin-bot-redis --tail 100

# Check container health
docker inspect linkedin-bot-worker | grep -A 20 "Health"
```

**Solution: Check for specific error**

Look for these patterns in logs:

1. **Memory errors:** See [Memory Issues](#memory-issues)
1. **Network errors:** See [Network Issues](#network-issues)
1. **Authentication errors:** See [Authentication Issues](#authentication-issues)
1. **Dependency errors:**

```bash
# Rebuild with latest dependencies
docker-compose -f docker-compose.pi4-standalone.yml down
docker-compose -f docker-compose.pi4-standalone.yml build --no-cache
docker-compose -f docker-compose.pi4-standalone.yml up -d
```

### Issue: Container health check failing

**Diagnosis:**

```bash
# Check health status
docker inspect linkedin-bot-redis | grep -A 10 '"Health"'
docker inspect linkedin-bot-worker | grep -A 10 '"Health"'

# Manual health check for Redis
docker exec linkedin-bot-redis redis-cli ping

# Manual health check for worker
docker exec linkedin-bot-worker python -c "import sys; sys.exit(0)"
```

**Solution:**

```bash
# Restart unhealthy container
docker-compose -f docker-compose.pi4-standalone.yml restart redis
docker-compose -f docker-compose.pi4-standalone.yml restart rq-worker

# If still failing, rebuild
docker-compose -f docker-compose.pi4-standalone.yml up -d --force-recreate redis
docker-compose -f docker-compose.pi4-standalone.yml up -d --force-recreate rq-worker
```

______________________________________________________________________

## 💾 Memory Issues

### Issue: Worker container crashes with OOM (Out of Memory)

**Error in logs:**

```
Killed
```

**Diagnosis:**

```bash
# Check memory usage
free -h

# Check container memory
docker stats --no-stream

# Check Docker logs for OOM
sudo dmesg | grep -i "out of memory"
sudo dmesg | grep -i "oom"

# Check if OOM killer activated
sudo journalctl -k | grep -i "killed process"
```

**Solution 1: Increase swap**

```bash
# Increase swap file size
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile

# Change to:
# CONF_SWAPSIZE=2048

# Apply changes
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Verify
free -h
```

**Solution 2: Reduce container memory limits**

```bash
# Edit docker-compose.pi4-standalone.yml
nano docker-compose.pi4-standalone.yml

# For 2GB Raspberry Pi, reduce limits:
# rq-worker:
#   deploy:
#     resources:
#       limits:
#         memory: 1G  # Instead of 1.2G
#       reservations:
#         memory: 600M  # Instead of 800M

# Restart with new limits
docker-compose -f docker-compose.pi4-standalone.yml down
docker-compose -f docker-compose.pi4-standalone.yml up -d
```

**Solution 3: Enable headless mode**

Ensure browser runs in headless mode to save memory:

```bash
# Check/create .env file
nano .env

# Add or verify:
LINKEDIN_BOT_BROWSER_HEADLESS=true

# Restart worker
docker-compose -f docker-compose.pi4-standalone.yml restart rq-worker
```

**Solution 4: Add Chromium memory flags**

```bash
# Edit .env
nano .env

# Add:
CHROMIUM_ARGS=--disable-dev-shm-usage --disable-gpu --no-sandbox

# Restart
docker-compose -f docker-compose.pi4-standalone.yml restart rq-worker
```

### Issue: Redis memory warnings

#### Warning 1: Kernel memory soft limit

**Warning:**

```
WARNING: kernel does not support memory soft limit capabilities
```

**This is EXPECTED on Raspberry Pi and can be safely ignored.**

#### Warning 2: Memory overcommit

**Warning:**

```
WARNING Memory overcommit must be enabled! Without it, a background save or
replication may fail under low memory condition.
```

**This warning has been fixed in the Docker Compose configuration** by enabling sysctls for both Redis containers:

```yaml
sysctls:
  - net.core.somaxconn=511
  - vm.overcommit_memory=1
```

This configuration:
- Automatically applies memory overcommit settings to Redis containers
- Eliminates the warning without requiring host-level configuration
- Works seamlessly with Docker's security model

**No additional configuration required!** The warning should no longer appear after restarting containers:

```bash
docker-compose -f docker-compose.pi4-standalone.yml restart redis-bot redis-dashboard
```

### Issue: System running out of memory

**Symptoms:**

- System becomes unresponsive
- SSH disconnects
- Random process kills

**Diagnosis:**

```bash
# Check memory usage
free -h

# Check top memory consumers
ps aux --sort=-%mem | head -20

# Check if swap is enabled
swapon --show
```

**Solution:**

```bash
# 1. Stop non-essential services
sudo systemctl stop bluetooth
sudo systemctl disable bluetooth

# 2. Increase swap (see Solution 1 above)

# 3. Reduce container limits (see Solution 2 above)

# 4. Close any unnecessary processes
# Find and kill heavy processes
ps aux | grep -E "chromium|firefox|electron" | grep -v grep

# 5. Restart containers with lower limits
docker-compose -f docker-compose.pi4-standalone.yml restart
```

______________________________________________________________________

## 🌐 Network Issues

### Issue: Docker image pull timeout (TLS handshake timeout)

**Error during installation/deployment:**

```
failed to copy: httpReadSeeker: failed open: failed to do request: Get "https://registry-1.docker.io/...": net/http: TLS handshake timeout
```

**Explanation:**

This error occurs when downloading Docker images on slow or unstable internet connections. The Raspberry Pi's connection might timeout before large images finish downloading, especially when multiple images are pulled simultaneously.

**The deployment script now handles this automatically with:**
- ✅ **Automatic retry** with exponential backoff (up to 5 attempts)
- ✅ **Sequential image pull** (one by one, more reliable than parallel)
- ✅ **Extended timeouts** (300 seconds for slow connections)

**If the error persists after automatic retries:**

**Solution 1: Check your internet connection**

```bash
# Test internet speed
ping -c 10 8.8.8.8

# Check DNS resolution
nslookup docker.io
nslookup ghcr.io

# Test Docker Hub connectivity
curl -I https://registry-1.docker.io/v2/

# Test GitHub Container Registry
curl -I https://ghcr.io/v2/
```

**Solution 2: Pull images manually one by one**

```bash
cd ~/linkedin-birthday-auto

# Pull Redis images first (smallest)
docker pull redis:7-alpine

# Pull bot image (can be large, ~500MB)
docker pull ghcr.io/gaspardd78/linkedin-birthday-auto-bot:latest

# Pull dashboard image (can be large, ~400MB)
docker pull ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest

# Then retry deployment
./scripts/deploy_pi4_pull.sh
```

**Solution 3: Optimize Docker for slow connections**

```bash
# Edit Docker daemon config
sudo nano /etc/docker/daemon.json

# Add or update with extended timeouts:
{
  "max-concurrent-downloads": 1,
  "max-download-attempts": 5,
  "dns": ["8.8.8.8", "8.8.4.4"]
}

# Restart Docker
sudo systemctl restart docker

# Retry deployment
cd ~/linkedin-birthday-auto
./scripts/deploy_pi4_pull.sh
```

**Solution 4: Use a wired connection if possible**

Wi-Fi on Raspberry Pi can be unstable:

```bash
# Check current connection
ifconfig

# If using Wi-Fi, consider:
# 1. Moving closer to router
# 2. Using Ethernet cable (more stable)
# 3. Reducing interference (other devices)
# 4. Upgrading to 5GHz Wi-Fi if available
```

**Solution 5: Wait and retry during off-peak hours**

Docker registries can be slow during peak hours:

```bash
# Simply retry the deployment
cd ~/linkedin-birthday-auto
./scripts/deploy_pi4_pull.sh

# The script will automatically:
# - Skip already downloaded images
# - Retry only failed ones
# - Use exponential backoff
```

**Solution 6: Use a Docker registry mirror (advanced)**

```bash
# Add a registry mirror
sudo nano /etc/docker/daemon.json

# Add (adjust with your preferred mirror):
{
  "registry-mirrors": ["https://mirror.gcr.io"]
}

# Restart Docker
sudo systemctl restart docker
```

### Issue: Worker cannot connect to Redis

**Error in worker logs:**

```
redis.exceptions.ConnectionError: Error connecting to Redis
Connection refused
```

**Diagnosis:**

```bash
# Check if Redis is running
docker ps | grep redis

# Check Redis logs
docker logs linkedin-bot-redis

# Test Redis connectivity from host
docker exec linkedin-bot-redis redis-cli ping

# Test Redis connectivity from worker
docker exec linkedin-bot-worker ping redis
```

**Solution:**

```bash
# Check network configuration
docker network inspect linkedin-birthday-auto_default

# Ensure containers are on the same network
docker-compose -f docker-compose.pi4-standalone.yml ps

# Restart containers
docker-compose -f docker-compose.pi4-standalone.yml restart

# If still failing, recreate network
docker-compose -f docker-compose.pi4-standalone.yml down
docker-compose -f docker-compose.pi4-standalone.yml up -d
```

### Issue: Cannot access internet from containers

**Error:**

```
Could not resolve host
Network unreachable
```

**Diagnosis:**

```bash
# Test internet from host
ping -c 3 8.8.8.8

# Test DNS from host
nslookup google.com

# Test internet from container
docker exec linkedin-bot-worker ping -c 3 8.8.8.8

# Test DNS from container
docker exec linkedin-bot-worker nslookup google.com
```

**Solution:**

```bash
# Check Docker network settings
sudo nano /etc/docker/daemon.json

# Add DNS servers if missing:
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}

# Restart Docker
sudo systemctl restart docker

# Restart containers
docker-compose -f docker-compose.pi4-standalone.yml restart
```

### Issue: LinkedIn connection timeout

**Error:**

```
TimeoutError: Navigation timeout
```

**Diagnosis:**

```bash
# Test internet connectivity
ping -c 3 linkedin.com

# Check if LinkedIn is accessible
curl -I https://www.linkedin.com

# Check worker logs for details
docker logs linkedin-bot-worker --tail 100
```

**Solution:**

```bash
# 1. Verify internet connection is stable
# 2. Check if LinkedIn is blocking your IP
# 3. Increase timeouts in configuration

# Add to .env:
nano .env

# Add:
LINKEDIN_BOT_BROWSER_TIMEOUT=60000  # 60 seconds

# Restart worker
docker-compose -f docker-compose.pi4-standalone.yml restart rq-worker
```

______________________________________________________________________

## 🔐 Authentication Issues

### Issue: LinkedIn authentication fails

**Error:**

```
AuthenticationError: Failed to authenticate with LinkedIn
```

**Diagnosis:**

```bash
# Check if auth_state.json exists
ls -la auth_state.json

# Verify it's valid JSON
cat auth_state.json | jq . 2>/dev/null || echo "Invalid JSON"

# Check environment variables
docker exec linkedin-bot-worker env | grep LINKEDIN
```

**Solution 1: Regenerate auth_state.json**

On a computer with GUI:

```bash
# Clone repo
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-new.txt
playwright install chromium

# Run bot once to authenticate
python main.py bot --dry-run

# Transfer to Raspberry Pi
scp auth_state.json pi@raspberrypi.local:~/linkedin-birthday-auto/

# Restart worker
docker-compose -f docker-compose.pi4-standalone.yml restart rq-worker
```

**Solution 2: Use Cookie-Editor extension**

1. Install [Cookie-Editor](https://cookie-editor.cgagnier.ca/)
1. Log in to LinkedIn (complete 2FA if required)
1. Click Cookie-Editor → Export → Copy as JSON
1. Create auth_state.json on Raspberry Pi:

```bash
nano auth_state.json
# Paste the JSON
# Save: Ctrl+O, Enter, Ctrl+X

# Restart worker
docker-compose -f docker-compose.pi4-standalone.yml restart rq-worker
```

### Issue: 2FA code requested every time

**Problem:** Bot keeps asking for 2FA code

**Solution:**

Ensure you're saving the session correctly:

```bash
# Verify auth_state.json is mounted in container
docker exec linkedin-bot-worker ls -la /app/auth_state.json

# If missing, check docker-compose.pi4-standalone.yml
nano docker-compose.pi4-standalone.yml

# Verify this line exists under rq-worker volumes:
#   - ./auth_state.json:/app/auth_state.json:ro

# Restart if you made changes
docker-compose -f docker-compose.pi4-standalone.yml down
docker-compose -f docker-compose.pi4-standalone.yml up -d
```

### Issue: Session expired

**Error:**

```
LinkedIn session has expired
```

**Solution:**

LinkedIn sessions typically last weeks/months but can expire. Regenerate:

```bash
# Remove old session
rm auth_state.json

# Generate new session (see Solution 1 or 2 above)

# Restart worker
docker-compose -f docker-compose.pi4-standalone.yml restart rq-worker
```

______________________________________________________________________

## ⚡ Performance Issues

### Issue: Bot runs very slowly

**Diagnosis:**

```bash
# Check system load
uptime

# Check CPU usage
top -n 1

# Check CPU temperature
vcgencmd measure_temp

# Check if throttling
vcgencmd get_throttled
# 0x0 = no throttling
# Other values = throttling occurred
```

**Solution 1: Cooling**

If temperature > 75°C:

```bash
# Check current temperature
vcgencmd measure_temp

# Install a heatsink or fan
# Improve ventilation

# Monitor temperature
watch -n 2 vcgencmd measure_temp
```

**Solution 2: Reduce CPU frequency (if overheating persists)**

```bash
# Edit boot config
sudo nano /boot/config.txt

# Add:
arm_freq=1200  # Reduce from 1500
over_voltage=0  # Disable overvolting

# Reboot
sudo reboot
```

**Solution 3: Optimize Docker**

```bash
# Limit container CPU usage
nano docker-compose.pi4-standalone.yml

# Adjust CPU limits:
# rq-worker:
#   deploy:
#     resources:
#       limits:
#         cpus: '2.0'  # Reduce if needed
#       reservations:
#         cpus: '1.0'

# Restart
docker-compose -f docker-compose.pi4-standalone.yml down
docker-compose -f docker-compose.pi4-standalone.yml up -d
```

### Issue: Chromium crashes or is very slow

**Diagnosis:**

```bash
# Check worker logs for Chromium errors
docker logs linkedin-bot-worker | grep -i chromium

# Check available memory when running
docker stats --no-stream linkedin-bot-worker
```

**Solution:**

```bash
# Add Chromium optimization flags
nano .env

# Add:
CHROMIUM_ARGS=--disable-dev-shm-usage --disable-gpu --no-sandbox --disable-accelerated-2d-canvas --disable-software-rasterizer

# Ensure headless mode
LINKEDIN_BOT_BROWSER_HEADLESS=true

# Restart
docker-compose -f docker-compose.pi4-standalone.yml restart rq-worker
```

### Issue: Disk I/O very slow

**Diagnosis:**

```bash
# Check disk I/O
iostat -x 1 5

# Check if using swap heavily
vmstat 1 5

# Check SD card health
sudo dmesg | grep -i mmc
```

**Solution:**

```bash
# 1. Use a faster SD card (UHS-I or better)

# 2. Reduce disk writes
# Enable Docker log rotation
sudo nano /etc/docker/daemon.json

# Add:
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

# Restart Docker
sudo systemctl restart docker

# 3. Consider using USB SSD boot (if possible)
```

______________________________________________________________________

## 🖥️ System Issues

### Issue: Raspberry Pi becomes unresponsive

**Symptoms:**

- Cannot SSH
- No response from system
- Need to hard reboot

**Prevention:**

```bash
# 1. Set up watchdog timer
sudo apt install watchdog
sudo systemctl enable watchdog
sudo systemctl start watchdog

# 2. Monitor system health
# Create health check script
nano ~/health_check.sh
```

```bash
#!/bin/bash
MEM_AVAILABLE=$(free -m | awk 'NR==2 {print $7}')
if [ "$MEM_AVAILABLE" -lt 100 ]; then
    echo "Low memory detected: ${MEM_AVAILABLE}MB"
    # Restart containers to free memory
    docker-compose -f ~/linkedin-birthday-auto/docker-compose.pi4-standalone.yml restart
fi
```

```bash
chmod +x ~/health_check.sh

# Add to crontab
crontab -e
# Add:
*/15 * * * * ~/health_check.sh >> ~/health.log 2>&1
```

### Issue: SD card corruption

**Symptoms:**

- Read-only filesystem errors
- Docker fails to start
- System won't boot

**Prevention:**

```bash
# 1. Use quality SD card (Samsung, SanDisk)

# 2. Ensure proper shutdown
# Add to .bashrc
echo "alias reboot='sudo sync && sudo reboot'" >> ~/.bashrc
echo "alias poweroff='sudo sync && sudo poweroff'" >> ~/.bashrc

# 3. Reduce writes
# Use log rotation (see above)

# 4. Regular backups
sudo dd if=/dev/mmcblk0 of=/path/to/backup.img bs=4M status=progress
```

**Recovery:**

```bash
# 1. Boot from another SD card
# 2. Mount corrupted card
# 3. Run filesystem check
sudo fsck -y /dev/mmcblk0p2

# 4. If unsuccessful, restore from backup or fresh install
```

### Issue: System clock incorrect

**Problem:** Raspberry Pi doesn't have RTC, time resets on power loss

**Solution:**

```bash
# Install and enable NTP
sudo apt install systemd-timesyncd
sudo systemctl enable systemd-timesyncd
sudo systemctl start systemd-timesyncd

# Verify
timedatectl status

# Force sync
sudo timedatectl set-ntp true
```

______________________________________________________________________

## ⚠️ Expected Warnings

### These warnings are NORMAL and can be ignored:

#### 1. Redis Kernel Memory Limit Warning

```
WARNING: kernel does not support memory soft limit capabilities or the cgroup is not mounted
```

**Explanation:** Raspberry Pi kernel doesn't support all cgroup memory features. This doesn't affect
functionality and can be safely ignored.

**Note:** The memory overcommit warning has been fixed in the Docker Compose configuration and should no longer appear.

#### 2. Docker Compose Warning

```
WARNING: The requested image's platform (linux/arm64/v8) does not match the detected host platform (linux/arm/v7) and no specific platform was requested
```

**Explanation:** Architecture mismatch warning. If containers run fine, ignore it.

#### 3. Container Health Check Warnings

Initial health check failures during startup are normal:

```
health check failed: <reason>
```

Wait 30-60 seconds for containers to fully initialize.

______________________________________________________________________

## 🆘 Getting Help

If you've tried the above and still have issues:

### 1. Gather Diagnostic Information

```bash
# Run full diagnostics
cd ~/linkedin-birthday-auto
./scripts/verify_rpi_docker.sh > diagnostic_output.txt 2>&1

# Add system info
echo "=== System Info ===" >> diagnostic_output.txt
uname -a >> diagnostic_output.txt
free -h >> diagnostic_output.txt
df -h >> diagnostic_output.txt
vcgencmd measure_temp >> diagnostic_output.txt

# Add Docker info
echo "=== Docker Info ===" >> diagnostic_output.txt
docker --version >> diagnostic_output.txt
docker compose version >> diagnostic_output.txt
docker ps -a >> diagnostic_output.txt

# Add container logs
echo "=== Redis Logs ===" >> diagnostic_output.txt
docker logs linkedin-bot-redis --tail 50 >> diagnostic_output.txt 2>&1

echo "=== Worker Logs ===" >> diagnostic_output.txt
docker logs linkedin-bot-worker --tail 50 >> diagnostic_output.txt 2>&1
```

### 2. Check GitHub Issues

Search existing issues: https://github.com/GaspardD78/linkedin-birthday-auto/issues

### 3. Create a New Issue

If your problem isn't documented:

1. Go to: https://github.com/GaspardD78/linkedin-birthday-auto/issues/new
1. Include:
   - Raspberry Pi model and RAM
   - OS version
   - Docker and Docker Compose versions
   - Output from diagnostic_output.txt
   - Steps to reproduce
   - What you've already tried

______________________________________________________________________

## 📚 Additional Resources

- [Raspberry Pi Docker Setup Guide](RASPBERRY_PI_DOCKER_SETUP.md)
- [Main README](../README.md)
- [Architecture Documentation](../ARCHITECTURE.md)
- [Deployment Guide](../DEPLOYMENT.md)

______________________________________________________________________

## ✅ Quick Recovery Commands

Keep these handy for quick fixes:

```bash
# Full restart
cd ~/linkedin-birthday-auto
docker-compose -f docker-compose.pi4-standalone.yml restart

# Clean restart
docker-compose -f docker-compose.pi4-standalone.yml down
docker-compose -f docker-compose.pi4-standalone.yml up -d

# Full rebuild
docker-compose -f docker-compose.pi4-standalone.yml down
docker-compose -f docker-compose.pi4-standalone.yml build --no-cache
docker-compose -f docker-compose.pi4-standalone.yml up -d

# Check status
./scripts/verify_rpi_docker.sh

# View logs
docker-compose -f docker-compose.pi4-standalone.yml logs -f

# Check resources
docker stats
free -h
df -h
vcgencmd measure_temp
```

______________________________________________________________________

**Remember:** Most issues can be resolved with a clean restart or rebuild. When in doubt, start
fresh!
