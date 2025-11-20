# 🏠 Installation sur NAS Synology & Freebox Pop

Guide d'installation du bot LinkedIn Birthday sur votre **NAS Synology** ou **Freebox Pop** pour utiliser votre IP résidentielle gratuitement.

---

## 🎯 Pourquoi c'est la Meilleure Solution ?

| Critère | NAS Synology | Freebox Pop | Raspberry Pi |
|---------|--------------|-------------|--------------|
| **Déjà possédé** | ✅ Oui | ✅ Oui | ❌ À acheter |
| **Toujours allumé** | ✅ 24/7 | ✅ 24/7 | ⚠️ Manuel |
| **Consommation** | ~20W | ~10W | ~3W |
| **IP Résidentielle** | ✅ Oui | ✅ Oui | ✅ Oui |
| **Facilité setup** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Coût additionnel** | 0€ | 0€ | ~40€ |

**Verdict : NAS Synology = Solution IDÉALE** (si vous l'avez déjà)

---

# 📦 OPTION A : NAS Synology

## Prérequis

- NAS Synology avec DSM 7.0 ou supérieur
- Package Center accessible
- 1GB d'espace disque disponible
- Accès SSH (optionnel mais recommandé)

---

## 🚀 Méthode 1 : Avec Docker (RECOMMANDÉ)

### Avantages Docker
- ✅ Installation propre et isolée
- ✅ Facile à mettre à jour
- ✅ Facile à supprimer
- ✅ Pas de conflit avec le système

### 1. Installer Docker

1. Ouvrir **Package Center** sur DSM
2. Chercher "**Container Manager**" (anciennement Docker)
3. Cliquer sur **Installer**
4. Attendre la fin de l'installation

### 2. Créer le Dockerfile

Via **File Station** :

1. Créer un dossier : `/volume1/docker/linkedin-bot`
2. Créer un fichier `Dockerfile` avec ce contenu :

```dockerfile
FROM python:3.11-slim

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Playwright
RUN apt-get update && apt-get install -y \
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
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Cloner le projet
RUN git clone https://github.com/GaspardD78/linkedin-birthday-auto.git .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Installer Playwright et les navigateurs
RUN playwright install chromium
RUN playwright install-deps chromium

# Point d'entrée
CMD ["python", "linkedin_birthday_wisher.py"]
```

3. Créer un fichier `.env` dans le même dossier :

```bash
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=votre_mot_de_passe
DRY_RUN=false
ENABLE_PROXY_ROTATION=false
HEADLESS_BROWSER=true
```

### 3. Construire l'Image Docker

**Via SSH** (méthode recommandée) :

```bash
# Se connecter au NAS
ssh admin@votre-nas.local

# Aller dans le dossier
cd /volume1/docker/linkedin-bot

# Construire l'image (peut prendre 5-10 minutes)
sudo docker build -t linkedin-bot:latest .
```

**Via Container Manager** (interface graphique) :

1. Ouvrir **Container Manager**
2. Aller dans **Image**
3. Cliquer sur **Ajouter** → **Construire via Dockerfile**
4. Sélectionner le dossier `/volume1/docker/linkedin-bot`
5. Nom de l'image : `linkedin-bot:latest`
6. Cliquer sur **Construire**

### 4. Créer le Conteneur

**Via SSH** :

```bash
sudo docker run -d \
  --name linkedin-birthday-bot \
  --restart unless-stopped \
  -v /volume1/docker/linkedin-bot/.env:/app/.env:ro \
  -v /volume1/docker/linkedin-bot/data:/app/data \
  linkedin-bot:latest
```

**Via Container Manager** :

1. Aller dans **Conteneur**
2. Cliquer sur **Créer**
3. Sélectionner l'image `linkedin-bot:latest`
4. Configurer :
   - Nom : `linkedin-birthday-bot`
   - Restart policy : `Unless-stopped`
   - Volumes :
     - `/volume1/docker/linkedin-bot/.env` → `/app/.env` (lecture seule)
     - `/volume1/docker/linkedin-bot/data` → `/app/data`
5. Cliquer sur **Appliquer**

### 5. Automatiser avec Task Scheduler

1. Ouvrir **Control Panel** → **Task Scheduler**
2. Créer → **Scheduled Task** → **User-defined script**
3. Configuration :
   - **General**
     - Task : `LinkedIn Birthday Bot`
     - User : `root`
   - **Schedule**
     - Date : Daily
     - Time : `08:30` (ou heure souhaitée)
     - Frequency : Every day
   - **Task Settings**
     - User-defined script :
       ```bash
       docker start linkedin-birthday-bot && docker logs -f linkedin-birthday-bot
       ```
4. Cocher "Send run details by email" (optionnel)
5. Cliquer sur **OK**

### 6. Vérifier les Logs

**Via SSH** :

```bash
# Voir les logs en temps réel
sudo docker logs -f linkedin-birthday-bot

# Voir les dernières lignes
sudo docker logs --tail 50 linkedin-birthday-bot
```

**Via Container Manager** :

1. Aller dans **Conteneur**
2. Sélectionner `linkedin-birthday-bot`
3. Cliquer sur **Détails**
4. Onglet **Journal**

---

## 🐍 Méthode 2 : Installation Python Native

### 1. Activer SSH

1. **Control Panel** → **Terminal & SNMP**
2. Cocher "Enable SSH service"
3. Port : `22` (par défaut)
4. Cliquer sur **Apply**

### 2. Se Connecter en SSH

```bash
ssh admin@votre-nas.local
# Ou ssh admin@192.168.x.x
```

### 3. Installer Python 3

Via **Package Center** :

1. Chercher "**Python 3**"
2. Installer la dernière version (3.8+)

Via SSH (si pas disponible dans Package Center) :

```bash
# Vérifier si Python 3 est disponible
python3 --version

# Si non disponible, utiliser ipkg ou entware
# (voir documentation Synology pour votre modèle)
```

### 4. Cloner le Projet

```bash
# Créer un dossier dans votre home
cd /volume1/homes/admin
mkdir linkedin-bot
cd linkedin-bot

# Cloner le repository
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git .
```

### 5. Installer les Dépendances

```bash
# Installer pip si nécessaire
sudo python3 -m ensurepip

# Installer les dépendances
pip3 install --user -r requirements.txt

# Installer Playwright
playwright install chromium
```

### 6. Créer le Fichier .env

```bash
nano .env
```

Contenu :

```bash
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=votre_mot_de_passe
DRY_RUN=false
ENABLE_PROXY_ROTATION=false
HEADLESS_BROWSER=true
```

### 7. Créer un Script de Lancement

```bash
nano run.sh
```

Contenu :

```bash
#!/bin/bash

# Charger les variables d'environnement
export $(cat /volume1/homes/admin/linkedin-bot/.env | xargs)

# Se placer dans le dossier
cd /volume1/homes/admin/linkedin-bot

# Lancer le script
python3 linkedin_birthday_wisher.py

# Log
echo "Exécuté le $(date)" >> /volume1/homes/admin/linkedin-bot/execution.log
```

Rendre exécutable :

```bash
chmod +x run.sh
```

### 8. Automatiser avec Task Scheduler

1. **Control Panel** → **Task Scheduler**
2. Créer → **Scheduled Task** → **User-defined script**
3. Configuration identique à la méthode Docker, mais script :
   ```bash
   /volume1/homes/admin/linkedin-bot/run.sh
   ```

---

# 📺 OPTION B : Freebox Pop

## Prérequis

- Freebox Pop ou Freebox Delta
- Mode Bridge désactivé (pour SSH)
- Compte Free avec accès administrateur

---

## 🔓 1. Activer l'Accès SSH

### Via l'Interface Freebox OS

1. Se connecter à **mafreebox.freebox.fr**
2. Aller dans **Paramètres de la Freebox** → **Mode avancé**
3. Cocher **"Activer l'accès par SSH"**
4. Noter le port SSH (22 par défaut)
5. Cocher **"Autoriser la connexion par mot de passe"**

### Trouver l'IP de la Freebox

```bash
# L'IP locale est généralement
192.168.1.254

# Ou via
ping mafreebox.freebox.fr
```

---

## 🐧 2. Se Connecter à la Freebox

```bash
# Utilisateur par défaut : freebox
# Mot de passe : celui de votre compte Free
ssh freebox@mafreebox.freebox.fr

# Ou
ssh freebox@192.168.1.254
```

⚠️ **Important** : La Freebox Pop utilise un système Linux limité (busybox), certaines commandes peuvent ne pas être disponibles.

---

## 📦 3. Vérifier les Outils Disponibles

```bash
# Vérifier Python
python3 --version

# Si Python pas disponible, vérifier Python 2
python --version

# Vérifier l'espace disque
df -h

# Vérifier la RAM
free -m
```

---

## 🔧 4. Installation Selon Configuration

### Cas 1 : Python 3 Disponible (Freebox Delta)

```bash
# Créer un dossier de travail
mkdir -p /Disque\ dur/linkedin-bot
cd /Disque\ dur/linkedin-bot

# Cloner le projet (si git disponible)
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git .

# Ou télécharger manuellement via wget
wget https://github.com/GaspardD78/linkedin-birthday-auto/archive/refs/heads/main.zip
unzip main.zip
mv linkedin-birthday-auto-main/* .

# Installer les dépendances
pip3 install --user -r requirements.txt
playwright install chromium
```

### Cas 2 : Python Non Disponible (Freebox Pop)

La Freebox Pop a des limitations. **Solutions alternatives** :

#### Solution A : Utiliser Docker sur Freebox

```bash
# Vérifier si Docker est disponible
docker --version

# Si oui, utiliser la méthode Docker du NAS Synology
# (voir section précédente)
```

#### Solution B : Installation via Entware

```bash
# Installer Entware (gestionnaire de paquets)
# Documentation officielle : https://github.com/Entware/Entware/wiki

# Exemple d'installation (peut varier selon modèle)
wget -O - http://bin.entware.net/armv7sf-k3.2/installer/generic.sh | sh

# Mettre à jour
opkg update

# Installer Python 3
opkg install python3 python3-pip

# Continuer avec l'installation normale
```

#### Solution C : Utiliser un Conteneur LXC (Freebox Delta uniquement)

1. Via Freebox OS : **Paramètres** → **VMs**
2. Créer un conteneur Debian
3. Installer Python dans le conteneur
4. Suivre le guide normal

---

## ⚠️ Limitations Freebox Pop

La Freebox Pop a des ressources limitées :

- **RAM** : ~512MB disponible
- **CPU** : ARM limité
- **Stockage** : Selon disque externe

**Recommandation** :
- ✅ **Freebox Delta** : Parfaite pour ce projet
- ⚠️ **Freebox Pop** : Possible mais limité, privilégier le NAS Synology si disponible
- ❌ **Freebox Revolution/Mini** : Pas adapté

---

## 🔄 5. Automatisation sur Freebox

### Via Crontab

```bash
# Éditer le crontab
crontab -e

# Ajouter la tâche (tous les jours à 8h30)
30 8 * * * /Disque\ dur/linkedin-bot/run.sh >> /Disque\ dur/linkedin-bot/cron.log 2>&1
```

### Script run.sh

```bash
#!/bin/sh

# Charger les variables
export $(cat /Disque\ dur/linkedin-bot/.env | xargs)

# Lancer
cd /Disque\ dur/linkedin-bot
python3 linkedin_birthday_wisher.py

# Log
echo "Exécuté le $(date)" >> /Disque\ dur/linkedin-bot/execution.log
```

---

## 📊 Comparaison NAS vs Freebox

| Critère | NAS Synology | Freebox Pop | Freebox Delta |
|---------|--------------|-------------|---------------|
| **Facilité d'installation** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Stabilité** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Gestion logs** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Dashboard Web** | ✅ Facile | ⚠️ Complexe | ✅ Possible |
| **Consommation** | ~20W | ~10W | ~15W |
| **Recommandation** | ✅ PARFAIT | ⚠️ OK | ✅ EXCELLENT |

---

## 🎯 Ma Recommandation Finale

### Si vous avez un NAS Synology
→ **UTILISEZ-LE !** C'est la solution parfaite :
- Interface graphique
- Docker intégré
- Gestion des logs
- Task Scheduler puissant
- Dashboard Web accessible

### Si vous avez une Freebox Delta
→ **Excellente option** :
- VMs disponibles
- Bonnes performances
- Python disponible

### Si vous avez une Freebox Pop
→ **Possible mais compliqué** :
- Ressources limitées
- Installation manuelle complexe
- Considérez plutôt un Raspberry Pi (~35€)

---

## 🚀 Guide Rapide : NAS Synology (5 minutes)

```bash
# 1. Créer le dossier
mkdir /volume1/docker/linkedin-bot

# 2. Créer .env (avec vos identifiants)
nano /volume1/docker/linkedin-bot/.env

# 3. Créer le Dockerfile (copier le contenu du guide)
nano /volume1/docker/linkedin-bot/Dockerfile

# 4. Builder l'image
cd /volume1/docker/linkedin-bot
sudo docker build -t linkedin-bot .

# 5. Lancer le conteneur
sudo docker run -d \
  --name linkedin-bot \
  --restart unless-stopped \
  -v /volume1/docker/linkedin-bot/.env:/app/.env:ro \
  linkedin-bot:latest

# 6. Configurer Task Scheduler (via DSM)
# Script : docker start linkedin-bot
# Schedule : Daily @ 8:30

# 7. Vérifier
sudo docker logs -f linkedin-bot
```

✅ **C'est tout !** Votre bot tourne sur votre NAS avec votre IP résidentielle !

---

## 📱 Accéder au Dashboard depuis votre Téléphone

### Sur NAS Synology

1. **Exposer le port Flask** dans Docker :
   ```bash
   sudo docker run -d \
     --name linkedin-bot \
     -p 5000:5000 \
     -v /volume1/docker/linkedin-bot/.env:/app/.env:ro \
     linkedin-bot:latest \
     python app.py
   ```

2. **Accéder via navigateur** :
   ```
   http://votre-nas.local:5000
   # ou
   http://192.168.x.x:5000
   ```

3. **Accès externe (optionnel)** :
   - Configurer QuickConnect sur Synology
   - Ou créer un reverse proxy

---

## 🆘 Dépannage

### NAS Synology : Erreur Docker

```bash
# Vérifier que Docker tourne
sudo docker ps -a

# Voir les logs d'erreur
sudo docker logs linkedin-bot

# Reconstruire si nécessaire
sudo docker stop linkedin-bot
sudo docker rm linkedin-bot
sudo docker rmi linkedin-bot
# Puis rebuild
```

### Freebox : Commandes Non Trouvées

```bash
# Vérifier le PATH
echo $PATH

# Installer Entware pour avoir plus d'outils
# (voir documentation Entware)
```

### Problèmes de Permissions

```bash
# Sur NAS
sudo chmod +x run.sh
sudo chown -R admin:users /volume1/docker/linkedin-bot

# Sur Freebox
chmod +x run.sh
```

---

## ✅ Checklist de Validation

- [ ] SSH activé et accessible
- [ ] Python 3.8+ installé ou Docker disponible
- [ ] Projet cloné dans le bon dossier
- [ ] Fichier .env créé avec identifiants
- [ ] Test manuel réussi
- [ ] Tâche automatisée configurée
- [ ] Logs accessibles et lisibles
- [ ] Premier run successful visible dans les logs

---

## 🎉 Félicitations !

Votre bot LinkedIn tourne maintenant sur votre **NAS/Freebox** avec votre **IP résidentielle** :

✅ **0€ de coût supplémentaire**
✅ **Indétectable par LinkedIn**
✅ **Totalement automatisé**
✅ **Accessible depuis votre réseau local**

Profitez ! 🚀
