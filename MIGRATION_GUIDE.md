# Guide de Migration vers v2.0

Ce guide vous aide à migrer de l'ancienne architecture vers la nouvelle version 2.0 modulaire.

## ⚠️ Important

**Les anciens scripts continuent de fonctionner !**

La nouvelle architecture coexiste avec l'ancienne. Vous pouvez migrer progressivement :
- `linkedin_birthday_wisher.py` → continue de fonctionner
- `linkedin_birthday_wisher_unlimited.py` → continue de fonctionner
- Nouvelle API → disponible en parallèle

---

## Changements principaux

### 1. Configuration centralisée

**Avant (v1.x)** :
```python
# Configuration dispersée dans le code
HEADLESS_BROWSER = True
DRY_RUN = os.getenv('DRY_RUN', 'false')
WEEKLY_MESSAGE_LIMIT = 80
# ... etc.
```

**Après (v2.0)** :
```yaml
# config/config.yaml - Configuration centralisée
bot_mode: "standard"
dry_run: false

browser:
  headless: true

messaging_limits:
  weekly_message_limit: 80
```

### 2. Variables d'environnement standardisées

**Avant** :
```bash
export DRY_RUN=true
export ENABLE_ADVANCED_DEBUG=true
```

**Après** :
```bash
export LINKEDIN_BOT_DRY_RUN=true
export LINKEDIN_BOT_DEBUG_ADVANCED_DEBUG=true
```

Toutes les variables commencent par `LINKEDIN_BOT_` pour éviter les conflits.

### 3. Point d'entrée unifié

**Avant** :
```bash
python linkedin_birthday_wisher.py
python linkedin_birthday_wisher_unlimited.py
```

**Après** :
```bash
# Mode standard
python main_example.py

# Mode personnalisé avec config
LINKEDIN_BOT_CONFIG_PATH=./config/my_config.yaml python main_example.py
```

---

## Migration étape par étape

### Étape 1 : Installation des nouvelles dépendances

```bash
# Installer les nouvelles dépendances
pip install -r requirements-new.txt

# Installer Playwright browsers
playwright install chromium
```

### Étape 2 : Créer votre fichier de configuration

```bash
# Copier le template
cp config/config.yaml config/my_config.yaml

# Éditer selon vos besoins
nano config/my_config.yaml
```

### Étape 3 : Migrer vos variables d'environnement

Créez un fichier `.env` :

```bash
# Ancienne variable (toujours supportée)
LINKEDIN_AUTH_STATE=<votre_auth_state>

# Nouvelles variables (optionnelles, overrides)
LINKEDIN_BOT_DRY_RUN=false
LINKEDIN_BOT_BROWSER_HEADLESS=true
LINKEDIN_BOT_DEBUG_LOG_LEVEL=INFO
```

### Étape 4 : Tester la nouvelle configuration

```bash
# Test avec dry-run
LINKEDIN_BOT_DRY_RUN=true python main_example.py

# Vérifier les logs
tail -f logs/linkedin_bot.log
```

### Étape 5 : Migration progressive

**Option A : Utiliser les anciens scripts (recommandé pour la transition)**
```bash
# Continue de fonctionner comme avant
python linkedin_birthday_wisher.py
```

**Option B : Migrer vers la nouvelle API (quand prête)**
```python
# Quand BirthdayBot sera implémenté
from src.bots.birthday_bot import BirthdayBot

with BirthdayBot() as bot:
    results = bot.run()
```

---

## Correspondance des configurations

| Ancienne variable | Nouvelle config YAML | Variable env override |
|-------------------|---------------------|----------------------|
| `HEADLESS_BROWSER` | `browser.headless` | `LINKEDIN_BOT_BROWSER_HEADLESS` |
| `DRY_RUN` | `dry_run` | `LINKEDIN_BOT_DRY_RUN` |
| `WEEKLY_MESSAGE_LIMIT` | `messaging_limits.weekly_message_limit` | `LINKEDIN_BOT_MESSAGING_LIMITS_WEEKLY_MESSAGE_LIMIT` |
| `DAILY_START_HOUR` | `scheduling.daily_start_hour` | `LINKEDIN_BOT_SCHEDULING_DAILY_START_HOUR` |
| `DAILY_END_HOUR` | `scheduling.daily_end_hour` | `LINKEDIN_BOT_SCHEDULING_DAILY_END_HOUR` |
| `MIN_DELAY_SECONDS` | `delays.min_delay_seconds` | `LINKEDIN_BOT_DELAYS_MIN_DELAY_SECONDS` |
| `MAX_DELAY_SECONDS` | `delays.max_delay_seconds` | `LINKEDIN_BOT_DELAYS_MAX_DELAY_SECONDS` |

---

## Nouveautés de la v2.0

### 1. Validation de configuration

La configuration est maintenant validée automatiquement au démarrage :

```python
from src.config import get_config

config = get_config()
# ✅ Configuration garantie valide ou erreur au démarrage
```

### 2. Gestion d'erreurs améliorée

```python
from src.utils.exceptions import LinkedInBotError, is_critical_error

try:
    bot.run()
except LinkedInBotError as e:
    if is_critical_error(e):
        # Erreur critique (session expirée, compte restreint)
        notify_admin(e)
    elif e.recoverable:
        # Erreur récupérable (timeout, element not found)
        retry_with_backoff(e.retry_after)
```

### 3. Context managers

Cleanup automatique des ressources :

```python
with BrowserManager() as manager:
    # ... utilisation
# Browser fermé automatiquement

with AuthManager() as auth:
    # ... utilisation
# Fichiers temporaires nettoyés
```

### 4. Statistiques enrichies

```python
from src.core.database import get_database

db = get_database()
stats = db.get_statistics(days=30)

print(f"Messages envoyés : {stats['messages']['total']}")
print(f"Taux de succès : {stats['messages']['on_time']}")
print(f"Contacts uniques : {stats['contacts']['unique']}")
```

---

## FAQ Migration

### Q: Mes scripts actuels vont-ils continuer de fonctionner ?

**R:** Oui ! Les anciens scripts restent totalement fonctionnels. La nouvelle architecture est ajoutée en parallèle.

### Q: Dois-je migrer immédiatement ?

**R:** Non. Vous pouvez migrer progressivement quand vous êtes prêt. Les deux versions coexistent.

### Q: Que devient mon auth_state.json ?

**R:** Il reste valide et est utilisé automatiquement par le nouvel AuthManager.

### Q: Mes messages.txt et late_messages.txt ?

**R:** Ils restent utilisés. Vous pouvez les configurer dans `config.yaml` :
```yaml
messages:
  messages_file: "messages.txt"
  late_messages_file: "late_messages.txt"
```

### Q: Mon fichier proxy_config.json ?

**R:** Il reste compatible. Configurez le chemin dans `config.yaml` :
```yaml
proxy:
  enabled: true
  config_file: "proxy_config.json"
```

### Q: La base de données linkedin_automation.db ?

**R:** Elle reste utilisée et est compatible avec la nouvelle version.

### Q: Comment activer le mode debug ?

**R:** Plusieurs options :

```bash
# Via variable d'environnement
LINKEDIN_BOT_DEBUG_LOG_LEVEL=DEBUG python main_example.py

# Via config.yaml
debug:
  log_level: "DEBUG"
  advanced_debug: true
```

### Q: Comment tester la nouvelle architecture sans risque ?

**R:** Utilisez le mode dry-run :

```bash
# Test sans envoyer de messages
LINKEDIN_BOT_DRY_RUN=true python main_example.py
```

---

## Checklist de migration

- [ ] Installer nouvelles dépendances (`pip install -r requirements-new.txt`)
- [ ] Créer `config/my_config.yaml` avec vos paramètres
- [ ] Tester avec `LINKEDIN_BOT_DRY_RUN=true`
- [ ] Vérifier les logs dans `logs/linkedin_bot.log`
- [ ] Valider que l'auth fonctionne
- [ ] Tester en mode réel sur quelques contacts
- [ ] Monitorer les premiers runs
- [ ] Migrer vos cron jobs / GitHub Actions (optionnel)

---

## Support

### Documentation

- **Architecture** : Voir [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Configuration** : Voir [config/config.yaml](./config/config.yaml)
- **Code source** : Voir [src/](./src/)

### Problèmes courants

#### Erreur : "No valid authentication found"
```bash
# Solution : Vérifier que auth_state.json existe ou que LINKEDIN_AUTH_STATE est défini
ls -la auth_state.json
echo $LINKEDIN_AUTH_STATE
```

#### Erreur : "Configuration validation failed"
```bash
# Solution : Vérifier la syntaxe YAML
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
```

#### Erreur : "Module not found"
```bash
# Solution : Installer les dépendances
pip install -r requirements-new.txt
```

---

## Retour en arrière

Si vous rencontrez des problèmes avec la v2.0, vous pouvez facilement revenir à v1.x :

```bash
# Les anciens scripts sont toujours là
python linkedin_birthday_wisher.py

# Ou via git
git checkout <ancien_commit>
```

**Note** : Aucune donnée n'est perdue lors de la migration. La base de données reste compatible.

---

**Version du guide** : 1.0
**Date** : 2025-11-22
**Compatible avec** : LinkedIn Birthday Bot v2.0+
