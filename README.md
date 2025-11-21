# 🍓 LinkedIn Birthday Bot pour Raspberry Pi

Bot automatique pour souhaiter les anniversaires de vos contacts LinkedIn, optimisé pour fonctionner 24/7 sur **Raspberry Pi**.

## ✨ Fonctionnalités

- ✅ **Détection automatique** des anniversaires du jour et en retard (jusqu'à 10 jours)
- ✅ **Messages personnalisés** avec rotation aléatoire et mémorisation
- ✅ **Comportement humain** : délais aléatoires, mouvements de souris, scrolling naturel
- ✅ **Base de données SQLite** : historique complet des messages envoyés
- ✅ **Dashboard Web** : visualisation en temps réel via interface Flask
- ✅ **Gestion intelligente** : évite les doublons, adapte les messages selon l'historique
- ✅ **Support 2FA** : authentification via fichier `auth_state.json`
- ✅ **Correction automatique** : gestion des modales multiples et erreurs DOM

## 🎯 Pourquoi Raspberry Pi ?

| Critère | Raspberry Pi | Cloud (GitHub Actions) |
|---------|--------------|------------------------|
| **IP** | ✅ Résidentielle légitime | ❌ Datacenter détectable |
| **Détection LinkedIn** | ✅ Impossible | ⚠️ Risque élevé |
| **Coût mensuel** | ✅ ~1€ d'électricité | ⚠️ Nécessite proxies payants |
| **Configuration** | ✅ Une fois pour toutes | ⚠️ Secrets à maintenir |
| **Disponibilité** | ✅ 24/7 garanti | ⚠️ Dépend de GitHub |
| **Contrôle** | ✅ Total | ⚠️ Limité |

## 🚀 Installation Rapide

```bash
# 1. Cloner le projet
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# 2. Installer les dépendances
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium

# 3. Générer l'authentification (avec support 2FA)
python3 generate_auth_simple.py

# 4. Configurer l'environnement
cat > .env << EOF
# Authentification (utilisée uniquement si auth_state.json n'existe pas)
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=VotreMotDePasse123

# Mode
DRY_RUN=true  # false pour envoyer vraiment les messages
HEADLESS_BROWSER=true

# Proxies (désactivé pour IP locale)
ENABLE_PROXY_ROTATION=false
EOF

# 5. Sécuriser .env
chmod 600 .env

# 6. Tester le bot
python3 linkedin_birthday_wisher.py
```

## 📋 Configuration Détaillée

### 1. Génération de auth_state.json (avec 2FA)

Le script `generate_auth_simple.py` simplifie l'authentification LinkedIn :

```bash
python3 generate_auth_simple.py
```

**Ce script va :**
1. Ouvrir un navigateur Chromium
2. Vous rediriger vers la page de connexion LinkedIn
3. Attendre que vous vous connectiez (email, mot de passe, **code 2FA**)
4. Sauvegarder votre session dans `auth_state.json`

**Avantages :**
- ✅ Plus besoin de saisir le code 2FA à chaque exécution
- ✅ Session valide pendant plusieurs semaines/mois
- ✅ Compatible avec tous les types d'authentification LinkedIn

**Si la session expire :**
```bash
rm auth_state.json
python3 generate_auth_simple.py
```

### 2. Fichiers de Configuration

#### `.env` - Variables d'environnement

```bash
# AUTHENTIFICATION
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=VotreMotDePasse123

# Si auth_state.json existe, ces identifiants ne sont utilisés que pour le fallback

# MODE DE TEST
DRY_RUN=true  # true = test (affiche sans envoyer), false = production

# NAVIGATEUR
HEADLESS_BROWSER=true  # false pour voir le navigateur (debug)

# PROXIES (optionnel)
ENABLE_PROXY_ROTATION=false
# Pour activer :
# ENABLE_PROXY_ROTATION=true
# PROXY_LIST=["http://user:pass@proxy1.com:8080", "http://user:pass@proxy2.com:8080"]

# DEBUG AVANCÉ (optionnel)
# ENABLE_ADVANCED_DEBUG=false
# SCREENSHOT_ON_ERROR=true
```

#### `messages.txt` - Messages d'anniversaire

```text
Joyeux anniversaire, {name} ! J'espère que tu passes une excellente journée.
Bon anniversaire {name} ! 🎉
Hello {name}, happy birthday!
Un grand bonjour et un excellent anniversaire {name} ! 🎂
```

Le placeholder `{name}` sera automatiquement remplacé par le prénom du contact.

#### `late_messages.txt` - Messages pour anniversaires en retard

```text
Bonjour {name}, joyeux anniversaire avec un peu de retard ! 🎂
{name}, j'espère que tu as passé un super anniversaire ! 🎉
Meilleurs vœux d'anniversaire {name}, même s'ils arrivent un peu tard !
```

### 3. Personnalisation du Comportement

Éditez `config.json` pour le script `visit_profiles.py` (optionnel) :

```json
{
  "keywords": ["Azure", "DevOps", "Cloud"],
  "location": "Ile-de-France",
  "limits": {
    "profiles_per_run": 15,
    "max_pages_to_scrape": 100
  },
  "delays": {
    "min_seconds": 8,
    "max_seconds": 20,
    "profile_visit_min": 15,
    "profile_visit_max": 55
  },
  "timezone": {
    "start_hour": 7,
    "end_hour": 20
  }
}
```

## 🤖 Automatisation avec Cron

### Créer le Script de Lancement

```bash
nano ~/linkedin-birthday-auto/run.sh
```

```bash
#!/bin/bash
PROJECT_DIR="/home/pi/linkedin-birthday-auto"
LOG_FILE="$PROJECT_DIR/logs/cron.log"

mkdir -p "$PROJECT_DIR/logs"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Démarrage du bot" | tee -a "$LOG_FILE"

cd "$PROJECT_DIR" || exit 1
source "$PROJECT_DIR/venv/bin/activate"

export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)

python3 "$PROJECT_DIR/linkedin_birthday_wisher.py" 2>&1 | tee -a "$LOG_FILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Fin d'exécution" | tee -a "$LOG_FILE"
```

```bash
chmod +x ~/linkedin-birthday-auto/run.sh
```

### Configurer Cron

```bash
crontab -e
```

Ajouter :

```bash
# Exécution tous les jours à 8h30
30 8 * * * /home/pi/linkedin-birthday-auto/run.sh

# Alternative : Heure aléatoire entre 8h et 10h (plus naturel)
# 0 8 * * * sleep $((RANDOM \% 7200)) && /home/pi/linkedin-birthday-auto/run.sh
```

## 📊 Dashboard Web (Optionnel)

Surveillez l'activité du bot via une interface web :

```bash
# Lancer le dashboard
python3 dashboard_app.py

# Accessible sur http://raspberrypi.local:5000
```

**Fonctionnalités du dashboard :**
- 📈 Statistiques en temps réel
- 📅 Historique des messages envoyés
- 🔍 Recherche par contact ou date
- 📊 Graphiques de performance

## 🔧 Maintenance

### Consulter les Logs

```bash
# Logs de cron
tail -f ~/linkedin-birthday-auto/logs/cron.log

# Base de données SQLite
sqlite3 ~/linkedin-birthday-auto/linkedin_birthday.db

# Voir les derniers messages envoyés
sqlite3 ~/linkedin-birthday-auto/linkedin_birthday.db \
  "SELECT * FROM birthday_messages ORDER BY timestamp DESC LIMIT 10;"
```

### Sauvegardes Automatiques

Créer `backup.sh` :

```bash
#!/bin/bash
BACKUP_DIR="/home/pi/linkedin-birthday-auto/backups"
mkdir -p "$BACKUP_DIR"

BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).db"
cp ~/linkedin-birthday-auto/linkedin_birthday.db "$BACKUP_FILE"

# Garder seulement les 30 dernières sauvegardes
cd "$BACKUP_DIR"
ls -t | tail -n +31 | xargs -r rm --

echo "[$(date)] Sauvegarde créée : $BACKUP_FILE"
```

```bash
chmod +x backup.sh
```

Ajouter au crontab (hebdomadaire) :

```bash
# Sauvegarde hebdomadaire le dimanche à minuit
0 0 * * 0 /home/pi/linkedin-birthday-auto/backup.sh
```

### Mise à Jour du Bot

Utilisez simplement le script de mise à jour automatique :

```bash
./update_bot.sh
```

Ou manuellement :

```bash
cd ~/linkedin-birthday-auto
git pull origin main
source venv/bin/activate
pip install --upgrade -r requirements.txt
playwright install chromium
```

## 🐛 Dépannage

### Le bot ne détecte pas les anniversaires

```bash
# Tester la connexion
python3 linkedin_birthday_wisher.py

# Vérifier auth_state.json
ls -la auth_state.json

# Régénérer l'authentification
rm auth_state.json
python3 generate_auth_simple.py
```

### Erreur "Element is not attached to the DOM"

✅ **Corrigé automatiquement !**

Le bot détecte maintenant les modales multiples et :
1. Ferme toutes les modales ouvertes
2. Re-recherche le bouton Message (évite le détachement DOM)
3. Ré-ouvre la modale proprement
4. Continue le traitement

### Erreur de mémoire sur Raspberry Pi 2GB

```bash
# Augmenter la swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Modifier : CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Températures élevées

```bash
# Vérifier la température
vcgencmd measure_temp

# Si > 75°C, installer un ventilateur ou boîtier avec dissipateur
```

## 📚 Documentation Complète

Pour un guide pas-à-pas ultra-détaillé :

**[📖 RASPBERRY_PI4_GUIDE.md](RASPBERRY_PI4_GUIDE.md)** - Guide complet d'installation sur Raspberry Pi 4

**Contenu :**
- ✅ Installation Raspberry Pi OS
- ✅ Configuration initiale
- ✅ Installation du bot
- ✅ Gestion du 2FA (4 méthodes détaillées)
- ✅ Automatisation avec cron
- ✅ Monitoring et maintenance
- ✅ Optimisations performances
- ✅ Dépannage complet

**Autres guides :**
- [DEBUGGING.md](DEBUGGING.md) - Guide de débogage avancé
- [SCRIPTS_USAGE.md](SCRIPTS_USAGE.md) - Utilisation des scripts auxiliaires
- [PROXY_FREE_TRIALS_GUIDE.md](PROXY_FREE_TRIALS_GUIDE.md) - Guide des essais gratuits de proxies (optionnel)

## 🔒 Sécurité

- ✅ Fichier `.env` avec permissions `600` (lecture seule par vous)
- ✅ `auth_state.json` jamais commité dans Git (dans `.gitignore`)
- ✅ Pas de mot de passe en clair dans le code
- ✅ Base de données locale uniquement
- ✅ Pas de transmission de données à des tiers

## 🆘 Support

En cas de problème :

1. **Consultez les logs** : `tail -f logs/cron.log`
2. **Testez manuellement** : `python3 linkedin_birthday_wisher.py`
3. **Vérifiez les issues GitHub** : [github.com/GaspardD78/linkedin-birthday-auto/issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)
4. **Consultez le guide détaillé** : [RASPBERRY_PI4_GUIDE.md](RASPBERRY_PI4_GUIDE.md)

## 📜 Licence

Ce projet est fourni "tel quel", sans garantie d'aucune sorte.

Utilisation à vos propres risques. LinkedIn peut détecter et bloquer l'automatisation.

**Recommandations :**
- ⚠️ Limitez à 20-30 messages/jour maximum
- ⚠️ Utilisez votre propre IP résidentielle (Raspberry Pi)
- ⚠️ Variez les messages et les horaires
- ⚠️ Ne sur-automatisez pas

## 🎉 Améliorations Récentes

### ✅ Version 2.0 - Corrections Majeures

**Bugs corrigés :**

1. **🐛 Bug des modales multiples**
   - **Problème** : Erreur "Element is not attached to the DOM" lors de modales multiples
   - **Solution** : Détection automatique, fermeture de toutes les modales, re-recherche du bouton
   - **Résultat** : Plus d'erreurs de détachement DOM

2. **⏱️ Attente inutile après skip**
   - **Problème** : Pause de 3-4 minutes même quand le contact est skippé (pas de bouton Message)
   - **Solution** : Pause de 1-3 secondes uniquement pour les skips
   - **Résultat** : Script 10x plus rapide lors de contacts sans bouton

**Fonctionnalités ajoutées :**

3. **🔐 Script d'authentification simplifié**
   - **Nouveau** : `generate_auth_simple.py`
   - **Avantage** : Interface guidée, support 2FA natif, aucune configuration complexe

---

**Conçu avec ❤️ pour Raspberry Pi**
