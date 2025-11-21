# 🍓 Guide Complet d'Installation sur Raspberry Pi 4

Guide pas-à-pas ultra-détaillé pour installer le bot LinkedIn Birthday sur un Raspberry Pi 4. Ce guide part de zéro et vous accompagne jusqu'à l'automatisation complète.

---

## 📋 Table des Matières

1. [Prérequis](#prérequis)
2. [Installation du Raspberry Pi OS](#installation-du-raspberry-pi-os)
3. [Configuration Initiale](#configuration-initiale)
4. [Installation du Bot](#installation-du-bot)
5. [Configuration et Test](#configuration-et-test)
6. [Automatisation](#automatisation)
7. [Surveillance et Maintenance](#surveillance-et-maintenance)
8. [Optimisations](#optimisations)
9. [Dépannage](#dépannage)

---

## 🎯 Prérequis

### Matériel Requis

**Raspberry Pi 4 - Configuration Recommandée :**
- ✅ **Raspberry Pi 4 Model B - 2GB RAM minimum** (4GB ou 8GB recommandé)
- ✅ **Carte microSD 32GB** (Classe 10 ou UHS-I pour de meilleures performances)
- ✅ **Alimentation USB-C 5V/3A** officielle Raspberry Pi
- ✅ **Câble Ethernet** (recommandé) ou WiFi
- ⚪ Boîtier avec ventilateur (optionnel mais recommandé)
- ⚪ Clavier, souris et écran HDMI pour la configuration initiale

**Budget Total :** ~60-90€ selon la configuration

### Avantages du Raspberry Pi 4

| Critère | Raspberry Pi 4 | NAS DS213J | PC Windows |
|---------|---------------|------------|------------|
| **RAM** | ✅ 2-8 GB | ❌ 512 MB | ✅ 4-16 GB |
| **CPU** | ✅ ARM Cortex-A72 64-bit | ❌ ARMv7 32-bit | ✅ x86-64 |
| **Chromium** | ✅ Compatible | ❌ Non supporté | ✅ Compatible |
| **Consommation** | ✅ 3-5W (~1€/mois) | ✅ 3W | ❌ 50-100W (~15€/mois) |
| **Bruit** | ✅ Silencieux | ✅ Silencieux | ⚠️ Ventilateurs |
| **Prix** | ✅ 60-90€ | N/A | ✅ Déjà possédé |
| **Disponibilité 24/7** | ✅ Idéal | ✅ Idéal | ⚠️ Gaspillage d'énergie |

---

## 💿 Installation du Raspberry Pi OS

### Étape 1 : Télécharger Raspberry Pi Imager

Sur votre ordinateur Windows/Mac/Linux :

1. Téléchargez **Raspberry Pi Imager** : https://www.raspberrypi.com/software/
2. Installez l'application
3. Insérez votre carte microSD dans votre ordinateur

### Étape 2 : Flasher la Carte SD

1. **Lancez Raspberry Pi Imager**
2. **Choisir le modèle** : Sélectionnez "Raspberry Pi 4"
3. **Choisir l'OS** :
   - Cliquez sur "Choose OS"
   - Sélectionnez **"Raspberry Pi OS (64-bit)"** (recommandé)
   - Ou **"Raspberry Pi OS Lite (64-bit)"** si vous n'avez pas besoin d'interface graphique
4. **Choisir le stockage** : Sélectionnez votre carte microSD

### Étape 3 : Configuration Avancée (IMPORTANT)

1. Cliquez sur l'icône **⚙️ (Paramètres)** en bas à droite
2. **Configurez les paramètres suivants** :

```
┌─────────────────────────────────────────┐
│ Paramètres OS (personnalisés)          │
├─────────────────────────────────────────┤
│ [✓] Activer SSH                         │
│     ⚪ Utiliser authentification mdp    │
│                                         │
│ [✓] Définir nom utilisateur et mdp      │
│     Utilisateur : pi                    │
│     Mot de passe : ************         │
│                                         │
│ [✓] Configurer WiFi                     │
│     SSID : VotreWiFi                    │
│     Mot de passe : ************         │
│     Pays : FR                           │
│                                         │
│ [✓] Définir paramètres régionaux        │
│     Fuseau horaire : Europe/Paris       │
│     Clavier : fr                        │
└─────────────────────────────────────────┘
```

3. Cliquez sur **"Sauvegarder"**
4. Cliquez sur **"Écrire"** puis confirmez
5. Attendez la fin du processus (5-10 minutes)

### Étape 4 : Premier Démarrage

1. Retirez la carte microSD de votre ordinateur
2. Insérez-la dans le Raspberry Pi
3. Branchez le câble Ethernet (recommandé) ou utilisez le WiFi
4. Branchez l'alimentation USB-C
5. Le Raspberry Pi démarre automatiquement (LED verte clignote)
6. Attendez 2-3 minutes pour le premier démarrage

---

## 🔧 Configuration Initiale

### Étape 5 : Se Connecter au Raspberry Pi

#### Option A : Connexion SSH (Recommandé - Sans Écran)

**Sur Windows :**
1. Ouvrez **PowerShell** ou **CMD**
2. Tapez :
```powershell
ssh pi@raspberrypi.local
```

**Sur Mac/Linux :**
1. Ouvrez le **Terminal**
2. Tapez :
```bash
ssh pi@raspberrypi.local
```

Si `raspberrypi.local` ne fonctionne pas, trouvez l'IP du Raspberry Pi :
- Sur votre box internet, consultez la liste des appareils connectés
- Ou utilisez un scanner réseau comme **Fing** (application mobile)

```bash
ssh pi@192.168.1.X
```

3. Acceptez la clé SSH (tapez `yes`)
4. Entrez le mot de passe configuré à l'étape 3

#### Option B : Connexion Directe (Avec Écran)

1. Branchez un écran HDMI, clavier et souris
2. Le bureau Raspberry Pi OS s'affiche
3. Ouvrez le **Terminal** (icône en haut)

### Étape 6 : Mise à Jour du Système

Une fois connecté, mettez à jour le système :

```bash
# Mettre à jour la liste des paquets
sudo apt update

# Mettre à jour tous les paquets installés (peut prendre 10-15 minutes)
sudo apt upgrade -y

# Nettoyer les paquets inutiles
sudo apt autoremove -y
```

### Étape 7 : Configuration Raspberry Pi

```bash
# Ouvrir l'outil de configuration
sudo raspi-config
```

**Naviguer dans le menu avec les flèches ⬆️⬇️ et Entrée :**

1. **1 System Options** → **S4 Hostname** → Changez en `linkedin-bot` (optionnel)
2. **5 Localisation Options** → **L1 Locale** → Sélectionnez `fr_FR.UTF-8` (si pas déjà fait)
3. **5 Localisation Options** → **L2 Timezone** → `Europe` → `Paris`
4. **6 Advanced Options** → **A1 Expand Filesystem** (important !)
5. Sélectionnez **Finish** → Redémarrer : **Yes**

**Reconnectez-vous après le redémarrage** (attendez 1 minute) :
```bash
ssh pi@raspberrypi.local
# ou
ssh pi@linkedin-bot.local
```

---

## 🚀 Installation du Bot

### Étape 8 : Installer les Dépendances Système

```bash
# Installer Python 3, pip et Git
sudo apt install -y python3 python3-pip python3-venv git

# Vérifier les versions installées
python3 --version  # Doit afficher Python 3.9 ou supérieur
pip3 --version
git --version
```

### Étape 9 : Installer les Dépendances Playwright

Playwright nécessite plusieurs bibliothèques système pour fonctionner :

```bash
# Installer les dépendances Playwright/Chromium
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1
```

### Étape 10 : Cloner le Projet GitHub

```bash
# Se placer dans le dossier home
cd ~

# Cloner le repository
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git

# Entrer dans le dossier
cd linkedin-birthday-auto

# Vérifier le contenu
ls -la
```

Vous devriez voir :
```
linkedin_birthday_wisher.py
linkedin_birthday_wisher_unlimited.py
visit_profiles.py
proxy_manager.py
requirements.txt
README.md
...
```

### Étape 11 : Créer un Environnement Virtuel Python (Recommandé)

```bash
# Créer un environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
source venv/bin/activate

# Votre prompt devrait maintenant commencer par (venv)
```

### Étape 12 : Installer les Dépendances Python

```bash
# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances du projet
pip install -r requirements.txt

# Cela peut prendre 5-10 minutes
```

### Étape 13 : Installer Playwright et les Navigateurs

```bash
# Installer le navigateur Chromium pour Playwright
playwright install chromium

# Installer les dépendances système manquantes
playwright install-deps chromium
```

**Note :** Sur Raspberry Pi 4, Chromium peut prendre 200-300 MB d'espace disque.

---

## ⚙️ Configuration et Test

### Étape 14 : Créer le Fichier de Configuration

```bash
# Créer le fichier .env
nano .env
```

**Collez le contenu suivant** (remplacez par vos vraies informations) :

```bash
# ===== IDENTIFIANTS LINKEDIN =====
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=VotreMotDePasse123

# ===== MODE DE TEST =====
# true = Mode test (ne envoie PAS de messages, juste affiche ce qui serait fait)
# false = Mode production (envoie VRAIMENT les messages)
DRY_RUN=true

# ===== PARAMÈTRES NAVIGATEUR =====
# Mode headless (sans interface graphique)
HEADLESS_BROWSER=true

# ===== ROTATION DE PROXIES (Désactivé pour IP locale) =====
ENABLE_PROXY_ROTATION=false

# Si vous voulez utiliser des proxies (optionnel) :
# ENABLE_PROXY_ROTATION=true
# PROXY_CONFIG_JSON={"proxies":[{"url":"http://user:pass@proxy1.com:8080","type":"residential"}]}

# ===== DEBUG (Optionnel) =====
# ENABLE_ADVANCED_DEBUG=true
# SCREENSHOT_ON_ERROR=true
```

**Sauvegarder et quitter :**
- Appuyez sur `Ctrl+O` puis `Entrée` pour sauvegarder
- Appuyez sur `Ctrl+X` pour quitter nano

### Étape 15 : Sécuriser le Fichier .env

```bash
# Rendre le fichier accessible uniquement par vous
chmod 600 .env

# Vérifier les permissions
ls -la .env
# Doit afficher : -rw------- 1 pi pi ...
```

### Étape 15bis : Gérer l'Authentification à Deux Facteurs (2FA) 🔐

Si vous avez activé le **2FA (authentification à deux facteurs)** sur LinkedIn, le simple login/mot de passe ne fonctionnera pas. Voici **3 solutions** :

#### Solution 1 : Générer auth_state.json sur PC puis le transférer (RECOMMANDÉ)

**Sur votre PC/Mac (avec interface graphique) :**

```bash
# Cloner le repository temporairement
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# Installer les dépendances
pip install -r requirements.txt
playwright install chromium

# Créer un fichier .env temporaire
cat > .env << EOF
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=VotreMotDePasse123
HEADLESS_BROWSER=false
DRY_RUN=true
EOF

# Lancer le script UNE FOIS en mode non-headless
python3 linkedin_birthday_wisher.py
```

**Lors de l'exécution :**
1. Le navigateur Chromium s'ouvre
2. Vous êtes redirigé vers la page de connexion LinkedIn
3. Entrez votre email/mot de passe
4. **Entrez le code 2FA** depuis votre téléphone/application
5. Une fois connecté, le script crée automatiquement `auth_state.json`
6. Le script continue et se termine

**Transférer auth_state.json vers le Raspberry Pi :**

```bash
# Sur votre PC, depuis le dossier du projet
scp auth_state.json pi@raspberrypi.local:~/linkedin-birthday-auto/

# Ou si vous connaissez l'IP
scp auth_state.json pi@192.168.1.X:~/linkedin-birthday-auto/
```

**Sur le Raspberry Pi, vérifier que le fichier est bien là :**

```bash
ls -la ~/linkedin-birthday-auto/auth_state.json
```

Maintenant le bot utilisera `auth_state.json` pour se connecter automatiquement **sans demander le code 2FA** à chaque exécution !

#### Solution 2 : Première connexion en mode GUI sur le Raspberry Pi

Si vous avez un écran HDMI connecté au Raspberry Pi :

```bash
# Modifier .env pour désactiver le mode headless TEMPORAIREMENT
nano ~/linkedin-birthday-auto/.env
```

Modifier la ligne :
```bash
HEADLESS_BROWSER=false
```

**Lancer le script :**

```bash
cd ~/linkedin-birthday-auto
source venv/bin/activate
python3 linkedin_birthday_wisher.py
```

1. Le navigateur Chromium s'ouvre sur l'écran du Raspberry Pi
2. Connectez-vous à LinkedIn
3. Entrez le code 2FA
4. Le fichier `auth_state.json` est généré automatiquement
5. Le script se termine

**Réactiver le mode headless :**

```bash
nano ~/linkedin-birthday-auto/.env
```

Remettre :
```bash
HEADLESS_BROWSER=true
```

**Désormais, le bot se connectera automatiquement sans 2FA.**

#### Solution 3 : Utiliser VNC pour accéder au bureau du Raspberry Pi

Si vous n'avez pas d'écran HDMI mais voulez quand même voir l'interface graphique :

**Activer VNC sur le Raspberry Pi :**

```bash
sudo raspi-config
```

1. **3 Interface Options** → **I3 VNC** → **Yes**
2. Reboot : `sudo reboot`

**Sur votre PC/Mac :**
1. Téléchargez **VNC Viewer** : https://www.realvnc.com/en/connect/download/viewer/
2. Connectez-vous à `raspberrypi.local` ou `192.168.1.X`
3. Vous verrez le bureau du Raspberry Pi

**Puis suivez la Solution 2** en lançant le script depuis le Terminal VNC.

#### Solution 4 : Désactiver temporairement le 2FA (Non Recommandé)

Si vraiment aucune solution ne fonctionne :

1. Allez dans les paramètres LinkedIn sur votre navigateur
2. Désactivez temporairement le 2FA
3. Lancez le script UNE FOIS pour générer `auth_state.json`
4. Réactivez le 2FA

**⚠️ Moins sécurisé, à utiliser en dernier recours uniquement.**

---

### 💡 Comprendre auth_state.json

Le fichier `auth_state.json` contient les **cookies et tokens de session LinkedIn**. Une fois généré :
- ✅ Le bot se connecte automatiquement sans redemander vos identifiants
- ✅ Pas besoin du code 2FA à chaque exécution
- ✅ Valide généralement pendant **plusieurs semaines/mois**
- ⚠️ Si LinkedIn vous déconnecte, il faudra régénérer le fichier

**Régénérer auth_state.json :**

```bash
# Supprimer l'ancien fichier
rm ~/linkedin-birthday-auto/auth_state.json

# Relancer le script (suivre Solution 1 ou 2)
python3 ~/linkedin-birthday-auto/linkedin_birthday_wisher.py
```

---

### Étape 16 : Test Manuel Initial

```bash
# Activer l'environnement virtuel si pas déjà fait
source ~/linkedin-birthday-auto/venv/bin/activate

# Lancer le script en mode test
cd ~/linkedin-birthday-auto
python3 linkedin_birthday_wisher.py
```

**Ce qui devrait se passer :**
1. Le script se lance
2. Connexion à LinkedIn
3. Recherche des anniversaires
4. Affichage des messages qui seraient envoyés (mais ne les envoie PAS car DRY_RUN=true)
5. Fin du script avec un résumé

**Exemple de sortie attendue :**
```
[INFO] Mode DRY RUN activé - Aucun message ne sera envoyé
[INFO] Connexion à LinkedIn...
[INFO] Connexion réussie !
[INFO] Recherche des anniversaires...
[INFO] 3 anniversaires trouvés aujourd'hui
[DRY RUN] Message qui serait envoyé à Jean Dupont :
"Bonjour Jean, je te souhaite un excellent anniversaire ! 🎉"
[DRY RUN] Message qui serait envoyé à Marie Martin :
"Bonjour Marie, je te souhaite un excellent anniversaire ! 🎉"
[INFO] Script terminé avec succès
```

### Étape 17 : Vérifier les Logs

```bash
# Voir la base de données créée
ls -la linkedin_birthday.db

# Consulter les entrées dans la base
sqlite3 linkedin_birthday.db "SELECT * FROM birthday_messages LIMIT 5;"

# Quitter sqlite3
.quit
```

---

## 🤖 Automatisation

### Étape 18 : Créer le Script de Lancement

```bash
# Créer le script de lancement
nano ~/linkedin-birthday-auto/run.sh
```

**Contenu du script :**

```bash
#!/bin/bash

# ===========================================
# Script de Lancement du Bot LinkedIn Birthday
# ===========================================

# Définir le dossier du projet
PROJECT_DIR="/home/pi/linkedin-birthday-auto"
LOG_FILE="$PROJECT_DIR/logs/cron.log"
EXEC_LOG="$PROJECT_DIR/logs/execution.log"

# Créer le dossier logs s'il n'existe pas
mkdir -p "$PROJECT_DIR/logs"

# Fonction de logging
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Début du script
log_message "================================================"
log_message "Démarrage du script LinkedIn Birthday Bot"
log_message "================================================"

# Charger les variables d'environnement depuis .env
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)
    log_message "Variables d'environnement chargées depuis .env"
else
    log_message "ERREUR : Fichier .env introuvable !"
    exit 1
fi

# Se placer dans le dossier du projet
cd "$PROJECT_DIR" || exit 1

# Activer l'environnement virtuel Python
if [ -d "$PROJECT_DIR/venv" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
    log_message "Environnement virtuel activé"
else
    log_message "ATTENTION : Environnement virtuel non trouvé"
fi

# Lancer le script Python
log_message "Lancement du script Python..."
python3 "$PROJECT_DIR/linkedin_birthday_wisher.py" 2>&1 | tee -a "$EXEC_LOG"

# Capturer le code de retour
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    log_message "✅ Script terminé avec succès"
else
    log_message "❌ Script terminé avec une erreur (code: $EXIT_CODE)"
fi

log_message "================================================"
log_message ""

# Désactiver l'environnement virtuel
deactivate 2>/dev/null

exit $EXIT_CODE
```

**Rendre le script exécutable :**

```bash
chmod +x ~/linkedin-birthday-auto/run.sh
```

### Étape 19 : Tester le Script de Lancement

```bash
# Tester l'exécution du script
~/linkedin-birthday-auto/run.sh

# Vérifier les logs
tail -f ~/linkedin-birthday-auto/logs/cron.log
```

### Étape 20 : Configurer l'Automatisation avec Cron

```bash
# Ouvrir le crontab
crontab -e
```

**Si c'est la première fois, choisissez l'éditeur :** Sélectionnez `1` (nano) avec les flèches et Entrée.

**Ajouter à la fin du fichier :**

```bash
# ============================================================
# LinkedIn Birthday Bot - Exécution Automatique Quotidienne
# ============================================================

# Exécution tous les jours à 8h30
30 8 * * * /home/pi/linkedin-birthday-auto/run.sh

# Alternative : Exécution avec heure aléatoire entre 8h et 10h
# 0 8 * * * sleep $((RANDOM \% 7200)) && /home/pi/linkedin-birthday-auto/run.sh

# Alternative : Exécution du lundi au vendredi uniquement (pas le weekend)
# 30 8 * * 1-5 /home/pi/linkedin-birthday-auto/run.sh
```

**Sauvegarder et quitter :**
- `Ctrl+O` puis `Entrée` pour sauvegarder
- `Ctrl+X` pour quitter

**Vérifier que la tâche est bien enregistrée :**

```bash
# Lister les tâches cron
crontab -l

# Vérifier que le service cron est actif
sudo systemctl status cron

# Si inactif, l'activer
sudo systemctl enable cron
sudo systemctl start cron
```

### Étape 21 : Créer un Script avec Heure Aléatoire (Recommandé)

Pour être encore plus discret et imiter un comportement humain :

```bash
nano ~/linkedin-birthday-auto/run_random.sh
```

**Contenu :**

```bash
#!/bin/bash

# ===========================================
# Script avec Délai Aléatoire
# ===========================================

PROJECT_DIR="/home/pi/linkedin-birthday-auto"
LOG_FILE="$PROJECT_DIR/logs/cron.log"

# Générer un délai aléatoire entre 0 et 2 heures (7200 secondes)
DELAY=$((RANDOM % 7200))
MINUTES=$((DELAY / 60))

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Délai aléatoire : $MINUTES minutes ($DELAY secondes)" >> "$LOG_FILE"

# Attendre le délai aléatoire
sleep $DELAY

# Exécuter le script principal
/home/pi/linkedin-birthday-auto/run.sh
```

**Rendre exécutable :**

```bash
chmod +x ~/linkedin-birthday-auto/run_random.sh
```

**Modifier le crontab pour utiliser ce script :**

```bash
crontab -e
```

**Remplacer la ligne précédente par :**

```bash
# Lancer à 8h, mais exécution réelle entre 8h et 10h (aléatoire)
0 8 * * * /home/pi/linkedin-birthday-auto/run_random.sh
```

---

## 📊 Surveillance et Maintenance

### Étape 22 : Consulter les Logs

```bash
# Voir les logs de cron (dernières lignes)
tail -20 ~/linkedin-birthday-auto/logs/cron.log

# Suivre les logs en temps réel
tail -f ~/linkedin-birthday-auto/logs/cron.log

# Voir les logs d'exécution détaillés
tail -50 ~/linkedin-birthday-auto/logs/execution.log

# Voir les logs système de cron
grep CRON /var/log/syslog | tail -20
```

### Étape 23 : Consulter la Base de Données

```bash
# Ouvrir la base de données SQLite
sqlite3 ~/linkedin-birthday-auto/linkedin_birthday.db

# Voir les derniers messages envoyés
SELECT * FROM birthday_messages ORDER BY timestamp DESC LIMIT 10;

# Compter le nombre de messages envoyés
SELECT COUNT(*) FROM birthday_messages;

# Voir les messages envoyés aujourd'hui
SELECT * FROM birthday_messages WHERE DATE(timestamp) = DATE('now');

# Quitter sqlite3
.quit
```

### Étape 24 : Créer des Sauvegardes Automatiques

```bash
# Créer un script de sauvegarde
nano ~/linkedin-birthday-auto/backup.sh
```

**Contenu :**

```bash
#!/bin/bash

# Dossier de sauvegarde
BACKUP_DIR="/home/pi/linkedin-birthday-auto/backups"
mkdir -p "$BACKUP_DIR"

# Nom du fichier de sauvegarde avec date
BACKUP_FILE="$BACKUP_DIR/linkedin_birthday_backup_$(date +%Y%m%d_%H%M%S).db"

# Copier la base de données
cp /home/pi/linkedin-birthday-auto/linkedin_birthday.db "$BACKUP_FILE"

# Conserver uniquement les 30 dernières sauvegardes
cd "$BACKUP_DIR"
ls -t | tail -n +31 | xargs -r rm --

echo "[$(date)] Sauvegarde créée : $BACKUP_FILE"
```

**Rendre exécutable :**

```bash
chmod +x ~/linkedin-birthday-auto/backup.sh
```

**Ajouter au crontab (sauvegarde hebdomadaire le dimanche à minuit) :**

```bash
crontab -e
```

**Ajouter :**

```bash
# Sauvegarde hebdomadaire de la base de données (dimanche à minuit)
0 0 * * 0 /home/pi/linkedin-birthday-auto/backup.sh >> /home/pi/linkedin-birthday-auto/logs/backup.log 2>&1
```

### Étape 25 : Monitoring avec un Script de Santé

```bash
nano ~/linkedin-birthday-auto/health_check.sh
```

**Contenu :**

```bash
#!/bin/bash

PROJECT_DIR="/home/pi/linkedin-birthday-auto"
LOG_FILE="$PROJECT_DIR/logs/health.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Vérifier que la base de données existe
if [ ! -f "$PROJECT_DIR/linkedin_birthday.db" ]; then
    log "❌ ALERTE : Base de données introuvable !"
fi

# Vérifier l'espace disque
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    log "⚠️ AVERTISSEMENT : Espace disque à ${DISK_USAGE}%"
fi

# Vérifier la mémoire disponible
MEM_AVAILABLE=$(free -m | awk 'NR==2 {print $7}')
if [ "$MEM_AVAILABLE" -lt 100 ]; then
    log "⚠️ AVERTISSEMENT : Mémoire faible (${MEM_AVAILABLE}MB disponibles)"
fi

# Vérifier la température du CPU
TEMP=$(vcgencmd measure_temp | egrep -o '[0-9]*\.[0-9]*')
if (( $(echo "$TEMP > 70" | bc -l) )); then
    log "⚠️ AVERTISSEMENT : Température CPU élevée (${TEMP}°C)"
fi

log "✅ Vérification de santé OK"
```

**Rendre exécutable et ajouter au crontab :**

```bash
chmod +x ~/linkedin-birthday-auto/health_check.sh

crontab -e
```

**Ajouter (vérification toutes les heures) :**

```bash
# Health check toutes les heures
0 * * * * /home/pi/linkedin-birthday-auto/health_check.sh
```

---

## ⚡ Optimisations

### Réduire la Consommation Électrique

```bash
# Désactiver le Bluetooth (si non utilisé)
sudo systemctl disable bluetooth
sudo systemctl stop bluetooth

# Désactiver le WiFi si vous utilisez l'Ethernet
sudo rfkill block wifi

# Réduire la luminosité des LEDs (optionnel)
echo 0 | sudo tee /sys/class/leds/led0/brightness  # LED d'activité (verte)
echo 0 | sudo tee /sys/class/leds/led1/brightness  # LED power (rouge)
```

### Optimiser les Performances

```bash
# Augmenter la swap si vous avez un Raspberry Pi 4 avec 2GB RAM
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
```

**Modifier la ligne :**
```
CONF_SWAPSIZE=2048
```

**Appliquer :**
```bash
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Activer le Ventilateur (Si Présent)

```bash
# Éditer la configuration
sudo nano /boot/config.txt
```

**Ajouter à la fin :**
```
# Activer le ventilateur à partir de 60°C
dtoverlay=gpio-fan,gpiopin=14,temp=60000
```

**Redémarrer :**
```bash
sudo reboot
```

### Mise à Jour Automatique du Bot

```bash
nano ~/linkedin-birthday-auto/update.sh
```

**Contenu :**

```bash
#!/bin/bash

cd /home/pi/linkedin-birthday-auto

# Sauvegarder les modifications locales
git stash

# Mettre à jour depuis GitHub
git pull origin main

# Réappliquer les modifications locales
git stash pop

# Mettre à jour les dépendances Python
source venv/bin/activate
pip install --upgrade -r requirements.txt

echo "[$(date)] Bot mis à jour"
```

**Rendre exécutable et ajouter au crontab (mise à jour hebdomadaire) :**

```bash
chmod +x ~/linkedin-birthday-auto/update.sh

crontab -e
```

**Ajouter :**
```bash
# Mise à jour automatique du bot (dimanche à 2h du matin)
0 2 * * 0 /home/pi/linkedin-birthday-auto/update.sh >> /home/pi/linkedin-birthday-auto/logs/update.log 2>&1
```

---

## 🔧 Dépannage

### Le script ne s'exécute pas automatiquement

**1. Vérifier que cron est actif :**
```bash
sudo systemctl status cron
```

Si inactif :
```bash
sudo systemctl enable cron
sudo systemctl start cron
```

**2. Vérifier les tâches cron configurées :**
```bash
crontab -l
```

**3. Vérifier les logs système :**
```bash
grep CRON /var/log/syslog | tail -20
```

**4. Tester le script manuellement :**
```bash
/home/pi/linkedin-birthday-auto/run.sh
```

**5. Vérifier les permissions :**
```bash
ls -la ~/linkedin-birthday-auto/run.sh
# Doit afficher : -rwxr-xr-x
```

### Erreur "playwright: command not found"

```bash
# Réactiver l'environnement virtuel
cd ~/linkedin-birthday-auto
source venv/bin/activate

# Réinstaller Playwright
pip install playwright
playwright install chromium
playwright install-deps chromium
```

### Erreur de mémoire ou crash de Chromium

Sur Raspberry Pi 4 avec 2GB RAM, Chromium peut manquer de mémoire.

**Solution 1 : Augmenter la swap**
```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Modifier : CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

**Solution 2 : Ajouter des arguments Chromium**

Éditer `.env` :
```bash
nano ~/.env
```

Ajouter :
```
CHROMIUM_ARGS=--disable-dev-shm-usage --no-sandbox --disable-gpu
```

### Connexion LinkedIn échoue

**1. Vérifier les identifiants dans .env**
```bash
cat ~/linkedin-birthday-auto/.env | grep LINKEDIN
```

**2. Désactiver le 2FA sur LinkedIn** (ou configurer l'auth state)

**3. Tester en mode non-headless pour voir ce qui se passe**
```bash
nano ~/linkedin-birthday-auto/.env
```

Modifier :
```
HEADLESS_BROWSER=false
```

**4. Régénérer l'auth state**
```bash
rm ~/linkedin-birthday-auto/auth_state.json
python3 ~/linkedin-birthday-auto/linkedin_birthday_wisher.py
```

### Température CPU élevée

```bash
# Vérifier la température
vcgencmd measure_temp

# Si > 75°C, installer un ventilateur ou améliorer la ventilation

# Réduire la fréquence du CPU (dernière option)
sudo nano /boot/config.txt
```

Ajouter :
```
arm_freq=1200
```

Redémarrer :
```bash
sudo reboot
```

### Espace disque insuffisant

```bash
# Vérifier l'espace disque
df -h

# Nettoyer les paquets inutiles
sudo apt clean
sudo apt autoremove -y

# Supprimer les anciennes sauvegardes
rm ~/linkedin-birthday-auto/backups/linkedin_birthday_backup_202*.db

# Supprimer les logs anciens
truncate -s 0 ~/linkedin-birthday-auto/logs/cron.log
truncate -s 0 ~/linkedin-birthday-auto/logs/execution.log
```

---

## 📱 Notifications (Optionnel)

### Option 1 : Notifications par Email

Installer `msmtp` :
```bash
sudo apt install -y msmtp msmtp-mta mailutils
```

Configurer :
```bash
nano ~/.msmtprc
```

**Contenu (exemple avec Gmail) :**
```
defaults
auth on
tls on
tls_trust_file /etc/ssl/certs/ca-certificates.crt
logfile ~/.msmtp.log

account gmail
host smtp.gmail.com
port 587
from votre.email@gmail.com
user votre.email@gmail.com
password votre_mot_de_passe_app

account default : gmail
```

**Sécuriser :**
```bash
chmod 600 ~/.msmtprc
```

**Tester :**
```bash
echo "Test email" | mail -s "Test depuis Raspberry Pi" votre.email@gmail.com
```

**Modifier run.sh pour envoyer un email en cas d'erreur :**

Ajouter à la fin de `run.sh` :
```bash
if [ $EXIT_CODE -ne 0 ]; then
    echo "Le script LinkedIn Bot a échoué avec le code $EXIT_CODE" | mail -s "🚨 Erreur LinkedIn Bot" votre.email@gmail.com
fi
```

### Option 2 : Notifications Telegram

```bash
# Activer l'environnement virtuel
source ~/linkedin-birthday-auto/venv/bin/activate

# Installer le module Telegram
pip install python-telegram-bot
```

Créer un bot Telegram :
1. Ouvrir Telegram
2. Chercher `@BotFather`
3. Envoyer `/newbot` et suivre les instructions
4. Récupérer le **token** du bot

Obtenir votre chat ID :
1. Chercher `@userinfobot` sur Telegram
2. Envoyer `/start`
3. Récupérer votre **chat_id**

**Créer un script de notification :**

```bash
nano ~/linkedin-birthday-auto/send_telegram.sh
```

**Contenu :**
```bash
#!/bin/bash

BOT_TOKEN="VOTRE_BOT_TOKEN"
CHAT_ID="VOTRE_CHAT_ID"
MESSAGE="$1"

curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -d chat_id="${CHAT_ID}" \
    -d text="${MESSAGE}" \
    -d parse_mode="HTML"
```

**Rendre exécutable :**
```bash
chmod +x ~/linkedin-birthday-auto/send_telegram.sh
```

**Modifier run.sh pour envoyer des notifications :**

Ajouter à la fin de `run.sh` :
```bash
if [ $EXIT_CODE -eq 0 ]; then
    ~/linkedin-birthday-auto/send_telegram.sh "✅ Bot LinkedIn exécuté avec succès"
else
    ~/linkedin-birthday-auto/send_telegram.sh "❌ Erreur lors de l'exécution du bot (code: $EXIT_CODE)"
fi
```

---

## ✅ Checklist Finale

Vérifiez que tout est en place :

- [ ] Raspberry Pi 4 installé et configuré
- [ ] SSH activé et fonctionnel
- [ ] Système à jour (`sudo apt update && sudo apt upgrade`)
- [ ] Python 3.9+ installé (`python3 --version`)
- [ ] Git installé
- [ ] Projet cloné dans `~/linkedin-birthday-auto`
- [ ] Environnement virtuel créé et actif
- [ ] Dépendances Python installées (`pip list | grep playwright`)
- [ ] Playwright et Chromium installés
- [ ] Fichier `.env` créé avec identifiants LinkedIn
- [ ] Permissions `.env` configurées (`chmod 600`)
- [ ] Test manuel réussi en mode DRY_RUN
- [ ] Script `run.sh` créé et exécutable
- [ ] Tâche cron configurée (`crontab -l`)
- [ ] Logs créés et accessibles
- [ ] Sauvegardes automatiques configurées
- [ ] Health check configuré (optionnel)
- [ ] Notifications configurées (optionnel)

---

## 🚀 Prochaines Étapes

1. **Laisser tourner 1 semaine en mode test** (`DRY_RUN=true`)
2. **Surveiller les logs** quotidiennement :
   ```bash
   tail -f ~/linkedin-birthday-auto/logs/cron.log
   ```
3. **Vérifier que les anniversaires sont bien détectés**
4. **Activer le mode production** :
   ```bash
   nano ~/linkedin-birthday-auto/.env
   # Changer : DRY_RUN=false
   ```
5. **Configurer les notifications** (email ou Telegram)
6. **Profiter de vos messages d'anniversaire automatiques !** 🎉

---

## 🎯 Avantages de cette Installation

✅ **100% Gratuit** - Pas de coût de proxy, juste l'électricité (~1€/mois)
✅ **IP Résidentielle Légitime** - Votre vraie connexion internet
✅ **Zéro Détection** - LinkedIn voit une connexion normale
✅ **Disponible 24/7** - Le Raspberry Pi consomme très peu
✅ **Silencieux** - Aucun bruit de ventilateur
✅ **Compact** - Taille d'une carte de crédit
✅ **Fiable** - Redémarre automatiquement en cas de coupure
✅ **Contrôle Total** - Vous gérez tout vous-même

---

## 🆘 Support

En cas de problème :

1. **Consultez les logs** : `tail -f ~/linkedin-birthday-auto/logs/cron.log`
2. **Testez manuellement** : `~/linkedin-birthday-auto/run.sh`
3. **Vérifiez les issues GitHub** : [github.com/GaspardD78/linkedin-birthday-auto/issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)
4. **Consultez le README** : [github.com/GaspardD78/linkedin-birthday-auto](https://github.com/GaspardD78/linkedin-birthday-auto)

---

**Félicitations !** 🎉

Votre bot LinkedIn Birthday tourne maintenant sur votre Raspberry Pi 4, 24/7, avec votre propre IP résidentielle, 100% gratuit et totalement indétectable !
