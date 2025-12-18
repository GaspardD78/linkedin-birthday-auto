# 🤖 LinkedIn Auto RPi4 - Automation Platform

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-multiarch-blue.svg)](https://www.docker.com/)
[![Next.js](https://img.shields.io/badge/next.js-14-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-success.svg)](#)

**Professional LinkedIn automation platform** engineered for **Raspberry Pi 4** (ARM64, 4GB RAM).

Automate repetitive LinkedIn tasks: birthday wishes, targeted profile visits, invitation management — all running 24/7 on a low-power device.

---

## 🎯 Quick Navigation

**⚠️ NEW: This README was revised on 2025-12-18**

- 📚 **Full Documentation:** See [`docs/KNOWLEDGE_BASE_v1.1.md`](docs/KNOWLEDGE_BASE_v1.1.md) — **THE source of truth**
- 🚀 **Quick Setup:** Jump to [Installation](#-installation)
- 📖 **Architecture Docs:** See Knowledge Base, Part B
- 🔧 **Operations Manual:** See Knowledge Base, Part D (SOP)
- ❓ **FAQ:** See bottom of this README

---

## ✨ Features

### 🤖 Four Autonomous Bots

| Bot | Purpose | Schedule |
|-----|---------|----------|
| **Birthday Bot** | Send personalized messages on connection anniversaries | Daily (configurable) |
| **Visitor Bot** | Visit targeted profiles (increases profile visibility) | Configurable |
| **Invitation Manager** | Auto-accept/decline old pending invitations | Weekly |
| **Unlimited Bot** | Extended birthday wish with late message handling | Optional |

### 🖥️ Web Dashboard (Next.js)

- **Real-time monitoring** of bot executions
- **Job queue management** (start, stop, view logs)
- **Configuration editor** (YAML based)
- **Authentication upload** (cookies via web interface)
- **System health** (memory, CPU, uptime)

### 🔒 Security

- ✅ Encrypted cookie storage (Fernet AES-128)
- ✅ Password hashing (bcrypt)
- ✅ JWT API authentication
- ✅ Rate limiting (Nginx)
- ✅ HTTPS support (Let's Encrypt ready)

### ⚡ Optimized for Raspberry Pi 4

- ✅ **Memory:** Garbage collection + ZRAM compression
- ✅ **Concurrency:** Single worker (respects 4GB limit)
- ✅ **Database:** SQLite WAL mode (no external dependencies)
- ✅ **I/O:** Structlog JSON (optimized logging)
- ✅ **Container:** Multi-arch Docker (1.3GB image size)

---

## 📋 Requirements

### Hardware
- **Raspberry Pi 4** with 4GB+ RAM (8GB recommended for future scaling)
- **SD Card:** 32GB+ (Class A1 minimum)
- **Optional:** Ventilator or heatsink (throttles at 80°C)

### Software
- **OS:** Raspberry Pi OS (64-bit) Lite or Desktop
- **Docker:** 20.10+
- **Docker Compose:** 2.0+
- **Git:** 2.30+

### Connectivity
- Stable internet connection (WiFi or Ethernet)
- Access to LinkedIn.com

---

## 🚀 Installation

### Step 1: Prepare Raspberry Pi

```bash
# SSH into your RPi4
ssh pi@<IP_ADDRESS>

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pi
```

### Step 2: Clone Repository

```bash
cd /home/pi
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto
```

### Step 3: Configure Environment

```bash
# Copy example config
cp .env.pi4.example .env

# Edit with your values
nano .env
```

**Required variables:**
```bash
API_KEY=<generate-new-secret>              # 32 hex chars
JWT_SECRET=<generate-new-secret>           # 32 hex chars
DASHBOARD_PASSWORD=<bcrypt-hash>           # See note below
LINKEDIN_COOKIES=<path-or-json>            # Can be set later
```

**Generate secrets:**
```bash
# Generate API_KEY
python3 -c "import secrets; print(secrets.token_hex(16))"

# Generate JWT_SECRET (same)
python3 -c "import secrets; print(secrets.token_hex(16))"

# Hash password (you'll need to do this via Docker after build)
# Or use the setup.sh script (it handles this)
```

### Step 4: Run Setup Script

This script will:
- Configure ZRAM (swap compression)
- Set kernel parameters
- Build Docker images
- Start all services
- Run health checks

```bash
sudo ./setup.sh
```

⏱️ **This takes 45-60 minutes on first run** (Docker image build)

### Step 5: Verify Installation

```bash
# Check services are running
docker compose -f docker-compose.pi4-standalone.yml ps

# Watch logs
docker compose -f docker-compose.pi4-standalone.yml logs -f
```

**Services should be:**
- `api` → Up (port 8000)
- `dashboard` → Up (port 3000)
- `redis-bot` → Up (port 6379)
- `bot-worker` → Up (running jobs)

### Step 6: Access Dashboard

Open browser to: **`http://<PI_IP>:3000`**

- Default password: `<DASHBOARD_PASSWORD from .env>`
- Upload LinkedIn cookies via **Settings → Authentication**

---

## 📖 Documentation Structure

| Document | Purpose | Audience |
|----------|---------|----------|
| **[KNOWLEDGE_BASE_v1.1.md](docs/KNOWLEDGE_BASE_v1.1.md)** | Complete technical reference | Developers, Architects |
| **[AUDIT_REPORT.md](AUDIT_REPORT.md)** | Security & performance audit | DevOps, Project Leads |
| **[CONTEXT.md](CONTEXT.md)** | Project context & history | Team members |
| **[README.md](README.md)** | Quick start (THIS FILE) | New users |

**➡️ For detailed architecture, procedures, and standards: See [KNOWLEDGE_BASE_v1.1.md](docs/KNOWLEDGE_BASE_v1.1.md)**

---

## 🛠️ Common Operations

### Run a Bot Manually

```bash
# Via API
curl -X POST http://localhost:8000/bot/birthday/trigger \
    -H "Authorization: Bearer <API_KEY>" \
    -H "Content-Type: application/json"

# Or via Dashboard
# Settings → Bots → Select bot → Click "Run"
```

### View Logs

```bash
# All services
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Specific service
docker compose -f docker-compose.pi4-standalone.yml logs -f api

# Parse JSON logs (structlog)
docker compose -f docker-compose.pi4-standalone.yml logs api | \
    jq '.message' | head -50
```

### Check Memory Usage

```bash
free -h
zramctl                    # Show ZRAM compression ratio
swapon --show              # Show swap status
ps aux --sort=-%mem | head # Top memory consumers
```

### Database Queries

```bash
# Open SQLite shell
sqlite3 ./data/linkedin.db

# Example queries
SELECT COUNT(*) FROM bot_executions;
SELECT bot_name, status, COUNT(*) FROM bot_executions GROUP BY bot_name, status;
PRAGMA journal_mode;        # Should return "wal"
PRAGMA integrity_check;     # Should return "ok"
```

### Cleanup Zombie Processes

```bash
# Remove orphaned Chromium processes
./scripts/cleanup_chromium_zombies.sh

# Force cleanup (even if worker active)
./scripts/cleanup_chromium_zombies.sh --force
```

### Restart Services

```bash
# Restart all
docker compose -f docker-compose.pi4-standalone.yml restart

# Restart specific service
docker compose -f docker-compose.pi4-standalone.yml restart api
```

---

## ⚙️ Configuration

### Bot Scheduling

Edit `config/default_config.yaml`:

```yaml
bots:
  birthday:
    enabled: true
    schedule: "0 8 * * *"           # 08:00 daily
    max_concurrent: 1

  visitor:
    enabled: true
    schedule: "0 10 * * *"          # 10:00 daily
    max_profiles: 50
    delay_between_visits: 10        # seconds

  invitation_manager:
    enabled: true
    schedule: "0 0 * * 0"           # Weekly Sunday midnight
```

### Browser Configuration

Also in `config/default_config.yaml`:

```yaml
browser:
  headless: true
  viewport: { width: 1280, height: 720 }
  timeout: 120000                    # milliseconds (RPi4 needs 120s)
  user_agent: "Mozilla/5.0..."       # Randomized per execution
```

---

## 🔒 Security Best Practices

1. **Change Dashboard Password Monthly**
   ```bash
   # Generate new hash
   python3 -c "from src.utils.encryption import hash_password; print(hash_password('NewPassword!'))"

   # Update .env
   nano .env  # Update DASHBOARD_PASSWORD

   # Restart
   docker compose -f docker-compose.pi4-standalone.yml restart api
   ```

2. **Rotate API Keys Every 6 Months**
   - Generate new API_KEY in .env
   - Update any external integrations
   - Restart API service

3. **Monitor Access Logs**
   ```bash
   docker compose -f docker-compose.pi4-standalone.yml logs api | grep -i "unauthorized\|invalid"
   ```

4. **Keep System Updated**
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ./scripts/deploy_pi4_standalone.sh  # Updates Docker images
   ```

---

## 📊 Performance Metrics

### Expected Resource Usage (Normal State)

| Component | Typical Usage |
|-----------|---------------|
| **Memory** | 500-900MB / 4GB (12-22%) |
| **CPU** | 5-10% idle, 20-50% during bot run |
| **Swap** | 0-500MB (ZRAM) |
| **Disk I/O** | Logs: 1-5MB/day, DB: <10MB/day |

### Health Indicators

- ✅ Memory stable (no growth over hours)
- ✅ ZRAM compression ratio < 2:1
- ✅ No Chromium zombie processes
- ✅ SQLite checkpoint succeeds
- ✅ Bot timeouts < 120 seconds

---

## 🚨 Troubleshooting

### "Dashboard not responding"

```bash
# 1. Check if container is running
docker compose -f docker-compose.pi4-standalone.yml ps dashboard

# 2. If stopped, restart
docker compose -f docker-compose.pi4-standalone.yml restart dashboard

# 3. Check logs for errors
docker compose -f docker-compose.pi4-standalone.yml logs --tail=50 dashboard

# 4. If still stuck, full restart
docker compose -f docker-compose.pi4-standalone.yml down
docker compose -f docker-compose.pi4-standalone.yml up -d
```

### "Out of Memory error"

```bash
# 1. Free zombie processes
./scripts/cleanup_chromium_zombies.sh --force

# 2. Check ZRAM
sudo zramctl

# 3. If memory still high, restart worker
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker

# 4. Review logs for memory leaks
docker compose -f docker-compose.pi4-standalone.yml logs bot-worker | tail -100 | grep -i "memory\|gc"
```

### "Bot timeout (120s exceeded)"

```bash
# 1. Verify internet connection
ping -c 3 8.8.8.8

# 2. Check LinkedIn accessibility
curl -I https://www.linkedin.com

# 3. If timeout consistent, increase limit in src/core/base_bot.py
# Change job_timeout from 120 to 150

# 4. Rebuild and restart
./scripts/deploy_pi4_standalone.sh
```

### "SQLite database locked"

```bash
# 1. Check for stuck processes
ps aux | grep sqlite

# 2. Check WAL mode is enabled
sqlite3 ./data/linkedin.db "PRAGMA journal_mode;"
# Should return: wal

# 3. If corrupted, restore from backup
cp ./data/backups/linkedin-YYYYMMDD.db ./data/linkedin.db

# 4. Verify integrity
sqlite3 ./data/linkedin.db "PRAGMA integrity_check;"
```

---

## 📚 Further Reading

For **complete technical documentation**, see:

👉 **[docs/KNOWLEDGE_BASE_v1.1.md](docs/KNOWLEDGE_BASE_v1.1.md)**

Contains:
- **Part A:** Strategic vision & technology choices
- **Part B:** Detailed architecture (data flow, memory management, Docker)
- **Part C:** Script index with memory strategies
- **Part D:** Operating procedures (SOP) & emergency protocols
- **Part E:** Coding standards & security norms

---

## 📞 FAQ

**Q: Can I run multiple workers?**
A: No. The RPi4's 4GB RAM limits us to 1 worker. See Knowledge Base, Part B, B.6 for architectural reasoning.

**Q: How do I update to a new version?**
A:
```bash
git pull
./scripts/deploy_pi4_standalone.sh
```

**Q: Can I use external database (PostgreSQL)?**
A: Not recommended. SQLite + WAL is optimized for RPi4 constraints. External DB would need network reliability.

**Q: How long do bots typically run?**
A: Birthday Bot: 30-60s, Visitor Bot: 5-10min (depends on profile count), Invitation Manager: 2-5min.

**Q: Where are logs stored?**
A:
- Container logs: `docker compose logs`
- File logs: `logs/linkedin_bot.log` (rotated daily, 5MB max)
- Database: `data/linkedin.db` (bot_executions table)

**Q: Can I backup the database?**
A: Yes, manually:
```bash
cp ./data/linkedin.db ./data/backups/linkedin-$(date +%Y%m%d).db
```

Or scheduled via Knowledge Base, Part D.2.

**Q: What if cookies expire?**
A: Upload new cookies via Dashboard → Settings → Authentication → Upload auth_state.json.

**Q: How do I reset everything?**
A:
```bash
docker compose -f docker-compose.pi4-standalone.yml down -v  # ⚠️ Deletes data!
rm -rf ./data/*
./setup.sh  # Reinitialize
```

---

## 🤝 Contributing

Pull Requests welcome! Please:

1. Ensure code passes `flake8` (PEP8)
2. Use `structlog` for all logging (never `print()`)
3. Test on ARMv8 (RPi4) if possible
4. Keep Docker image < 1.5GB
5. Update [KNOWLEDGE_BASE_v1.1.md](docs/KNOWLEDGE_BASE_v1.1.md) if architecture changes

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file.

---

## 🏗️ Project Status

**2025-12-18 Update:**
- ✅ All audit corrections applied
- ✅ Playwright confirmed (no Selenium)
- ✅ Garbage collection active
- ✅ ZRAM configured
- ✅ Knowledge Base v1.1 written
- ✅ Production-ready

**Next Review:** 2026-03-18

---

**Questions?** See [docs/KNOWLEDGE_BASE_v1.1.md](docs/KNOWLEDGE_BASE_v1.1.md) or open an issue.

**For system architects:** Knowledge Base contains Part A (strategy), Part B (architecture), Part C (scripts), Part D (operations), Part E (standards).

---

*Last Updated: 2025-12-18*
*Maintained by: Claude (DevOps & Lead Developer)*
*Status: ✅ Production Ready for Raspberry Pi 4*
