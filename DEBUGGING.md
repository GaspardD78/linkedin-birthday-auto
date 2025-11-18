# 🔧 Système de Debugging Avancé

Le script LinkedIn Birthday Wisher inclut maintenant un système complet de debugging et monitoring pour détecter les changements de LinkedIn et les problèmes potentiels.

## 🎯 Fonctionnalités

### 1. **Captures d'écran Automatiques**
- Screenshots à chaque étape critique de l'exécution
- Screenshots d'erreur avec préfixe `ERROR_`
- Stockage organisé dans `debug_screenshots/` avec timestamps

### 2. **Validation de Structure DOM**
- Vérifie que tous les sélecteurs LinkedIn critiques sont valides
- Détecte les changements de structure du site
- Génère un rapport JSON : `dom_validation_report.json`

### 3. **Détection de Restrictions**
- Détecte automatiquement les CAPTCHAs
- Identifie les rate limits
- Repère les suspensions de compte
- Arrête le script avant d'aggraver la situation

### 4. **Logging Enrichi**
- Logs détaillés avec numéro de ligne et fonction
- Fichier de log séparé : `linkedin_bot_detailed.log`
- Contexte complet pour chaque action

### 5. **Système d'Alertes Email**
- Notifications par email en cas d'erreur critique
- Attache automatiquement screenshots et logs
- Configurable via variables d'environnement

## 🚀 Activation du Mode Debug

### Configuration de base

Pour activer le debugging avancé, définis ces variables d'environnement :

```bash
export ENABLE_ADVANCED_DEBUG=true
```

### Configuration complète avec alertes email

```bash
export ENABLE_ADVANCED_DEBUG=true
export ENABLE_EMAIL_ALERTS=true

# Configuration email (Gmail example)
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export ALERT_EMAIL=your-email@gmail.com
export ALERT_EMAIL_PASSWORD=your-app-password
export RECIPIENT_EMAIL=your-notification-email@gmail.com
```

### Dans GitHub Actions

Ajoute ces secrets dans ton repository :

```yaml
env:
  ENABLE_ADVANCED_DEBUG: 'true'
  ENABLE_EMAIL_ALERTS: 'true'
  SMTP_SERVER: 'smtp.gmail.com'
  SMTP_PORT: '587'
  ALERT_EMAIL: ${{ secrets.ALERT_EMAIL }}
  ALERT_EMAIL_PASSWORD: ${{ secrets.ALERT_EMAIL_PASSWORD }}
  RECIPIENT_EMAIL: ${{ secrets.RECIPIENT_EMAIL }}
```

## 📊 Interprétation des Résultats

### Structure des Screenshots

Les screenshots sont nommés selon le pattern :
```
[TYPE]_[SESSION_ID]_[TIME]_[STEP_NAME].png
```

**Exemples :**
- `DEBUG_20250118_143022_103045_01_browser_start.png` - Screenshot normal
- `ERROR_20250118_143022_105234_policy_violation_critical.png` - Erreur critique

### Types de Screenshots

| Étape | Description |
|-------|-------------|
| `01_browser_start` | Démarrage initial |
| `02_after_login` | Après connexion LinkedIn |
| `03_birthdays_page_loaded` | Page anniversaires chargée |
| `policy_violation_*` | Violation de politique détectée |
| `selector_failed_*` | Échec de validation de sélecteur |
| `error_timeout` | Timeout Playwright |
| `error_unexpected` | Erreur inattendue |
| `99_execution_completed` | Exécution terminée avec succès |

### Rapport de Validation DOM

Le fichier `dom_validation_report.json` contient :

```json
{
  "timestamp": "2025-01-18T14:30:45.123456",
  "overall_status": "PASS",
  "selectors": {
    "birthday_card": {
      "selector": "div[role='listitem']",
      "found": true,
      "visible": true,
      "count": 15,
      "status": "✅"
    },
    "message_button": {
      "selector": "button.artdeco-button--secondary",
      "found": false,
      "error": "Element not found",
      "status": "❌"
    }
  }
}
```

**Actions selon le statut :**
- ✅ `PASS` : Tout fonctionne normalement
- ❌ `FAIL` : LinkedIn a changé sa structure → Vérifier les sélecteurs

### Rapport de Restrictions

Le fichier `restriction_alert.json` est créé si une restriction est détectée :

```json
{
  "timestamp": "2025-01-18T14:35:12.789012",
  "issues": [
    {
      "type": "captcha",
      "keyword": "verify you're human",
      "severity": "CRITICAL"
    }
  ],
  "action_required": "STOP_SCRIPT"
}
```

**Sévérités :**
- `CRITICAL` : Arrêt immédiat requis (CAPTCHA, suspension)
- `WARNING` : À surveiller (rate limit approché)

## 🛠️ Utilisation Pratique

### Mode Debug Local

Pour tester localement avec debug complet :

```bash
export ENABLE_ADVANCED_DEBUG=true
export DRY_RUN=true
export HEADLESS_BROWSER=false

python linkedin_birthday_wisher.py
```

### Analyser les Logs après Exécution

```bash
# Voir les erreurs critiques
grep "ERROR\|CRITICAL" linkedin_bot_detailed.log

# Voir les validations DOM
grep "Validating DOM" linkedin_bot_detailed.log

# Voir les restrictions détectées
grep "restriction\|captcha\|rate limit" -i linkedin_bot_detailed.log
```

### Diagnostic Rapide

Le module inclut une fonction de diagnostic rapide :

```python
from debug_utils import quick_debug_check

# Dans ton code après avoir ouvert LinkedIn
quick_debug_check(page)
```

Affiche immédiatement :
```
==================================================
🔍 QUICK DEBUG CHECK
==================================================
✅ Page URL: https://www.linkedin.com/mynetwork/...
✅ Page Title: Birthday | LinkedIn
✅ Birthday cards found: 12
❌ Message button visible: False
✅ Send button exists: True
==================================================
```

## 🔍 Détection Proactive des Problèmes

### Vérifications Automatiques

Le système effectue ces vérifications automatiquement :

1. **Au démarrage :**
   - Validation de la connexion
   - Validation de la structure DOM
   - Détection de restrictions

2. **Toutes les 5 messages :**
   - Vérification de restrictions en temps réel
   - Arrêt automatique si problème détecté

3. **À chaque erreur :**
   - Screenshot automatique
   - Log détaillé
   - Email d'alerte (si activé)

### Signaux d'Alerte LinkedIn

Le système détecte ces indicateurs :

**CAPTCHA :**
- "captcha"
- "verify you're human"
- "security check"

**Rate Limit :**
- "you've reached"
- "slow down"
- "try again later"
- "too many"

**Restriction de Compte :**
- "restricted"
- "suspended"
- "violation"
- "unusual activity"

## 📧 Configuration Email (Gmail)

### 1. Créer un App Password

1. Va sur https://myaccount.google.com/security
2. Active la vérification en 2 étapes
3. Cherche "App passwords"
4. Crée un mot de passe pour "Mail"
5. Utilise ce mot de passe (pas ton mot de passe Gmail)

### 2. Variables d'Environnement

```bash
export ALERT_EMAIL=your-gmail@gmail.com
export ALERT_EMAIL_PASSWORD=your-16-char-app-password
export RECIPIENT_EMAIL=where-to-send-alerts@gmail.com
```

### 3. Test de Configuration

Crée un fichier `test_email.py` :

```python
from debug_utils import AlertSystem

alert = AlertSystem()
success = alert.send_alert(
    "Test Alert",
    "Si tu reçois cet email, les alertes fonctionnent !"
)

print("✅ Email envoyé !" if success else "❌ Échec d'envoi")
```

```bash
python test_email.py
```

## 🐛 Résolution de Problèmes Courants

### "ModuleNotFoundError: No module named 'debug_utils'"

Assure-toi que `debug_utils.py` est dans le même dossier que `linkedin_birthday_wisher.py`.

### "Email alerts not working"

Vérifications :
1. App password Gmail (pas le mot de passe normal)
2. Variables d'environnement correctement définies
3. `ENABLE_EMAIL_ALERTS=true`

### "Too many screenshots filling disk"

Les screenshots s'accumulent dans `debug_screenshots/`. Nettoyage :

```bash
# Garder seulement les 7 derniers jours
find debug_screenshots/ -name "*.png" -mtime +7 -delete

# Garder seulement les erreurs
find debug_screenshots/ -name "DEBUG_*.png" -delete
```

### "DOM validation always fails"

LinkedIn a probablement changé sa structure. Mets à jour les sélecteurs dans `debug_utils.py` :

```python
CRITICAL_SELECTORS = {
    'birthday_card': "NEW_SELECTOR_HERE",
    # ...
}
```

## 📈 Métriques de Performance

Le système de debug a un impact minimal :

- **Overhead mémoire** : ~5-10 MB (screenshots)
- **Overhead temps** : ~2-3 secondes par session
- **Taille logs** : ~100-500 KB par exécution

Pour une performance optimale en production, désactive le debug avancé :

```bash
export ENABLE_ADVANCED_DEBUG=false
```

Les fonctionnalités de sécurité (délais gaussiens, pauses longues, simulation d'activité) restent actives.

## 🔒 Sécurité

**⚠️ Important :**

- Ne committe **JAMAIS** les fichiers de log ou screenshots dans Git
- Ajoute au `.gitignore` :
  ```
  debug_screenshots/
  *.log
  *_report.json
  *_alert.json
  ```

- Les emails d'alerte peuvent contenir des informations sensibles
- Utilise des App Passwords Gmail (jamais ton mot de passe principal)

## 📚 Références des Classes

### `DebugScreenshotManager`
```python
manager = DebugScreenshotManager(debug_dir="custom_folder")
manager.capture(page, "step_name", error=False)
manager.capture_element(page, "css_selector", "element_name")
```

### `DOMStructureValidator`
```python
validator = DOMStructureValidator(page)
is_valid = validator.validate_all_selectors(screenshot_mgr)
report = validator.export_validation_report()
```

### `LinkedInPolicyDetector`
```python
detector = LinkedInPolicyDetector(page)
is_ok, issues = detector.check_for_restrictions(screenshot_mgr)
send_success = detector.check_message_sent_successfully()
```

### `AlertSystem`
```python
alerts = AlertSystem()
alerts.send_alert("Subject", "Body", attach_files=["file.png"])
alerts.alert_policy_violation(issues, screenshot_path)
```

## 🎓 Bonnes Pratiques

1. **Active le debug avancé pour les 2 premières semaines**
   - Détecte rapidement les problèmes
   - Vérifie la stabilité des sélecteurs

2. **Désactive en production stable**
   - Réduit les logs
   - Économise l'espace disque

3. **Configure les alertes email**
   - Sois notifié immédiatement des problèmes
   - Même si GitHub Actions échoue silencieusement

4. **Révise les logs mensuellement**
   - Cherche des patterns d'échec
   - Anticipe les changements LinkedIn

5. **Sauvegarde les screenshots d'erreur**
   - Utile pour déboguer a posteriori
   - Peut servir de preuve si LinkedIn change sans préavis

## 🆘 Support

En cas de problème avec le système de debugging :

1. Vérifie que Python >= 3.10
2. Vérifie que Playwright est bien installé
3. Consulte les logs détaillés
4. Ouvre une issue GitHub avec :
   - Le message d'erreur complet
   - Un screenshot de l'erreur (si possible)
   - Le contenu de `linkedin_bot_detailed.log`
