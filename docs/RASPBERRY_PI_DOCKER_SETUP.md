# 🍓 Raspberry Pi Docker Setup Guide

Complete guide for running the LinkedIn Birthday Bot on Raspberry Pi using Docker Compose with Redis and RQ workers.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Detailed Installation](#detailed-installation)
5. [Verification](#verification)
6. [Configuration](#configuration)
7. [Automation](#automation)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Performance Optimization](#performance-optimization)

---

## 🎯 Overview

This guide covers the **modern Docker-based architecture (v2.0)** for Raspberry Pi:

```
┌─────────────────────────────────────────┐
│         Raspberry Pi 4                  │
│  ┌───────────────────────────────────┐  │
│  │      Docker Compose               │  │
│  │  ┌─────────────┐  ┌────────────┐  │  │
│  │  │   Redis     │  │ RQ Worker  │  │  │
│  │  │   (Queue)   │◄─┤ (Bot)      │  │  │
│  │  └─────────────┘  └────────────┘  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Advantages:**
- ✅ Containerized environment (isolated, reproducible)
- ✅ Automatic restarts and health checks
- ✅ Resource limits (memory, CPU) for stability
- ✅ Easy updates and rollbacks
- ✅ Redis-backed queue for reliability

---

## 🔧 Prerequisites

### Hardware Requirements

**Minimum:**
- Raspberry Pi 4 Model B - **2GB RAM**
- 32GB microSD card (Class 10 or better)
- Stable internet connection (Ethernet recommended)
- 5V/3A USB-C power supply

**Recommended:**
- Raspberry Pi 4 Model B - **4GB or 8GB RAM**
- Cooling solution (heatsink or fan)
- 64GB microSD card

### Software Requirements

- **OS:** Raspberry Pi OS (64-bit) - Debian Bookworm or newer
- **Kernel:** Linux 4.19+ (for cgroup v2 support)
- **Docker:** 20.10+
- **Docker Compose:** 2.0+

---

## 🚀 Quick Start

If you already have Raspberry Pi OS installed with SSH access:

```bash
# 1. Connect to your Raspberry Pi
ssh pi@raspberrypi.local

# 2. Update system
sudo apt update && sudo apt upgrade -y

# 3. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# 4. Install Docker Compose (if not included)
# Check if already installed
docker compose version

# If not, install it:
sudo apt install docker-compose-plugin

# 5. Clone the repository
cd ~
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# 6. Set up authentication (see Configuration section)
# Create auth_state.json with your LinkedIn session

# 7. Start the containers
docker-compose -f docker-compose.queue.yml up -d

# 8. Verify the setup
./scripts/verify_rpi_docker.sh
```

---

## 📦 Detailed Installation

### Step 1: Prepare Raspberry Pi OS

#### Option A: Fresh Installation

1. Download **Raspberry Pi Imager**: https://www.raspberrypi.com/software/
2. Flash **Raspberry Pi OS (64-bit)** to your microSD card
3. Enable SSH and configure WiFi/credentials in advanced settings
4. Boot your Raspberry Pi and connect via SSH

#### Option B: Existing Installation

```bash
# Update to latest packages
sudo apt update && sudo apt upgrade -y

# Verify 64-bit OS
uname -m
# Should output: aarch64

# Check available memory
free -h

# Check disk space
df -h
```

### Step 2: Install Docker

```bash
# Install Docker using the official convenience script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group
sudo usermod -aG docker $USER

# Apply group membership (or log out and back in)
newgrp docker

# Verify Docker installation
docker --version
docker run hello-world

# Enable Docker to start on boot
sudo systemctl enable docker
```

### Step 3: Install Docker Compose

```bash
# Check if Docker Compose plugin is already installed
docker compose version

# If not installed, install the plugin
sudo apt update
sudo apt install docker-compose-plugin

# Verify installation
docker compose version
# Should output: Docker Compose version v2.x.x
```

### Step 4: Clone the Repository

```bash
# Navigate to home directory
cd ~

# Clone the repository
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git

# Enter the project directory
cd linkedin-birthday-auto

# Check the structure
ls -la

# You should see:
# - docker-compose.queue.yml
# - Dockerfile.multiarch
# - src/
# - config/
# - etc.
```

### Step 5: Configure System Resources (Recommended)

```bash
# 1. Increase swap for better stability (if using 2GB RAM Pi)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set: CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# 2. Enable memory overcommit for Redis (optional but recommended)
sudo sysctl vm.overcommit_memory=1

# Make it permanent
echo "vm.overcommit_memory = 1" | sudo tee -a /etc/sysctl.conf
```

---

## ⚙️ Configuration

### Step 6: Set Up LinkedIn Authentication

The bot requires LinkedIn authentication. You have several options:

#### Option 1: Export Cookies (Recommended)

1. Install [Cookie-Editor](https://cookie-editor.cgagnier.ca/) browser extension
2. Log in to LinkedIn (including 2FA if enabled)
3. Click Cookie-Editor icon → Export → Copy as JSON
4. Create `auth_state.json` on your Raspberry Pi:

```bash
cd ~/linkedin-birthday-auto
nano auth_state.json
```

Paste the exported JSON and save (Ctrl+O, Enter, Ctrl+X).

#### Option 2: Generate auth_state.json on a Desktop Computer

If you have 2FA enabled, it's easier to generate the file on a desktop with GUI:

```bash
# On your desktop (Windows/Mac/Linux)
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-new.txt
playwright install chromium

# Run bot once to authenticate (GUI browser will open)
python main.py bot --dry-run

# Transfer auth_state.json to Raspberry Pi
scp auth_state.json pi@raspberrypi.local:~/linkedin-birthday-auto/
```

#### Option 3: Environment Variable

You can also use base64-encoded auth state:

```bash
# Encode auth_state.json
export LINKEDIN_AUTH_STATE=$(cat auth_state.json | base64)

# Add to .env file for persistence
echo "LINKEDIN_AUTH_STATE=${LINKEDIN_AUTH_STATE}" >> .env
```

### Step 7: Configure Environment Variables (Optional)

Create a `.env` file for custom configuration:

```bash
nano .env
```

Add any overrides:

```bash
# Dry run mode (test without sending messages)
LINKEDIN_BOT_DRY_RUN=false

# Bot mode
LINKEDIN_BOT_BOT_MODE=standard

# Headless browser (recommended for Raspberry Pi)
LINKEDIN_BOT_BROWSER_HEADLESS=true

# Messaging limits
LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT=80

# Redis configuration
REDIS_HOST=redis
REDIS_PORT=6379

# Logging
LOG_LEVEL=INFO
```

Save and exit (Ctrl+O, Enter, Ctrl+X).

---

## 🐳 Running with Docker Compose

### Step 8: Start the Containers

```bash
cd ~/linkedin-birthday-auto

# Start containers in detached mode
docker-compose -f docker-compose.queue.yml up -d

# You should see:
# [+] Running 3/3
#  ✔ Network linkedin-birthday-auto_default  Created
#  ✔ Container linkedin-bot-redis            Started
#  ✔ Container linkedin-bot-worker           Started
```

**Expected Warning:**

You may see a warning about memory soft limits:
```
WARNING: kernel does not support memory soft limit capabilities or the cgroup is not mounted
```

This is **normal and expected** on Raspberry Pi. It's documented and doesn't affect functionality.

### Step 9: Verify the Setup

```bash
# Run the verification script
cd ~/linkedin-birthday-auto
./scripts/verify_rpi_docker.sh
```

This will check:
- System information (RAM, disk, architecture)
- Docker installation
- Container status
- Redis health
- Worker health
- Expected warnings

---

## 📊 Verification

### Manual Verification Commands

```bash
# Check container status
docker-compose -f docker-compose.queue.yml ps

# Should show:
# NAME                    STATUS              PORTS
# linkedin-bot-redis      Up (healthy)        6379/tcp
# linkedin-bot-worker     Up (healthy)

# Check Redis
docker exec linkedin-bot-redis redis-cli ping
# Should output: PONG

# Check Redis memory
docker exec linkedin-bot-redis redis-cli INFO MEMORY | grep used_memory_human

# View Redis keys
docker exec linkedin-bot-redis redis-cli KEYS '*'

# View worker logs
docker logs linkedin-bot-worker --tail 50

# Follow logs in real-time
docker logs linkedin-bot-worker -f

# View Redis logs
docker logs linkedin-bot-redis --tail 50
```

### Health Checks

The containers have built-in health checks:

```bash
# Check health status
docker inspect linkedin-bot-redis | grep -A 10 '"Health"'
docker inspect linkedin-bot-worker | grep -A 10 '"Health"'

# View health check logs
docker inspect --format='{{json .State.Health}}' linkedin-bot-redis | jq
```

---

## 🤖 Automation

### Step 10: Create Systemd Service (Optional)

For automatic startup on boot and better integration with the system:

```bash
sudo nano /etc/systemd/system/linkedin-bot.service
```

Add:

```ini
[Unit]
Description=LinkedIn Birthday Bot
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/linkedin-birthday-auto
ExecStart=/usr/bin/docker compose -f docker-compose.queue.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.queue.yml down
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable linkedin-bot.service
sudo systemctl start linkedin-bot.service

# Check status
sudo systemctl status linkedin-bot.service
```

### Step 11: Schedule Bot Execution

The worker container runs continuously and processes jobs from the queue. To schedule daily execution:

#### Option A: Cron Job

```bash
crontab -e
```

Add:

```bash
# Run bot daily at 8:30 AM
30 8 * * * docker exec linkedin-bot-worker python -m src.queue.producer

# Or with random delay (8-10 AM)
0 8 * * * sleep $((RANDOM \% 7200)) && docker exec linkedin-bot-worker python -m src.queue.producer
```

#### Option B: Systemd Timer

Create timer unit:

```bash
sudo nano /etc/systemd/system/linkedin-bot-daily.service
```

```ini
[Unit]
Description=LinkedIn Birthday Bot Daily Execution
After=linkedin-bot.service

[Service]
Type=oneshot
ExecStart=/usr/bin/docker exec linkedin-bot-worker python -m src.queue.producer
User=pi
```

Create timer:

```bash
sudo nano /etc/systemd/system/linkedin-bot-daily.timer
```

```ini
[Unit]
Description=LinkedIn Birthday Bot Daily Timer
Requires=linkedin-bot-daily.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 08:30:00
RandomizedDelaySec=7200
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable linkedin-bot-daily.timer
sudo systemctl start linkedin-bot-daily.timer

# Check timer status
systemctl list-timers --all | grep linkedin
```

---

## 📈 Monitoring

### Container Monitoring

```bash
# View container resource usage
docker stats

# Specific container stats
docker stats linkedin-bot-redis linkedin-bot-worker

# Container logs with timestamps
docker logs linkedin-bot-worker --timestamps --tail 100

# Export logs to file
docker logs linkedin-bot-worker > ~/linkedin-bot-worker.log 2>&1
```

### Create Monitoring Script

```bash
nano ~/linkedin-birthday-auto/scripts/monitor.sh
```

```bash
#!/bin/bash

# Monitor LinkedIn Bot Docker Containers

echo "=== Container Status ==="
docker-compose -f ~/linkedin-birthday-auto/docker-compose.queue.yml ps

echo ""
echo "=== Resource Usage ==="
docker stats --no-stream linkedin-bot-redis linkedin-bot-worker

echo ""
echo "=== Redis Health ==="
docker exec linkedin-bot-redis redis-cli INFO STATS | grep -E "total_commands_processed|total_connections_received"

echo ""
echo "=== Recent Worker Logs ==="
docker logs linkedin-bot-worker --tail 10 2>&1
```

Make executable and run:

```bash
chmod +x ~/linkedin-birthday-auto/scripts/monitor.sh
./scripts/monitor.sh
```

Add to crontab for periodic monitoring:

```bash
crontab -e

# Add:
0 */6 * * * ~/linkedin-birthday-auto/scripts/monitor.sh >> ~/linkedin-bot-monitor.log 2>&1
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Containers Not Starting

```bash
# Check Docker daemon
sudo systemctl status docker

# View container logs
docker-compose -f docker-compose.queue.yml logs

# Remove and recreate containers
docker-compose -f docker-compose.queue.yml down
docker-compose -f docker-compose.queue.yml up -d
```

#### 2. Redis Memory Warning

```
WARNING: kernel does not support memory soft limit capabilities
```

**This is expected on Raspberry Pi.** To silence it (optional):

```bash
sudo sysctl vm.overcommit_memory=1
echo "vm.overcommit_memory = 1" | sudo tee -a /etc/sysctl.conf
```

#### 3. Worker Crashing / Out of Memory

```bash
# Check memory usage
free -h
docker stats

# Increase swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set: CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Reduce worker memory limit in docker-compose.queue.yml
nano docker-compose.queue.yml
# Adjust: memory: 1G (instead of 1.2G)
```

#### 4. Authentication Failures

```bash
# Regenerate auth_state.json
rm auth_state.json

# On desktop with GUI
python main.py bot --dry-run

# Transfer to Raspberry Pi
scp auth_state.json pi@raspberrypi.local:~/linkedin-birthday-auto/

# Restart worker
docker-compose -f docker-compose.queue.yml restart rq-worker
```

#### 5. Network Issues

```bash
# Check container network
docker network ls
docker network inspect linkedin-birthday-auto_default

# Restart containers
docker-compose -f docker-compose.queue.yml restart

# Rebuild network
docker-compose -f docker-compose.queue.yml down
docker-compose -f docker-compose.queue.yml up -d
```

### Debug Mode

Run containers in foreground to see detailed output:

```bash
# Stop background containers
docker-compose -f docker-compose.queue.yml down

# Run in foreground
docker-compose -f docker-compose.queue.yml up

# Press Ctrl+C to stop
```

### View All Logs

```bash
# All logs since start
docker-compose -f docker-compose.queue.yml logs

# Follow logs in real-time
docker-compose -f docker-compose.queue.yml logs -f

# Last 100 lines
docker-compose -f docker-compose.queue.yml logs --tail 100

# Specific service
docker-compose -f docker-compose.queue.yml logs rq-worker
```

---

## ⚡ Performance Optimization

### 1. Raspberry Pi Configuration

```bash
# Increase GPU memory (if not using GUI)
sudo nano /boot/config.txt
# Add: gpu_mem=16

# Disable unused services
sudo systemctl disable bluetooth
sudo systemctl stop bluetooth

# If using Ethernet, disable WiFi
sudo rfkill block wifi
```

### 2. Docker Optimization

```bash
# Enable Docker log rotation
sudo nano /etc/docker/daemon.json
```

Add:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
```

Restart Docker:

```bash
sudo systemctl restart docker
```

### 3. Redis Optimization

The `docker-compose.queue.yml` already includes optimizations:
- `maxmemory 256mb` - Limit memory usage
- `maxmemory-policy allkeys-lru` - Evict least recently used keys
- AOF persistence with reasonable sync intervals

### 4. Resource Limits

Adjust limits in `docker-compose.queue.yml` based on your Raspberry Pi RAM:

**For 2GB RAM:**
```yaml
redis:
  deploy:
    resources:
      limits:
        memory: 300M
      reservations:
        memory: 200M

rq-worker:
  deploy:
    resources:
      limits:
        memory: 1G
      reservations:
        memory: 600M
```

**For 4GB+ RAM:**
```yaml
redis:
  deploy:
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 300M

rq-worker:
  deploy:
    resources:
      limits:
        memory: 1.5G
      reservations:
        memory: 1G
```

---

## 🔄 Updates and Maintenance

### Update the Bot

```bash
cd ~/linkedin-birthday-auto

# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose -f docker-compose.queue.yml down
docker-compose -f docker-compose.queue.yml build --no-cache
docker-compose -f docker-compose.queue.yml up -d

# Verify
./scripts/verify_rpi_docker.sh
```

### Clean Up Docker Resources

```bash
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove unused volumes
docker volume prune -f

# Remove unused networks
docker network prune -f

# Remove everything unused (be careful!)
docker system prune -a --volumes -f
```

### Backup

```bash
# Backup Redis data
docker exec linkedin-bot-redis redis-cli SAVE
docker cp linkedin-bot-redis:/data/dump.rdb ~/backups/redis-$(date +%Y%m%d).rdb

# Backup configuration
tar -czf ~/backups/linkedin-bot-config-$(date +%Y%m%d).tar.gz \
  ~/linkedin-birthday-auto/auth_state.json \
  ~/linkedin-birthday-auto/.env \
  ~/linkedin-birthday-auto/config/
```

---

## 📋 Checklist

- [ ] Raspberry Pi OS (64-bit) installed
- [ ] Docker and Docker Compose installed
- [ ] Repository cloned
- [ ] `auth_state.json` configured
- [ ] Containers started successfully
- [ ] Verification script passes
- [ ] Cron job or systemd timer configured
- [ ] Monitoring in place
- [ ] Backups configured

---

## 🆘 Getting Help

If you encounter issues:

1. **Run the verification script:**
   ```bash
   ./scripts/verify_rpi_docker.sh
   ```

2. **Check the logs:**
   ```bash
   docker-compose -f docker-compose.queue.yml logs --tail 100
   ```

3. **Review common issues** in the Troubleshooting section above

4. **Check GitHub Issues:**
   https://github.com/GaspardD78/linkedin-birthday-auto/issues

5. **System information to include when reporting issues:**
   ```bash
   uname -a
   docker --version
   docker compose version
   free -h
   df -h
   ```

---

## ✅ Success!

Your LinkedIn Birthday Bot should now be running on your Raspberry Pi with:

- ✅ Automatic restarts on failures
- ✅ Health monitoring
- ✅ Resource limits for stability
- ✅ Redis-backed queue for reliability
- ✅ Scheduled daily execution
- ✅ Low power consumption (~3-5W)
- ✅ Residential IP (no proxy needed)

**Next steps:**

1. Test in dry-run mode for a week
2. Monitor logs and resource usage
3. Adjust limits if needed
4. Enable production mode when ready

Happy automating! 🎉
