# 🚀 Guide de Déploiement - Dashboard LinkedIn Bot v2

Ce guide vous explique comment déployer le Dashboard v2 sur différentes plateformes.

---

## 📋 Table des Matières

1. [Déploiement Docker (Recommandé)](#1-déploiement-docker-recommandé)
2. [Déploiement sur Raspberry Pi 4](#2-déploiement-sur-raspberry-pi-4)
3. [Déploiement sur Vercel](#3-déploiement-sur-vercel)
4. [Déploiement Manuel](#4-déploiement-manuel)
5. [Configuration des Variables d'Environnement](#5-configuration-des-variables-denvironnement)
6. [Vérification et Monitoring](#6-vérification-et-monitoring)

---

## 1. Déploiement Docker (Recommandé)

### Prérequis
- Docker >= 20.10
- Docker Compose >= 2.0
- 2GB RAM minimum (4GB recommandé)

### Étapes de déploiement

#### 1.1 Configuration de l'environnement

Créez un fichier `.env` dans le dossier `dashboard/` :

```bash
# dashboard/.env

# Base de données (choisir une option)
# Option 1: MySQL (Synology)
DATABASE_URL=mysql://linkedin_user:password@192.168.1.X:3306/linkedin_bot

# Option 2: SQLite local (pour test)
# DATABASE_URL=sqlite:///app/data/dashboard.db

# Redis
REDIS_URL=redis://redis:6379

# API Bot (Backend Python)
BOT_API_URL=http://localhost:8000
BOT_API_KEY=votre_clé_secrète_ici

# Puppeteer (si utilisé)
HEADLESS=true
PUPPETEER_ARGS=--no-sandbox,--disable-setuid-sandbox
```

#### 1.2 Build et lancement

```bash
cd dashboard

# Build l'image Docker
docker-compose build

# Lancer les services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f app
```

#### 1.3 Accès au dashboard

Le dashboard sera accessible sur : **http://localhost:3000**

#### 1.4 Commandes utiles

```bash
# Arrêter les services
docker-compose down

# Redémarrer
docker-compose restart

# Voir les logs en temps réel
docker-compose logs -f

# Rebuild après modifications
docker-compose up -d --build

# Nettoyer tout (⚠️ supprime les données)
docker-compose down -v
```

---

## 2. Déploiement sur Raspberry Pi 4

### Prérequis
- Raspberry Pi 4 avec 4GB RAM
- Raspberry Pi OS (64-bit recommandé)
- Docker installé

### Installation Docker sur Raspberry Pi

```bash
# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Installer Docker Compose
sudo apt-get install docker-compose

# Redémarrer
sudo reboot
```

### Déploiement optimisé pour Pi 4

Utilisez le Dockerfile spécifique : `Dockerfile.prod.pi4`

```bash
cd dashboard

# Build avec le Dockerfile optimisé Pi
docker build -f Dockerfile.prod.pi4 -t linkedin-dashboard:pi4 .

# Lancer avec docker-compose (déjà optimisé pour Pi)
docker-compose up -d
```

### Optimisations spécifiques Pi 4

Le `docker-compose.yml` est déjà configuré avec :
- Limite mémoire : 1GB max (600-800MB utilisés)
- Limite CPU : 1.5 cores max
- Redis configuré pour cache uniquement (128MB)
- Pas de persistance Redis (économie de RAM)

### Monitoring sur Pi

```bash
# Surveiller les ressources
docker stats

# Surveiller les logs
docker logs -f linkedin_dashboard

# Vérifier la santé du conteneur
docker inspect linkedin_dashboard | grep -A 5 "Health"
```

---

## 3. Déploiement sur Vercel

Vercel est la plateforme native pour Next.js - déploiement ultra-simple !

### Étapes

#### 3.1 Préparer le repository

```bash
# Assurez-vous que tout est committé
git add .
git commit -m "feat: ready for Vercel deployment"
git push
```

#### 3.2 Déployer sur Vercel

**Option A : Via l'interface web**

1. Allez sur [vercel.com](https://vercel.com)
2. Connectez votre compte GitHub
3. Cliquez sur "New Project"
4. Sélectionnez votre repository `linkedin-birthday-auto`
5. **Important** : Configurez le `Root Directory` → `dashboard`
6. Configurez les variables d'environnement (voir section 5)
7. Cliquez sur "Deploy"

**Option B : Via CLI**

```bash
# Installer Vercel CLI
npm i -g vercel

# Se connecter
vercel login

# Déployer depuis le dossier dashboard
cd dashboard
vercel

# Pour la production
vercel --prod
```

#### 3.3 Configuration Vercel

Créez un fichier `vercel.json` dans `dashboard/` :

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["cdg1"],
  "env": {
    "BOT_API_URL": "@bot-api-url",
    "BOT_API_KEY": "@bot-api-key"
  }
}
```

### ⚠️ Limitations Vercel

- **Serverless** : Pas de processus persistant (pas de WebSockets)
- **Timeout** : 10s pour le plan gratuit
- **Base de données** : Nécessite une DB externe (MySQL/PostgreSQL)
- **Redis** : Nécessite un Redis cloud (Upstash recommandé)

---

## 4. Déploiement Manuel

Pour un déploiement sur VPS/serveur dédié.

### Prérequis
- Node.js 20+
- PM2 (pour le process management)
- Nginx (pour le reverse proxy)

### Étapes

#### 4.1 Installation

```bash
# Cloner le repo
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto/dashboard

# Installer les dépendances
npm ci --production

# Build de production
npm run build
```

#### 4.2 Lancer avec PM2

```bash
# Installer PM2
npm install -g pm2

# Créer le fichier ecosystem
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'linkedin-dashboard',
    script: 'npm',
    args: 'start',
    cwd: '/chemin/vers/dashboard',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PORT: 3000,
      BOT_API_URL: 'http://localhost:8000',
      REDIS_URL: 'redis://localhost:6379'
    }
  }]
}
EOF

# Lancer avec PM2
pm2 start ecosystem.config.js

# Sauvegarder la config PM2
pm2 save

# Auto-démarrage au boot
pm2 startup
```

#### 4.3 Configuration Nginx

```nginx
# /etc/nginx/sites-available/linkedin-dashboard

server {
    listen 80;
    server_name dashboard.votredomaine.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/linkedin-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 4.4 SSL avec Let's Encrypt

```bash
# Installer Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtenir le certificat SSL
sudo certbot --nginx -d dashboard.votredomaine.com

# Renouvellement automatique (déjà configuré par défaut)
sudo certbot renew --dry-run
```

---

## 5. Configuration des Variables d'Environnement

### Variables requises

| Variable | Description | Exemple | Requis |
|----------|-------------|---------|--------|
| `DATABASE_URL` | URL de connexion à la base de données | `mysql://user:pass@host:3306/db` | ✅ |
| `REDIS_URL` | URL de connexion Redis | `redis://localhost:6379` | ✅ |
| `BOT_API_URL` | URL de l'API Python du bot | `http://localhost:8000` | ✅ |
| `BOT_API_KEY` | Clé d'authentification API | `secret_key_here` | ✅ |
| `NODE_ENV` | Environnement | `production` | ✅ |
| `PORT` | Port d'écoute | `3000` | ❌ |
| `NEXT_TELEMETRY_DISABLED` | Désactiver la télémétrie Next.js | `1` | ❌ |

### Variables optionnelles (Puppeteer)

| Variable | Description | Valeur |
|----------|-------------|--------|
| `HEADLESS` | Mode headless Puppeteer | `true` |
| `PUPPETEER_ARGS` | Arguments Puppeteer | `--no-sandbox,--disable-setuid-sandbox` |
| `PUPPETEER_EXECUTABLE_PATH` | Chemin Chrome | `/usr/bin/google-chrome-stable` |

### Fichier .env exemple

```bash
# .env.production

# Database
DATABASE_URL=mysql://linkedin_user:SecurePassword123@192.168.1.100:3306/linkedin_bot

# Redis
REDIS_URL=redis://localhost:6379

# Bot API
BOT_API_URL=http://192.168.1.100:8000
BOT_API_KEY=super_secret_key_change_this

# Next.js
NODE_ENV=production
PORT=3000
NEXT_TELEMETRY_DISABLED=1

# Puppeteer (si utilisé)
HEADLESS=true
PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
```

---

## 6. Vérification et Monitoring

### Health Checks

Le dashboard expose des endpoints de santé :

```bash
# Vérifier la santé globale
curl http://localhost:3000/api/health

# Vérifier la connexion à l'API
curl http://localhost:3000/api/stats

# Vérifier les logs
curl http://localhost:3000/api/logs
```

### Monitoring avec Docker

```bash
# Ressources en temps réel
docker stats linkedin_dashboard

# Logs
docker logs -f linkedin_dashboard

# État du conteneur
docker inspect linkedin_dashboard --format='{{.State.Health.Status}}'
```

### Monitoring avec PM2

```bash
# Dashboard PM2
pm2 monit

# Logs en temps réel
pm2 logs linkedin-dashboard

# Statistiques
pm2 show linkedin-dashboard
```

### Logs du Dashboard

Les logs sont disponibles :
- **Docker** : `docker logs linkedin_dashboard`
- **PM2** : `~/.pm2/logs/`
- **Manuel** : `stdout` du processus Node.js

---

## 🔧 Troubleshooting

### Problème : Le dashboard ne démarre pas

```bash
# Vérifier les logs
docker-compose logs app

# Vérifier les variables d'environnement
docker exec linkedin_dashboard env | grep BOT_API_URL

# Rebuild complet
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Problème : Connexion à la base de données échoue

```bash
# Tester la connexion MySQL
docker exec -it linkedin_dashboard sh
nc -zv 192.168.1.X 3306

# Vérifier DATABASE_URL
echo $DATABASE_URL
```

### Problème : Erreur "Cannot connect to API"

```bash
# Vérifier que l'API bot est accessible
curl http://localhost:8000/health

# Vérifier BOT_API_URL
docker exec linkedin_dashboard env | grep BOT_API_URL
```

### Problème : Manque de mémoire (Raspberry Pi)

```bash
# Réduire les limites dans docker-compose.yml
deploy:
  resources:
    limits:
      memory: 800M  # Réduire de 1G à 800M
```

---

## 🎯 Recommandations par Environnement

### Développement Local
```bash
cd dashboard
npm install
npm run dev
# Accès: http://localhost:3000
```

### Staging / Test
- **Docker** : Déploiement sur VPS avec docker-compose
- **Variables** : Fichier `.env.staging`

### Production - Petit projet
- **Vercel** : Déploiement le plus simple
- **Coût** : Gratuit (avec limitations)

### Production - Raspberry Pi / Serveur Local
- **Docker** : Avec `docker-compose.yml` optimisé
- **Backup** : Script de backup MySQL

### Production - Haute disponibilité
- **VPS** : Déploiement manuel avec Nginx + PM2
- **Load Balancing** : Nginx upstream
- **Monitoring** : Prometheus + Grafana

---

## 📊 Performance

### Ressources typiques

| Plateforme | RAM | CPU | Disque |
|------------|-----|-----|--------|
| Docker (production) | 600-800MB | 0.5-1 CPU | 500MB |
| Raspberry Pi 4 | 800MB-1GB | 1-1.5 CPU | 500MB |
| Vercel | Serverless | Auto | N/A |
| VPS (PM2) | 400-600MB | 0.3-0.8 CPU | 500MB |

---

## 🔒 Sécurité

### Checklist de sécurité

- [ ] Variables d'environnement sécurisées (pas de commit `.env`)
- [ ] Base de données avec mot de passe fort
- [ ] API key pour BOT_API_KEY
- [ ] HTTPS configuré (Let's Encrypt)
- [ ] Firewall configuré (ufw/iptables)
- [ ] Conteneurs Docker non-root (déjà configuré)
- [ ] Mise à jour régulière des dépendances
- [ ] Logs rotatifs pour éviter le remplissage disque

### Générer une clé API sécurisée

```bash
# Linux/Mac
openssl rand -base64 32

# Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

---

## 📝 Mises à jour

### Mettre à jour le dashboard

```bash
# Récupérer les dernières modifications
git pull origin main

# Rebuild et redémarrer
cd dashboard
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 🆘 Support

- **Issues GitHub** : [https://github.com/GaspardD78/linkedin-birthday-auto/issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)
- **Documentation** : `README.md` du projet
- **Logs** : `docker-compose logs -f`

---

**Bon déploiement ! 🚀**
