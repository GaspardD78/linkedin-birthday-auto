# 🎂 LinkedIn Birthday Auto Bot v2.0

[![Raspberry Pi 4](https://img.shields.io/badge/Raspberry%20Pi-Optimized-red.svg)](docs/RPI_QUICKSTART.md)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Automatisez vos messages d'anniversaire LinkedIn** avec intelligence, flexibilité et sécurité.

Bot moderne et modulaire pour souhaiter les anniversaires de vos contacts LinkedIn de manière
naturelle et personnalisée. Optimisé pour fonctionner en local ou sur serveur (Raspberry Pi, VPS).

______________________________________________________________________

## ✨ Caractéristiques principales

### 🎯 Modes d'exécution

- **Mode Standard** : Anniversaires du jour uniquement avec limites hebdomadaires (80/semaine
  recommandé)
- **Mode Unlimited** : Aujourd'hui + retard (jusqu'à N jours) sans limites hebdomadaires
- **Mode API REST** : Contrôle via HTTP avec FastAPI (health checks, metrics, triggers)

### 🧠 Intelligence

- **Messages personnalisés** avec rotation automatique et historique anti-répétition
- **Comportement humain** : délais aléatoires, mouvements, scrolling naturel
- **Gestion d'erreurs** robuste avec retry et recovery automatique
- **Anti-détection** : User-Agent rotation, viewport randomization, stealth mode

### 📊 Monitoring & Déploiement

- **Database SQLite** avec historique complet (messages, visites, erreurs)
- **Statistiques en temps réel** via API `/metrics`
- **Logs structurés** avec niveaux (DEBUG, INFO, WARNING, ERROR)
- **Health checks** pour supervision
- **🆕 Dashboard de déploiement** : surveillance des services, gestion des jobs, maintenance
  automatisée
- **🆕 Script de déploiement** : automatisation complète (pull, rebuild, restart)
- **🆕 Arrêt d'urgence** : bouton pour arrêter immédiatement tous les workers

### 🔧 Architecture v2.0

- **Modulaire** : Configuration Pydantic, exceptions typées, managers séparés
- **Testable** : 30+ tests (unitaires, intégration, E2E) avec 85%+ coverage
- **Type-safe** : Type hints complets + mypy validation
- **Production-ready** : Pre-commit hooks, CI/CD, Docker support

______________________________________________________________________

## 🚀 Quick Start

### 🍓 Raspberry Pi 4 Users

**⚠️ NE PAS UTILISER `pip install` !** L'installation sur Raspberry Pi est entièrement automatisée
via Docker pour éviter les problèmes de compilation.

👉 **[SUIVRE LE GUIDE D'INSTALLATION RPI 4 (CLIQUEZ ICI)](docs/RPI_QUICKSTART.md)**

______________________________________________________________________

### Installation Standard (PC/Mac/Linux)

```bash
# 1. Cloner le projet
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# 2. Créer environnement virtuel
python3.9 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. Installer dépendances
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium

# 4. Configurer (voir section suivante)
cp config/config.yaml config/my_config.yaml
nano config/my_config.yaml  # Éditer selon vos besoins
```

### Configuration minimale

**Option A: Variables d'environnement** (recommandé)

```bash
# Créer .env
cat > .env << 'EOF'
# Authentification LinkedIn (base64)
LINKEDIN_AUTH_STATE=eyJjb29raWVzIjpbeyJuYW1lIjoibGlfYXQiLC...

# Mode
LINKEDIN_BOT_DRY_RUN=false  # true pour tester
LINKEDIN_BOT_MODE=standard

# Optionnel
LINKEDIN_BOT_BROWSER_HEADLESS=true
EOF

chmod 600 .env
```

**Option B: Fichier YAML**

```yaml
# config/my_config.yaml
version: "2.0.0"
dry_run: false
bot_mode: "standard"

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

### Authentification LinkedIn

**Méthode 1: Exporter les cookies** (recommandé)

1. Installez l'extension [Cookie-Editor](https://cookie-editor.cgagnier.ca/)
1. Connectez-vous à LinkedIn (avec 2FA si activé)
1. Exportez les cookies en JSON
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

**Méthode 2: Variable d'environnement**

```bash
export LINKEDIN_AUTH_STATE=$(cat auth_state.json | base64)
```

### Premiers tests

```bash
# 1. Valider configuration
python main.py validate

# 2. Dry-run (test sans envoyer)
python main.py bot --dry-run

# 3. Production mode standard
python main.py bot

# 4. Mode unlimited (rattraper retard)
python main.py bot --mode unlimited --max-days-late 10
```

______________________________________________________________________

## 📖 Documentation

| Document                                                                         | Description                                                   |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| **[ARCHITECTURE.md](ARCHITECTURE.md)**                                           | Architecture détaillée, patterns, composants                  |
| **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)**                                     | Migration depuis v1.x vers v2.0                               |
| **[DEPLOYMENT.md](DEPLOYMENT.md)**                                               | Guide déploiement (local, cloud, Docker)                      |
| **[SETUP_PI4_FREEBOX.md](SETUP_PI4_FREEBOX.md)**                                 | 🆕 **Déploiement Pi4 Standalone** (sans NAS) - **Recommandé** |
| **[SETUP_PI4_SYNOLOGY_FREEBOX.md](SETUP_PI4_SYNOLOGY_FREEBOX.md)**               | Déploiement Pi4 + Synology NAS + Freebox Pop                  |
| **[RASPBERRY_PI4_GUIDE.md](RASPBERRY_PI4_GUIDE.md)**                             | Installation sur Raspberry Pi (méthode manuelle v1.x)         |
| **[docs/RASPBERRY_PI_DOCKER_SETUP.md](docs/RASPBERRY_PI_DOCKER_SETUP.md)**       | Installation Docker sur Raspberry Pi (v2.0 recommandé)        |
| **[docs/RASPBERRY_PI_TROUBLESHOOTING.md](docs/RASPBERRY_PI_TROUBLESHOOTING.md)** | Guide de dépannage pour Raspberry Pi                          |

______________________________________________________________________

## 🎯 Utilisation

### CLI (Command Line Interface)

Le bot dispose d'une CLI riche avec 3 commandes principales:

#### 1. Valider configuration

```bash
# Valider config + authentification
python main.py validate

# Avec config custom
python main.py validate --config ./prod.yaml
```

#### 2. Exécuter le bot

```bash
# Mode standard (anniversaires du jour uniquement)
python main.py bot

# Mode unlimited (today + late birthdays)
python main.py bot --mode unlimited --max-days-late 10

# Dry-run (test sans envoyer)
python main.py bot --dry-run

# Debug mode
python main.py bot --debug

# Avec config custom
python main.py bot --config ./prod.yaml

# Toutes les options
python main.py bot --help
```

#### 3. Lancer l'API REST

```bash
# Mode production
python main.py api

# Mode développement (auto-reload)
python main.py api --reload

# Custom host/port
python main.py api --host 0.0.0.0 --port 8080
```

### API REST

L'API REST FastAPI permet un contrôle à distance:

```bash
# Démarrer l'API
python main.py api

# Health check
curl http://localhost:8000/health

# Métriques (30 derniers jours)
curl http://localhost:8000/metrics

# Déclencher un job
curl -X POST http://localhost:8000/trigger \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "bot_mode": "standard",
    "dry_run": true
  }'

# Vérifier statut du job
curl http://localhost:8000/jobs/{job_id}

# Consulter les logs
curl http://localhost:8000/logs?limit=100

# Documentation interactive
open http://localhost:8000/docs
```

### Python (usage programmatique)

```python
from src.bots.birthday_bot import BirthdayBot
from src.bots.unlimited_bot import UnlimitedBirthdayBot
from src.config import get_config

# Configuration
config = get_config()
config.dry_run = True

# Mode standard
with BirthdayBot(config=config) as bot:
    results = bot.run()
    print(f"Messages sent: {results['messages_sent']}")

# Mode unlimited
with UnlimitedBirthdayBot(config=config) as bot:
    results = bot.run()
    print(f"Total processed: {results['contacts_processed']}")
```

______________________________________________________________________

## 🔧 Configuration avancée

### Structure du fichier config.yaml

```yaml
version: "2.0.0"
dry_run: false
bot_mode: "standard"  # ou "unlimited"

# Navigateur
browser:
  headless: true
  locale: "fr-FR"
  timezone: "Europe/Paris"
  slow_mo: [80, 150]  # Ralentissement (ms) pour paraître humain
  viewport_sizes:  # Résolutions aléatoires
    - [1920, 1080]
    - [1366, 768]
  user_agents:  # Rotation User-Agent
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."

# Authentification
auth:
  auth_file_path: "auth_state.json"
  auth_env_var: "LINKEDIN_AUTH_STATE"

# Limites de messages
messaging_limits:
  weekly_message_limit: 80
  daily_message_limit: null  # null = pas de limite quotidienne
  max_messages_per_run: null  # null = pas de limite par run

# Filtrage des anniversaires
birthday_filter:
  process_today: true
  process_late: false  # true pour mode unlimited
  max_days_late: 10  # Si process_late=true

# Délais entre messages
delays:
  min_delay_seconds: 180  # 3 minutes
  max_delay_seconds: 300  # 5 minutes

# Messages
messages:
  message_file_path: "messages.txt"
  late_message_file_path: "late_messages.txt"
  avoid_repetition_years: 2

# Base de données
database:
  enabled: true
  db_path: "data/linkedin_bot.db"

# Scheduling
scheduling:
  daily_start_hour: 7
  daily_end_hour: 19

# Debug
debug:
  log_level: "INFO"
  screenshot_on_error: true
  save_html_on_error: false
```

### Variables d'environnement (overrides)

Toutes les config YAML peuvent être overridées via env vars:

```bash
# Format: LINKEDIN_BOT_<SECTION>_<KEY>
export LINKEDIN_BOT_DRY_RUN=true
export LINKEDIN_BOT_BOT_MODE=unlimited
export LINKEDIN_BOT_BROWSER_HEADLESS=false
export LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT=100
```

______________________________________________________________________

## 🤖 Automatisation

### Cron (Linux/macOS)

```bash
# Éditer crontab
crontab -e

# Ajouter (exécution quotidienne à 9h)
0 9 * * * cd /path/to/linkedin-birthday-auto && /path/to/venv/bin/python main.py bot

# Avec logs
0 9 * * * cd /path/to/linkedin-birthday-auto && /path/to/venv/bin/python main.py bot >> /var/log/linkedin-bot.log 2>&1
```

### Docker

**Option 1: Configuration basique**

```bash
# Build
docker build -t linkedin-bot .

# Run
docker run -e LINKEDIN_AUTH_STATE=$AUTH linkedin-bot

# Docker Compose
docker-compose up -d
```

**Option 2: Raspberry Pi 4 + Freebox (Standalone) - Recommandé**

Configuration optimisée pour RPi4 (4GB RAM) en mode autonome.

- **Backend**: FastAPI (Python) + RQ Worker (Redis)
- **Frontend**: Next.js 14 (Optimisé sans Puppeteer)
- **Database**: SQLite (local) + Redis (Queue/Cache)

```bash
# Déploiement automatique (Bot + Dashboard + Redis + SQLite)
# Ce script gère le nettoyage, le build optimisé et le déploiement
./scripts/deploy_pi4_standalone.sh

# Ou manuellement
docker compose -f docker-compose.pi4-standalone.yml up -d

# Accès dashboard: http://192.168.1.X:3000
```

*Optimisations appliquées :*

- Image Dashboard ultra-légère (Puppeteer retiré)
- Limites mémoire strictes (API: 300MB, Dashboard: 400MB, Worker: 900MB)
- Utilisation de `rq.Queue` pour décharger l'API des tâches lourdes

📖 **Documentation complète** : [SETUP_PI4_FREEBOX.md](SETUP_PI4_FREEBOX.md)

**Option 3: Raspberry Pi 4 + Synology + Freebox**

Si vous avez un NAS Synology pour MySQL/stockage :

📖 **Documentation** : [SETUP_PI4_SYNOLOGY_FREEBOX.md](SETUP_PI4_SYNOLOGY_FREEBOX.md)

### Systemd (Linux service)

```ini
# /etc/systemd/system/linkedin-bot.service
[Unit]
Description=LinkedIn Birthday Bot
After=network.target

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/path/to/linkedin-birthday-auto
ExecStart=/path/to/venv/bin/python main.py bot
EnvironmentFile=/path/to/.env

[Install]
WantedBy=multi-user.target
```

```bash
# Activer et démarrer
sudo systemctl enable linkedin-bot.service
sudo systemctl start linkedin-bot.service
```

______________________________________________________________________

## 🧪 Tests

### Exécuter les tests

```bash
# Tous les tests
pytest

# Tests unitaires uniquement
pytest tests/unit/ -v

# Tests d'intégration
pytest tests/integration/ -v

# Tests E2E
pytest tests/e2e/ -v -m e2e

# Avec couverture
pytest --cov=src --cov-report=html --cov-report=term-missing

# Test spécifique
pytest tests/unit/test_config.py::TestConfigSchema::test_default_config_is_valid -v
```

### Pre-commit hooks

```bash
# Installer
pip install pre-commit
pre-commit install

# Exécuter manuellement
pre-commit run --all-files

# Hooks inclus:
# - black (formatting)
# - ruff (linting)
# - mypy (type checking)
# - bandit (security)
# - markdown formatting
```

______________________________________________________________________

## 📊 Monitoring

### Logs

```bash
# Suivre les logs en temps réel
tail -f logs/linkedin_bot.log

# Rechercher des erreurs
grep ERROR logs/linkedin_bot.log

# Statistiques database
sqlite3 data/linkedin_bot.db "SELECT COUNT(*) FROM birthday_messages WHERE DATE(timestamp) = DATE('now');"
```

### Métriques API

```bash
# Métriques des 30 derniers jours
curl http://localhost:8000/metrics

# Réponse:
{
  "period_days": 30,
  "messages": {
    "total": 45,
    "per_day_avg": 1.5
  },
  "contacts": {
    "unique": 42,
    "repeated": 3
  },
  "profile_visits": {
    "total": 120
  },
  "errors": {
    "total": 2,
    "rate": 0.04
  }
}
```

______________________________________________________________________

## 🔒 Sécurité & Bonnes pratiques

### Sécurité

- ✅ **Jamais committer** `auth_state.json` ou `.env` (dans `.gitignore`)
- ✅ **Permissions strictes** : `chmod 600 .env auth_state.json`
- ✅ **Secrets chiffrés** : Utiliser variables d'environnement sécurisées
- ✅ **2FA activé** sur LinkedIn (recommandé)
- ✅ **Rotation User-Agent** et anti-détection activés
- ✅ **Pas de données transmises** à des tiers

### Limites recommandées

Pour éviter la détection LinkedIn:

| Paramètre                | Recommandation             | Justification                               |
| ------------------------ | -------------------------- | ------------------------------------------- |
| **Messages/semaine**     | 80 maximum                 | Limite LinkedIn non documentée ~100/semaine |
| **Messages/jour**        | 15-20 maximum              | Éviter pics suspects                        |
| **Délai entre messages** | 3-5 minutes                | Comportement humain                         |
| **Horaires**             | 7h-19h                     | Heures ouvrables                            |
| **Mode headless**        | `true` en prod             | Performance                                 |
| **IP**                   | Résidentielle > Datacenter | LinkedIn détecte les IPs cloud              |

### Utilisation responsable

⚠️ **Avertissement**: L'automatisation LinkedIn viole potentiellement leurs
[CGU](https://www.linkedin.com/legal/user-agreement). Utilisez à vos propres risques.

**Recommandations:**

- 🟢 Utiliser pour un usage personnel raisonnable
- 🟢 Messages authentiques et personnalisés
- 🟢 Respecter les limites recommandées
- 🔴 Pas de spam ou messages non sollicités
- 🔴 Pas d'usage commercial massif
- 🔴 Pas de collecte de données

______________________________________________________________________

## 🐛 Dépannage

### Problèmes courants

**1. "Authentication failed"**

```bash
# Vérifier auth
python main.py validate

# Régénérer auth_state.json
# Exporter à nouveau les cookies depuis LinkedIn
```

**2. "Playwright browser not found"**

```bash
playwright install chromium
playwright install-deps chromium
```

**3. "Weekly limit reached"**

```bash
# Vérifier limite actuelle
python -c "from src.core.database import get_database; print(get_database().get_weekly_message_count())"

# Attendre lundi ou passer en mode unlimited
python main.py bot --mode unlimited
```

**4. "Database locked"**

```bash
# Tuer processus existants
pkill -f "python.*main.py"

# Supprimer lock
rm data/linkedin_bot.db-wal data/linkedin_bot.db-shm
```

**5. Mode headless échoue**

```bash
# Tester en mode visible
python main.py bot --headless false --debug
```

Voir **[DEPLOYMENT.md](DEPLOYMENT.md#d%C3%A9pannage)** pour plus de solutions.

______________________________________________________________________

## 📦 Structure du projet

```
linkedin-birthday-auto/
├── main.py                    # Point d'entrée CLI unifié
├── config/
│   └── config.yaml           # Configuration YAML
├── src/
│   ├── api/
│   │   └── app.py           # API REST FastAPI
│   ├── bots/
│   │   ├── birthday_bot.py  # Bot standard
│   │   └── unlimited_bot.py # Bot unlimited
│   ├── config/
│   │   ├── config_schema.py # Schémas Pydantic
│   │   └── config_manager.py # Singleton config
│   ├── core/
│   │   ├── base_bot.py      # Classe abstraite
│   │   ├── browser_manager.py
│   │   ├── auth_manager.py
│   │   └── database.py
│   └── utils/
│       └── exceptions.py     # Hiérarchie exceptions
├── tests/
│   ├── unit/                # Tests unitaires
│   ├── integration/         # Tests intégration
│   └── e2e/                 # Tests E2E
├── pyproject.toml           # Config moderne (black, ruff, mypy, pytest)
├── .pre-commit-config.yaml  # Pre-commit hooks
├── ARCHITECTURE.md          # Architecture détaillée
├── MIGRATION_GUIDE.md       # Migration v1 -> v2
└── DEPLOYMENT.md            # Guide déploiement
```

______________________________________________________________________

## 🎉 Changelog v2.0

### 🆕 Nouvelles fonctionnalités

- ✅ **Architecture modulaire** avec Pydantic, managers, bots séparés
- ✅ **API REST FastAPI** avec health checks, metrics, triggers
- ✅ **CLI riche** avec 3 commandes (validate, bot, api)
- ✅ **Tests complets** (30+ tests, 85%+ coverage)
- ✅ **Mode unlimited** pour rattraper les retards
- ✅ **Type hints** complets + mypy validation
- ✅ **Pre-commit hooks** (black, ruff, mypy, bandit)
- ✅ **Documentation complète** (ARCHITECTURE, MIGRATION, DEPLOYMENT)

### 🐛 Bugs corrigés

- ✅ **Modales multiples** : Détection et nettoyage automatique
- ✅ **Element detached** : Re-recherche des éléments DOM
- ✅ **Délais skip** : 1-3s au lieu de 3-4min
- ✅ **Database locks** : WAL mode + retry avec backoff
- ✅ **Memory leaks** : Cleanup proper des ressources

### ⚡ Performances

- ✅ **10x plus rapide** lors de contacts sans bouton Message
- ✅ **Thread-safe** : Singleton avec locks
- ✅ **Retry intelligent** : Exponential backoff
- ✅ **Connection pooling** : Database WAL mode

### 🔄 Breaking changes

Voir **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** pour migration depuis v1.x.

______________________________________________________________________

## 🤝 Contribution

Les contributions sont bienvenues !

```bash
# Fork et clone
git clone https://github.com/your-username/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# Installer dev dependencies
pip install -r requirements-new.txt
pip install -e ".[dev]"

# Installer pre-commit
pre-commit install

# Créer branche
git checkout -b feature/ma-fonctionnalite

# Développer + tests
# ...

# Lancer tests et quality checks
pytest
pre-commit run --all-files

# Commit et push
git add .
git commit -m "feat: ma nouvelle fonctionnalité"
git push origin feature/ma-fonctionnalite
```

______________________________________________________________________

## 📜 Licence

Ce projet est fourni "tel quel", sans garantie d'aucune sorte.

**Utilisation à vos propres risques.** LinkedIn peut détecter et bloquer l'automatisation.

______________________________________________________________________

## 🙏 Crédits

- **Playwright** pour l'automatisation browser
- **FastAPI** pour l'API REST
- **Pydantic** pour la validation
- **Communauté open-source** pour les feedbacks et contributions

______________________________________________________________________

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)
- **Discussions**:
  [GitHub Discussions](https://github.com/GaspardD78/linkedin-birthday-auto/discussions)
- **Documentation**: Voir les fichiers `.md` dans le repo

______________________________________________________________________

**Conçu avec ❤️ pour automatiser intelligemment**

*LinkedIn Birthday Auto Bot v2.0 - Architecture moderne, tests complets, production-ready*
