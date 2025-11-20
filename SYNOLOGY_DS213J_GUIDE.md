# 💾 Guide Complet : Installation sur NAS Synology DS213J (Sans Docker)

Guide pas-à-pas ultra-détaillé pour installer le bot LinkedIn Birthday sur votre **NAS Synology DS213J** en Python natif (sans Container Manager/Docker).

---

## 🎯 Votre Configuration

- **NAS Synology DS213J** (Processeur ARM Marvell)
- **DSM 5.x ou 6.x** (pas compatible DSM 7)
- **Pas de Docker/Container Manager** (modèle trop ancien)
- **Installation Python native** via ipkg/bootstrap

---

## ✅ Avantages de cette Solution

- 💰 **Totalement gratuit** (vous avez déjà le NAS)
- 🏠 **IP résidentielle** de votre box (indétectable par LinkedIn)
- 💾 **Stockage NAS** (base de données bien sauvegardée)
- ⏰ **Automatisation 24/7** (toujours allumé)
- 🔧 **Interface DSM** pour gérer facilement

---

## ⏱️ Temps Estimé : 60 minutes

- Activation SSH : 5 minutes
- Installation Python : 30 minutes
- Configuration du bot : 15 minutes
- Tests et automatisation : 10 minutes

---

## 📋 Prérequis

✅ NAS Synology DS213J ou similaire (DS212, DS213, etc.)
✅ Accès administrateur au NAS
✅ Au moins 1GB d'espace disque disponible
✅ Connexion Internet stable
✅ Vos identifiants LinkedIn

---

## 🔓 ÉTAPE 1 : Activer SSH sur le NAS

### 1.1 Se Connecter à DSM

1. Ouvrir un navigateur web

2. Aller sur l'adresse de votre NAS :
   - `http://diskstation.local:5000`
   - Ou `http://192.168.x.x:5000` (votre IP locale)

3. Se connecter avec votre compte administrateur

### 1.2 Activer le Service SSH

1. Aller dans **Panneau de configuration**

2. Cliquer sur **Terminal & SNMP**

3. Onglet **Terminal**

4. ☑️ Cocher **"Activer le service SSH"**

5. Port : Laisser **22** (par défaut)

6. Cliquer sur **Appliquer**

✅ **Validation** : Message "Les paramètres ont été enregistrés avec succès"

---

## 🖥️ ÉTAPE 2 : Se Connecter en SSH

### Sur Mac ou Linux

Ouvrir le **Terminal** :

```bash
ssh admin@diskstation.local
# Ou avec l'IP
ssh admin@192.168.x.x
```

### Sur Windows

**PowerShell (Windows 10/11) :**
```powershell
ssh admin@diskstation.local
```

**Ou utiliser PuTTY :**
1. Télécharger PuTTY : https://www.putty.org/
2. Host Name : `diskstation.local`
3. Port : `22`
4. Connection type : SSH
5. Open

### Première Connexion

```
The authenticity of host 'diskstation.local' can't be established.
Are you sure you want to continue connecting (yes/no)?
```

Taper : **yes** puis Entrée

Entrer votre **mot de passe administrateur**

✅ **Validation** : Vous voyez `admin@DiskStation:~$`

---

## 📦 ÉTAPE 3 : Installer Bootstrap/ipkg

Le DS213J n'a pas Docker, nous allons utiliser **ipkg** (gestionnaire de paquets pour anciens Synology).

### 3.1 Vérifier l'Architecture

```bash
# Vérifier l'architecture du processeur
uname -a
```

**Sortie attendue** :
```
Linux DiskStation ... armv7l GNU/Linux
```

Le DS213J utilise une architecture **ARM**.

### 3.2 Installer Bootstrap

```bash
# Télécharger le script d'installation ipkg
cd /volume1/@tmp

# Pour ARM (DS213J)
wget http://ipkg.nslu2-linux.org/feeds/optware/cs08q1armel/cross/stable/bootstrap-armel.sh

# Si wget n'est pas disponible, utiliser curl
# curl -O http://ipkg.nslu2-linux.org/feeds/optware/cs08q1armel/cross/stable/bootstrap-armel.sh

# Rendre le script exécutable
chmod +x bootstrap-armel.sh

# Exécuter l'installation (en tant que root)
sudo sh bootstrap-armel.sh
```

**Attention** : Cette étape peut prendre 5-10 minutes.

### 3.3 Mettre à Jour ipkg

```bash
# Mettre à jour la liste des paquets
/opt/bin/ipkg update
```

### 3.4 Ajouter ipkg au PATH

```bash
# Éditer le profil
nano ~/.profile
```

**Ajouter à la fin du fichier** :
```bash
export PATH=/opt/bin:/opt/sbin:$PATH
```

**Sauvegarder** : `Ctrl + O`, `Entrée`, `Ctrl + X`

**Recharger le profil** :
```bash
source ~/.profile
```

✅ **Validation** :
```bash
which ipkg
# Doit afficher : /opt/bin/ipkg
```

---

## 🐍 ÉTAPE 4 : Installer Python 3

### 4.1 Installer Python 3 via ipkg

```bash
# Rechercher Python disponible
ipkg list | grep python

# Installer Python 3 (peut s'appeler python3 ou python38)
ipkg install python3

# Ou si python3 n'existe pas
ipkg install python

# Installer pip
ipkg install python3-pip
```

**Note** : Si Python 3 n'est pas disponible via ipkg, nous utiliserons une autre méthode (voir 4.2).

### 4.2 Alternative : Installer Python depuis les sources

Si ipkg n'a pas Python 3, installation manuelle :

```bash
# Installer les dépendances de compilation
ipkg install gcc make

# Télécharger Python 3.9 (dernière version compatible ARM)
cd /volume1/@tmp
wget https://www.python.org/ftp/python/3.9.18/Python-3.9.18.tgz

# Extraire
tar -xzf Python-3.9.18.tgz
cd Python-3.9.18

# Compiler et installer
./configure --prefix=/opt --enable-optimizations
make
sudo make install

# Vérifier l'installation
/opt/bin/python3 --version
```

**Attention** : La compilation peut prendre 1-2 heures sur un DS213J !

### 4.3 Solution Recommandée : Python via Synology Package Center

**La plus simple :**

1. Ouvrir **Package Center** dans DSM

2. Chercher **"Python"** ou **"Python Module"**

3. Installer **Python 3.x** (si disponible)

4. Une fois installé, Python sera accessible via :
   ```bash
   /volume1/@appstore/Python3/bin/python3
   ```

5. Créer un lien symbolique :
   ```bash
   sudo ln -s /volume1/@appstore/Python3/bin/python3 /usr/local/bin/python3
   sudo ln -s /volume1/@appstore/Python3/bin/pip3 /usr/local/bin/pip3
   ```

✅ **Validation** :
```bash
python3 --version
# Doit afficher : Python 3.x.x
```

---

## 📂 ÉTAPE 5 : Créer les Dossiers du Projet

### 5.1 Via File Station (Interface Graphique)

1. Ouvrir **File Station** dans DSM

2. Naviguer vers un dossier partagé (ex: `web`, `homes`, ou créer `linkedin-bot`)

3. Créer un nouveau dossier : `linkedin-bot`

4. Dans ce dossier, créer 2 sous-dossiers :
   - `data` (pour la base de données)
   - `logs` (pour les logs)

### 5.2 Via SSH (Alternative)

```bash
# Créer le dossier principal
sudo mkdir -p /volume1/web/linkedin-bot/data
sudo mkdir -p /volume1/web/linkedin-bot/logs

# Donner les permissions
sudo chown -R admin:users /volume1/web/linkedin-bot
sudo chmod -R 755 /volume1/web/linkedin-bot

# Aller dans le dossier
cd /volume1/web/linkedin-bot
```

✅ **Validation** :
```bash
ls -la /volume1/web/linkedin-bot
```

Vous devez voir `data/` et `logs/`

---

## 📥 ÉTAPE 6 : Télécharger le Projet

### 6.1 Installer Git

```bash
# Via ipkg
ipkg install git

# Ou via Package Center dans DSM
# Chercher "Git Server" et l'installer
```

### 6.2 Cloner le Repository

```bash
# Aller dans le dossier du projet
cd /volume1/web/linkedin-bot

# Cloner le projet
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git .
```

**Le point à la fin est important** (clone dans le dossier actuel)

✅ **Validation** :
```bash
ls -la
```

Vous devez voir tous les fichiers du projet.

---

## 📦 ÉTAPE 7 : Installer les Dépendances Python

### 7.1 Mettre à Jour pip

```bash
# Se placer dans le dossier du projet
cd /volume1/web/linkedin-bot

# Mettre à jour pip
python3 -m pip install --upgrade pip --user
```

### 7.2 Installer les Requirements

```bash
# Installer les dépendances
pip3 install -r requirements.txt --user
```

**Attention** : Cette étape peut prendre 15-20 minutes sur un DS213J.

**Si erreur de mémoire** :
```bash
# Installer les packages un par un
pip3 install --user playwright
pip3 install --user python-dotenv
pip3 install --user flask
# etc.
```

### 7.3 Installer Playwright

```bash
# Installer Playwright
pip3 install --user playwright

# Installer les navigateurs
python3 -m playwright install chromium
```

**⚠️ ATTENTION** : Chromium peut ne pas fonctionner sur ARM ancien.

**Alternative** : Utiliser Firefox au lieu de Chromium :

```bash
# Installer Firefox pour Playwright
python3 -m playwright install firefox

# Modifier les scripts pour utiliser Firefox
# (voir section Dépannage)
```

✅ **Validation** :
```bash
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
```

---

## 🔧 ÉTAPE 8 : Configurer le Bot

### 8.1 Créer le Fichier .env

```bash
cd /volume1/web/linkedin-bot
nano .env
```

**Contenu** (remplacer par VOS informations) :

```bash
# Identifiants LinkedIn
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=VotreMotDePasse123!

# Mode de test
DRY_RUN=true

# Mode navigateur
HEADLESS_BROWSER=true

# Proxies (désactivé)
ENABLE_PROXY_ROTATION=false

# Debug
ENABLE_ADVANCED_DEBUG=false
```

**Sauvegarder** : `Ctrl + O`, `Entrée`, `Ctrl + X`

### 8.2 Protéger le Fichier

```bash
chmod 600 .env
```

✅ **Validation** :
```bash
cat .env
```

---

## 🧪 ÉTAPE 9 : Premier Test

### 9.1 Test Manuel

```bash
cd /volume1/web/linkedin-bot

# Lancer le script
python3 linkedin_birthday_wisher.py
```

**Sortie attendue** :
```
✅ Playwright stealth mode activated
✅ Connexion à LinkedIn réussie
🎂 X anniversaires trouvés

🧪 DRY RUN MODE
✅ Message simulé pour : Jean Dupont
```

### 9.2 En Cas d'Erreur Chromium sur ARM

Si erreur "Chromium not supported on ARM" :

**Solution : Utiliser Firefox**

1. Modifier `linkedin_birthday_wisher.py` :

```bash
nano linkedin_birthday_wisher.py
```

2. Chercher la ligne (Ctrl + W) :
```python
browser = p.chromium.launch(
```

3. Remplacer par :
```python
browser = p.firefox.launch(
```

4. Sauvegarder et retester

✅ **Validation** : Le script s'exécute sans erreur

---

## 📜 ÉTAPE 10 : Créer un Script de Lancement

### 10.1 Créer le Script

```bash
nano /volume1/web/linkedin-bot/run.sh
```

**Contenu** :

```bash
#!/bin/sh

# Charger les variables d'environnement
export $(cat /volume1/web/linkedin-bot/.env | xargs)

# Se placer dans le dossier
cd /volume1/web/linkedin-bot

# Ajouter Python au PATH si nécessaire
export PATH=/opt/bin:/usr/local/bin:$PATH

# Lancer le script
python3 linkedin_birthday_wisher.py

# Log de fin
echo "Script exécuté le $(date)" >> /volume1/web/linkedin-bot/logs/execution.log
```

**Sauvegarder** : `Ctrl + O`, `Entrée`, `Ctrl + X`

### 10.2 Rendre Exécutable

```bash
chmod +x /volume1/web/linkedin-bot/run.sh
```

### 10.3 Tester le Script

```bash
/volume1/web/linkedin-bot/run.sh
```

✅ **Validation** : Le script s'exécute et crée `execution.log`

---

## ⏰ ÉTAPE 11 : Automatiser avec le Planificateur DSM

### 11.1 Ouvrir le Planificateur de Tâches

1. Dans DSM, aller dans **Panneau de configuration**

2. Cliquer sur **Planificateur de tâches**

3. Cliquer sur **Créer** → **Tâche planifiée** → **Script défini par l'utilisateur**

### 11.2 Configuration de la Tâche

**Onglet Général :**
- **Nom de la tâche** : `LinkedIn Birthday Bot`
- **Utilisateur** : `root` (important pour les permissions)
- ☑️ **Activé**

**Onglet Planification :**
- **Exécuter aux dates suivantes** : Quotidien
- **Heure** : `08:30` (ou l'heure souhaitée)
- **Fréquence** : Une seule fois
- **Jours** : Tous les jours cochés

**Onglet Paramètres de la tâche :**
- ☑️ **Envoyer les détails d'exécution par email** (optionnel)
- **Script défini par l'utilisateur** :

```bash
#!/bin/bash

# Ajouter au PATH
export PATH=/opt/bin:/usr/local/bin:$PATH

# Exécuter le script
/volume1/web/linkedin-bot/run.sh >> /volume1/web/linkedin-bot/logs/cron.log 2>&1
```

4. Cliquer sur **OK**

### 11.3 Tester la Tâche

1. Dans le **Planificateur de tâches**, sélectionner votre tâche

2. Cliquer sur **Exécuter**

3. Attendre quelques secondes

4. Vérifier les logs via File Station :
   - `/volume1/web/linkedin-bot/logs/cron.log`

✅ **Validation** : La tâche s'exécute et génère des logs

---

## 🎛️ ÉTAPE 12 : Passer en Mode Production

### 12.1 Vérifications

Après plusieurs tests en `DRY_RUN=true` :

✅ Connexion LinkedIn réussie
✅ Détection des anniversaires
✅ Messages simulés visibles
✅ Aucune erreur

### 12.2 Activer le Mode Production

Via File Station ou SSH :

```bash
nano /volume1/web/linkedin-bot/.env
```

**Modifier** :
```bash
DRY_RUN=false
```

**Sauvegarder**

### 12.3 Redémarrer la Tâche

Dans le Planificateur, cliquer sur **Exécuter** pour tester.

⚠️ **ATTENTION** : Le bot envoie maintenant de vrais messages !

✅ **Validation** : Messages envoyés sur LinkedIn

---

## 📊 ÉTAPE 13 : Surveillance

### 13.1 Consulter les Logs

**Via File Station :**
1. Naviguer vers `/volume1/web/linkedin-bot/logs/`
2. Double-cliquer sur `execution.log` ou `cron.log`

**Via SSH :**
```bash
# Logs d'exécution
tail -f /volume1/web/linkedin-bot/logs/execution.log

# Logs du planificateur
tail -f /volume1/web/linkedin-bot/logs/cron.log
```

### 13.2 Consulter la Base de Données

Si SQLite est disponible :

```bash
# Installer sqlite3
ipkg install sqlite3

# Ouvrir la base
sqlite3 /volume1/web/linkedin-bot/data/linkedin_birthday.db

# Voir les derniers messages
SELECT * FROM birthday_messages ORDER BY timestamp DESC LIMIT 10;

# Quitter
.exit
```

### 13.3 Dashboard Web (Optionnel)

**Lancer le serveur Flask** :

```bash
cd /volume1/web/linkedin-bot
python3 app.py
```

**Accéder depuis un navigateur** :
```
http://diskstation.local:5000
```

---

## 🔄 ÉTAPE 14 : Sauvegardes Automatiques

### 14.1 Créer un Script de Backup

```bash
nano /volume1/web/linkedin-bot/backup.sh
```

**Contenu** :

```bash
#!/bin/sh

# Dossier de backup
BACKUP_DIR="/volume1/web/linkedin-bot/backups"
mkdir -p "$BACKUP_DIR"

# Date du jour
DATE=$(date +%Y%m%d)

# Copier la base de données
cp /volume1/web/linkedin-bot/data/linkedin_birthday.db \
   "$BACKUP_DIR/linkedin_birthday_$DATE.db"

# Garder seulement les 30 derniers backups
ls -t "$BACKUP_DIR"/*.db | tail -n +31 | xargs rm -f

echo "Backup créé : linkedin_birthday_$DATE.db"
```

**Rendre exécutable** :
```bash
chmod +x /volume1/web/linkedin-bot/backup.sh
```

### 14.2 Automatiser les Backups

Dans le **Planificateur de tâches DSM** :

1. Créer une nouvelle tâche : `LinkedIn Backup`
2. Planification : Hebdomadaire, Dimanche, 00:00
3. Script :
```bash
/volume1/web/linkedin-bot/backup.sh >> /volume1/web/linkedin-bot/logs/backup.log 2>&1
```

✅ **Validation** : Backup créé chaque dimanche

---

## 🆘 DÉPANNAGE DS213J

### Problème 1 : Python 3 Non Disponible

**Solution** : Utiliser Python 2 en attendant (pas idéal) :
```bash
ipkg install python
pip install --upgrade pip
```

Ou compiler Python 3 depuis les sources (voir Étape 4.2)

### Problème 2 : Chromium Ne Marche Pas sur ARM

**Solution** : Utiliser Firefox

```bash
# Installer Firefox
python3 -m playwright install firefox

# Modifier le code
nano linkedin_birthday_wisher.py
# Remplacer p.chromium par p.firefox
```

### Problème 3 : Mémoire Insuffisante

Le DS213J a peu de RAM (~512MB).

**Solution** : Ajouter un swap

```bash
# Créer un fichier de swap de 512MB
sudo dd if=/dev/zero of=/volume1/swapfile bs=1M count=512
sudo chmod 600 /volume1/swapfile
sudo mkswap /volume1/swapfile
sudo swapon /volume1/swapfile

# Vérifier
free -m
```

### Problème 4 : ipkg Update Échoue

**Solution** : Utiliser un autre miroir

```bash
# Éditer la config ipkg
nano /opt/etc/ipkg.conf

# Changer le miroir par :
src/gz cross http://ipkg.nslu2-linux.org/feeds/optware/cs08q1armel/cross/stable
```

### Problème 5 : Permission Denied

**Solution** :
```bash
# Donner les bonnes permissions
sudo chown -R admin:users /volume1/web/linkedin-bot
sudo chmod -R 755 /volume1/web/linkedin-bot
sudo chmod 600 /volume1/web/linkedin-bot/.env
```

---

## ✅ CHECKLIST DE VALIDATION FINALE

- [ ] SSH activé et connexion réussie
- [ ] ipkg/bootstrap installé
- [ ] Python 3 installé et fonctionnel
- [ ] Projet cloné dans `/volume1/web/linkedin-bot`
- [ ] Dépendances Python installées
- [ ] Playwright installé (Chromium ou Firefox)
- [ ] Fichier .env créé avec vos identifiants
- [ ] Premier test manuel réussi (DRY_RUN=true)
- [ ] Script run.sh créé et exécutable
- [ ] Tâche planifiée DSM configurée
- [ ] Test manuel de la tâche réussi
- [ ] Logs accessibles et lisibles
- [ ] (Optionnel) Backup automatique configuré
- [ ] Mode production activé (DRY_RUN=false)

---

## 📊 Performances Attendues

| Critère | DS213J | NAS Récent | Freebox Pop |
|---------|--------|------------|-------------|
| **Setup** | ⏱️ 60 min | ⏱️ 30 min | ⏱️ 45 min |
| **Performance** | ⭐⭐⭐ Correct | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Bon |
| **RAM** | 512MB | 1-4GB | 512MB |
| **Compatibilité** | ⚠️ Firefox uniquement | ✅ Chromium | ✅ Chromium |
| **Fiabilité** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**Note** : Le DS213J fonctionne bien pour ce projet, mais peut être plus lent qu'un NAS récent.

---

## 🔄 Mise à Jour

Quand une nouvelle version sort :

```bash
cd /volume1/web/linkedin-bot

# Sauvegarder la base
cp data/linkedin_birthday.db data/linkedin_birthday_backup.db

# Mettre à jour
git pull origin main

# Réinstaller les dépendances si nécessaire
pip3 install -r requirements.txt --user

# Tester
./run.sh
```

---

## 🎉 FÉLICITATIONS !

Votre bot LinkedIn Birthday tourne maintenant sur votre **NAS DS213J** !

### Ce Qui Se Passe Maintenant :

✅ Chaque jour à 8h30, votre NAS :
1. Se connecte à LinkedIn avec votre IP résidentielle
2. Détecte les anniversaires
3. Envoie des messages personnalisés
4. Enregistre tout dans la base de données
5. Génère des logs détaillés

### Avantages :

- 🏠 **IP résidentielle** : Indétectable
- 💰 **0€ de coût** : Matériel existant
- 💾 **Sauvegarde NAS** : Données sécurisées
- 🔄 **Automatique** : Aucune intervention
- 📊 **Interface DSM** : Gestion facile

---

**Votre NAS DS213J est parfaitement capable de faire tourner ce bot ! 🚀**

**Économie réalisée** : ~100€/mois en proxies premium ! 💰
