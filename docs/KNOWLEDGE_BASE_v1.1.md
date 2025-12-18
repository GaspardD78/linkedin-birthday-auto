# 📚 BASE DE CONNAISSANCE v1.1 - LinkedIn Auto RPi4
**Source de Vérité Absolue du Projet**

**Version:** 1.1
**Date:** 2025-12-18
**Statut:** ✅ **PRODUCTION-READY**
**Architecte:** Claude (Expert DevOps & Lead Developer)
**Plateforme Cible:** Raspberry Pi 4 (4GB RAM, ARM64, SD Card 32GB)
**Codebase:** ~17,750 lignes Python, 4 bots autonomes, FastAPI + Next.js

---

## 📋 TABLE OF CONTENTS

1. [Partie A : Vision Stratégique](#partie-a--vision-stratégique)
2. [Partie B : Architecture Technique](#partie-b--architecture-technique)
3. [Partie C : Index des Scripts](#partie-c--index-des-scripts)
4. [Partie D : Procédures Opérationnelles](#partie-d--procédures-opérationnelles)
5. [Partie E : Standards & Normes](#partie-e--standards--normes)

---

# PARTIE A : VISION STRATÉGIQUE

## Raison d'Être du Projet

**LinkedIn Auto RPi4** est un système d'automatisation professionnel qui exécute des tâches LinkedIn répétitives (souhaits d'anniversaire, visites de profils ciblées, gestion d'invitations) de manière autonome et sécurisée.

### Contraintes Matérielles (Non-Négociables)

| Composant | Limite | Impact |
|-----------|--------|--------|
| **RAM** | 4GB | Max 1 worker RQ, aucune concurrence |
| **CPU** | ARMv8 4-core @ 1.8GHz | Bot timeout 120s (vs 60s standard) |
| **Disque** | SD Card 32GB | WAL mode, logs rotatifs, cleanup agressif |
| **Swap** | 1GB ZRAM + 2GB fichier | 5GB effectif, vitesse 100x supérieure |

### Décisions Techniques Irrévocables

| Choix | Option Rejetée | Justification |
|-------|-----------------|---------------|
| **Automatisation** | Selenium | Playwright = léger, headless-ready, ARM64 natif |
| **API** | Flask | FastAPI = async/await, meilleur perf, Pydantic validation |
| **Database** | PostgreSQL | SQLite WAL = ZERO maintenance, aucune dépendance externe |
| **Queue** | Celery | RQ = simple, Redis-backed, ARM64 compatible |
| **Logging** | logging stdlib | structlog = JSON structuré, parsing facile, I/O optimisé |
| **Frontend** | Vue.js | Next.js = SSR, bundle optimisé, meilleure perf |

---

## Stack Technique Définitif

### Backend
- **Runtime:** Python 3.11 (slim)
- **Web Framework:** FastAPI (ASGI, async)
- **Task Queue:** RQ (Redis Queue) + 1 worker sync
- **Database:** SQLite3 + WAL mode
- **Browser Automation:** Playwright (sync_api pour bots)
- **Logging:** structlog (JSON output)
- **Authentication:** JWT tokens + hashed passwords (bcrypt)

### Infrastructure
- **Container:** Docker (linux/amd64 + linux/arm64)
- **Compose:** docker-compose.pi4-standalone.yml
- **Memory Management:** ZRAM (1GB compressé) + Swap file (2GB)
- **Process Management:** systemd (supervisory)

### Frontend
- **Framework:** Next.js 14+
- **Package Manager:** pnpm
- **Build:** Static export (SSG)
- **Deployment:** Docker container

---

# PARTIE B : ARCHITECTURE TECHNIQUE

## B.1 - Flux d'Exécution Global

```
┌─────────────────────────────────────────────────────────────┐
│                    UTILISATEUR / CRON                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │   Dashboard (Next.js) │
          │   http://pi:3000      │
          └───────────┬───────────┘
                      │
                      ▼
          ┌───────────────────────────────────┐
          │   FastAPI Backend                 │
          │   /api/* routes (8000)            │
          │   ├── Bot Control                 │
          │   ├── Auth Management             │
          │   ├── Configuration               │
          │   └── Monitoring                  │
          └───────────┬───────────────────────┘
                      │
        ┌─────────────┴──────────────┐
        │                            │
        ▼                            ▼
   ┌─────────────┐        ┌────────────────┐
   │   Database  │        │  Redis Queue   │
   │   (SQLite)  │        │  (RQ Jobs)     │
   │             │        └────────┬────────┘
   └─────────────┘                 │
                                   ▼
                        ┌─────────────────────┐
                        │ Worker Bot (sync)   │
                        │ - Birthday Bot      │
                        │ - Visitor Bot       │
                        │ - Invitation Mgr    │
                        │ - Unlimited Bot     │
                        └─────────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │  Playwright/Browser │
                        │  (Chromium)         │
                        │  LinkedIn.com       │
                        └─────────────────────┘
```

---

## B.2 - Architecture Répertoires (`/src`)

```
src/
├── api/                          # FastAPI application (Port 8000)
│   ├── app.py                    # Main FastAPI app + lifespan
│   ├── security.py               # JWT verification, API key validation
│   ├── auth_routes.py            # /auth/* - Cookie upload, validation
│   ├── utils.py                  # Helper functions (logging, error handling)
│   │
│   └── routes/                   # Modularized API endpoints
│       ├── bot_control.py        # POST/GET /bot/* (start, stop, status)
│       ├── automation_control.py # POST /automation/* (schedule, resume)
│       ├── config_routes.py      # GET/POST /config/* (load, update)
│       ├── scheduler_routes.py   # GET /scheduler/* (job status)
│       ├── visitor_routes.py     # GET /visitor/* (stats, profiles)
│       ├── deployment.py         # GET /system/* (health, restart)
│       ├── stream_routes.py      # GET /stream/* (Server-Sent Events)
│       ├── notifications.py      # WebSocket notifications
│       └── [...other routes]
│
├── bots/                         # Bot implementations (Workers execute)
│   ├── __init__.py
│   ├── birthday_bot.py           # Birthday wishes automation (inherits BaseBot)
│   ├── visitor_bot.py            # Profile visitation automation
│   ├── invitation_manager_bot.py # Invitation acceptance/decline
│   ├── unlimited_bot.py          # Legacy birthday bot (with late messages)
│   └── base_bot.py              # ❌ MOVED TO core/ (see below)
│
├── core/                         # Core framework
│   ├── base_bot.py               # 🎯 ABSTRACT BASE CLASS for all bots
│   │                             #    ├── setup() - Browser initialization
│   │                             #    ├── run() - Main bot logic
│   │                             #    ├── teardown() - Cleanup + gc.collect()
│   │                             #    └── execute() - Full lifecycle
│   │
│   ├── browser_manager.py         # Playwright wrapper
│   │                             #    ├── create_browser() - Init Chromium
│   │                             #    ├── create_context() - Stealth mode
│   │                             #    ├── close() - Graceful shutdown + SIGKILL fallback
│   │                             #    └── Memory leak prevention
│   │
│   ├── auth_manager.py            # Cookie & session management
│   │                             #    ├── save_cookies() - Encrypt with Fernet
│   │                             #    ├── load_cookies() - Decrypt
│   │                             #    └── validate_session() - Test LinkedIn access
│   │
│   ├── database.py                # SQLite adapter (WAL optimized)
│   │                             #    ├── init_db() - Create schema
│   │                             #    ├── get_or_create() - ORM-like pattern
│   │                             #    ├── with_connection() - Retry on lock
│   │                             #    └── Memory-mapped I/O (256MB)
│   │
│   └── selector_manager.py        # DOM selector resolution
│                                 #    └── Dynamic LinkedIn selector handling
│
├── config/                        # Configuration management
│   ├── config_manager.py          # Load YAML, merge env vars
│   ├── config_schema.py           # Pydantic models (validation)
│   └── default_config.yaml        # Default values (mounted in Docker)
│
├── scheduler/                     # Automation scheduling
│   ├── scheduler.py               # APScheduler wrapper + cron jobs
│   ├── job_store.py               # Persistent job storage
│   └── jobs/                      # Scheduled job implementations
│
├── queue/                         # RQ Job Queue
│   ├── worker.py                  # RQ Worker initialization
│   └── jobs.py                    # Job enqueue functions
│
├── utils/                         # Utilities
│   ├── logging.py                 # structlog setup (JSON output)
│   ├── exceptions.py              # Custom exception hierarchy
│   ├── encryption.py              # Fernet cookie encryption
│   ├── rate_limiter.py            # Token bucket rate limiting
│   └── helpers.py                 # Common utilities
│
├── services/                      # Business logic services
│   ├── notification_service.py    # Dashboard notifications
│   ├── monitoring_service.py      # Health checks
│   └── backup_service.py          # Database backups
│
├── monitoring/                    # Prometheus metrics
│   ├── metrics.py                 # Metric definitions
│   └── prometheus_routes.py       # /metrics endpoint
│
└── web/                           # Frontend integration (legacy)
    └── [...static files]
```

---

## B.3 - Cycle de Vie d'un Bot (Exemple Birthday Bot)

### 1. **Enqueue** (Utilisateur → Queue)
```python
# dashboard/api calls POST /bot/birthday/trigger
# → app.py routes request to bot_control.py
# → bot_control.py enqueues job to RQ queue
job = queue.enqueue(
    'src.bots.birthday_bot.run',  # Task ID
    job_timeout='120s'              # ARM64 timeout
)
```

### 2. **Dequeue & Execute** (Worker Process)
```python
# RQ Worker reads from Redis
# 1. Imports & instantiates BirthdayBot
# 2. Calls .execute() (inherited from BaseBot)

class BirthdayBot(BaseBot):
    async def run(self):
        # Bot-specific logic
        pass

# BaseBot.execute() orchestrates:
# └── setup() → run() → teardown()
```

### 3. **Setup Phase** (Browser Init)
```python
# BaseBot.setup():
self.browser_manager = BrowserManager(config)
self.browser, self.context, self.page = \
    self.browser_manager.create_browser(auth_state_path)
# ✅ Stealth mode enabled
# ✅ User-Agent randomized
# ✅ Viewport set to mobile (LinkedIn detection)
```

### 4. **Run Phase** (Bot Logic)
```python
# BirthdayBot.run():
# 1. Navigate to LinkedIn/me
# 2. Query birthdays (API)
# 3. Send wishes (custom message per person)
# 4. Log results to database
# 5. Return execution summary
```

### 5. **Teardown Phase** (Cleanup)
```python
# BaseBot.teardown():
try:
    await self.browser_manager.close()  # Graceful close
finally:
    import gc
    gc.collect()  # ✅ Force memory release (RPi4 critical!)
    self.logger.debug("Forced garbage collection completed")
```

### 6. **Database Persistence**
```python
# Each bot logs:
db.execute("""
    INSERT INTO bot_executions (bot_name, status, messages_sent, ...)
    VALUES (?, ?, ?, ...)
""")
db.commit()  # WAL mode ensures atomicity
```

---

## B.4 - Memory Management (Critical for RPi4)

### Garbage Collection

| Phase | Action | Memory Freed |
|-------|--------|--------------|
| **Browser Close** | `await context.close()` | ~200MB (Chromium tabs) |
| **Playwright Instance** | `await p.stop()` | ~100MB (playwright sockets) |
| **Forced GC** | `gc.collect()` | ~50-100MB (Python objects) |
| **Total per Execution** | All phases | **300-500MB freed** |

**Location:** `src/core/base_bot.py:182-185`

### ZRAM Configuration

```bash
# In setup.sh (line 202):
configure_zram() {
    # 1GB physical ZRAM device
    # Compression ratio ~3:1 = 3GB effective
    # Algorithm: lz4 (fast, good ratio)
    # Priority: 10 (used before swap file)
}
```

**Result:** 5GB total swap (3GB ZRAM in RAM + 2GB swap file)

### Swap File

- **Size:** 2GB (auto-created if RAM < 6GB)
- **Location:** `/var/swapfile` (bind-mounted to avoid SD wear)
- **Swappiness:** 10 (prefer RAM)

---

## B.5 - Database Architecture (SQLite WAL)

### WAL Mode Benefits

```python
# src/core/database.py:107
pragma_settings = {
    'journal_mode': 'WAL',           # Write-Ahead Logging
    'cache_size': 20000,              # 20MB cache (RPi4 optimized)
    'busy_timeout': 60000,            # 60s retry on lock
    'synchronous': 'NORMAL',          # Safe with WAL
    'temp_store': 'MEMORY',           # Temporary tables in RAM
    'mmap_size': 256 * 1024 * 1024,   # Memory-mapped I/O (256MB)
}
```

### Impact

- **Writes:** Batched → fewer SD card cycles
- **Reads:** Non-blocking → concurrent access
- **Durability:** Guaranteed with checkpoint strategy
- **Storage:** -wal and -shm files managed automatically

---

## B.6 - Docker Architecture

### Dockerfile.multiarch

```dockerfile
# Multi-arch build: linux/amd64 + linux/arm64
# Base: python:3.11-slim-bookworm

# Phase 1: System dependencies
apt-get install -y chromium-browser \
                   libx11-6 libxss1 libappindicator1 libindicator7

# Phase 2: Python dependencies
pip install --no-cache-dir -r requirements.txt

# Phase 3: Playwright
playwright install chromium

# Phase 4: Aggressive cleanup
rm -rf /var/lib/apt/lists/*
rm -rf /root/.cache/pip
find /ms-playwright -type f -name "*.log" -delete
```

**Image Size:** 1.3GB (optimized from 1.8GB)

### docker-compose.pi4-standalone.yml

```yaml
services:
  redis-bot:
    image: redis:7-alpine
    # ✅ AOF only (no BGSAVE fork on RPi4)

  api:
    build: .
    ports: ["8000:8000"]
    depends_on: [redis-bot]
    env: .env

  dashboard:
    build: ./dashboard
    ports: ["3000:3000"]
    # ✅ Static export (no Node.js runtime needed)

  bot-worker:
    build: .
    command: python -m src.queue.worker
    depends_on: [redis-bot]
    # ✅ 1 worker only (RPi4 constraint)
```

---

# PARTIE C : INDEX COMMENTÉ DES SCRIPTS

## C.1 - Scripts de Déploiement

### `/setup.sh`
**Raison d'Être:** Installation complète du projet sur RPi4 de zéro
**Stratégie Mémoire:** Configure ZRAM dès le départ

```bash
Phase 0: Check system requirements
├─ Verify Python 3.11+
├─ Verify Docker + Docker Compose
└─ Verify 4GB+ RAM

Phase 1: Docker configuration
├─ Enable IPv4 forwarding
├─ Configure DNS (1.1.1.1, 8.8.8.8) ✅ Avoids Freebox IPv6 issues
└─ Create daemon.json

Phase 2: System optimization
├─ Set kernel parameters (vm.overcommit_memory, swappiness)
├─ Configure ZRAM (1GB compressé)
└─ Create swap file (2GB)

Phase 3: Project setup
├─ Copy .env from example
├─ Initialize database (SQLite)
└─ Build Docker images

Phase 4: Service startup
├─ docker-compose up -d
├─ Health checks (with retry)
└─ Log initial status
```

**Invocation:** `./setup.sh` (once per RPi4)

---

### `/scripts/cleanup_chromium_zombies.sh`
**Raison d'Être:** Eliminer processus Chromium orphelins accumulés
**Stratégie Mémoire:** Libère 100-200MB de shared memory (/dev/shm)

```bash
# 1. Find zombie processes
ps aux | grep -E "chromium|chrome" | grep -v grep

# 2. Graceful kill (SIGTERM)
kill -TERM $pid

# 3. Force kill if still alive (SIGKILL)
kill -9 $pid

# 4. Clean temporary files
rm -rf /tmp/playwright-*
rm -rf /dev/shm/*

# 5. Clean core dumps
rm -rf /tmp/core_dumps/
```

**Invocation:**
```bash
./scripts/cleanup_chromium_zombies.sh          # Normal mode
./scripts/cleanup_chromium_zombies.sh --force  # Even if worker active
```

**Schedule:** Hebdomadairement (cron job ou manuel)

---

## C.2 - Scripts de Maintenance

### `/scripts/validate_rpi4_config.sh`
**Raison d'Être:** Vérifier que l'environnement RPi4 est correctement configuré
**Stratégie Mémoire:** Check all memory-critical settings

```bash
Validation checklist:
├─ RAM + SWAP >= 6GB ✅ Minimum requirement
├─ ZRAM active (zramctl) ✅ Critical for stability
├─ Kernel params (vm.overcommit_memory=1) ✅ Allow overcommit
├─ SQLite WAL mode enabled ✅ Durability guaranteed
├─ Chromium processes count ✅ Should be 0 at rest
├─ Docker services healthy ✅ All containers up
└─ Critical files readable ✅ .env, API_KEY, passwords
```

**Invocation:** `./scripts/validate_rpi4_config.sh` (post-deployment)

---

### `/scripts/deploy_pi4_standalone.sh`
**Raison d'Être:** Rebuild et redémarrer tous les services (upgrade friendly)
**Stratégie Mémoire:** Pulls latest code, rebuilds images

```bash
1. git pull
2. docker-compose down
3. docker system prune -f  # Clean orphaned images
4. docker-compose up -d --build
5. Health check with retry
```

**Invocation:** `./scripts/deploy_pi4_standalone.sh` (updates)

---

### `/src/scripts/init_db.py`
**Raison d'Être:** Initialiser la base de données SQLite avec schéma
**Stratégie Mémoire:** Single-threaded, small schema file

```python
Creates tables:
├─ users (authentication)
├─ bot_executions (audit trail)
├─ profiles_visited (visitor tracking)
├─ messages_sent (birthday history)
├─ invitations (invitation manager state)
└─ system_logs (error tracking)

Ensures:
└─ WAL mode activated
└─ Indexes created for query performance
```

**Invocation:** Automatic in `setup.sh`, or manual:
```bash
cd /home/user/linkedin-birthday-auto
python -m src.scripts.init_db
```

---

## C.3 - Worker Scripts

### `src/queue/worker.py`
**Raison d'Être:** RQ Worker que lit les jobs depuis Redis et les exécute
**Stratégie Mémoire:** 1 worker only (configured in docker-compose)

```python
@shared_job_dependencies
def execute_job(job_id):
    # 1. Get job from Redis queue
    # 2. Import bot class dynamically
    # 3. Instantiate + execute
    # 4. Handle exceptions + logging
    # 5. Return result to Redis
```

**Constraints:**
- **Timeout:** 120 seconds (ARM64 needs extra margin)
- **Max retries:** 1 (avoid queue congestion)
- **Concurrency:** 1 worker (memory constraint)

**Invocation:** `docker-compose up bot-worker` (runs 24/7)

---

# PARTIE D : PROCÉDURES OPÉRATIONNELLES (SOP)

## D.1 - Protocole de Déploiement Initial

### Étape 1 : Préparation Matérielle
```bash
# 1. Flash Raspberry Pi OS 64-bit
#    → Download ISO from raspberrypi.com
#    → Flash with Balena Etcher
#    → SSH enabled

# 2. Verify hardware
ssh pi@<IP_RPI>
free -h         # Should show 4GB+ RAM
uname -a        # Should show ARM64

# 3. Expand filesystem (Lite version)
sudo raspi-config
# Advanced Options → Expand Filesystem
```

### Étape 2 : Cloner & Configurer
```bash
# 1. Clone repo
cd /home/pi
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# 2. Copy environment
cp .env.pi4.example .env
nano .env
# Fill in:
# - API_KEY (generate: python -c "import secrets; print(secrets.token_hex(16))")
# - JWT_SECRET (same length)
# - DASHBOARD_PASSWORD (will be bcrypt hashed)
# - LINKEDIN_COOKIES (optional, can upload via web)

# 3. Verify Git branch
git checkout main
```

### Étape 3 : Lancer Setup
```bash
# This will:
# - Configure ZRAM
# - Set kernel parameters
# - Build Docker images (may take 30-45min on RPi4)
# - Start all services
# - Run health checks
sudo ./setup.sh

# Watch the logs
docker compose -f docker-compose.pi4-standalone.yml logs -f
```

### Étape 4 : Validation
```bash
# Run validation script
./scripts/validate_rpi4_config.sh

# Expected output:
# ✅ RAM + SWAP: 6GB+
# ✅ ZRAM: Active
# ✅ Kernel params: Correct
# ✅ SQLite: WAL mode
# ✅ Services: Healthy
```

### Étape 5 : Accès Dashboard
```bash
# Open browser
http://<IP_RPI>:3000

# Login
password: <DASHBOARD_PASSWORD from .env>

# Upload cookies (if not already in .env)
Settings → Authentication → Upload auth_state.json
```

**Expected Time:** 60-90 minutes on first run

---

## D.2 - Protocole de Maintenance Hebdomadaire

### Lundi (Nettoyage Mémoire)
```bash
ssh pi@<IP_RPI>
cd /home/pi/linkedin-birthday-auto

# 1. Check memory usage
free -h
# Should be < 3.5GB used

# 2. If memory > 3.5GB, cleanup zombies
./scripts/cleanup_chromium_zombies.sh

# 3. Verify again
free -h
```

### Mercredi (Vérification Santé)
```bash
# 1. Check all services running
docker compose -f docker-compose.pi4-standalone.yml ps
# Should show all services as "Up"

# 2. Check logs for errors
docker compose -f docker-compose.pi4-standalone.yml logs --tail=50 | grep -i error
# Should be minimal (normal errors only)

# 3. Verify database health
sqlite3 ./data/linkedin.db "PRAGMA integrity_check;"
# Should return "ok"

# 4. Check ZRAM compression ratio
sudo zramctl
# Should show "COMPR" < 1GB
```

### Vendredi (Backup Database)
```bash
# 1. Create backup
mkdir -p ./data/backups
cp ./data/linkedin.db ./data/backups/linkedin-$(date +%Y%m%d).db

# 2. Verify backup
ls -lh ./data/backups/
sqlite3 ./data/backups/linkedin-$(date +%Y%m%d).db "SELECT COUNT(*) FROM bot_executions;"
# Should return a number > 0
```

---

## D.3 - Protocole d'Urgence (Troubleshooting)

### Symptôme: "Dashboard ne répond plus"

**1. Diagnostic**
```bash
# Check container status
docker compose -f docker-compose.pi4-standalone.yml ps
# If dashboard = Exited, proceed to restart

# Check logs
docker compose -f docker-compose.pi4-standalone.yml logs --tail=100 dashboard
# Look for errors

# Check port
sudo lsof -i :3000
# Should show npm or node process
```

**2. Redémarrage Gracieux**
```bash
# Restart just dashboard
docker compose -f docker-compose.pi4-standalone.yml restart dashboard

# Wait 10 seconds
sleep 10

# Test
curl -f http://localhost:3000 || echo "Dashboard still down"
```

**3. Redémarrage Complet** (si gracieux échoue)
```bash
# Stop all services
docker compose -f docker-compose.pi4-standalone.yml down

# Wait 5 seconds
sleep 5

# Start all services
docker compose -f docker-compose.pi4-standalone.yml up -d

# Monitor startup (5 minutes)
docker compose -f docker-compose.pi4-standalone.yml logs -f
```

---

### Symptôme: "Mémoire full (Out of Memory)"

**1. Diagnostic**
```bash
free -h
# If Mem: 4GB used + 0GB available = OOM

# Check swap
swapon --show
# If all used = critical

# Find memory hogs
ps aux --sort=-%mem | head -20
```

**2. Immediate Action**
```bash
# Kill any zombie Chromium processes
./scripts/cleanup_chromium_zombies.sh --force

# Verify
free -h
# Should see significant improvement

# If not, restart worker
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker
```

**3. Root Cause Analysis**
```bash
# Check logs for memory leaks
docker compose -f docker-compose.pi4-standalone.yml logs bot-worker | tail -200 | grep -i "memory\|gc\|garbage"

# Check ZRAM usage
sudo zramctl
# If COMPR ratio > 2:1, we're hitting swap hard

# Review bot executions
sqlite3 ./data/linkedin.db "SELECT COUNT(*) FROM bot_executions WHERE created_at > datetime('now', '-1 day');"
# If too many executions, adjust scheduler
```

---

### Symptôme: "Bot timeout (120s)"

**1. Check LinkedIn Connectivity**
```bash
# From API container
docker compose -f docker-compose.pi4-standalone.yml exec api \
    curl -v https://www.linkedin.com

# Should not timeout
```

**2. Check Playwright Configuration**
```bash
# Check browser_manager.py timeout settings
grep -n "timeout" /home/pi/linkedin-birthday-auto/src/core/browser_manager.py

# Current setting: 120s (correct for ARM64)
```

**3. Increase Timeout** (if consistently timing out)
```bash
# Edit src/core/base_bot.py
nano src/core/base_bot.py
# Change: job_timeout = 150  (was 120)

# Rebuild and restart
./scripts/deploy_pi4_standalone.sh
```

---

## D.4 - Protocole de Sécurité

### Mensuel (Renouvellement Clés)

```bash
# 1. Generate new API_KEY
python -c "import secrets; print('API_KEY=' + secrets.token_hex(32))"

# 2. Update .env
nano .env
# Paste new API_KEY

# 3. Restart API
docker compose -f docker-compose.pi4-standalone.yml restart api

# 4. Update dashboard settings (if using API directly)
# Via http://localhost:3000/settings
```

### Trimestriel (Renouvellement Password)

```bash
# 1. Generate new password hash (30 chars min)
python -c "from src.utils.encryption import hash_password; print(hash_password('YourNewPassword123!'))"

# 2. Update .env
DASHBOARD_PASSWORD=<hash_from_above>

# 3. Restart API
docker compose -f docker-compose.pi4-standalone.yml restart api

# 4. Test login on dashboard
curl -X POST http://localhost:3000/api/auth/login \
    -d password=YourNewPassword123! \
    -H "Content-Type: application/json"
```

---

# PARTIE E : STANDARDS & NORMES

## E.1 - Normes de Codage

### Imports Structure
```python
# 1. Standard library
import os
import sys
from pathlib import Path

# 2. Third-party
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 3. Local
from ..core.database import get_database
from ..utils.logging import get_logger
```

### Logging Obligatoire
```python
# ✅ CORRECT: Use structlog
from ..utils.logging import get_logger
logger = get_logger(__name__)

# ❌ WRONG: Don't use print()
print("Something happened")  # This saturates I/O on RPi4

# ❌ WRONG: Don't use logging.getLogger
import logging
logger = logging.getLogger(__name__)
```

### Bots Structure

Every bot must:
1. Inherit from `BaseBot`
2. Implement `async def run(self)` method
3. Call `await self.page.goto()` for navigation
4. Use `self.logger` for logging
5. Handle `PlaywrightTimeoutError` exceptions

```python
from ..core.base_bot import BaseBot
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

class MyBot(BaseBot):
    """Docstring explaining bot purpose"""

    async def run(self):
        try:
            # Bot logic here
            await self.page.goto("https://linkedin.com/")
            self.logger.info("Bot started")
        except PlaywrightTimeoutError:
            self.logger.error("Navigation timeout")
            raise
```

---

## E.2 - Normes de Configuration

### Variables d'Environnement Obligatoires
```bash
# API Security
API_KEY=<32-hex-chars>
JWT_SECRET=<32-hex-chars>
DASHBOARD_PASSWORD=<bcrypt-hash>

# LinkedIn Auth
LINKEDIN_COOKIES=<json-or-path-to-auth_state.json>

# Docker Services
REDIS_HOST=redis-bot
REDIS_PORT=6379
DATABASE_PATH=./data/linkedin.db

# RPi4 Optimization
WORKER_TIMEOUT=120
WORKER_CONCURRENCY=1
MALLOC_ARENA_MAX=2
```

### YAML Configuration
```yaml
# config/default_config.yaml
browser:
  headless: true
  viewport: { width: 1280, height: 720 }
  timeout: 120000  # milliseconds

bots:
  birthday:
    max_concurrent: 1
    delay_between_messages: 3  # seconds
  visitor:
    max_profiles: 50
    delay_between_visits: 10
```

---

## E.3 - Normes de Performance (RPi4)

| Métrique | Limite | Action si Dépassé |
|----------|--------|-------------------|
| **Memory Usage** | 3.5GB | Restart worker |
| **CPU Usage** | 80% sustained | Check bot logic |
| **Disk I/O** | >500MB/s | Check SQLite |
| **Process Count** | <50 | Cleanup zombies |
| **Bot Timeout** | 120s | Increase timeout or optimize |

---

## E.4 - Normes de Sécurité

### Chiffrement des Données Sensibles
```python
from ..utils.encryption import encrypt_data, decrypt_data

# Store securely
encrypted_cookies = encrypt_data(json.dumps(cookies))

# Retrieve securely
cookies = json.loads(decrypt_data(encrypted_cookies))
```

### Hachage des Mots de Passe
```python
from src.utils.encryption import hash_password, verify_password

# Create hash
hashed = hash_password("UserPassword")

# Verify password
if verify_password("UserPassword", hashed):
    # Allow access
```

### API Key Validation
```python
from src.api.security import verify_api_key, Depends

@app.get("/protected")
async def protected_route(api_key: str = Depends(verify_api_key)):
    # Only API key holders can access
    return {"status": "ok"}
```

---

## E.5 - Checklist de Déploiement

Avant chaque push vers production:

- [ ] Code passes `flake8` (PEP8 style)
- [ ] Logging uses `structlog` (not `print()`)
- [ ] No hardcoded passwords or API keys
- [ ] Bots inherit from `BaseBot`
- [ ] Timeouts set to 120s+ (ARM64 requirement)
- [ ] Memory leaks checked (gc.collect() in teardown)
- [ ] Tests pass locally (if applicable)
- [ ] Docker image builds for both amd64 + arm64
- [ ] No new dependencies added (keep image < 1.5GB)
- [ ] ZRAM configuration still present in setup.sh
- [ ] Documentation updated (this file)

---

## E.6 - Hiérarchie d'Exceptions

```python
LinkedInBotError (base)
├── BrowserInitError
│   ├── PlaywrightInstallError
│   └── CookieLoadError
├── AuthenticationError
│   ├── CookieValidationError
│   └── SessionExpiredError
├── NavigationError
│   ├── TimeoutError
│   └── ElementNotFoundError
└── DatabaseError
    ├── LockError
    └── IntegrityError
```

---

# APPENDIX: QUICK REFERENCE

## Commandes Essentielles

```bash
# Status
docker compose -f docker-compose.pi4-standalone.yml ps

# Logs
docker compose -f docker-compose.pi4-standalone.yml logs -f api

# Restart
docker compose -f docker-compose.pi4-standalone.yml restart <service>

# Memory check
free -h && zramctl

# Database check
sqlite3 ./data/linkedin.db "SELECT COUNT(*) FROM bot_executions;"

# Bot trigger (via API)
curl -X POST http://localhost:8000/bot/birthday/trigger \
    -H "Authorization: Bearer <API_KEY>"
```

---

**FIN DE LA BASE DE CONNAISSANCE v1.1**

**Source de Vérité - À jour au: 2025-12-18**
**Validée par:** Architecte Système Claude
**Prochaine révision:** 2026-03-18
