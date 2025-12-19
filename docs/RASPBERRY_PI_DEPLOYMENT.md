# 🍓 Guide de Déploiement Raspberry Pi OS Lite 64-bit

Guide complet pour installer **LinkedIn Birthday Auto Bot** sur **Raspberry Pi OS Lite 64-bit** sans dépendance Git.

---

## 📋 Table des Matières

1. [Prérequis Matériels](#-prérequis-matériels)
2. [Installation du Système](#-installation-du-système)
3. [Méthode 1: Installation avec Git (Recommandée)](#-méthode-1-installation-avec-git-recommandée)
4. [Méthode 2: Installation sans Git (OS Lite)](#-méthode-2-installation-sans-git-os-lite)
5. [Configuration Post-Installation](#-configuration-post-installation)
6. [Optimisations pour Raspberry Pi](#-optimisations-pour-raspberry-pi)
7. [Dépannage](#-dépannage)

---

## 🖥️ Prérequis Matériels

### Configuration Minimale

- **Raspberry Pi 4** - 4GB RAM minimum (8GB recommandé)
- **Carte microSD** - 32GB minimum (Classe 10 / U3)
- **Alimentation** - 5V 3A officielle recommandée
- **Connexion réseau** - Ethernet recommandé (WiFi possible)

### Configuration Recommandée

- **Raspberry Pi 4** - 8GB RAM
- **Carte microSD** - 64GB+ (SanDisk Extreme ou Samsung EVO Plus)
- **Refroidissement** - Ventilateur ou dissipateurs passifs
- **Connexion réseau** - Ethernet pour stabilité

---

## 💿 Installation du Système

### 1. Télécharger Raspberry Pi OS Lite 64-bit

```bash
# Depuis votre ordinateur, téléchargez Raspberry Pi Imager:
# https://www.raspberrypi.com/software/

# Ou téléchargez l'image directement:
# https://www.raspberrypi.com/software/operating-systems/
```

**Sélectionnez:** Raspberry Pi OS Lite (64-bit) - Version Bookworm ou plus récente

### 2. Flasher la Carte SD

Avec **Raspberry Pi Imager**:
1. Choisir "Raspberry Pi OS Lite (64-bit)"
2. Sélectionner votre carte SD
3. **⚙️ Paramètres avancés** (engrenage en bas à droite):
   - ✅ Activer SSH
   - ✅ Configurer nom d'utilisateur/mot de passe
   - ✅ Configurer WiFi (si nécessaire)
   - ✅ Configurer locale/timezone
4. Écrire l'image

### 3. Premier Démarrage

```bash
# Insérer la carte SD dans le Raspberry Pi
# Démarrer le Pi

# Se connecter via SSH (ou clavier/écran local)
ssh votreuser@adresse-ip-du-pi

# Ou si vous avez configuré le hostname:
ssh votreuser@raspberrypi.local
```

### 4. Mise à Jour Système

```bash
# Mettre à jour le système (IMPORTANT)
sudo apt update && sudo apt upgrade -y

# Redémarrer si nécessaire
sudo reboot
```

---

## 🚀 Méthode 1: Installation avec Git (Recommandée)

Si vous pouvez installer Git (connexion Internet disponible), c'est la méthode la plus simple:

### Installer Git

```bash
sudo apt install git -y
```

### Cloner et Installer

```bash
# Cloner le dépôt
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# Lancer l'installation
chmod +x setup.sh
./setup.sh
```

**Suivez les instructions interactives** du script setup.sh (voir section Configuration).

---

## 📦 Méthode 2: Installation sans Git (OS Lite)

Si Git n'est pas disponible ou que vous préférez ne pas l'installer:

### Option A: Téléchargement Direct via wget/curl

```bash
# Créer un répertoire de travail
mkdir -p ~/linkedin-birthday-auto
cd ~/linkedin-birthday-auto

# Télécharger l'archive du projet (dernière version)
wget https://github.com/GaspardD78/linkedin-birthday-auto/archive/refs/heads/main.zip -O linkedin-bot.zip

# Installer unzip si nécessaire
sudo apt install unzip -y

# Extraire l'archive
unzip linkedin-bot.zip

# Déplacer le contenu dans le bon répertoire
mv linkedin-birthday-auto-main/* .
mv linkedin-birthday-auto-main/.* . 2>/dev/null || true
rmdir linkedin-birthday-auto-main
rm linkedin-bot.zip

# Rendre le script setup exécutable
chmod +x setup.sh

# Lancer l'installation
./setup.sh
```

### Option B: Téléchargement depuis un autre ordinateur

Si le Raspberry Pi n'a pas accès direct à Internet:

**Sur votre ordinateur:**

```bash
# Télécharger l'archive ZIP depuis GitHub
# https://github.com/GaspardD78/linkedin-birthday-auto/archive/refs/heads/main.zip

# Transférer via SCP au Raspberry Pi
scp linkedin-birthday-auto-main.zip votreuser@adresse-ip-du-pi:/home/votreuser/
```

**Sur le Raspberry Pi:**

```bash
# Installer unzip
sudo apt install unzip -y

# Créer le répertoire
mkdir -p ~/linkedin-birthday-auto
cd ~/linkedin-birthday-auto

# Extraire l'archive
unzip ~/linkedin-birthday-auto-main.zip

# Déplacer le contenu
mv linkedin-birthday-auto-main/* .
mv linkedin-birthday-auto-main/.* . 2>/dev/null || true
rmdir linkedin-birthday-auto-main

# Nettoyer
rm ~/linkedin-birthday-auto-main.zip

# Rendre le script setup exécutable
chmod +x setup.sh

# Lancer l'installation
./setup.sh
```

### Option C: Clé USB (Sans Réseau)

**Sur votre ordinateur:**

1. Télécharger le ZIP depuis GitHub
2. Copier sur une clé USB formatée en FAT32 ou exFAT

**Sur le Raspberry Pi:**

```bash
# Brancher la clé USB et identifier le périphérique
lsblk

# Monter la clé USB (remplacer sdX1 par votre device)
sudo mkdir -p /mnt/usb
sudo mount /dev/sda1 /mnt/usb

# Copier et installer
mkdir -p ~/linkedin-birthday-auto
cd ~/linkedin-birthday-auto

# Installer unzip
sudo apt install unzip -y

# Copier et extraire
cp /mnt/usb/linkedin-birthday-auto-main.zip .
unzip linkedin-birthday-auto-main.zip
mv linkedin-birthday-auto-main/* .
mv linkedin-birthday-auto-main/.* . 2>/dev/null || true
rmdir linkedin-birthday-auto-main

# Démonter la clé USB
sudo umount /mnt/usb

# Lancer l'installation
chmod +x setup.sh
./setup.sh
```

---

## ⚙️ Configuration Post-Installation

### Phase Interactive du Setup

Le script `setup.sh` vous posera **3 questions importantes**:

#### 1️⃣ Configuration HTTPS (Phase 4.7)

```
Choisissez votre configuration HTTPS:
1) LAN uniquement (HTTP simple, réseau interne)
2) Let's Encrypt (production, certificats automatiques)
3) Certificats existants (import certificats custom)
4) Configuration manuelle (vous gérez après setup)
```

**Recommandation pour démarrage:**
- **Choix 1** si vous testez en local (LAN uniquement)
- **Choix 2** si vous avez un domaine et accès Internet public

#### 2️⃣ Sauvegardes Google Drive (Phase 5.1)

```
Configurer les sauvegardes Google Drive?
1) Oui, activer avec chiffrement (recommandé)
2) Oui, activer sans chiffrement
3) Non, configurer plus tard
```

**Recommandation:**
- **Choix 3** pour premier déploiement (configurer plus tard)
- **Choix 1** pour production (après avoir configuré rclone)

#### 3️⃣ Rapport Sécurité (Automatique)

À la fin, vous verrez un rapport de sécurité:

```
════════════════════════════════════════════════════
RAPPORT DE SÉCURITÉ
════════════════════════════════════════════════════

1. Mot de passe Dashboard... ✓ OK (hash bcrypt)
2. HTTPS... ⚠ DEV (certificats auto-signés)
3. Sauvegardes Google Drive... ⚠ NON CONFIGURÉ
4. Fichier .env secrets... ✓ OK (pas de secrets en clair)

SCORE SÉCURITÉ : 2 / 4
⚠️ ATTENTION - Améliorations recommandées
```

---

## 🎯 Accéder au Dashboard

Une fois l'installation terminée:

```bash
# Le script affichera:
╔═══════════════════════════════════════════╗
║  Dashboard LinkedIn Birthday Auto Bot      ║
╠═══════════════════════════════════════════╣
║  URL HTTPS: https://votre-ip-locale       ║
║  URL HTTP:  http://votre-ip-locale:3000   ║
║  Login:     admin                          ║
║  Mot passe: [AFFICHÉ ICI]                 ║
╚═══════════════════════════════════════════╝
```

**Ouvrir dans votre navigateur:**
- `https://192.168.1.x` (remplacer par l'IP de votre Pi)
- Accepter le certificat auto-signé (si pas Let's Encrypt)
- Se connecter avec les identifiants affichés

---

## 🔧 Optimisations pour Raspberry Pi

### 1. Gestion Mémoire (Automatique)

Le script `setup.sh` configure automatiquement:
- ✅ ZRAM pour compression mémoire
- ✅ SWAP sur disque si nécessaire (2-4GB)
- ✅ Limites mémoire Docker optimisées

### 2. Performance Réseau

```bash
# Priorité Ethernet sur WiFi (recommandé)
sudo nmcli connection modify "Wired connection 1" connection.autoconnect-priority 10
sudo nmcli connection modify "WiFi" connection.autoconnect-priority 0
```

### 3. Refroidissement

Surveiller la température:

```bash
# Vérifier température CPU
vcgencmd measure_temp

# Si > 70°C en charge, envisager:
# - Ventilateur actif
# - Dissipateurs thermiques
# - Boîtier avec refroidissement
```

### 4. Stockage (Optionnel)

Pour améliorer les performances et la durabilité:

```bash
# Désactiver logs excessifs
sudo systemctl disable rsyslog

# Monter /tmp et /var/log en RAM
echo "tmpfs /tmp tmpfs defaults,noatime,mode=1777 0 0" | sudo tee -a /etc/fstab
echo "tmpfs /var/log tmpfs defaults,noatime,mode=0755 0 0" | sudo tee -a /etc/fstab

# Redémarrer
sudo reboot
```

⚠️ **Attention:** Les logs seront perdus au redémarrage

---

## 🛠️ Commandes Utiles Post-Installation

### Vérifier l'État des Services

```bash
# Tous les services Docker
docker compose -f docker-compose.pi4-standalone.yml ps

# Logs en temps réel
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Logs d'un service spécifique
docker compose logs -f dashboard
docker compose logs -f api
```

### Redémarrer les Services

```bash
# Redémarrer tous les services
docker compose -f docker-compose.pi4-standalone.yml restart

# Redémarrer un service spécifique
docker compose restart nginx
```

### Gérer le Mot de Passe

```bash
# Script interactif de gestion du mot de passe
./scripts/manage_dashboard_password.sh

# Options:
# 1) Changer le mot de passe
# 2) Réinitialiser (génère un mot de passe temporaire)
# 3) Afficher le statut
```

### Sauvegardes Manuelles

```bash
# Sauvegarder la base de données
mkdir -p ~/backups
sudo cp -r /var/lib/docker/volumes/linkedin-birthday-auto_db_data ~/backups/db-$(date +%Y%m%d-%H%M%S)

# Sauvegarder la configuration
tar czf ~/backups/config-$(date +%Y%m%d-%H%M%S).tar.gz config/ .env
```

---

## 🆕 Mise à Jour du Bot

### Avec Git (Si installé)

```bash
cd ~/linkedin-birthday-auto
git pull
./setup.sh
```

### Sans Git (Méthode manuelle)

```bash
# 1. Sauvegarder la configuration actuelle
cd ~/linkedin-birthday-auto
cp .env .env.backup
cp -r config config.backup

# 2. Télécharger la nouvelle version
wget https://github.com/GaspardD78/linkedin-birthday-auto/archive/refs/heads/main.zip -O update.zip
unzip -o update.zip

# 3. Copier les nouveaux fichiers (sans écraser .env et config)
rsync -av --exclude='.env' --exclude='config/' linkedin-birthday-auto-main/ .

# 4. Nettoyer
rm -rf linkedin-birthday-auto-main update.zip

# 5. Relancer le setup
./setup.sh
```

---

## 🔍 Dépannage

### Problème: Docker non trouvé

```bash
# Installer Docker
curl -fsSL https://get.docker.com | sh

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER
newgrp docker

# Vérifier
docker --version
```

### Problème: Permission denied

```bash
# Si "Permission denied" lors de l'accès Docker
sudo usermod -aG docker $USER
newgrp docker

# Ou redémarrer la session SSH
```

### Problème: Mémoire insuffisante

```bash
# Vérifier la mémoire disponible
free -h

# Le script setup.sh peut configurer SWAP automatiquement
# Ou manuellement:
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Modifier: CONF_SWAPSIZE=2048 (pour 2GB)
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Problème: Téléchargement très lent

```bash
# Si le téléchargement Docker est très lent:
# 1. Utiliser Ethernet au lieu de WiFi
# 2. Configurer un miroir Docker plus proche

# Éditer /etc/docker/daemon.json
sudo mkdir -p /etc/docker
echo '{
  "registry-mirrors": ["https://mirror.gcr.io"]
}' | sudo tee /etc/docker/daemon.json

sudo systemctl restart docker
```

### Problème: Setup.sh échoue

```bash
# Vérifier les logs
./setup.sh --verbose

# Ou voir les logs du script
tail -f /tmp/setup-*.log

# Mode reprise après erreur
./setup.sh --resume
```

### Problème: Port 80/443 déjà utilisé

```bash
# Identifier le processus
sudo lsof -i :80
sudo lsof -i :443

# Arrêter le service conflictuel (exemple: apache2)
sudo systemctl stop apache2
sudo systemctl disable apache2

# Relancer le setup
./setup.sh
```

---

## 📊 Monitoring Système

### Surveillance Ressources

```bash
# CPU, RAM, température
htop

# Espace disque
df -h

# Température CPU
watch -n 2 vcgencmd measure_temp

# Stats Docker
docker stats
```

### Logs Système

```bash
# Logs kernel
sudo dmesg | tail

# Logs système
sudo journalctl -xe

# Logs Docker spécifiques
docker compose logs --tail=100 -f
```

---

## 🔒 Sécurité Post-Installation

### Recommandations Essentielles

1. **Changer le mot de passe Pi par défaut**
   ```bash
   passwd
   ```

2. **Configurer le firewall (UFW)**
   ```bash
   sudo apt install ufw -y
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow ssh
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **Désactiver SSH par mot de passe (utiliser clés)**
   ```bash
   # Copier votre clé publique
   ssh-copy-id votreuser@ip-du-pi

   # Puis désactiver auth par mot de passe
   sudo nano /etc/ssh/sshd_config
   # Modifier: PasswordAuthentication no
   sudo systemctl restart ssh
   ```

4. **Mettre à jour régulièrement**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

---

## 📚 Documentation Complémentaire

Pour plus de détails, consultez:

| Document | Description |
|----------|-------------|
| [QUICK_START_2025.md](QUICK_START_2025.md) | Guide de démarrage rapide |
| [SETUP_HTTPS_GUIDE.md](SETUP_HTTPS_GUIDE.md) | Configuration HTTPS détaillée |
| [SETUP_BACKUP_GUIDE.md](SETUP_BACKUP_GUIDE.md) | Configuration sauvegardes Google Drive |
| [PASSWORD_MANAGEMENT_GUIDE.md](PASSWORD_MANAGEMENT_GUIDE.md) | Gestion des mots de passe |
| [TROUBLESHOOTING_2025.md](TROUBLESHOOTING_2025.md) | Dépannage complet |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architecture technique |
| [SECURITY.md](SECURITY.md) | Sécurité et hardening |

---

## ✅ Checklist Installation Complète

- [ ] Raspberry Pi OS Lite 64-bit installé et à jour
- [ ] Connexion réseau stable configurée
- [ ] Docker installé et fonctionnel
- [ ] Projet téléchargé et extrait
- [ ] Script `setup.sh` exécuté avec succès
- [ ] Dashboard accessible via navigateur
- [ ] Mot de passe Dashboard sécurisé
- [ ] Compte LinkedIn configuré dans les settings
- [ ] Bots configurés (Birthday/Visitor)
- [ ] HTTPS configuré (Let's Encrypt ou certificats)
- [ ] Sauvegardes Google Drive configurées (optionnel)
- [ ] Firewall configuré (UFW)
- [ ] Monitoring système en place

---

## 🎉 Installation Terminée!

Votre **LinkedIn Birthday Auto Bot** est maintenant opérationnel sur votre Raspberry Pi! 🚀

**Questions ou problèmes?**
- Consultez [TROUBLESHOOTING_2025.md](TROUBLESHOOTING_2025.md)
- Ouvrez une Issue sur [GitHub](https://github.com/GaspardD78/linkedin-birthday-auto/issues)

---

**Développé avec ❤️ pour la communauté Raspberry Pi**
