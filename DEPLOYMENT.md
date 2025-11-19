# Guide de Déploiement - LinkedIn Birthday Auto

## Vue d'ensemble

Ce guide couvre le déploiement complet de LinkedIn Birthday Auto avec toutes les fonctionnalités de la Phase 1.

---

## 🚀 Déploiement Local

### Prérequis

```bash
# Python 3.9+
python --version

# Git
git --version
```

### Installation

#### 1. Cloner le repository

```bash
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto
```

#### 2. Créer un environnement virtuel

```bash
# Créer l'environnement
python -m venv venv

# Activer (Linux/Mac)
source venv/bin/activate

# Activer (Windows)
venv\Scripts\activate
```

#### 3. Installer les dépendances

```bash
pip install -r requirements.txt
playwright install chromium
```

#### 4. Initialiser la base de données

```bash
# La base de données sera créée automatiquement au premier lancement
python database.py
```

✅ **Output attendu:**
```
SQLite configured: WAL mode, 30s timeout, optimized cache
✓ Base de données créée avec succès
✓ Contact créé avec ID: 1
✓ Message créé avec ID: 1
✓ Statistiques: {...}
✓ Export JSON créé
✓ Tous les tests sont passés avec succès !
```

---

## 🧪 Tests (GitHub Actions uniquement)

**IMPORTANT:** Les tests automatisés doivent être exécutés uniquement via GitHub Actions, pas en local.

### Exécuter les tests via GitHub Actions

1. **Déclenchement manuel:**
   - Allez sur GitHub → Actions → "Test Suite - Phase 1"
   - Cliquez sur "Run workflow"
   - Les tests s'exécutent automatiquement

2. **Déclenchement automatique:**
   - Les tests s'exécutent automatiquement sur chaque push/PR vers main/master
   - Les tests s'exécutent quand des fichiers Python sont modifiés

3. **Consulter les résultats:**
   - GitHub → Actions → Sélectionner le workflow run
   - Télécharger les artifacts "test-results" pour voir les logs détaillés
   - Les résultats sont commentés automatiquement sur les PRs

### Ce qui est testé

Le workflow `.github/workflows/test.yml` exécute `scripts/test_all.sh` qui vérifie:

- ✅ Environnement (Python, pip, git)
- ✅ Dépendances (playwright, flask, pytz, sqlite3)
- ✅ Base de données (création, CRUD, WAL mode, schema version)
- ✅ Singleton thread-safe
- ✅ Fichiers de configuration
- ✅ Dashboard Flask (routes, API endpoints)

**Taux de réussite attendu:** 100% (26/26 tests passés)

---

### Configuration

#### 1. Générer l'état d'authentification LinkedIn

```bash
python generate_auth_state.py
```

Cela va:
1. Ouvrir un navigateur
2. Vous demander de vous connecter à LinkedIn
3. Sauvegarder la session dans `auth_state.json`
4. Encoder en base64 pour GitHub Secrets

#### 2. Configurer les messages

Personnalisez vos messages d'anniversaire:

```bash
# Messages normaux
nano messages.txt

# Messages en retard
nano late_messages.txt
```

Format:
```
Joyeux anniversaire {name} ! J'espère que tu passes une excellente journée.
Hello {name}, happy birthday!
```

⚠️ **Important:** Gardez le placeholder `{name}` !

#### 3. Configurer la recherche de profils

```bash
nano config.json
```

```json
{
  "keywords": ["Azure", "Cloud", "DevOps"],
  "location": "Ile-de-France"
}
```

---

## 🧪 Tests

### Test Complet Automatisé

```bash
./scripts/test_all.sh
```

Ou manuellement:

```bash
# Test de la base de données
python database.py

# Test du validateur de sélecteurs
python -c "from selector_validator import SelectorValidator; print('✓ Import OK')"

# Test du dashboard (sans Playwright)
python -c "from dashboard_app import app; print('✓ Dashboard OK')"
```

### Test en Mode DRY RUN

```bash
# Test du script d'anniversaires (sans envoyer de messages)
DRY_RUN=true python linkedin_birthday_wisher.py

# Test de visites de profils
DRY_RUN=true python visit_profiles.py
```

✅ **Vérifications:**
- Aucune erreur "database locked"
- Mode WAL confirmé
- Messages enregistrés dans la BDD
- Logs structurés affichés

---

## 📊 Déploiement du Dashboard

### Lancement Local

#### Option 1: Script de démarrage

```bash
./scripts/start_dashboard.sh
```

#### Option 2: Manuel

```bash
python dashboard_app.py
```

✅ **Accès:** http://localhost:5000

#### Configuration avancée

Variables d'environnement:

```bash
# Port personnalisé
PORT=8080 python dashboard_app.py

# Mode production (pas de debug)
FLASK_DEBUG=false python dashboard_app.py

# Secret key personnalisée (IMPORTANT en production!)
FLASK_SECRET_KEY="votre-cle-secrete-aleatoire" python dashboard_app.py

# Base de données personnalisée
DATABASE_PATH=/chemin/vers/ma.db python dashboard_app.py
```

### Production avec Gunicorn

```bash
# Installer gunicorn
pip install gunicorn

# Lancer en production (4 workers)
gunicorn -w 4 -b 0.0.0.0:5000 dashboard_app:app

# Avec logs
gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - --error-logfile - dashboard_app:app
```

---

## ☁️ Déploiement Cloud

### Heroku

#### 1. Prérequis

```bash
# Installer Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login
heroku login
```

#### 2. Créer l'application

```bash
# Créer l'app
heroku create linkedin-birthday-dashboard

# Ajouter buildpack Python
heroku buildpacks:add heroku/python
```

#### 3. Créer Procfile

```bash
cat > Procfile << EOF
web: gunicorn dashboard_app:app
EOF
```

#### 4. Déployer

```bash
# Commit les changements
git add Procfile
git commit -m "Add Procfile for Heroku"

# Push vers Heroku
git push heroku main

# Ouvrir l'app
heroku open
```

#### 5. Configuration

```bash
# Secret key
heroku config:set FLASK_SECRET_KEY="$(openssl rand -hex 32)"

# Mode production
heroku config:set FLASK_DEBUG=false

# Voir les logs
heroku logs --tail
```

### Railway

#### 1. Installation

```bash
# Installer Railway CLI
npm install -g @railway/cli

# Login
railway login
```

#### 2. Initialiser

```bash
# Créer nouveau projet
railway init

# Déployer
railway up
```

#### 3. Configuration

```bash
# Variables d'environnement
railway variables set FLASK_SECRET_KEY="$(openssl rand -hex 32)"
railway variables set FLASK_DEBUG=false

# Voir les logs
railway logs
```

### Render

1. Aller sur https://render.com
2. New → Web Service
3. Connecter votre repo GitHub
4. Configuration:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn dashboard_app:app`
   - **Environment Variables:**
     - `FLASK_SECRET_KEY`: Générer une clé aléatoire
     - `FLASK_DEBUG`: `false`
5. Deploy

---

## 🤖 GitHub Actions

### Configuration des Secrets

1. Aller dans **Settings** → **Secrets and variables** → **Actions**
2. Ajouter les secrets:

```
LINKEDIN_AUTH_STATE=<votre-auth-state-base64>
DRY_RUN=false
```

Optionnel (pour les alertes email):

```
ENABLE_EMAIL_ALERTS=true
ENABLE_ADVANCED_DEBUG=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
ALERT_EMAIL=votre-email@gmail.com
ALERT_EMAIL_PASSWORD=votre-app-password
RECIPIENT_EMAIL=destinataire@email.com
```

### Workflows Disponibles

Les workflows sont déjà configurés:

1. **`.github/workflows/main.yml`**
   - Exécution quotidienne à 7h-9h (Paris)
   - Envoie les messages d'anniversaire
   - Limite hebdomadaire: 80 messages

2. **`.github/workflows/birthday_unlimited.yml`**
   - Déclenchement manuel uniquement
   - Mode rattrapage sans limite
   - Pour les anniversaires en retard

3. **`.github/workflows/visit_profiles.yml`**
   - Déclenchement manuel
   - Visite 15 profils par exécution
   - Basé sur config.json

### Exécution Manuelle

1. Aller dans **Actions**
2. Sélectionner le workflow
3. Cliquer **Run workflow**
4. Choisir la branche
5. **Run workflow**

### Monitoring

```bash
# Voir les logs d'une exécution
gh run view <run-id> --log

# Liste des dernières exécutions
gh run list

# Voir les artifacts
gh run download <run-id>
```

---

## 🔒 Sécurité

### Bonnes Pratiques

#### 1. Secrets

```bash
# JAMAIS committer:
auth_state.json
*.db
.env

# Toujours utiliser GitHub Secrets pour:
- LINKEDIN_AUTH_STATE
- SMTP passwords
- API keys
```

#### 2. Flask Secret Key

```bash
# Générer une clé sécurisée
python -c "import secrets; print(secrets.token_hex(32))"

# Définir en variable d'environnement
export FLASK_SECRET_KEY="votre-cle-generee"
```

#### 3. Protection CSRF (si dashboard public)

```bash
pip install flask-wtf

# Dans dashboard_app.py:
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
```

#### 4. HTTPS Only

Si déployé publiquement, forcer HTTPS:

```python
# dashboard_app.py
from flask_talisman import Talisman
Talisman(app)
```

---

## 📈 Monitoring

### Logs

#### Local

```bash
# Logs des scripts
tail -f linkedin_bot_detailed.log

# Logs du dashboard
FLASK_DEBUG=true python dashboard_app.py
```

#### GitHub Actions

```bash
# Via web interface
https://github.com/VOTRE-USERNAME/linkedin-birthday-auto/actions

# Via CLI
gh run list
gh run view --log
```

### Métriques

Le dashboard affiche:
- Quota hebdomadaire (80 messages max)
- Messages envoyés (7j, 30j)
- Profils visités
- Erreurs récentes
- Top contacts

**URL:** http://localhost:5000

### Alertes Email

Si configuré, vous recevrez des emails pour:
- Échecs de connexion
- Validations DOM échouées
- Restrictions LinkedIn détectées
- Erreurs critiques

---

## 🐛 Troubleshooting

### Database Locked

**Problème:** Erreur "database is locked"

**Solutions:**
```bash
# 1. Vérifier le mode WAL
sqlite3 linkedin_automation.db "PRAGMA journal_mode"
# Doit afficher: WAL

# 2. Si pas en WAL, forcer:
sqlite3 linkedin_automation.db "PRAGMA journal_mode=WAL"

# 3. Supprimer et recréer
rm linkedin_automation.db
python database.py
```

### Import Playwright Failed

**Problème:** `ModuleNotFoundError: No module named 'playwright'`

**Solution:**
```bash
pip install playwright
playwright install chromium
```

### Dashboard Won't Start

**Problème:** Dashboard ne démarre pas

**Solutions:**
```bash
# 1. Vérifier Flask
pip install flask

# 2. Vérifier les imports
python -c "from dashboard_app import app"

# 3. Port déjà utilisé
PORT=8080 python dashboard_app.py
```

### Authentication Expired

**Problème:** Session LinkedIn expirée

**Solution:**
```bash
# Régénérer l'auth state
python generate_auth_state.py

# Mettre à jour le secret GitHub
# Settings → Secrets → LINKEDIN_AUTH_STATE
```

### Memory Issues

**Problème:** Out of memory

**Solutions:**
```bash
# 1. Nettoyer les anciennes données
python -c "from database import get_database; db = get_database(); db.cleanup_old_data(180)"

# 2. Supprimer les screenshots
rm -f *.png

# 3. Vacuum la BDD
sqlite3 linkedin_automation.db "VACUUM"
```

---

## 📊 Checklist de Déploiement

### Pré-déploiement

- [ ] Environnement virtuel créé et activé
- [ ] Dépendances installées (`pip install -r requirements.txt`)
- [ ] Playwright installé (`playwright install chromium`)
- [ ] Auth state généré (`python generate_auth_state.py`)
- [ ] Messages personnalisés (`messages.txt`, `late_messages.txt`)
- [ ] Config.json configuré
- [ ] Tests passés (`python database.py`)

### GitHub Actions

- [ ] Secrets configurés (LINKEDIN_AUTH_STATE)
- [ ] Workflow testé en mode DRY_RUN
- [ ] Cron jobs vérifiés (7h-9h Paris)
- [ ] Emails d'alerte testés (optionnel)

### Dashboard

- [ ] Dashboard démarre (`python dashboard_app.py`)
- [ ] Accessible sur http://localhost:5000
- [ ] Statistiques affichées
- [ ] Secret key configurée (si production)
- [ ] HTTPS configuré (si public)

### Production

- [ ] Gunicorn installé
- [ ] FLASK_DEBUG=false
- [ ] Secret key sécurisée
- [ ] Logs configurés
- [ ] Monitoring en place
- [ ] Backups planifiés

---

## 🔄 Maintenance

### Quotidienne

- Vérifier le dashboard pour erreurs
- Consulter les logs GitHub Actions
- Vérifier le quota hebdomadaire

### Hebdomadaire

- Exporter la BDD (`python -c "from database import get_database; get_database().export_to_json('backup.json')"`)
- Nettoyer les vieux screenshots (`rm -f *.png`)
- Vérifier l'auth state (régénérer si expiré)

### Mensuelle

- Nettoyer la BDD (`db.cleanup_old_data(365)`)
- VACUUM SQLite (`sqlite3 linkedin_automation.db "VACUUM"`)
- Mettre à jour les dépendances (`pip install -U -r requirements.txt`)
- Vérifier les sélecteurs LinkedIn (dashboard → Sélecteurs)

### Trimestrielle

- Audit de sécurité
- Review des messages
- Optimisation des requêtes BDD
- Backup complet

---

## 📚 Ressources

### Documentation

- [README.md](README.md) - Vue d'ensemble
- [PHASE1.md](PHASE1.md) - Fonctionnalités Phase 1
- [AUDIT.md](AUDIT.md) - Audit complet
- [BUGFIXES.md](BUGFIXES.md) - Corrections appliquées
- [SECURITY_IMPROVEMENTS.md](SECURITY_IMPROVEMENTS.md) - Sécurité anti-détection

### Liens Utiles

- [Playwright Docs](https://playwright.dev/python/)
- [Flask Docs](https://flask.palletsprojects.com/)
- [SQLite WAL](https://www.sqlite.org/wal.html)
- [GitHub Actions](https://docs.github.com/en/actions)

### Support

- **Issues:** https://github.com/GaspardD78/linkedin-birthday-auto/issues
- **Discussions:** https://github.com/GaspardD78/linkedin-birthday-auto/discussions

---

## ⚠️ Avertissements

### Légal

- ⚠️ L'automatisation viole les ToS de LinkedIn
- ⚠️ Risque de suspension de compte (temporaire ou permanente)
- ⚠️ Utiliser à vos propres risques

### Recommandations

- Commencer en mode DRY_RUN
- Limiter à 10-15 messages/jour
- Varier les horaires d'exécution
- Ne pas exécuter tous les jours
- Surveiller les notifications LinkedIn

---

**Dernière mise à jour:** 2025-01-19
**Version:** 2.1.0
