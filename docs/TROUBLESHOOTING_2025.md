# 🔧 GUIDE TROUBLESHOOTING COMPLET
## Solutions pour Problèmes Courants (Jan 2025)

**Version:** 3.3+
**Date:** Jan 2025
**Format:** Organisation par symptôme + solutions progressives

---

## 📋 Table des Matières

1. [Setup Phase](#setup-phase)
2. [Déploiement Docker](#déploiement-docker)
3. [HTTPS & Certificats](#https--certificats)
4. [Google Drive Backup](#google-drive-backup)
5. [Dashboard & API](#dashboard--api)
6. [Ressources & Support](#ressources--support)

---

## 🏗️ Setup Phase

### ❌ "Docker not found"

**Message d'erreur:**
```
Docker introuvable. Installation requise.
```

**Solutions:**

1. **Installer Docker:**
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```

2. **Vérifier installation:**
   ```bash
   docker --version
   # Output: Docker version 20.10.x, ...
   ```

3. **Relancer setup:**
   ```bash
   ./setup.sh
   ```

---

### ❌ "Permission denied" au setup

**Message d'erreur:**
```
Permission denied while trying to connect to Docker daemon
```

**Causes & Solutions:**

```bash
# Solution 1: Ajouter user au groupe docker
sudo usermod -aG docker $USER
newgrp docker
./setup.sh

# Solution 2: Utiliser sudo (moins recommandé)
sudo ./setup.sh

# Solution 3: Vérifier socket permissions
ls -la /var/run/docker.sock
# Doit voir: srw-rw---- root docker
```

---

### ❌ "Insufficient memory"

**Message d'erreur:**
```
Mémoire insuffisante (<6GB). Risque de crash élevé.
```

**Solutions progressives:**

```bash
# 1. Vérifier mémoire actuelle:
free -h

# 2. Le script proposera augmenter SWAP
# Choisir: o (oui)

# 3. Ou augmenter manuellement:
# Créer swapfile 4GB:
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 4. Vérifier:
free -h
# Doit voir ≥ 6GB total (RAM + SWAP)

# 5. Rendre persistant (au reboot):
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

### ❌ "DNS configuration failed"

**Message d'erreur:**
```
Impossible de configurer Docker DNS
```

**Solutions:**

```bash
# 1. Vérifier daemon.json:
cat /etc/docker/daemon.json

# 2. Reset Docker config:
sudo systemctl stop docker
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
sudo rm /etc/docker/daemon.json

# 3. Relancer setup:
./setup.sh

# 4. Vérifier:
docker info | grep -A 5 "DNS"
```

---

### ❌ "Password hashing failed" (Setup Phase 4)

**Message d'erreur:**
```
[ERROR] Impossible de hasher le mot de passe (aucune méthode disponible)
[ERROR] Setup échoué (Code 1)
```

**Causes possibles :**
1. Python `bcrypt` module not installed
2. No fallback hashing tools available (htpasswd, crypt)
3. All hashing methods failed

**Solutions progressives:**

```bash
# 1. Relancer setup (auto-installs bcrypt v4.0+):
./setup.sh

# 2. Si erreur persiste, installer manuellement:
python3 -m pip install -q bcrypt --break-system-packages

# 3. Vérifier crypt module:
python3 -c "import crypt; print('crypt available')"

# 4. Installer Apache utils (fallback):
sudo apt-get update
sudo apt-get install -y apache2-utils

# 5. Relancer setup:
./setup.sh --resume
```

**Note:** v4.0+ auto-installs bcrypt, so this should not happen. See docs/PASSWORD_HASHING_ROBUSTNESS_2025.md for details.

---

## 🐳 Déploiement Docker

### ❌ "Docker pull timeout"

**Message d'erreur:**
```
Download time out while pulling images
```

**Causes:**
- Réseau lent
- Registry surchargé
- IPv6 issues sur RPi4

**Solutions:**

```bash
# 1. Relancer (retry automatique):
./setup.sh

# 2. Ou pull images manuellement:
docker pull redis:7-alpine
docker pull ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest
docker pull ghcr.io/gaspardd78/linkedin-birthday-auto-api:latest

# 3. Vérifier Internet:
ping 8.8.8.8

# 4. Forcer IPv4 (si problème IPv6):
# Éditer /etc/docker/daemon.json:
{
  "ipv6": false
}
# Restart Docker:
sudo systemctl restart docker
```

---

### ❌ "Conteneur crash loop"

**Message d'erreur:**
```
docker compose ps
# Container status: "Restarting (1) 5 seconds ago"
```

**Solutions progressives:**

```bash
# 1. Voir les logs:
docker compose logs SERVICE_NAME

# 2. Exemple pour dashboard:
docker compose logs dashboard
# Chercher ERROR ou Exception

# 3. Problèmes courants & fixes:

# Problème A: Port already in use
docker compose ps
# Si port 3000 en use:
sudo lsof -i :3000
# Kill processus conflictuel

# Problème B: Pas assez mémoire
# Aumenter SWAP (voir section Insufficient Memory)

# Problème C: Volume permissions
docker compose down
sudo chown -R 1000:1000 data logs config
docker compose up -d

# 4. Relancer:
docker compose up -d
```

---

### ❌ "Cannot connect to API"

**Message d'erreur:**
```
error: connect ECONNREFUSED 127.0.0.1:8000
```

**Solutions:**

```bash
# 1. Vérifier API running:
docker compose ps api
# Status doit être: Up

# 2. Voir logs API:
docker compose logs api

# 3. Test direct:
curl http://localhost:8000/health
# Output: {"status": "ok"}

# 4. Si fail:
# Redémarrer API:
docker compose restart api

# 5. Si persiste:
docker compose down
docker compose up -d
```

---

## 🔐 HTTPS & Certificats

### ❌ "ERR_CERT_SELF_SIGNED"

**Message d'erreur (Browser):**
```
Your connection is not private
NET::ERR_CERT_SELF_SIGNED
```

**C'est normal pour auto-signé!**

**Solutions:**

```
1. Accepter risque (click: Advanced → Proceed)
   Temporaire pendant setup

2. Utiliser Let's Encrypt (solution permanente):
   ./scripts/setup_letsencrypt.sh
```

---

### ❌ "Let's Encrypt DNS validation failed"

**Message d'erreur:**
```
DNS resolution failed for domain.com
```

**Solutions:**

```bash
# 1. Vérifier DNS pointant:
nslookup domain.com
# Output: Address: 1.2.3.4 (votre IP publique)

# 2. Vérifier port 80 accessible:
curl -v http://domain.com
# Doit retourner 301 (redirect HTTPS)

# 3. Firewall/routeur:
# Vérifier port 80 forwarding vers RPi4
# Vérifier port 443 forwarding

# 4. Relancer Let's Encrypt setup:
sudo rm -rf /etc/letsencrypt/live/domain.com
./scripts/setup_letsencrypt.sh
```

---

### ❌ "HTTP 520 Bad Gateway"

**Message d'erreur (HTTPS connexion OK, mais contenu fail):**
```
502 Bad Gateway / 520 Unknown Error
```

**Causes:** Nginx → services back-end down

**Solutions:**

```bash
# 1. Vérifier services:
docker compose ps

# 2. Tous doivent être "Up":
# - dashboard
# - api
# - nginx
# - redis-bot
# - redis-dashboard

# 3. Si un est Down/Exited:
docker compose restart SERVICE_NAME

# 4. Voir logs:
docker compose logs nginx
docker compose logs dashboard
docker compose logs api

# 5. Si problème persiste:
docker compose down
docker compose up -d

# 6. Attendre 30s et retry
sleep 30
curl https://domain.com
```

---

## ☁️ Google Drive Backup

### ❌ "rclone not found"

**Message d'erreur:**
```
rclone n'est pas installé. Abandon.
```

**Solutions:**

```bash
# Installer:
sudo apt-get update
sudo apt-get install -y rclone

# Vérifier:
rclone version
```

---

### ❌ "No remote rclone configured"

**Message d'erreur:**
```
Aucun remote rclone configuré.
```

**Solutions:**

```bash
# Configuration interactive:
rclone config

# Steps:
# 1. New remote → n
# 2. Name: gdrive
# 3. Type: drive (Google Drive)
# 4. OAuth flow (browser authorize)
# 5. Done

# Vérifier:
rclone listremotes
# Doit voir: gdrive:
```

---

### ❌ "Backup script échoue"

**Message d'erreur:**
```
ERROR Échec à la ligne XX
```

**Solutions progressives:**

```bash
# 1. Voir logs complets:
cat logs/backup_gdrive.log

# 2. Vérifier préalables:
rclone listremotes        # Remote configured?
ls data/linkedin.db       # DB existe?
ls config/                # Config existe?

# 3. Test backup manuel:
./scripts/backup_to_gdrive.sh --verbose

# 4. Problèmes courants:

# A) Network fail:
ping 8.8.8.8              # Internet OK?
rclone ls gdrive:         # Google Drive accessible?

# B) Permission issues:
ls -la data/              # User owns? (pas root)
ls -la logs/              # Writable logs?

# C) Disk full:
df -h                     # ≥ 500MB libre?

# D) DB locked:
docker compose restart    # Unlock DB
./scripts/backup_to_gdrive.sh

# 5. If still fail: Check cron logs
sudo journalctl -u cron | tail -20
```

---

### ❌ "Restore fails: archive corrupted"

**Message d'erreur:**
```
tar: Unexpected end of file
```

**Solutions:**

```bash
# 1. Test archive:
tar -tzf backup_file.tar.gz > /dev/null

# Si error → corrupted

# 2. Solutions:
# A) Try earlier backup:
rclone ls gdrive:LinkedInBot_Backups
# Pick older file

# B) Re-download:
rclone copy gdrive:LinkedInBot_Backups/FILE /tmp/
# Re-test: tar -tzf

# C) Last resort: Full restore from Google Drive UI
# Download encrypted backup
# Decrypt manually
```

---

## 🌐 Dashboard & API

### ❌ "Dashboard won't load"

**Symptôme:**
```
Page blanc ou infinite loading
```

**Solutions:**

```bash
# 1. Vérifier Dashboard running:
docker compose ps dashboard
# Status: Up

# 2. Voir logs:
docker compose logs dashboard | tail -50

# 3. Si problème mémoire:
docker stats
# Si %MEM > 90%: augmenter SWAP

# 4. Redémarrer:
docker compose restart dashboard

# 5. Full reset:
docker compose down
docker compose up -d

# 6. Browser:
# Vider cache: Ctrl+Shift+Del
# Hard refresh: Ctrl+F5
# Try incognito: Ctrl+Shift+N
```

---

### ❌ "Cannot login to Dashboard"

**Symptôme:**
```
Wrong username/password (même correct?)
```

**Solutions:**

```bash
# 1. Vérifier credentials:
grep DASHBOARD_PASSWORD .env

# 2. Reset password:
./scripts/manage_dashboard_password.sh
# Choisir: 2 (Reset)

# 3. Utilisateur temporaire:
# Temporaire s'affiche une fois
# Sauvegarder!

# 4. Login avec temporaire

# 5. Changer vers nouveau password:
./scripts/manage_dashboard_password.sh
# Choisir: 1 (Change)
```

---

### ❌ "API returns 5xx errors"

**Symptôme:**
```
500 Internal Server Error
502 Bad Gateway
```

**Solutions:**

```bash
# 1. Voir logs API:
docker compose logs api | tail -100

# 2. Vérifier API santé:
curl http://localhost:8000/health

# 3. Redémarrer API:
docker compose restart api

# 4. Check DB:
sqlite3 data/linkedin.db ".tables"

# 5. Logs DB:
docker compose logs database

# 6. Full reset:
docker compose restart
sleep 30
curl http://localhost:8000/health
```

---

## 🆘 Emergency Recovery

### Complète System Reset

**Scenario:** Tout est cassé, besoin recréer zéro

```bash
# 1. Backup data (si possible):
cd linkedin-birthday-auto
cp -r data data.bak
cp -r config config.bak
cp .env .env.bak

# 2. Stop all:
docker compose down

# 3. Clean volumes (⚠️ destructif):
docker system prune -a --volumes

# 4. Re-setup:
git pull
./setup.sh

# 5. Restaurer data (optionnel):
# During setup à Phase 3 password,
# Si vos data OK:
cp config.bak/* config/
cp data.bak/linkedin.db data/

# 6. Restart:
docker compose restart
```

---

### Rollback à Version Précédente

```bash
# 1. Voir versionshistoriques:
git log --oneline | head -10

# 2. Rollback:
git checkout HEAD~1  # Une version avant
# Ou spécifique:
git checkout abc1234  # Commit hash

# 3. Setup:
./setup.sh

# 4. Recommit:
git pull origin main  # Retour version actuelle si stable
```

---

## 📞 Ressources & Support

### Logs Importants

```bash
# Setup logs:
docker compose logs

# Backup logs:
tail -50 logs/backup_gdrive.log

# Password history:
tail -20 logs/password_history.log

# System:
sudo journalctl -xe

# Cron:
sudo journalctl -u cron | tail -50
```

### Commandes Utiles Debug

```bash
# Docker status complet:
docker compose ps
docker stats

# Network:
docker network ls
docker network inspect linkedin-network

# Volumes:
docker volume ls
docker volume inspect PROJECT_data

# Images:
docker images

# Containers:
docker ps -a
```

### Docs Complets

| Problème | Doc |
|----------|-----|
| HTTPS | docs/SETUP_HTTPS_GUIDE.md |
| Backup | docs/SETUP_BACKUP_GUIDE.md |
| Password | docs/PASSWORD_MANAGEMENT_GUIDE.md |
| Password Hashing (v4.0+) | docs/PASSWORD_HASHING_ROBUSTNESS_2025.md |
| Password Hashing Details | docs/SETUP_SCRIPT_PASSWORD_HASHING.md |
| Security | docs/SECURITY.md |
| Architecture | docs/ARCHITECTURE.md |

### Support External

- **GitHub Issues:** https://github.com/GaspardD78/linkedin-birthday-auto/issues
- **Stack Overflow:** Tag `linkedin-birthday-auto`
- **Docker Docs:** https://docs.docker.com
- **Raspberry Pi Forum:** https://www.raspberrypi.org/forums/

---

## ✅ Debugging Checklist

- [ ] Docker running? `docker --version`
- [ ] Services up? `docker compose ps`
- [ ] Logs checked? `docker compose logs`
- [ ] Network OK? `ping 8.8.8.8`
- [ ] Storage OK? `df -h`
- [ ] Memory OK? `free -h`
- [ ] Perms OK? `ls -la data/`
- [ ] Try restart? `docker compose restart`
- [ ] Try full reset? `docker compose down && up`

---

**Si toujours bloqué:** Consultez docs ou ouvrez GitHub Issue avec:
- Symptôme détaillé
- Output logs (dernières 100 lignes)
- Commandes essayées
- Configuration système
