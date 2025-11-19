# 🎯 Guide Pas-à-Pas : Installation sur NAS Synology

Guide complet et détaillé pour installer le bot LinkedIn Birthday sur votre **NAS Synology** en utilisant Docker. Aucune connaissance technique avancée requise !

---

## ⏱️ Temps Estimé : 30 minutes

- Configuration initiale : 10 minutes
- Construction Docker : 15 minutes
- Tests et validation : 5 minutes

---

## 📋 Prérequis

✅ NAS Synology avec DSM 7.0 ou supérieur
✅ Au moins 1GB d'espace disque disponible
✅ Connexion Internet stable
✅ Vos identifiants LinkedIn

---

## 🚀 ÉTAPE 1 : Installer Container Manager (Docker)

### 1.1 Ouvrir Package Center

1. Connectez-vous à votre **NAS Synology** via DSM (Interface Web)
   - Adresse : `http://votre-nas.local:5000` ou `http://192.168.x.x:5000`
   - Identifiants : Votre compte administrateur

2. Cliquez sur le **Menu Principal** (coin supérieur gauche)

3. Sélectionnez **Package Center**

### 1.2 Installer Container Manager

1. Dans la barre de recherche, tapez : **Container Manager**
   - Anciennement appelé "Docker"

2. Cliquez sur **Container Manager** dans les résultats

3. Cliquez sur le bouton **Installer**

4. Attendez la fin de l'installation (2-3 minutes)

5. Une fois installé, cliquez sur **Ouvrir**

✅ **Validation** : L'interface Container Manager s'ouvre avec les onglets Projet, Conteneur, Registre, Image, Réseau, Journal

---

## 🔧 ÉTAPE 2 : Activer SSH (Optionnel mais Recommandé)

SSH permet d'utiliser des commandes directement sur le NAS.

### 2.1 Activer le Service SSH

1. Menu Principal → **Panneau de configuration**

2. Section **Terminal & SNMP**

3. Onglet **Terminal**

4. ☑️ Cocher **Activer le service SSH**

5. Port : Laisser **22** (par défaut)

6. Cliquer sur **Appliquer**

✅ **Validation** : "Le service SSH a été activé avec succès"

### 2.2 Tester la Connexion SSH

**Sur Mac/Linux :**
```bash
# Ouvrir le Terminal et taper :
ssh admin@votre-nas.local

# Ou avec l'IP
ssh admin@192.168.x.x
```

**Sur Windows :**
```powershell
# Ouvrir PowerShell et taper :
ssh admin@votre-nas.local
```

Entrer votre mot de passe administrateur quand demandé.

✅ **Validation** : Vous voyez `admin@NomDeVotreNAS:~$`

---

## 📁 ÉTAPE 3 : Créer la Structure de Dossiers

### 3.1 Via File Station (Interface Graphique)

1. Menu Principal → **File Station**

2. Naviguer vers **docker** (créer ce dossier s'il n'existe pas)
   - Clic droit sur **volume1** → **Créer un dossier** → Nom : `docker`

3. Dans le dossier `docker`, créer un nouveau dossier : `linkedin-bot`

4. Créer 2 sous-dossiers dans `linkedin-bot` :
   - `data` (pour la base de données)
   - `logs` (pour les logs)

**Structure finale :**
```
/volume1/
  └── docker/
      └── linkedin-bot/
          ├── data/
          └── logs/
```

### 3.2 Via SSH (Alternative)

```bash
# Se connecter en SSH
ssh admin@votre-nas.local

# Créer les dossiers
sudo mkdir -p /volume1/docker/linkedin-bot/data
sudo mkdir -p /volume1/docker/linkedin-bot/logs

# Vérifier
ls -la /volume1/docker/linkedin-bot/
```

✅ **Validation** : Les 3 dossiers existent

---

## 📝 ÉTAPE 4 : Créer les Fichiers de Configuration

### 4.1 Créer le Dockerfile

**Via File Station :**

1. Dans File Station, naviguer vers `/volume1/docker/linkedin-bot`

2. Clic droit → **Créer** → **Créer un fichier texte**

3. Nom du fichier : `Dockerfile` (exactement, sans extension)

4. Cliquer sur **Créer**

5. Double-cliquer sur `Dockerfile` pour l'éditer

6. Copier-coller EXACTEMENT ce contenu :

```dockerfile
FROM python:3.11-slim

# Définir les variables d'environnement
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Mettre à jour et installer les dépendances système de base
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances pour Playwright/Chromium
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
    libatspi2.0-0 \
    libxshmfence1 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Cloner le projet GitHub
RUN git clone https://github.com/GaspardD78/linkedin-birthday-auto.git .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Installer Playwright et Chromium
RUN playwright install chromium && \
    playwright install-deps chromium

# Créer les dossiers nécessaires
RUN mkdir -p /app/data /app/logs

# Point d'entrée par défaut
CMD ["python3", "linkedin_birthday_wisher.py"]
```

7. Cliquer sur **Enregistrer**

### 4.2 Créer le Fichier .env

1. Toujours dans `/volume1/docker/linkedin-bot`

2. Créer un nouveau fichier texte : `.env`

3. Double-cliquer pour éditer

4. Copier ce contenu et **REMPLACER** par vos vraies informations :

```bash
# Identifiants LinkedIn
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=VotreMotDePasse123!

# Mode de fonctionnement
DRY_RUN=true
# Mettre à false pour envoyer de vrais messages

# Paramètres du navigateur
HEADLESS_BROWSER=true
# true = mode invisible, false = voir le navigateur

# Proxies (désactivé car on utilise l'IP résidentielle du NAS)
ENABLE_PROXY_ROTATION=false

# Debug avancé (optionnel)
ENABLE_ADVANCED_DEBUG=false

# Alertes email (optionnel)
ENABLE_EMAIL_ALERTS=false
```

5. **IMPORTANT** : Remplacer :
   - `votre.email@example.com` par votre email LinkedIn
   - `VotreMotDePasse123!` par votre mot de passe LinkedIn

6. Cliquer sur **Enregistrer**

⚠️ **SÉCURITÉ** : Le fichier `.env` contient vos identifiants. Ne le partagez jamais !

✅ **Validation** : Vous avez maintenant 2 fichiers dans `/volume1/docker/linkedin-bot` :
- `Dockerfile`
- `.env`

---

## 🏗️ ÉTAPE 5 : Construire l'Image Docker

### 5.1 Via SSH (Méthode Recommandée)

```bash
# Se connecter au NAS
ssh admin@votre-nas.local

# Aller dans le dossier
cd /volume1/docker/linkedin-bot

# Construire l'image (prend 5-10 minutes)
sudo docker build -t linkedin-bot:latest .

# Voir la progression :
# - Téléchargement de Python
# - Installation des dépendances
# - Clone du projet GitHub
# - Installation de Playwright
# - Installation de Chromium
```

**Sortie attendue** (dernières lignes) :
```
Successfully built abc123def456
Successfully tagged linkedin-bot:latest
```

### 5.2 Via Container Manager (Alternative)

1. Ouvrir **Container Manager**

2. Onglet **Image**

3. Cliquer sur **Ajouter** → **Ajouter depuis fichier**

4. ⚠️ Cette méthode est plus complexe, SSH est recommandé

✅ **Validation** :
```bash
# Vérifier que l'image existe
sudo docker images | grep linkedin-bot
```

Vous devez voir :
```
linkedin-bot    latest    abc123def456    2 minutes ago    1.5GB
```

---

## 🚀 ÉTAPE 6 : Créer et Lancer le Conteneur

### 6.1 Créer le Conteneur

**Via SSH :**

```bash
# Lancer le conteneur
sudo docker run -d \
  --name linkedin-birthday-bot \
  --restart unless-stopped \
  --env-file /volume1/docker/linkedin-bot/.env \
  -v /volume1/docker/linkedin-bot/data:/app/data \
  -v /volume1/docker/linkedin-bot/logs:/app/logs \
  linkedin-bot:latest

# Explication des options :
# -d                     : Mode détaché (arrière-plan)
# --name                 : Nom du conteneur
# --restart unless-stopped : Redémarre auto après reboot NAS
# --env-file             : Charger les variables d'environnement
# -v                     : Monter les volumes (data et logs)
```

**Sortie attendue** :
```
abc123def456789...
```
(ID du conteneur)

### 6.2 Via Container Manager (Alternative)

1. Container Manager → Onglet **Conteneur**

2. Cliquer sur **Créer**

3. Sélectionner l'image `linkedin-bot:latest`

4. Configuration :
   - **Nom du conteneur** : `linkedin-birthday-bot`
   - **Activer le redémarrage automatique** : ☑️ Oui

5. **Variables d'environnement** → **Importer depuis fichier**
   - Sélectionner `/volume1/docker/linkedin-bot/.env`

6. **Volumes** :
   - Volume 1 :
     - Dossier : `/volume1/docker/linkedin-bot/data`
     - Point de montage : `/app/data`
   - Volume 2 :
     - Dossier : `/volume1/docker/linkedin-bot/logs`
     - Point de montage : `/app/logs`

7. Cliquer sur **Appliquer**

✅ **Validation** :
```bash
# Vérifier que le conteneur tourne
sudo docker ps | grep linkedin
```

Vous devez voir :
```
abc123    linkedin-bot:latest    ...    Up 2 minutes    linkedin-birthday-bot
```

---

## 📊 ÉTAPE 7 : Vérifier les Logs et Tester

### 7.1 Voir les Logs en Temps Réel

**Via SSH :**
```bash
# Suivre les logs en direct
sudo docker logs -f linkedin-birthday-bot

# Ou voir les 50 dernières lignes
sudo docker logs --tail 50 linkedin-birthday-bot
```

**Via Container Manager :**
1. Onglet **Conteneur**
2. Sélectionner `linkedin-birthday-bot`
3. Cliquer sur **Détails**
4. Onglet **Journal**

### 7.2 Vérifier que Tout Fonctionne

**Logs attendus** (si tout va bien) :

```
✅ Playwright stealth mode activated
✅ Connexion à LinkedIn réussie
✅ Navigation vers la page des anniversaires
🔍 Validation des sélecteurs...
✅ X anniversaires trouvés aujourd'hui
```

**En mode DRY_RUN=true**, vous verrez :
```
🧪 DRY RUN MODE - Aucun message ne sera envoyé
✅ Message simulé pour : Jean Dupont
✅ Message simulé pour : Marie Martin
```

**Si erreur de connexion LinkedIn :**
```
❌ Échec de la connexion à LinkedIn
```
→ Vérifier vos identifiants dans `.env`

### 7.3 Tester Manuellement (Première Fois)

```bash
# Arrêter le conteneur actuel
sudo docker stop linkedin-birthday-bot

# Le supprimer
sudo docker rm linkedin-birthday-bot

# Vérifier le fichier .env
cat /volume1/docker/linkedin-bot/.env

# Recréer avec les bons identifiants
sudo docker run -d \
  --name linkedin-birthday-bot \
  --restart unless-stopped \
  --env-file /volume1/docker/linkedin-bot/.env \
  -v /volume1/docker/linkedin-bot/data:/app/data \
  -v /volume1/docker/linkedin-bot/logs:/app/logs \
  linkedin-bot:latest

# Vérifier les logs
sudo docker logs -f linkedin-birthday-bot
```

✅ **Validation** : Les logs montrent une connexion réussie et la détection des anniversaires

---

## ⏰ ÉTAPE 8 : Automatiser l'Exécution Quotidienne

### 8.1 Créer une Tâche Planifiée

1. Menu Principal → **Panneau de configuration**

2. **Planificateur de tâches**

3. Cliquer sur **Créer** → **Tâche planifiée** → **Script défini par l'utilisateur**

### 8.2 Configuration de la Tâche

**Onglet Général :**
- **Nom de la tâche** : `LinkedIn Birthday Bot`
- **Utilisateur** : `root`
- ☑️ **Activé**

**Onglet Planification :**
- **Fréquence** : Quotidien
- **Heure** : `08:30` (ou l'heure souhaitée)
- **Fréquence** : Tous les jours
- ☑️ **Lundi à Dimanche** (tous cochés)

**Onglet Paramètres de la tâche :**
- **Envoyer les détails d'exécution par email** : ☑️ (optionnel)
  - Email : votre email

- **Script défini par l'utilisateur** :

```bash
#!/bin/bash

# Log de début
echo "================================" >> /volume1/docker/linkedin-bot/logs/scheduler.log
echo "Exécution du $(date)" >> /volume1/docker/linkedin-bot/logs/scheduler.log

# Arrêter le conteneur s'il tourne encore
docker stop linkedin-birthday-bot 2>/dev/null
docker rm linkedin-birthday-bot 2>/dev/null

# Redémarrer avec une exécution fraîche
docker run --rm \
  --name linkedin-birthday-bot \
  --env-file /volume1/docker/linkedin-bot/.env \
  -v /volume1/docker/linkedin-bot/data:/app/data \
  -v /volume1/docker/linkedin-bot/logs:/app/logs \
  linkedin-bot:latest

# Log de fin
echo "Terminé à $(date)" >> /volume1/docker/linkedin-bot/logs/scheduler.log
echo "================================" >> /volume1/docker/linkedin-bot/logs/scheduler.log
```

4. Cliquer sur **OK**

### 8.3 Tester l'Exécution Planifiée

1. Dans le **Planificateur de tâches**, sélectionner votre tâche

2. Cliquer sur **Exécuter**

3. Attendre quelques secondes

4. Vérifier les logs :
```bash
tail -f /volume1/docker/linkedin-bot/logs/scheduler.log
```

✅ **Validation** : Le script s'exécute et crée des logs dans `scheduler.log`

---

## 🎛️ ÉTAPE 9 : Passer en Mode Production

### 9.1 Vérifier que Tout Marche en DRY_RUN

Après avoir testé plusieurs fois en mode `DRY_RUN=true`, vérifier :

✅ Connexion LinkedIn réussie
✅ Détection des anniversaires
✅ Messages simulés visibles dans les logs
✅ Aucune erreur

### 9.2 Activer le Mode Production

1. Via File Station, éditer `.env` :

**Avant :**
```bash
DRY_RUN=true
```

**Après :**
```bash
DRY_RUN=false
```

2. Sauvegarder

3. Redémarrer le conteneur :
```bash
sudo docker restart linkedin-birthday-bot
```

⚠️ **ATTENTION** : À partir de maintenant, le bot **envoie de vrais messages** !

### 9.3 Surveiller la Première Exécution Réelle

```bash
# Suivre les logs
sudo docker logs -f linkedin-birthday-bot
```

Vous devriez voir :
```
✅ Message envoyé à : Jean Dupont
✅ Message envoyé à : Marie Martin
📊 Total : 2 messages envoyés
```

✅ **Validation** : Les messages sont envoyés sur LinkedIn

---

## 📱 ÉTAPE 10 : Accéder au Dashboard Web (Optionnel)

### 10.1 Lancer le Dashboard

```bash
# Créer un second conteneur pour le dashboard
sudo docker run -d \
  --name linkedin-dashboard \
  --restart unless-stopped \
  -p 5000:5000 \
  -v /volume1/docker/linkedin-bot/data:/app/data \
  linkedin-bot:latest \
  python3 app.py
```

### 10.2 Accéder au Dashboard

1. Ouvrir un navigateur (sur PC, téléphone, tablette)

2. Aller sur :
```
http://votre-nas.local:5000
# ou
http://192.168.x.x:5000
```

3. Vous verrez :
   - Statistiques des messages envoyés
   - Graphiques de performance
   - Métriques des proxies (si activés)
   - Logs en temps réel

✅ **Validation** : Le dashboard s'affiche correctement

---

## 🔍 ÉTAPE 11 : Surveillance et Maintenance

### 11.1 Vérifier les Logs Quotidiennement (Première Semaine)

```bash
# Logs du bot
sudo docker logs --tail 100 linkedin-birthday-bot

# Logs du scheduler
tail -f /volume1/docker/linkedin-bot/logs/scheduler.log
```

### 11.2 Consulter la Base de Données

```bash
# Se connecter au conteneur
sudo docker exec -it linkedin-birthday-bot /bin/bash

# Ouvrir la base de données
sqlite3 /app/data/linkedin_birthday.db

# Voir les derniers messages envoyés
SELECT * FROM birthday_messages ORDER BY timestamp DESC LIMIT 10;

# Quitter
.exit
exit
```

### 11.3 Sauvegardes Automatiques

**Via Planificateur de Tâches** :

1. Créer une nouvelle tâche : `LinkedIn Backup`

2. Planification : Hebdomadaire, Dimanche, 00:00

3. Script :
```bash
#!/bin/bash

# Dossier de backup
BACKUP_DIR="/volume1/docker/linkedin-bot/backups"
mkdir -p "$BACKUP_DIR"

# Date du jour
DATE=$(date +%Y%m%d)

# Copier la base de données
cp /volume1/docker/linkedin-bot/data/linkedin_birthday.db \
   "$BACKUP_DIR/linkedin_birthday_$DATE.db"

# Garder seulement les 30 derniers backups
ls -t "$BACKUP_DIR"/*.db | tail -n +31 | xargs rm -f

echo "Backup créé : linkedin_birthday_$DATE.db"
```

✅ **Validation** : Un backup est créé chaque dimanche

---

## ⚙️ PARAMÈTRES AVANCÉS (Optionnel)

### Heure Aléatoire d'Exécution

Pour plus de discrétion, modifier le script du planificateur :

```bash
#!/bin/bash

# Attendre un délai aléatoire entre 0 et 2 heures
DELAY=$((RANDOM % 7200))
echo "Attente de $DELAY secondes..." >> /volume1/docker/linkedin-bot/logs/scheduler.log
sleep $DELAY

# Puis exécuter normalement
docker run --rm \
  --name linkedin-birthday-bot \
  --env-file /volume1/docker/linkedin-bot/.env \
  -v /volume1/docker/linkedin-bot/data:/app/data \
  -v /volume1/docker/linkedin-bot/logs:/app/logs \
  linkedin-bot:latest
```

Ainsi, si la tâche est programmée à 8h, elle s'exécutera entre 8h et 10h aléatoirement.

---

## 🆘 DÉPANNAGE

### Problème 1 : "Permission denied" lors de docker build

**Solution :**
```bash
# Ajouter sudo devant les commandes
sudo docker build -t linkedin-bot:latest .
```

### Problème 2 : Le conteneur s'arrête immédiatement

**Diagnostic :**
```bash
# Voir pourquoi il s'est arrêté
sudo docker logs linkedin-birthday-bot
```

**Causes fréquentes :**
- Erreur dans `.env` (identifiants incorrects)
- Dépendances manquantes
- Erreur de syntaxe

### Problème 3 : "Cannot connect to LinkedIn"

**Solutions :**

1. Vérifier les identifiants dans `.env`
```bash
cat /volume1/docker/linkedin-bot/.env
```

2. Vérifier que le NAS a accès à Internet
```bash
ping google.com
```

3. LinkedIn a peut-être activé le 2FA
   - Désactiver temporairement le 2FA
   - Ou utiliser un mot de passe d'application

### Problème 4 : Image Docker trop volumineuse

L'image fait ~1.5GB, c'est normal (Chromium inclus).

**Vérifier l'espace :**
```bash
df -h /volume1
```

Si manque d'espace :
```bash
# Nettoyer les images inutilisées
sudo docker system prune -a
```

### Problème 5 : Le planificateur ne s'exécute pas

**Vérifications :**

1. Tâche activée ? (☑️ dans Planificateur)

2. Utilisateur = `root` ?

3. Tester manuellement :
   - Sélectionner la tâche → Cliquer sur **Exécuter**

4. Voir les erreurs :
```bash
tail -f /var/log/messages | grep Task
```

---

## ✅ CHECKLIST DE VALIDATION FINALE

Avant de considérer l'installation terminée :

- [ ] Container Manager installé
- [ ] SSH activé (optionnel mais recommandé)
- [ ] Dossiers créés (`/volume1/docker/linkedin-bot/`)
- [ ] `Dockerfile` créé et correct
- [ ] `.env` créé avec VOS identifiants LinkedIn
- [ ] Image Docker construite (`docker images | grep linkedin-bot`)
- [ ] Conteneur créé et démarré (`docker ps | grep linkedin`)
- [ ] Logs visibles sans erreur (`docker logs linkedin-birthday-bot`)
- [ ] Test en DRY_RUN=true réussi
- [ ] Tâche planifiée créée (8h30 chaque jour)
- [ ] Test manuel de la tâche planifiée réussi
- [ ] (Optionnel) Dashboard Web accessible
- [ ] (Optionnel) Sauvegarde automatique configurée
- [ ] Mode production activé (DRY_RUN=false) si souhaité

---

## 🎉 FÉLICITATIONS !

Votre bot LinkedIn Birthday tourne maintenant sur votre **NAS Synology** !

### Ce qui se passe maintenant :

✅ Chaque jour à 8h30 (heure choisie), le bot :
1. Se connecte à LinkedIn avec votre IP résidentielle
2. Détecte les anniversaires du jour
3. Envoie un message personnalisé à chacun
4. Enregistre tout dans la base de données
5. Génère des logs détaillés

### Avantages de votre configuration :

- 🏠 **IP résidentielle** : Totalement indétectable par LinkedIn
- 💰 **0€ de coût** : Aucun frais de proxy
- 🔒 **Sécurité** : Identifiants chiffrés dans le conteneur
- 📊 **Traçabilité** : Tous les messages dans la base de données
- 🔄 **Automatique** : Aucune intervention requise
- 💪 **Fiable** : Redémarre automatiquement après reboot NAS

---

## 📚 Ressources Supplémentaires

- **Dashboard Web** : `http://votre-nas.local:5000`
- **Logs** : `/volume1/docker/linkedin-bot/logs/`
- **Base de données** : `/volume1/docker/linkedin-bot/data/linkedin_birthday.db`
- **Backups** : `/volume1/docker/linkedin-bot/backups/`

---

## 🔄 Mettre à Jour le Bot

Quand une nouvelle version sort sur GitHub :

```bash
# 1. Arrêter et supprimer l'ancien conteneur
sudo docker stop linkedin-birthday-bot
sudo docker rm linkedin-birthday-bot

# 2. Supprimer l'ancienne image
sudo docker rmi linkedin-bot:latest

# 3. Reconstruire avec la nouvelle version
cd /volume1/docker/linkedin-bot
sudo docker build -t linkedin-bot:latest .

# 4. Relancer
sudo docker run -d \
  --name linkedin-birthday-bot \
  --restart unless-stopped \
  --env-file /volume1/docker/linkedin-bot/.env \
  -v /volume1/docker/linkedin-bot/data:/app/data \
  -v /volume1/docker/linkedin-bot/logs:/app/logs \
  linkedin-bot:latest
```

---

## 💬 Support

Si vous rencontrez un problème :

1. **Consulter les logs** : `sudo docker logs linkedin-birthday-bot`
2. **Vérifier les issues GitHub** : [github.com/GaspardD78/linkedin-birthday-auto/issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)
3. **Tester manuellement** : Lancer le conteneur en mode interactif pour débugger

---

**Votre bot fonctionne ? Profitez de votre automatisation LinkedIn totalement transparente ! 🚀**
