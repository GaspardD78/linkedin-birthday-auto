# 🏠 Configuration pour Raspberry Pi 4 + NAS Synology + Freebox Pop

Guide de configuration spécifique pour l'infrastructure **résidentielle** :
- **Raspberry Pi 4** (4 Go RAM)
- **NAS Synology DS213J**
- **Freebox Pop**

Ce guide **remplace** le guide générique et est **optimisé** pour cette configuration matérielle.

---

## 📋 Table des Matières

1. [Vue d'ensemble de l'architecture](#vue-densemble-de-larchitecture)
2. [Configuration réseau Freebox](#configuration-réseau-freebox)
3. [Configuration NAS Synology](#configuration-nas-synology)
4. [Installation sur Raspberry Pi 4](#installation-sur-raspberry-pi-4)
5. [Déploiement du Dashboard Web](#déploiement-du-dashboard-web)
6. [Optimisations spécifiques](#optimisations-spécifiques)
7. [Surveillance et maintenance](#surveillance-et-maintenance)
8. [Troubleshooting](#troubleshooting)

---

## 🏗️ Vue d'ensemble de l'architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      INTERNET                               │
│                         │                                   │
│                    Freebox Pop                             │
│                  (IP Résidentielle)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │   Réseau Local        │
          │   192.168.1.0/24      │
          └───────────┬───────────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
  ┌───▼────┐    ┌────▼─────┐   ┌─────▼──────┐
  │ Pi 4   │    │ Synology │   │ PC/Laptop  │
  │ 4GB    │◄───┤ DS213J   │   │            │
  │        │NFS │ (Backup) │   │            │
  └────────┘    └──────────┘   └────────────┘
     │              │
     │ Exécute:     │ Héberge:
     │ - Bot        │ - Base MySQL
     │ - Dashboard  │ - Backups DB
     │ - Redis      │ - Logs archivés
     │ - Cron jobs  │
```

### Rôles de chaque composant

| Composant | Rôle | Ressources |
|-----------|------|------------|
| **Freebox Pop** | - Connexion Internet<br>- IP résidentielle (légitime pour LinkedIn)<br>- DHCP/DNS local | - |
| **Raspberry Pi 4** | - Exécution du bot 24/7<br>- Dashboard Web (Next.js)<br>- Docker containers<br>- Cron automation | - 4 Go RAM<br>- 32 Go SD card<br>- 3-5W |
| **Synology DS213J** | - Stockage des sauvegardes<br>- Base MySQL (pour dashboard)<br>- Logs archivés | - 512 Mo RAM<br>- Disques RAID |

---

## 🌐 Configuration réseau Freebox

### Étape 1 : Accéder à l'interface Freebox

1. Ouvrir http://mafreebox.freebox.fr
2. Se connecter avec les identifiants Freebox

### Étape 2 : Réserver une IP fixe pour le Pi 4

**Pourquoi ?** Pour pouvoir toujours accéder au Pi via SSH et surveiller le bot.

1. **Paramètres de la Freebox** → **DHCP**
2. **Baux DHCP statiques** → **Ajouter**
3. Renseigner :
   - **Nom :** `raspberry-pi-linkedin`
   - **Adresse MAC :** (récupérée avec `ip link show eth0` sur le Pi)
   - **IP souhaitée :** `192.168.1.50` (ou autre IP disponible)
4. **Sauvegarder**

### Étape 3 : Redirection de port SSH (optionnel)

Si vous voulez accéder au Pi depuis l'extérieur (⚠️ déconseillé pour la sécurité) :

1. **Paramètres de la Freebox** → **Gestion des ports**
2. **Ajouter une redirection**
3. Configurer :
   - **IP de destination :** `192.168.1.50`
   - **Port externe :** `2222`
   - **Port interne :** `22`
   - **Protocole :** TCP
4. **Sauvegarder**

**⚠️ Recommandation :** Utiliser plutôt un VPN (Wireguard) pour accéder au réseau local de façon sécurisée.

### Étape 4 : Vérifier l'IP publique Freebox

```bash
# Sur le Pi, vérifier l'IP publique
curl ifconfig.me
# Exemple: 90.XX.XX.XX (IP résidentielle française)
```

**Important :** Cette IP est **résidentielle**, LinkedIn la considère comme légitime (contrairement aux proxies datacenter).

---

## 💾 Configuration NAS Synology

### Option A : Partage NFS pour sauvegardes (Recommandé)

Cette procédure est adaptée pour **Synology DiskStation Manager (DSM) 7.1+**.

#### Étape 1 : Activer le service NFS (Sur le Synology)

1. Allez dans **Panneau de configuration**
2. Cliquez sur **Services de fichiers** (section "Partage de fichiers")
3. Allez dans l'onglet **NFS**
4. Cochez la case **Activer le service NFS**
5. Dans "Protocole NFS maximum", sélectionnez **NFSv4.1** (ou NFSv3 minimum)
   - **NFSv4.1** est recommandé (plus moderne et performant)
   - NFSv3 fonctionne aussi si nécessaire
6. Cliquez sur **Appliquer**

#### Étape 2 : Créer le Dossier Partagé

1. Toujours dans **Panneau de configuration**, allez dans **Dossier partagé**
2. Cliquez sur **Créer** → **Créer**
3. Remplissez le formulaire :
   - **Nom :** `LinkedInBot`
   - **Volume :** Volume 1 (généralement)
   - **Corbeille :** Décocher "Activer la corbeille" (inutile pour backups automatisés)
4. Cliquez sur **Suivant** jusqu'à la fin et validez

#### Étape 3 : Réglage des Permissions NFS 🔥 CRITIQUE

**C'est l'étape la plus importante pour éviter les erreurs "Permission Denied" !**

1. Dans la liste des **Dossiers partagés**, sélectionnez `LinkedInBot`
2. Cliquez sur **Modifier**
3. Allez dans l'onglet **Autorisations NFS** (spécifique DSM 7)
4. Cliquez sur **Créer**
5. Remplissez le formulaire **avec précision** :
   - **Nom d'hôte ou IP :** `192.168.1.50` (IP fixe de votre Raspberry Pi)
   - **Privilège :** **Lecture/Écriture**
   - **Squash :** **Mappage de tous les utilisateurs sur admin**
     - ⚠️ Important pour éviter les problèmes de droits d'écriture
   - **Sécurité :** `sys`
   - ✅ Cochez : **"Activer le mode asynchrone"** (meilleures performances)
   - ✅ 🔥 **CRITIQUE** : Cochez **"Autoriser les connexions à partir des ports non privilégiés"**
     - Sans cette option → **Échec garanti** avec erreur "Permission Denied"
6. Cliquez sur **Sauvegarder** puis encore **Sauvegarder**

#### Étape 4 : Récupérer le chemin de montage

En bas de la fenêtre d'édition du dossier partagé, notez le chemin :

```
Chemin de montage : /volume1/LinkedInBot
```

**Notez ce chemin exact**, vous en aurez besoin pour le Pi.

#### Étape 5 : Configuration sur le Raspberry Pi 4

```bash
# Installer le client NFS
sudo apt install -y nfs-common

# Créer le point de montage
sudo mkdir -p /mnt/synology

# Monter le partage NFS
# Remplacer 192.168.1.X par l'IP de votre Synology
sudo mount -t nfs 192.168.1.X:/volume1/LinkedInBot /mnt/synology

# Tester l'accès en écriture
ls -la /mnt/synology
touch /mnt/synology/test.txt
rm /mnt/synology/test.txt

# Si le test réussit, rendre le montage permanent
echo "192.168.1.X:/volume1/LinkedInBot /mnt/synology nfs defaults 0 0" | sudo tee -a /etc/fstab

# Vérifier que le montage automatique fonctionne
sudo mount -a
df -h | grep synology
```

**Remplacer `192.168.1.X`** par l'IP de votre Synology.

**En cas d'erreur "Permission Denied" :**
- Vérifiez l'étape 3, option "Autoriser les connexions à partir des ports non privilégiés"
- Vérifiez que l'IP du Pi (192.168.1.50) est bien autorisée dans les permissions NFS
- Vérifiez le Squash : doit être "Mappage de tous les utilisateurs sur admin"

### Option B : Partage SMB/CIFS (Alternative)

```bash
# Installer cifs-utils
sudo apt install -y cifs-utils

# Créer le point de montage
sudo mkdir -p /mnt/synology

# Créer fichier credentials
sudo nano /root/.smbcredentials
```

Contenu :
```
username=votre_user_synology
password=votre_mot_de_passe
```

```bash
# Sécuriser le fichier
sudo chmod 600 /root/.smbcredentials

# Monter le partage
sudo mount -t cifs //192.168.1.X/LinkedInBot /mnt/synology -o credentials=/root/.smbcredentials,uid=pi,gid=pi

# Rendre permanent
echo "//192.168.1.X/LinkedInBot /mnt/synology cifs credentials=/root/.smbcredentials,uid=pi,gid=pi 0 0" | sudo tee -a /etc/fstab
```

### Configurer les sauvegardes automatiques

```bash
# Script de sauvegarde vers NAS
nano ~/linkedin-birthday-auto/backup_to_nas.sh
```

Contenu :
```bash
#!/bin/bash

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/mnt/synology/backups"
SOURCE_DB="linkedin_automation.db"

# Créer le dossier de backup si nécessaire
mkdir -p "$BACKUP_DIR"

# Copier la base de données
if [ -f "$SOURCE_DB" ]; then
    cp "$SOURCE_DB" "$BACKUP_DIR/linkedin_automation_${DATE}.db"
    echo "✅ Backup créé: linkedin_automation_${DATE}.db"
else
    echo "❌ Erreur: base de données introuvable"
    exit 1
fi

# Conserver uniquement les 30 derniers backups
cd "$BACKUP_DIR"
ls -t | tail -n +31 | xargs -r rm --

echo "✅ Backup terminé avec succès"
```

```bash
# Rendre exécutable
chmod +x ~/linkedin-birthday-auto/backup_to_nas.sh

# Ajouter au crontab (backup quotidien à 3h du matin)
crontab -e
```

Ajouter :
```bash
0 3 * * * /home/pi/linkedin-birthday-auto/backup_to_nas.sh >> /home/pi/linkedin-birthday-auto/logs/backup.log 2>&1
```

---

## 🍓 Installation sur Raspberry Pi 4

### Prérequis matériel

✅ **Configuration testée et validée :**
- Raspberry Pi 4 Model B - 4 Go RAM
- Carte microSD 32 Go (Classe 10 / UHS-I)
- Alimentation USB-C 5V/3A officielle
- Câble Ethernet (connexion Freebox)

### Installation OS (voir RASPBERRY_PI4_GUIDE.md)

Suivre le guide [RASPBERRY_PI4_GUIDE.md](RASPBERRY_PI4_GUIDE.md) jusqu'à l'étape 9.

### Configuration système optimisée pour Pi 4

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Docker (méthode officielle)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker pi

# Installer Docker Compose
sudo apt install -y docker-compose

# Redémarrer pour appliquer les changements
sudo reboot
```

### Cloner le projet

```bash
cd ~
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto
```

### Configuration spécifique Pi 4

La configuration dans `config/config.yaml` a été **pré-optimisée** pour Pi 4 avec :
- ✅ User-Agent unique (économie RAM)
- ✅ Viewport unique 1366x768
- ✅ Limites de messages réduites (10/jour, 50/semaine)
- ✅ Délais réduits (90-180s)
- ✅ Proxy désactivé (IP Freebox résidentielle)

**Aucun changement nécessaire** si vous utilisez l'infrastructure Pi 4/Freebox !

### Créer le fichier .env

```bash
nano .env
```

Contenu minimal :
```bash
# Identifiants LinkedIn
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=VotreMotDePasse

# Mode test (mettre false pour production)
DRY_RUN=true

# Headless obligatoire sur Pi 4
HEADLESS_BROWSER=true
```

### Lancer avec Docker Compose

```bash
# Build les images (prend 10-15 min sur Pi 4)
docker-compose -f docker-compose.queue.yml build

# Lancer les services
docker-compose -f docker-compose.queue.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.queue.yml logs -f
```

**Consommation mémoire attendue :**
```
CONTAINER           CPU %    MEM USAGE / LIMIT
linkedin-bot-redis  0.5%     50MiB / 300MiB
linkedin-bot-worker 15%      850MiB / 1.2GiB
TOTAL:                       ~900MiB / 4GiB (22% de RAM utilisée)
```

---

## ⚡ Optimisations spécifiques

### Optimisation 1 : Swap sur SD card

Le Pi 4 avec 4 Go a assez de RAM, mais on peut augmenter le swap en sécurité :

```bash
# Arrêter le swap
sudo dphys-swapfile swapoff

# Éditer la config
sudo nano /etc/dphys-swapfile
```

Modifier :
```
CONF_SWAPSIZE=1024
```

```bash
# Recréer le swap
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Vérifier
free -h
```

### Optimisation 2 : Overclocking modéré (optionnel)

**⚠️ Nécessite un ventilateur !**

```bash
sudo nano /boot/config.txt
```

Ajouter :
```
# Overclocking modéré Pi 4
over_voltage=2
arm_freq=1750
gpu_freq=600
```

```bash

---

## 📊 Déploiement du Dashboard Web

Le projet inclut un **Dashboard Web Next.js** pour surveiller et contrôler le bot via une interface graphique.

### Architecture du Dashboard

```
┌─────────────────────────────────────────────────┐
│                 NAVIGATEUR                      │
│           http://192.168.1.50:3000             │
└────────────────┬────────────────────────────────┘
                 │
      ┌──────────▼──────────┐
      │  Raspberry Pi 4     │
      │                     │
      │  ┌──────────────┐   │
      │  │ Dashboard    │   │ Port 3000
      │  │ (Next.js)    │◄──┼─── Votre navigateur
      │  └──────┬───────┘   │
      │         │           │
      │  ┌──────▼───────┐   │
      │  │ Redis        │   │ Port 6379
      │  │ (Cache)      │   │
      │  └──────────────┘   │
      └─────────┬───────────┘
                │
      ┌─────────▼──────────┐
      │  Synology DS213J   │
      │                    │
      │  MySQL Database    │ Port 3306
      │  (linkedin_bot)    │
      └────────────────────┘
```

### Fonctionnalités du Dashboard

✅ **Monitoring en temps réel**
- Statistiques des messages envoyés
- Anniversaires du jour
- Historique des exécutions
- État du bot (actif/inactif)

✅ **Contrôle à distance**
- Démarrer/arrêter le bot
- Lancer une exécution manuelle
- Voir les logs en direct

✅ **Visualisations**
- Graphiques d'activité
- Calendrier des anniversaires
- Taux de succès/échec

### Prérequis

1. **Base de données MySQL sur Synology** (recommandé)
   - OU SQLite locale (moins performant)
2. **Node.js 20+** installé sur Pi 4
3. **Docker et Docker Compose**

---

## 🗄️ Configuration Base MySQL sur Synology DS213J

### Option A : MariaDB sur Synology (Recommandé)

#### Étape 1 : Installer MariaDB sur Synology

1. **DSM** → **Package Center**
2. Rechercher **"MariaDB 10"**
3. Cliquer **Installer**
4. Attendre l'installation (~2 min)

#### Étape 2 : Configurer MariaDB

```bash
# SSH vers le Synology
ssh admin@192.168.1.X  # Remplacer X par l'IP du NAS

# Se connecter à MySQL en root
sudo mysql -u root -p
# Mot de passe: (celui configuré lors de l'installation)
```

```sql
-- Créer la base de données
CREATE DATABASE linkedin_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Créer l'utilisateur
CREATE USER 'linkedin_user'@'%' IDENTIFIED BY 'VotreMotDePasseSecurise';

-- Donner les permissions
GRANT ALL PRIVILEGES ON linkedin_bot.* TO 'linkedin_user'@'%';
FLUSH PRIVILEGES;

-- Vérifier
SHOW DATABASES;
SELECT User, Host FROM mysql.user WHERE User='linkedin_user';

-- Quitter
EXIT;
```

#### Étape 3 : Ouvrir le port MySQL (3306)

**DSM** → **Panneau de configuration** → **Sécurité** → **Pare-feu**

1. Modifier le profil actif
2. Ajouter une règle :
   - **Ports :** `3306`
   - **Protocole :** TCP
   - **Action :** Autoriser
   - **Source :** IP du Pi 4 (`192.168.1.50`)

#### Étape 4 : Tester depuis le Pi 4

```bash
# Installer client MySQL sur Pi 4
sudo apt install -y mysql-client

# Tester la connexion
mysql -h 192.168.1.X -u linkedin_user -p linkedin_bot
# Entrer le mot de passe

# Si connexion réussie:
SHOW TABLES;
EXIT;
```

### Option B : SQLite locale (Simple mais moins performant)

Si vous ne voulez pas utiliser MySQL sur le Synology :

```bash
# Le dashboard utilisera SQLite automatiquement
# Aucune configuration nécessaire
```

⚠️ **Limitation :** SQLite est moins performant pour les requêtes concurrentes.

---

## 🚀 Installation du Dashboard sur Pi 4

### Méthode 1 : Docker Compose (Recommandé)

#### Étape 1 : Vérifier les prérequis

```bash
# Docker installé ?
docker --version
# Docker version 24.0.0+

# Docker Compose installé ?
docker-compose --version
# Docker Compose version v2.20.0+
```

#### Étape 2 : Configurer les variables d'environnement

```bash
cd ~/linkedin-birthday-auto/dashboard
nano .env
```

**Contenu du fichier `.env` :**

```bash
# ===== BASE DE DONNÉES =====
# Option A: MySQL sur Synology (RECOMMANDÉ)
DATABASE_URL=mysql://linkedin_user:VotreMotDePasseSecurise@192.168.1.X:3306/linkedin_bot

# Option B: SQLite locale (décommenter si pas de MySQL)
# DATABASE_URL=sqlite:///app/data/dashboard.db

# ===== REDIS =====
REDIS_URL=redis://redis:6379

# ===== CONFIGURATION BOT =====
HEADLESS=true
PUPPETEER_ARGS=--no-sandbox,--disable-setuid-sandbox,--disable-dev-shm-usage

# ===== ENVIRONNEMENT =====
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

**Remplacer :**
- `192.168.1.X` → IP de votre Synology
- `VotreMotDePasseSecurise` → Mot de passe MySQL

#### Étape 3 : Modifier docker-compose.yml pour Pi 4

```bash
nano docker-compose.yml
```

**Optimisations pour Pi 4 :**

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    restart: unless-stopped
    container_name: linkedin_dashboard
    ports:
      - "3000:3000"
    deploy:
      resources:
        limits:
          memory: 1G      # Réduit pour Pi 4 (était 1.5G)
          cpus: '1.5'     # Réduit pour Pi 4
        reservations:
          memory: 600M
          cpus: '0.5'
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
      - HEADLESS=true
      - PUPPETEER_ARGS=--no-sandbox,--disable-setuid-sandbox,--disable-dev-shm-usage
    volumes:
      - ./logs:/app/logs
      - dashboard-data:/app/data
    depends_on:
      redis:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    container_name: linkedin_dashboard_redis
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
    restart: unless-stopped
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          memory: 150M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  redis_data:
  dashboard-data:
```

#### Étape 4 : Build de l'image (prend 15-20 min sur Pi 4)

```bash
cd ~/linkedin-birthday-auto/dashboard

# Build l'image Docker
docker-compose build

# Vérifier que l'image est créée
docker images | grep linkedin
```

**Sortie attendue :**
```
dashboard-app    latest    abc123def456    2 minutes ago    450MB
```

#### Étape 5 : Initialiser la base de données

```bash
# Lancer temporairement pour créer les tables
docker-compose up -d

# Attendre 30 secondes que Next.js initialise
sleep 30

# Vérifier les logs
docker-compose logs app | tail -20
```

**Rechercher dans les logs :**
```
✓ Ready in 5.2s
✓ Local: http://localhost:3000
```

#### Étape 6 : Tester le dashboard

```bash
# Depuis le Pi 4
curl http://localhost:3000

# Depuis votre PC (sur le même réseau)
# Ouvrir navigateur: http://192.168.1.50:3000
```

**Page d'accueil attendue :**
- Dashboard LinkedIn Bot
- Statistiques (0 messages pour l'instant)
- Formulaire de connexion (si activé)

#### Étape 7 : Vérifier les containers

```bash
docker-compose ps
```

**Sortie attendue :**
```
NAME                      STATUS    PORTS
linkedin_dashboard        Up        0.0.0.0:3000->3000/tcp
linkedin_dashboard_redis  Up        6379/tcp
```

---

### Méthode 2 : Installation Native (Sans Docker)

**⚠️ Moins recommandé sur Pi 4** (consommation mémoire plus élevée)

#### Étape 1 : Installer Node.js 20

```bash
# Ajouter le repository NodeSource
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# Installer Node.js
sudo apt install -y nodejs

# Vérifier
node --version  # v20.x.x
npm --version   # 10.x.x
```

#### Étape 2 : Installer les dépendances

```bash
cd ~/linkedin-birthday-auto/dashboard

# Installer les packages (prend 10-15 min sur Pi 4)
npm ci --production
```

#### Étape 3 : Créer le fichier .env

```bash
nano .env.local
```

**Contenu :**
```bash
DATABASE_URL=mysql://linkedin_user:password@192.168.1.X:3306/linkedin_bot
REDIS_URL=redis://localhost:6379
NODE_ENV=production
```

#### Étape 4 : Build du projet

```bash
# Build Next.js (prend 5-10 min sur Pi 4)
npm run build
```

#### Étape 5 : Installer Redis localement

```bash
sudo apt install -y redis-server

# Configurer Redis
sudo nano /etc/redis/redis.conf
```

**Modifier :**
```
maxmemory 128mb
maxmemory-policy allkeys-lru
```

```bash
# Redémarrer Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

#### Étape 6 : Lancer le dashboard

```bash
cd ~/linkedin-birthday-auto/dashboard

# Démarrer en production
npm start
```

**Sortie attendue :**
```
> linkedin-bot-dashboard@0.1.0 start
> next start

  ▲ Next.js 14.0.0
  - Local:        http://localhost:3000
  - Network:      http://192.168.1.50:3000

✓ Ready in 2.5s
```

#### Étape 7 : Créer un service systemd

```bash
sudo nano /etc/systemd/system/linkedin-dashboard.service
```

**Contenu :**
```ini
[Unit]
Description=LinkedIn Bot Dashboard
After=network.target redis-server.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/linkedin-birthday-auto/dashboard
Environment=NODE_ENV=production
ExecStart=/usr/bin/npm start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Activer le service
sudo systemctl daemon-reload
sudo systemctl enable linkedin-dashboard
sudo systemctl start linkedin-dashboard

# Vérifier le statut
sudo systemctl status linkedin-dashboard
```

---

## 🌐 Accès au Dashboard

### Depuis le Réseau Local

**URL :** `http://192.168.1.50:3000`

**Navigation :**
- **/** : Page d'accueil avec stats
- **/birthdays** : Liste des anniversaires
- **/history** : Historique des exécutions
- **/settings** : Configuration du bot
- **/logs** : Logs en temps réel

### Sécuriser l'Accès

#### Option A : Reverse Proxy Nginx (Recommandé)

```bash
# Installer Nginx
sudo apt install -y nginx

# Créer la configuration
sudo nano /etc/nginx/sites-available/linkedin-dashboard
```

**Contenu :**
```nginx
server {
    listen 80;
    server_name linkedin-bot.local;  # Ou votre domaine

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/linkedin-dashboard /etc/nginx/sites-enabled/

# Tester la config
sudo nginx -t

# Redémarrer Nginx
sudo systemctl restart nginx
```

**Accès :** `http://linkedin-bot.local` (après config DNS/hosts)

#### Option B : Authentification Basic Auth

```bash
# Créer fichier de mots de passe
sudo apt install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd admin

# Modifier la config Nginx
sudo nano /etc/nginx/sites-available/linkedin-dashboard
```

**Ajouter dans `location /` :**
```nginx
auth_basic "Dashboard LinkedIn Bot";
auth_basic_user_file /etc/nginx/.htpasswd;
```

```bash
sudo systemctl restart nginx
```

**Accès :** Demande login/mot de passe

---

## 📊 Métriques Dashboard sur Pi 4

Consommation attendue avec Dashboard actif :

| Service | RAM | CPU | Disque |
|---------|-----|-----|--------|
| **Dashboard Next.js** | 600-800 Mo | 10-15% | 450 Mo |
| **Redis (dashboard)** | 50-100 Mo | <1% | 10 Mo |
| **Bot Worker** | 900 Mo | 15-25% | 300 Mo |
| **Redis (bot)** | 200 Mo | <1% | 50 Mo |
| **Système** | 500 Mo | 5% | - |
| **TOTAL** | **~2.5 Go / 4 Go** | **30-40%** | **~800 Mo** |

**Marge restante :** ~1.5 Go RAM libre ✅

---

## 🔄 Mise à Jour du Dashboard

### Docker Compose

```bash
cd ~/linkedin-birthday-auto/dashboard

# Arrêter les services
docker-compose down

# Pull les dernières modifications
git pull origin main

# Rebuild
docker-compose build --no-cache

# Redémarrer
docker-compose up -d
```

### Installation Native

```bash
cd ~/linkedin-birthday-auto/dashboard

# Arrêter le service
sudo systemctl stop linkedin-dashboard

# Pull les modifications
git pull origin main

# Réinstaller les dépendances
npm ci --production

# Rebuild
npm run build

# Redémarrer
sudo systemctl start linkedin-dashboard
```

---

## 🐛 Troubleshooting Dashboard

### Problème : "Cannot connect to database"

```bash
# Vérifier la connexion MySQL depuis Pi 4
mysql -h 192.168.1.X -u linkedin_user -p linkedin_bot

# Si échec:
# 1. Vérifier le pare-feu Synology (port 3306 ouvert?)
# 2. Vérifier les credentials dans .env
# 3. Vérifier que MariaDB est démarré sur Synology
```

### Problème : "Redis connection refused"

```bash
# Docker Compose:
docker-compose logs redis

# Native:
sudo systemctl status redis-server

# Tester Redis
redis-cli ping
# Doit répondre: PONG
```

### Problème : "Port 3000 already in use"

```bash
# Trouver le process
sudo lsof -i :3000

# Tuer le process
sudo kill -9 <PID>

# Ou changer le port dans docker-compose.yml
ports:
  - "3001:3000"  # Utiliser 3001 au lieu de 3000
```

### Problème : Dashboard très lent sur Pi 4

**Solution 1 : Réduire la limite mémoire**
```yaml
# docker-compose.yml
limits:
  memory: 800M  # Au lieu de 1G
```

**Solution 2 : Désactiver le dashboard et utiliser uniquement le bot**
```bash
docker-compose down
# Utiliser uniquement docker-compose.queue.yml pour le bot
```

### Problème : "Build failed" sur Pi 4

```bash
# Augmenter la swap temporairement
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=2048

sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Relancer le build
docker-compose build
```

---

sudo reboot
```

### Optimisation 3 : Désactiver services inutiles

```bash
# Désactiver Bluetooth (si non utilisé)
sudo systemctl disable bluetooth
sudo systemctl stop bluetooth

# Désactiver WiFi (si Ethernet branché)
sudo rfkill block wifi

# Désactiver GUI (si Pi en headless)
sudo systemctl set-default multi-user.target
```

### Optimisation 4 : Logs rotatifs

```bash
sudo nano /etc/logrotate.d/linkedin-bot
```

Contenu :
```
/home/pi/linkedin-birthday-auto/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 pi pi
}
```

### Optimisation 5 : Température CPU

Surveiller la température :

```bash
# Script de monitoring
nano ~/check_temp.sh
```

Contenu :
```bash
#!/bin/bash
TEMP=$(vcgencmd measure_temp | egrep -o '[0-9]*\.[0-9]*')
echo "$(date): Temp CPU = ${TEMP}°C"

if (( $(echo "$TEMP > 75" | bc -l) )); then
    echo "⚠️ ALERTE: Température élevée!"
    # Optionnel: envoyer une notification
fi
```

```bash
chmod +x ~/check_temp.sh

# Ajouter au cron (toutes les heures)
crontab -e
```

Ajouter :
```bash
0 * * * * /home/pi/check_temp.sh >> /home/pi/temp.log
```

---

## 📊 Surveillance et maintenance

### Monitoring Docker

```bash
# Voir les stats en temps réel
docker stats

# Voir les logs
docker-compose -f docker-compose.queue.yml logs -f rq-worker

# Redémarrer un service
docker-compose -f docker-compose.queue.yml restart rq-worker
```

### Vérifier l'espace disque

```bash
# Espace total
df -h

# Nettoyer Docker
docker system prune -a --volumes

# Nettoyer apt
sudo apt clean
sudo apt autoremove -y
```

### Vérifier la mémoire

```bash
# Mémoire utilisée
free -h

# Top processes
htop
```

### Backup automatique vers Synology

Vérifier que les backups fonctionnent :

```bash
# Lister les backups sur NAS
ls -lh /mnt/synology/backups/

# Vérifier le dernier backup
ls -lt /mnt/synology/backups/ | head -5
```

---

## 🐛 Troubleshooting

### Problème : "Cannot connect to Docker daemon"

```bash
# Vérifier que Docker est lancé
sudo systemctl status docker

# Si arrêté, le démarrer
sudo systemctl start docker

# Vérifier les permissions
groups
# Doit contenir "docker"

# Si pas dans le groupe:
sudo usermod -aG docker pi
# Puis se déconnecter/reconnecter
```

### Problème : "Out of memory" sur Pi 4

```bash
# Vérifier la mémoire
free -h

# Arrêter les containers
docker-compose -f docker-compose.queue.yml down

# Vérifier les limites Docker
docker stats

# Réduire les limites dans docker-compose.queue.yml:
# memory: 1.2G → memory: 1.0G
```

### Problème : NAS Synology non accessible

```bash
# Ping le NAS
ping 192.168.1.X

# Vérifier le montage NFS
mount | grep synology

# Tester manuellement
sudo mount -t nfs 192.168.1.X:/volume1/LinkedInBot /mnt/synology

# Vérifier les permissions NFS sur Synology
# (voir section Configuration NAS)
```

### Problème : Bot ne se lance pas

```bash
# Vérifier les logs
docker-compose -f docker-compose.queue.yml logs rq-worker

# Erreurs communes:
# 1. Auth state manquant → Générer auth_state.json
# 2. Config invalide → Vérifier config/config.yaml
# 3. RAM insuffisante → Réduire max_messages_per_run

# Lancer en mode debug
docker-compose -f docker-compose.queue.yml run --rm rq-worker python main.py --dry-run
```

### Problème : Température CPU > 80°C

```bash
# Vérifier la température
vcgencmd measure_temp

# Solutions:
# 1. Ajouter un ventilateur
# 2. Améliorer la ventilation
# 3. Réduire l'overclocking (si activé)
# 4. Limiter la charge (réduire les limites Docker)
```

### Problème : SD card pleine

```bash
# Vérifier l'espace
df -h

# Trouver les gros fichiers
du -sh /* 2>/dev/null | sort -h

# Nettoyer Docker
docker system prune -a --volumes

# Nettoyer les logs
sudo journalctl --vacuum-time=3d

# Nettoyer apt
sudo apt clean && sudo apt autoremove -y
```

---

## 📈 Métriques de performance attendues

Sur Raspberry Pi 4 (4 Go) avec cette configuration :

| Métrique | Valeur Attendue |
|----------|----------------|
| **RAM utilisée (idle)** | ~200 Mo |
| **RAM utilisée (bot actif)** | ~900 Mo - 1.2 Go |
| **CPU utilisation (bot actif)** | 15-25% |
| **Température CPU** | 45-65°C (avec ventilateur) |
| **Temps de traitement** | ~30s par message |
| **Consommation électrique** | 3-5W (~1€/mois) |
| **Temps de build Docker** | 10-15 minutes |
| **Temps de démarrage bot** | 30-45 secondes |

---

## ✅ Checklist de production

Avant de passer en production (`DRY_RUN=false`) :

- [ ] Pi 4 configuré avec IP fixe sur Freebox
- [ ] NAS Synology accessible via NFS/SMB
- [ ] Docker et Docker Compose installés
- [ ] `config/config.yaml` vérifié (limites conservatrices)
- [ ] `.env` créé avec identifiants LinkedIn
- [ ] `auth_state.json` généré (voir RASPBERRY_PI4_GUIDE.md)
- [ ] Backups automatiques vers NAS configurés
- [ ] Monitoring température CPU actif
- [ ] Tests en mode `DRY_RUN=true` réussis
- [ ] Logs consultables et rotation configurée
- [ ] Docker limité à 1.2 Go RAM
- [ ] Cron job configuré pour exécution quotidienne

---

## 🎯 Configuration finale recommandée

**Crontab (exécution quotidienne à 9h) :**
```bash
crontab -e
```

```bash
# LinkedIn Bot - Exécution quotidienne
0 9 * * * cd /home/pi/linkedin-birthday-auto && docker-compose -f docker-compose.queue.yml up >> /home/pi/linkedin-birthday-auto/logs/cron.log 2>&1

# Backup vers NAS - 3h du matin
0 3 * * * /home/pi/linkedin-birthday-auto/backup_to_nas.sh >> /home/pi/linkedin-birthday-auto/logs/backup.log 2>&1

# Health check - toutes les heures
0 * * * * /home/pi/check_temp.sh >> /home/pi/temp.log
```

---

## 📞 Support

**Infrastructure spécifique :**
- Pi 4 : https://www.raspberrypi.com/documentation/
- Synology : https://www.synology.com/fr-fr/support
- Freebox : https://www.free.fr/assistance/

**Bot LinkedIn :**
- GitHub : https://github.com/GaspardD78/linkedin-birthday-auto
- Issues : https://github.com/GaspardD78/linkedin-birthday-auto/issues

---

**✅ Configuration validée pour :**
- Raspberry Pi 4 Model B (4 Go RAM)
- Synology DS213J
- Freebox Pop
- Debian 11 (Bullseye) / Raspberry Pi OS

**Date de dernière mise à jour :** 22 novembre 2025
