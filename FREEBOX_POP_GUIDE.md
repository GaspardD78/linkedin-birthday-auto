# 📺 Guide Complet : Installation sur Freebox Pop (Disque 1To)

Guide pas-à-pas ultra-détaillé pour installer le bot LinkedIn Birthday sur votre **Freebox Pop avec disque dur 1To**.

---

## 🎯 Votre Configuration

- **Freebox Pop** avec disque dur interne 1To
- **IP résidentielle Free** (parfait pour LinkedIn !)
- **0€ de coût supplémentaire**
- **Allumé 24/7** (consommation ~10W)

### ✅ Avantages de cette Solution

- 💰 **Totalement gratuit** (vous avez déjà tout !)
- 🏠 **IP résidentielle Free** (impossible à détecter par LinkedIn)
- 🔋 **Faible consommation** (~10W, soit ~2€/mois)
- 💾 **1To d'espace** (largement suffisant)
- ⏰ **Automatisation 24/7** (toujours allumé)

---

## ⏱️ Temps Estimé : 45 minutes

- Activation SSH : 5 minutes
- Installation des dépendances : 20 minutes
- Configuration du bot : 10 minutes
- Tests et automatisation : 10 minutes

---

## 📋 Prérequis

✅ Freebox Pop avec disque dur 1To
✅ Accès à l'interface Freebox OS
✅ Connexion Internet stable
✅ Vos identifiants LinkedIn

---

## 🔓 ÉTAPE 1 : Activer l'Accès SSH

### 1.1 Se Connecter à Freebox OS

1. Ouvrir un navigateur web

2. Aller sur : **http://mafreebox.freebox.fr**
   - Ou : **http://192.168.1.254**

3. Se connecter avec :
   - **Identifiant** : Votre identifiant Free
   - **Mot de passe** : Mot de passe de votre compte Free

### 1.2 Activer SSH

1. Dans Freebox OS, cliquer sur **Paramètres de la Freebox**

2. Aller dans **Mode avancé**

3. Onglet **SSH**

4. ☑️ Cocher **"Activer l'accès par SSH"**

5. Port SSH : Laisser **22** (par défaut)

6. ☑️ Cocher **"Autoriser la connexion par mot de passe"**

7. Cliquer sur **Enregistrer**

✅ **Validation** : Message "SSH activé avec succès"

### 1.3 Noter les Informations

- **Utilisateur** : `freebox`
- **Mot de passe** : Votre mot de passe Free (celui de Freebox OS)
- **IP** : `192.168.1.254` ou `mafreebox.freebox.fr`
- **Port** : `22`

---

## 🖥️ ÉTAPE 2 : Se Connecter en SSH

### Sur Mac ou Linux

Ouvrir le **Terminal** et taper :

```bash
ssh freebox@mafreebox.freebox.fr
```

Ou avec l'IP :

```bash
ssh freebox@192.168.1.254
```

### Sur Windows

**Option 1 : PowerShell (Windows 10/11)**

```powershell
ssh freebox@mafreebox.freebox.fr
```

**Option 2 : PuTTY** (si PowerShell ne fonctionne pas)

1. Télécharger PuTTY : https://www.putty.org/
2. Lancer PuTTY
3. Configuration :
   - Host Name : `mafreebox.freebox.fr`
   - Port : `22`
   - Connection type : SSH
4. Cliquer sur **Open**
5. Login : `freebox`
6. Password : Votre mot de passe Free

### Première Connexion

```
The authenticity of host 'mafreebox.freebox.fr' can't be established.
Are you sure you want to continue connecting (yes/no)?
```

Taper : **yes** puis Entrée

Entrer votre **mot de passe Free**

✅ **Validation** : Vous voyez `freebox@Freebox-Server:~$`

---

## 📂 ÉTAPE 3 : Explorer le Disque Dur

### 3.1 Identifier le Disque

```bash
# Voir les disques montés
df -h
```

**Sortie attendue** :
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       916G  1.2G  868G   1% /Disque dur
```

Votre disque dur 1To est monté sur `/Disque dur`

### 3.2 Créer le Dossier du Projet

```bash
# Aller sur le disque dur
cd "/Disque dur"

# Créer un dossier pour le bot
mkdir linkedin-bot

# Aller dans le dossier
cd linkedin-bot

# Vérifier qu'on est au bon endroit
pwd
```

**Sortie attendue** :
```
/Disque dur/linkedin-bot
```

✅ **Validation** : Le dossier est créé

---

## 🐍 ÉTAPE 4 : Installer Python 3

La Freebox Pop dispose d'un environnement Linux (Debian), mais Python 3 n'est pas installé par défaut.

### 4.1 Vérifier si Python 3 est Disponible

```bash
# Vérifier Python 3
python3 --version
```

**Si erreur** "command not found" :

### 4.2 Installer Entware (Gestionnaire de Paquets)

Entware permet d'installer des logiciels sur la Freebox Pop.

```bash
# Télécharger le script d'installation Entware
wget -O - http://bin.entware.net/armv7sf-k3.2/installer/generic.sh | sh
```

Attendre la fin de l'installation (2-3 minutes).

### 4.3 Mettre à Jour Entware

```bash
# Mettre à jour la liste des paquets
opkg update
```

### 4.4 Installer Python 3

```bash
# Installer Python 3 et pip
opkg install python3 python3-pip

# Installer git
opkg install git git-http

# Vérifier l'installation
python3 --version
```

**Sortie attendue** :
```
Python 3.9.x
```

✅ **Validation** : Python 3 installé

---

## 📥 ÉTAPE 5 : Télécharger le Projet

### 5.1 Cloner le Repository GitHub

```bash
# Aller dans le dossier du projet
cd "/Disque dur/linkedin-bot"

# Cloner le projet
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git .

# Le point à la fin est important (clone dans le dossier actuel)
```

**Sortie attendue** :
```
Cloning into '.'...
remote: Enumerating objects: ...
Receiving objects: 100% ...
```

### 5.2 Vérifier les Fichiers

```bash
# Lister les fichiers
ls -la
```

Vous devez voir :
```
linkedin_birthday_wisher.py
linkedin_birthday_wisher_unlimited.py
visit_profiles.py
requirements.txt
README.md
...
```

✅ **Validation** : Projet téléchargé

---

## 📦 ÉTAPE 6 : Installer les Dépendances Python

### 6.1 Installer les Packages Python

```bash
# Mettre à jour pip
python3 -m pip install --upgrade pip

# Installer les dépendances
pip3 install -r requirements.txt
```

**Attention** : Cette étape peut prendre 10-15 minutes sur la Freebox Pop.

### 6.2 Installer Playwright

```bash
# Installer Playwright
pip3 install playwright

# Installer les navigateurs (Chromium)
python3 -m playwright install chromium
```

**Note** : Si erreur de permissions, utiliser :
```bash
pip3 install --user playwright
python3 -m playwright install chromium
```

### 6.3 Installer les Dépendances Système de Playwright

⚠️ **Important** : Chromium nécessite des bibliothèques système.

```bash
# Installer les dépendances via Entware
opkg install \
    libstdcpp \
    libatomic \
    libnss \
    libasound \
    fontconfig \
    libfreetype \
    libpng
```

✅ **Validation** :
```bash
# Tester Playwright
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
```

Si "Playwright OK" s'affiche, c'est bon !

---

## 🔧 ÉTAPE 7 : Configurer le Bot

### 7.1 Créer le Fichier .env

```bash
# Créer le fichier de configuration
nano .env
```

**Contenu à copier** (remplacer par VOS informations) :

```bash
# Identifiants LinkedIn
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=VotreMotDePasse123!

# Mode de test (true = simulation, false = envoi réel)
DRY_RUN=true

# Mode navigateur (true = invisible, false = visible)
HEADLESS_BROWSER=true

# Proxies (désactivé car on utilise l'IP Free résidentielle)
ENABLE_PROXY_ROTATION=false

# Debug (optionnel)
ENABLE_ADVANCED_DEBUG=false
```

**Remplacer** :
- `votre.email@example.com` → Votre email LinkedIn
- `VotreMotDePasse123!` → Votre mot de passe LinkedIn

**Sauvegarder** :
- `Ctrl + O` (enregistrer)
- `Entrée` (confirmer)
- `Ctrl + X` (quitter)

### 7.2 Protéger le Fichier .env

```bash
# Rendre le fichier accessible uniquement par vous
chmod 600 .env
```

✅ **Validation** :
```bash
# Vérifier que le fichier existe
cat .env
```

---

## 🧪 ÉTAPE 8 : Premier Test

### 8.1 Test Manuel en DRY_RUN

```bash
# Lancer le script en mode test
python3 linkedin_birthday_wisher.py
```

**Sortie attendue** (si tout va bien) :

```
🔧 Using User-Agent: Mozilla/5.0...
✅ Playwright stealth mode activated
✅ Connexion à LinkedIn réussie
🔍 Validating birthday feed selectors...
✅ Navigation vers la page des anniversaires
🎂 X anniversaires trouvés aujourd'hui

🧪 DRY RUN MODE - Aucun message ne sera envoyé
✅ Message simulé pour : Jean Dupont
✅ Message simulé pour : Marie Martin

📊 Total : 2 messages (simulation)
```

### 8.2 En Cas d'Erreur

**Erreur : "Cannot connect to LinkedIn"**

Solution :
1. Vérifier vos identifiants dans `.env`
2. Vérifier que la Freebox a accès à Internet :
   ```bash
   ping google.com
   ```
3. Si 2FA activé sur LinkedIn, le désactiver temporairement

**Erreur : "playwright not found"**

Solution :
```bash
# Réinstaller Playwright
pip3 install --user playwright
python3 -m playwright install chromium
```

**Erreur : "Permission denied"**

Solution :
```bash
# Donner les permissions
chmod +x linkedin_birthday_wisher.py
```

✅ **Validation** : Le script s'exécute sans erreur et affiche les simulations

---

## 📜 ÉTAPE 9 : Créer un Script de Lancement

### 9.1 Créer le Script

```bash
# Créer le script
nano run.sh
```

**Contenu** :

```bash
#!/bin/sh

# Charger les variables d'environnement
export $(cat "/Disque dur/linkedin-bot/.env" | xargs)

# Se placer dans le dossier du projet
cd "/Disque dur/linkedin-bot"

# Lancer le script
python3 linkedin_birthday_wisher.py

# Log de fin
echo "Script exécuté le $(date)" >> "/Disque dur/linkedin-bot/execution.log"
```

**Sauvegarder** : `Ctrl + O`, `Entrée`, `Ctrl + X`

### 9.2 Rendre le Script Exécutable

```bash
# Donner les permissions d'exécution
chmod +x run.sh
```

### 9.3 Tester le Script

```bash
# Lancer le script
./run.sh
```

✅ **Validation** : Le script s'exécute et crée un fichier `execution.log`

---

## ⏰ ÉTAPE 10 : Automatiser avec Cron

### 10.1 Vérifier si Cron est Disponible

```bash
# Vérifier cron
which cron
```

**Si cron n'est pas installé** :

```bash
# Installer cronie (cron pour Entware)
opkg install cronie

# Démarrer le service cron
/opt/etc/init.d/S10cron start

# Activer au démarrage
ln -sf /opt/etc/init.d/S10cron /opt/etc/init.d/S10cron
```

### 10.2 Éditer le Crontab

```bash
# Ouvrir l'éditeur cron
crontab -e
```

**Si demandé, choisir** : `nano` (option 1)

### 10.3 Ajouter la Tâche Automatique

**Ajouter cette ligne** (tous les jours à 8h30) :

```bash
30 8 * * * /Disque\ dur/linkedin-bot/run.sh >> /Disque\ dur/linkedin-bot/cron.log 2>&1
```

**Explications** :
- `30 8 * * *` : Tous les jours à 8h30
- `/Disque\ dur/...` : Chemin du script (attention aux espaces échappés !)
- `>> cron.log` : Enregistrer les logs

**Autres exemples d'horaires** :

```bash
# Tous les jours à 9h15
15 9 * * * /Disque\ dur/linkedin-bot/run.sh >> /Disque\ dur/linkedin-bot/cron.log 2>&1

# Du lundi au vendredi à 8h30
30 8 * * 1-5 /Disque\ dur/linkedin-bot/run.sh >> /Disque\ dur/linkedin-bot/cron.log 2>&1

# Tous les jours entre 8h et 10h (heure aléatoire)
0 8 * * * sleep $((RANDOM \% 7200)) && /Disque\ dur/linkedin-bot/run.sh >> /Disque\ dur/linkedin-bot/cron.log 2>&1
```

**Sauvegarder** : `Ctrl + O`, `Entrée`, `Ctrl + X`

### 10.4 Vérifier la Configuration Cron

```bash
# Voir les tâches cron configurées
crontab -l
```

Vous devez voir votre ligne.

✅ **Validation** : Cron configuré

---

## 🔄 ÉTAPE 11 : Activer le Mode Production

### 11.1 Vérifier que Tout Marche

Après plusieurs tests en mode `DRY_RUN=true`, vérifier :

✅ Connexion LinkedIn réussie
✅ Détection des anniversaires
✅ Messages simulés affichés
✅ Aucune erreur dans les logs

### 11.2 Passer en Production

```bash
# Éditer le fichier .env
nano .env
```

**Modifier la ligne** :

```bash
# Avant
DRY_RUN=true

# Après
DRY_RUN=false
```

**Sauvegarder** : `Ctrl + O`, `Entrée`, `Ctrl + X`

### 11.3 Tester une Fois Manuellement

```bash
# Lancer pour tester
./run.sh
```

**Vérifier dans les logs** :
```bash
tail -f execution.log
```

Vous devez voir :
```
✅ Message envoyé à : Jean Dupont
✅ Message envoyé à : Marie Martin
📊 Total : 2 messages envoyés
```

⚠️ **ATTENTION** : À partir de maintenant, le bot **envoie de vrais messages** !

✅ **Validation** : Mode production actif

---

## 📊 ÉTAPE 12 : Surveiller et Maintenir

### 12.1 Voir les Logs d'Exécution

```bash
# Logs du script principal
tail -f /Disque\ dur/linkedin-bot/execution.log

# Logs du cron
tail -f /Disque\ dur/linkedin-bot/cron.log
```

### 12.2 Consulter la Base de Données

```bash
# Installer sqlite3 si besoin
opkg install sqlite3-cli

# Ouvrir la base de données
sqlite3 /Disque\ dur/linkedin-bot/linkedin_birthday.db

# Voir les derniers messages envoyés
SELECT * FROM birthday_messages ORDER BY timestamp DESC LIMIT 10;

# Voir les statistiques
SELECT COUNT(*) as total FROM birthday_messages;

# Quitter
.exit
```

### 12.3 Vérifier que Cron Fonctionne

```bash
# Voir si cron tourne
ps | grep cron

# Voir les logs système (si disponibles)
logread | grep cron
```

### 12.4 Sauvegardes Automatiques

**Créer un script de backup** :

```bash
nano /Disque\ dur/linkedin-bot/backup.sh
```

**Contenu** :

```bash
#!/bin/sh

# Dossier de backup
BACKUP_DIR="/Disque dur/linkedin-bot/backups"
mkdir -p "$BACKUP_DIR"

# Date du jour
DATE=$(date +%Y%m%d)

# Copier la base de données
cp "/Disque dur/linkedin-bot/linkedin_birthday.db" \
   "$BACKUP_DIR/linkedin_birthday_$DATE.db"

# Garder seulement les 30 derniers backups
ls -t "$BACKUP_DIR"/*.db | tail -n +31 | xargs rm -f

echo "Backup créé : linkedin_birthday_$DATE.db"
```

**Rendre exécutable** :

```bash
chmod +x /Disque\ dur/linkedin-bot/backup.sh
```

**Ajouter au crontab** (tous les dimanches à minuit) :

```bash
crontab -e
```

**Ajouter** :

```bash
0 0 * * 0 /Disque\ dur/linkedin-bot/backup.sh >> /Disque\ dur/linkedin-bot/backup.log 2>&1
```

✅ **Validation** : Backup automatique configuré

---

## 🔧 Optimisations Freebox Pop

### Réduire la Consommation Mémoire

La Freebox Pop a une RAM limitée. Pour optimiser :

```bash
# Ajouter dans .env
HEADLESS_BROWSER=true
ENABLE_ADVANCED_DEBUG=false
```

### Éviter les Redémarrages

La Freebox Pop peut redémarrer lors de mises à jour. Pour relancer automatiquement :

**Créer un script de démarrage** :

```bash
nano /Disque\ dur/linkedin-bot/startup.sh
```

**Contenu** :

```bash
#!/bin/sh

# Attendre que le réseau soit disponible
sleep 60

# Redémarrer cron (au cas où)
/opt/etc/init.d/S10cron restart

echo "Freebox redémarrée le $(date)" >> /Disque\ dur/linkedin-bot/startup.log
```

**Rendre exécutable** :

```bash
chmod +x /Disque\ dur/linkedin-bot/startup.sh
```

**Ajouter au crontab** (@reboot = au démarrage) :

```bash
crontab -e
```

**Ajouter** :

```bash
@reboot /Disque\ dur/linkedin-bot/startup.sh
```

---

## 🆘 DÉPANNAGE

### Problème 1 : "Connection timed out" lors du clone Git

**Cause** : Freebox Pop derrière un firewall restrictif

**Solution** :
```bash
# Utiliser HTTPS au lieu de git://
git config --global url."https://".insteadOf git://

# Réessayer
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git .
```

### Problème 2 : Playwright ne trouve pas Chromium

**Solution** :
```bash
# Installer dans le dossier utilisateur
export PLAYWRIGHT_BROWSERS_PATH="/Disque dur/linkedin-bot/.cache"
python3 -m playwright install chromium

# Ajouter dans run.sh
export PLAYWRIGHT_BROWSERS_PATH="/Disque dur/linkedin-bot/.cache"
```

### Problème 3 : "Out of memory" lors de l'exécution

**Cause** : RAM limitée de la Freebox Pop

**Solution** :
```bash
# Ajouter un swap (mémoire virtuelle)
# Créer un fichier de swap de 1GB
dd if=/dev/zero of=/Disque\ dur/swapfile bs=1M count=1024
chmod 600 /Disque\ dur/swapfile
mkswap /Disque\ dur/swapfile
swapon /Disque\ dur/swapfile

# Vérifier
free -m
```

### Problème 4 : Cron ne s'exécute pas

**Solution** :
```bash
# Vérifier que cron tourne
ps | grep cron

# Si pas de résultat, démarrer cron
/opt/etc/init.d/S10cron start

# Vérifier les logs
tail -f /Disque\ dur/linkedin-bot/cron.log
```

### Problème 5 : "Permission denied" sur les logs

**Solution** :
```bash
# Donner les bonnes permissions
chmod 755 /Disque\ dur/linkedin-bot
chmod 644 /Disque\ dur/linkedin-bot/*.log
chmod 600 /Disque\ dur/linkedin-bot/.env
```

---

## ✅ CHECKLIST DE VALIDATION FINALE

Avant de considérer l'installation terminée :

- [ ] SSH activé et connexion réussie
- [ ] Python 3 installé (`python3 --version`)
- [ ] Projet cloné dans `/Disque dur/linkedin-bot`
- [ ] Dépendances Python installées (`pip3 list`)
- [ ] Playwright et Chromium installés
- [ ] Fichier `.env` créé avec VOS identifiants
- [ ] Premier test manuel réussi en DRY_RUN=true
- [ ] Script `run.sh` créé et exécutable
- [ ] Cron installé et configuré (`crontab -l`)
- [ ] Test manuel de l'exécution cron réussi
- [ ] Logs accessibles (`execution.log`, `cron.log`)
- [ ] (Optionnel) Backup automatique configuré
- [ ] Mode production activé (DRY_RUN=false) si souhaité

---

## 📊 Comparaison : Freebox Pop vs Autres Solutions

| Critère | Freebox Pop | NAS Synology | Raspberry Pi |
|---------|-------------|--------------|--------------|
| **Coût initial** | 0€ (vous l'avez) | 0€ (si possédé) | ~40€ |
| **Setup** | ⏱️ 45 min | ⏱️ 30 min | ⏱️ 30 min |
| **Difficulté** | ⭐⭐⭐ Moyenne | ⭐⭐⭐⭐⭐ Facile | ⭐⭐⭐⭐ Facile |
| **RAM** | 512MB | 1-4GB | 1-4GB |
| **Performance** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Consommation** | ~10W (~2€/mois) | ~20W (~4€/mois) | ~3W (~0.65€/mois) |
| **Fiabilité** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **IP Résidentielle** | ✅ Free | ✅ Votre box | ✅ Votre box |
| **Recommandation** | ✅ Bon si vous l'avez | ✅ Parfait | ✅ Excellent |

---

## 🎉 FÉLICITATIONS !

Votre bot LinkedIn Birthday tourne maintenant sur votre **Freebox Pop** !

### Ce qui se passe maintenant :

✅ Chaque jour à 8h30 (heure choisie), votre Freebox :
1. Se connecte à LinkedIn avec votre **IP résidentielle Free**
2. Détecte les anniversaires du jour
3. Envoie un message personnalisé à chacun
4. Enregistre tout dans la base de données (stockée sur le disque 1To)
5. Génère des logs détaillés

### Avantages de votre configuration :

- 🏠 **IP résidentielle Free** : Totalement indétectable par LinkedIn
- 💰 **0€ de coût** : Vous utilisez un matériel que vous avez déjà
- 📦 **1To d'espace** : Largement suffisant pour la base de données
- 🔄 **Automatique** : Aucune intervention requise
- 🔋 **Économique** : Consommation de seulement ~10W

---

## 🔄 Mise à Jour du Bot

Quand une nouvelle version sort sur GitHub :

```bash
# Se connecter en SSH
ssh freebox@mafreebox.freebox.fr

# Aller dans le dossier
cd "/Disque dur/linkedin-bot"

# Sauvegarder la base de données
cp linkedin_birthday.db linkedin_birthday_backup.db

# Mettre à jour le code
git pull origin main

# Réinstaller les dépendances si nécessaire
pip3 install -r requirements.txt

# Tester
./run.sh
```

---

## 💬 Support

Si vous rencontrez un problème :

1. **Consulter les logs** :
   ```bash
   tail -f /Disque\ dur/linkedin-bot/execution.log
   tail -f /Disque\ dur/linkedin-bot/cron.log
   ```

2. **Vérifier que cron tourne** :
   ```bash
   ps | grep cron
   ```

3. **Tester manuellement** :
   ```bash
   ./run.sh
   ```

4. **Consulter les issues GitHub** :
   https://github.com/GaspardD78/linkedin-birthday-auto/issues

---

**Votre bot fonctionne sur votre Freebox Pop ? Profitez de votre automatisation LinkedIn totalement invisible ! 🚀**

**Économie réalisée** : ~100€/mois en proxies premium ! 💰
