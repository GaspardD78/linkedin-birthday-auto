# 🚀 Guide de déploiement - LinkedIn Birthday Auto Bot v2.0

Ce guide couvre tous les scénarios de déploiement du bot LinkedIn, de la machine locale aux
environnements cloud.

## 📋 Table des matières

- [Prérequis](#pr%C3%A9requis)
- [Déploiement local](#d%C3%A9ploiement-local)
- [Déploiement GitHub Actions](#d%C3%A9ploiement-github-actions)
- [Déploiement Docker](#d%C3%A9ploiement-docker)
- [Déploiement cloud](#d%C3%A9ploiement-cloud)
- [Monitoring et logs](#monitoring-et-logs)
- [Dépannage](#d%C3%A9pannage)

______________________________________________________________________

## 🎯 Prérequis

### Configuration minimale

- **Python**: 3.9 ou supérieur
- **RAM**: 512 MB minimum (2 GB recommandé)
- **Disque**: 500 MB minimum
- **OS**: Linux, macOS, Windows (WSL recommandé)

### Dépendances système

```bash
# Linux (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y \
    python3.9 \
    python3-pip \
    python3-venv \
    chromium-browser \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2

# macOS
brew install python@3.9
brew install --cask chromium

# Windows (WSL2 recommandé)
# Installer WSL2 et Ubuntu, puis suivre les instructions Linux
```

### Compte LinkedIn

- **Obligatoire**: Compte LinkedIn actif
- **Recommandé**: Compte avec 2FA activé (plus sécurisé)
- **Permissions**: Accès au réseau et messages

______________________________________________________________________

## 💻 Déploiement local

### 1. Installation

```bash
# Cloner le repository
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# Créer un environnement virtuel
python3.9 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Installer Playwright et les navigateurs
playwright install chromium
playwright install-deps chromium
```

### 2. Configuration

```bash
# Copier le fichier de config
cp config/config.yaml config/my_config.yaml

# Éditer la configuration
nano config/my_config.yaml
```

**Configuration minimale** (`config/my_config.yaml`):

```yaml
version: "2.0.0"
dry_run: false  # true pour tester sans envoyer
bot_mode: "standard"  # ou "unlimited"

browser:
  headless: true

messaging_limits:
  weekly_message_limit: 80

birthday_filter:
  process_today: true
  process_late: false

database:
  enabled: true
  db_path: "data/linkedin_bot.db"
```

### 3. Authentification

**Option A: Fichier JSON (recommandé)**

1. Connectez-vous manuellement à LinkedIn dans votre navigateur
1. Exportez les cookies (extension "EditThisCookie" ou "Cookie-Editor")
1. Sauvegardez dans `auth_state.json`:

```json
{
  "cookies": [
    {
      "name": "li_at",
      "value": "VOTRE_TOKEN_ICI",
      "domain": ".linkedin.com",
      "path": "/",
      "expires": 1234567890,
      "httpOnly": true,
      "secure": true,
      "sameSite": "None"
    }
  ],
  "origins": []
}
```

**Option B: Variable d'environnement**

```bash
# Base64 encoder le fichier auth_state.json
export LINKEDIN_AUTH_STATE=$(cat auth_state.json | base64)
```

**Option C: Fichier .env**

```bash
# Créer .env
cat > .env << 'EOF'
LINKEDIN_AUTH_STATE=eyJjb29raWVzIjpbeyJuYW1lIjoib...
EOF
```

### 4. Test de validation

```bash
# Valider la configuration et l'authentification
python main.py validate

# Tester en mode dry-run
python main.py bot --dry-run

# Vérifier les logs
tail -f logs/linkedin_bot.log
```

### 5. Exécution

```bash
# Mode standard (anniversaires du jour uniquement)
python main.py bot

# Mode unlimited (aujourd'hui + retard)
python main.py bot --mode unlimited --max-days-late 10

# Mode debug
python main.py bot --debug

# Avec config custom
python main.py bot --config ./config/my_config.yaml
```

______________________________________________________________________

## ⚙️ Déploiement GitHub Actions

### Avantages

- ✅ Exécution automatique quotidienne
- ✅ Pas de machine à maintenir
- ✅ Logs centralisés
- ✅ Gratuit (2000 min/mois)

### 1. Configuration du repository

```bash
# Forker ou cloner le repo sur votre compte GitHub
gh repo clone GaspardD78/linkedin-birthday-auto
cd linkedin-birthday-auto
gh repo create --public
git push origin main
```

### 2. Secrets GitHub

Aller dans `Settings > Secrets and variables > Actions` et ajouter:

| Secret Name                | Description                           | Exemple             |
| -------------------------- | ------------------------------------- | ------------------- |
| `LINKEDIN_AUTH_STATE`      | Auth LinkedIn en base64               | `eyJjb29raWVzIj...` |
| `LINKEDIN_BOT_DRY_RUN`     | Mode dry-run (optionnel)              | `false`             |
| `LINKEDIN_BOT_CONFIG_YAML` | Config complète en base64 (optionnel) | `dmVyc2lvbjog...`   |

**Générer les secrets**:

```bash
# Auth state
cat auth_state.json | base64 | pbcopy  # macOS
cat auth_state.json | base64 | xclip   # Linux

# Config (optionnel)
cat config/config.yaml | base64 | pbcopy
```

### 3. Workflow GitHub Actions

Créer `.github/workflows/daily-bot.yml`:

```yaml
name: Daily LinkedIn Birthday Bot

on:
  schedule:
    # Exécuter tous les jours à 9h Paris (7h UTC en hiver, 8h en été)
    - cron: '0 7 * * *'
  workflow_dispatch:  # Permet déclenchement manuel

jobs:
  run-bot:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
          playwright install-deps chromium

      - name: Run bot
        env:
          LINKEDIN_AUTH_STATE: ${{ secrets.LINKEDIN_AUTH_STATE }}
          LINKEDIN_BOT_DRY_RUN: ${{ secrets.LINKEDIN_BOT_DRY_RUN }}
        run: |
          python main.py bot

      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: bot-logs
          path: logs/
```

### 4. Vérification

```bash
# Déclencher manuellement
gh workflow run "Daily LinkedIn Birthday Bot"

# Voir les exécutions
gh run list

# Voir les logs
gh run view --log
```

______________________________________________________________________

## 🐳 Déploiement Docker

### 1. Dockerfile

Créer `Dockerfile`:

```dockerfile
FROM python:3.9-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy application
COPY . .

# Create directories
RUN mkdir -p /app/logs /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Run bot
CMD ["python", "main.py", "bot"]
```

### 2. Docker Compose

Créer `docker-compose.yml`:

```yaml
version: '3.8'

services:
  linkedin-bot:
    build: .
    container_name: linkedin-birthday-bot
    environment:
      - LINKEDIN_AUTH_STATE=${LINKEDIN_AUTH_STATE}
      - LINKEDIN_BOT_DRY_RUN=${LINKEDIN_BOT_DRY_RUN:-false}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped

  # API (optionnel)
  linkedin-api:
    build: .
    container_name: linkedin-bot-api
    command: python main.py api --host 0.0.0.0 --port 8000
    environment:
      - LINKEDIN_AUTH_STATE=${LINKEDIN_AUTH_STATE}
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped
```

### 3. Déploiement

```bash
# Build
docker-compose build

# Lancer en mode interactif (test)
docker-compose run --rm linkedin-bot python main.py bot --dry-run

# Lancer en production
docker-compose up -d

# Voir les logs
docker-compose logs -f linkedin-bot

# Arrêter
docker-compose down
```

### 4. Cron dans Docker

Pour exécution quotidienne:

```dockerfile
# Ajouter dans le Dockerfile
RUN apt-get install -y cron

# Créer crontab
RUN echo "0 9 * * * cd /app && python main.py bot >> /app/logs/cron.log 2>&1" | crontab -

CMD ["cron", "-f"]
```

______________________________________________________________________

## ☁️ Déploiement cloud

### AWS Lambda

**Avantages**: Serverless, pas de serveur à gérer

```bash
# Utiliser AWS SAM ou Serverless Framework
npm install -g serverless
serverless create --template aws-python3 --path linkedin-bot-lambda

# Configurer serverless.yml
# Déployer
serverless deploy
```

### Google Cloud Run

**Avantages**: Containers, scaling automatique

```bash
# Build et push l'image
gcloud builds submit --tag gcr.io/PROJECT_ID/linkedin-bot

# Déployer
gcloud run deploy linkedin-bot \
  --image gcr.io/PROJECT_ID/linkedin-bot \
  --platform managed \
  --region europe-west1 \
  --set-env-vars LINKEDIN_AUTH_STATE=$AUTH
```

### Heroku

**Avantages**: Simple, free tier disponible

```bash
# Login
heroku login

# Créer app
heroku create linkedin-birthday-bot

# Config
heroku config:set LINKEDIN_AUTH_STATE=$AUTH

# Déployer
git push heroku main

# Ajouter scheduler
heroku addons:create scheduler:standard
heroku addons:open scheduler
# Configurer: python main.py bot (daily à 9h)
```

### VPS (DigitalOcean, Linode, etc.)

```bash
# SSH dans le VPS
ssh user@your-vps-ip

# Installer
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto
./install.sh  # À créer

# Configurer cron
crontab -e
# Ajouter:
0 9 * * * cd /home/user/linkedin-birthday-auto && /home/user/linkedin-birthday-auto/venv/bin/python main.py bot
```

______________________________________________________________________

## 📊 Monitoring et logs

### Logs locaux

```bash
# Suivre les logs en temps réel
tail -f logs/linkedin_bot.log

# Rechercher des erreurs
grep ERROR logs/linkedin_bot.log

# Logs des 24 dernières heures
find logs/ -mtime -1 -type f -exec cat {} \;
```

### Monitoring API

Si vous utilisez l'API:

```bash
# Démarrer l'API
python main.py api

# Health check
curl http://localhost:8000/health

# Métriques
curl http://localhost:8000/metrics

# Déclencher un job
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -d '{"bot_mode": "standard", "dry_run": true}'
```

### Alertes

**Slack webhook** (exemple):

```python
# Ajouter dans src/utils/notifications.py
import requests


def send_slack_alert(message):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        requests.post(webhook_url, json={"text": message})
```

______________________________________________________________________

## 🔧 Dépannage

### Problèmes courants

#### 1. "Authentication failed"

```bash
# Vérifier auth state
python main.py validate

# Régénérer auth state
# Se reconnecter à LinkedIn et exporter les cookies à nouveau
```

#### 2. "Playwright browser not found"

```bash
# Réinstaller les navigateurs
playwright install chromium
playwright install-deps chromium
```

#### 3. "Weekly limit reached"

```bash
# Vérifier les stats database
python -c "from src.core.database import get_database; db = get_database(); print(db.get_weekly_message_count())"

# Attendre la semaine prochaine ou passer en mode unlimited
python main.py bot --mode unlimited
```

#### 4. "Database locked"

```bash
# Vérifier les processus
ps aux | grep python

# Supprimer le lock
rm data/linkedin_bot.db-wal
```

#### 5. Mode headless ne fonctionne pas

```bash
# Tester en mode headed
python main.py bot --headless false

# Vérifier Xvfb (Linux serveur sans GUI)
Xvfb :99 &
export DISPLAY=:99
python main.py bot
```

### Debug avancé

```bash
# Mode debug complet
python main.py bot --debug

# Désactiver headless pour voir le navigateur
LINKEDIN_BOT_BROWSER_HEADLESS=false python main.py bot --debug

# Screenshots d'erreur
# Automatiquement sauvegardés dans logs/screenshots/
```

### Support

- **Issues**: [GitHub Issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)
- **Discussions**:
  [GitHub Discussions](https://github.com/GaspardD78/linkedin-birthday-auto/discussions)
- **Documentation**: [ARCHITECTURE.md](ARCHITECTURE.md), [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

______________________________________________________________________

## 📝 Checklist de production

Avant de passer en production:

- [ ] Configuration validée (`python main.py validate`)
- [ ] Tests en dry-run réussis (`python main.py bot --dry-run`)
- [ ] Authentification LinkedIn valide et 2FA activé
- [ ] Database activée et testée
- [ ] Limites hebdomadaires configurées (recommandé: 80)
- [ ] Logs configurés et accessibles
- [ ] Backups réguliers de la database
- [ ] Monitoring en place (API ou logs)
- [ ] Alertes configurées pour les erreurs
- [ ] Secrets sécurisés (pas dans le code)
- [ ] Cron/scheduler configuré
- [ ] Documentation à jour

______________________________________________________________________

## 🎯 Recommandations

### Pour débuter

1. **Local** + **Dry-run** + **Mode standard**
1. Tester pendant 1 semaine en dry-run
1. Activer production en mode standard
1. Optionnel: passer en mode unlimited si besoin

### Pour production

1. **GitHub Actions** (recommandé pour simplicité)
1. **Docker** + **VPS** (pour contrôle total)
1. **Cloud Run** (pour scaling)

### Sécurité

1. Ne JAMAIS committer `auth_state.json`
1. Utiliser GitHub Secrets ou variables d'environnement
1. Activer 2FA sur LinkedIn
1. Régulièrement vérifier les logs
1. Limiter les permissions du bot

______________________________________________________________________

**Bon déploiement ! 🚀**
