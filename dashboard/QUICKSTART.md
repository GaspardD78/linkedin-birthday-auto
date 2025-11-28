# ⚡ Guide de Démarrage Rapide

Ce guide vous permet de déployer le Dashboard v2 en **moins de 5 minutes**.

______________________________________________________________________

## 🚀 Déploiement le Plus Rapide

### Option 1 : Script Automatique (Recommandé)

```bash
cd dashboard

# Développement local
./deploy.sh dev

# Production avec Docker
./deploy.sh production

# Raspberry Pi
./deploy.sh pi
```

### Option 2 : Docker Compose

```bash
cd dashboard

# 1. Créer le fichier .env
cat > .env << 'EOF'
DATABASE_URL=mysql://user:pass@host:3306/linkedin_bot
REDIS_URL=redis://redis:6379
BOT_API_URL=http://localhost:8000
BOT_API_KEY=votre_clé_secrète
NODE_ENV=production
EOF

# 2. Lancer
docker-compose up -d

# 3. Vérifier
docker-compose logs -f
```

**✅ Le dashboard est disponible sur http://localhost:3000**

______________________________________________________________________

## 🎯 Cheat Sheet - Commandes Essentielles

### Docker

```bash
# Démarrer
docker-compose up -d

# Arrêter
docker-compose down

# Logs
docker-compose logs -f app

# Redémarrer
docker-compose restart

# Rebuild
docker-compose up -d --build

# Monitoring
docker stats linkedin_dashboard
```

### Développement

```bash
# Installer
npm install

# Développement
npm run dev

# Build
npm run build

# Production
npm start
```

______________________________________________________________________

## 🔧 Configuration Minimale

### Fichier `.env` requis

```bash
# Base de données
DATABASE_URL=mysql://user:password@host:3306/database

# Redis
REDIS_URL=redis://localhost:6379

# API Bot
BOT_API_URL=http://localhost:8000
BOT_API_KEY=clé_secrète_ici

# Environnement
NODE_ENV=production
```

### Générer une clé API sécurisée

```bash
openssl rand -base64 32
```

______________________________________________________________________

## ⚠️ Problèmes Courants

### Le dashboard ne démarre pas

```bash
# Vérifier les logs
docker-compose logs app

# Vérifier les variables d'environnement
docker exec linkedin_dashboard env | grep BOT_API_URL

# Rebuild complet
docker-compose down -v && docker-compose up -d --build
```

### Erreur de connexion à la base de données

```bash
# Tester la connexion
nc -zv host_database 3306

# Vérifier l'URL dans .env
cat .env | grep DATABASE_URL
```

### Erreur "Cannot connect to API"

```bash
# Vérifier que l'API bot est accessible
curl http://localhost:8000/health

# Vérifier BOT_API_URL
echo $BOT_API_URL
```

______________________________________________________________________

## 📊 Vérification Rapide

```bash
# Health check
curl http://localhost:3000/api/health

# Stats
curl http://localhost:3000/api/stats

# Logs
curl http://localhost:3000/api/logs
```

______________________________________________________________________

## 🎯 Cas d'Usage Rapides

### 1. Test Local Rapide

```bash
./deploy.sh dev
```

### 2. Déploiement Raspberry Pi

```bash
# Sur le Raspberry Pi
cd dashboard
./deploy.sh pi
```

### 3. Mise à jour

```bash
./deploy.sh update
```

### 4. Production avec SSL (Nginx)

Voir le guide complet : [DEPLOYMENT.md](./DEPLOYMENT.md)

______________________________________________________________________

## 📚 Documentation Complète

Pour plus de détails, consultez :

- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Guide complet de déploiement
- **[README.md](../README.md)** - Documentation du projet

______________________________________________________________________

**🚀 Bon déploiement !**
