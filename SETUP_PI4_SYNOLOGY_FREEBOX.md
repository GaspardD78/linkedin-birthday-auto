# 🏠 Configuration pour Raspberry Pi 4 + NAS Synology + Freebox Pop

Guide de configuration spécifique pour l'infrastructure **résidentielle** :
- **Raspberry Pi 4** (4 Go RAM)
- **NAS Synology DS213J**
- **Freebox Pop**

Ce guide **remplace** le guide générique et est **optimisé** pour cette configuration matérielle.

---

## 📋 Table des Matières

1. [Vue d'ensemble de l'architecture](#vue-densemble-de-larchitecture)
2. [Configuration réseau Freebox](#configuration-réseau-freebox)
3. [Configuration NAS Synology](#configuration-nas-synology)
4. [Installation sur Raspberry Pi 4](#installation-sur-raspberry-pi-4)
5. [Optimisations spécifiques](#optimisations-spécifiques)
6. [Surveillance et maintenance](#surveillance-et-maintenance)
7. [Troubleshooting](#troubleshooting)

---

## 🏗️ Vue d'ensemble de l'architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      INTERNET                               │
│                         │                                   │
│                    Freebox Pop                             │
│                  (IP Résidentielle)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │   Réseau Local        │
          │   192.168.1.0/24      │
          └───────────┬───────────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
  ┌───▼────┐    ┌────▼─────┐   ┌─────▼──────┐
  │ Pi 4   │    │ Synology │   │ PC/Laptop  │
  │ 4GB    │◄───┤ DS213J   │   │            │
  │        │NFS │ (Backup) │   │            │
  └────────┘    └──────────┘   └────────────┘
     │
     │ Exécute:
     │ - Bot LinkedIn (Docker)
     │ - Redis (Docker)
     │ - Cron jobs
```

### Rôles de chaque composant

| Composant | Rôle | Ressources |
|-----------|------|------------|
| **Freebox Pop** | - Connexion Internet<br>- IP résidentielle (légitime pour LinkedIn)<br>- DHCP/DNS local | - |
| **Raspberry Pi 4** | - Exécution du bot 24/7<br>- Docker containers<br>- Cron automation | - 4 Go RAM<br>- 32 Go SD card<br>- 3-5W |
| **Synology DS213J** | - Stockage des sauvegardes<br>- Logs archivés<br>- Base de données (optionnel) | - 512 Mo RAM<br>- Disques RAID |

---

## 🌐 Configuration réseau Freebox

### Étape 1 : Accéder à l'interface Freebox

1. Ouvrir http://mafreebox.freebox.fr
2. Se connecter avec les identifiants Freebox

### Étape 2 : Réserver une IP fixe pour le Pi 4

**Pourquoi ?** Pour pouvoir toujours accéder au Pi via SSH et surveiller le bot.

1. **Paramètres de la Freebox** → **DHCP**
2. **Baux DHCP statiques** → **Ajouter**
3. Renseigner :
   - **Nom :** `raspberry-pi-linkedin`
   - **Adresse MAC :** (récupérée avec `ip link show eth0` sur le Pi)
   - **IP souhaitée :** `192.168.1.50` (ou autre IP disponible)
4. **Sauvegarder**

### Étape 3 : Redirection de port SSH (optionnel)

Si vous voulez accéder au Pi depuis l'extérieur (⚠️ déconseillé pour la sécurité) :

1. **Paramètres de la Freebox** → **Gestion des ports**
2. **Ajouter une redirection**
3. Configurer :
   - **IP de destination :** `192.168.1.50`
   - **Port externe :** `2222`
   - **Port interne :** `22`
   - **Protocole :** TCP
4. **Sauvegarder**

**⚠️ Recommandation :** Utiliser plutôt un VPN (Wireguard) pour accéder au réseau local de façon sécurisée.

### Étape 4 : Vérifier l'IP publique Freebox

```bash
# Sur le Pi, vérifier l'IP publique
curl ifconfig.me
# Exemple: 90.XX.XX.XX (IP résidentielle française)
```

**Important :** Cette IP est **résidentielle**, LinkedIn la considère comme légitime (contrairement aux proxies datacenter).

---

## 💾 Configuration NAS Synology

### Option A : Partage NFS pour sauvegardes (Recommandé)

#### Sur le Synology DS213J

1. **Panneau de configuration** → **Services de fichiers** → **NFS**
2. **Activer NFS**
3. Créer un dossier partagé :
   - **Nom :** `LinkedInBot`
   - **Permissions :** Lecture/Écriture
4. **NFS Permissions** → **Créer**
   - **Nom d'hôte :** `192.168.1.50` (IP du Pi)
   - **Privilège :** Lecture/Écriture
   - **Squash :** Map all users to admin
   - **Sécurité :** `sys`

#### Sur le Raspberry Pi 4

```bash
# Installer le client NFS
sudo apt install -y nfs-common

# Créer le point de montage
sudo mkdir -p /mnt/synology

# Monter le partage NFS
sudo mount -t nfs 192.168.1.X:/volume1/LinkedInBot /mnt/synology

# Tester l'accès
ls -la /mnt/synology
touch /mnt/synology/test.txt
rm /mnt/synology/test.txt

# Rendre le montage permanent
echo "192.168.1.X:/volume1/LinkedInBot /mnt/synology nfs defaults 0 0" | sudo tee -a /etc/fstab
```

**Remplacer `192.168.1.X`** par l'IP de votre Synology.

### Option B : Partage SMB/CIFS (Alternative)

```bash
# Installer cifs-utils
sudo apt install -y cifs-utils

# Créer le point de montage
sudo mkdir -p /mnt/synology

# Créer fichier credentials
sudo nano /root/.smbcredentials
```

Contenu :
```
username=votre_user_synology
password=votre_mot_de_passe
```

```bash
# Sécuriser le fichier
sudo chmod 600 /root/.smbcredentials

# Monter le partage
sudo mount -t cifs //192.168.1.X/LinkedInBot /mnt/synology -o credentials=/root/.smbcredentials,uid=pi,gid=pi

# Rendre permanent
echo "//192.168.1.X/LinkedInBot /mnt/synology cifs credentials=/root/.smbcredentials,uid=pi,gid=pi 0 0" | sudo tee -a /etc/fstab
```

### Configurer les sauvegardes automatiques

```bash
# Script de sauvegarde vers NAS
nano ~/linkedin-birthday-auto/backup_to_nas.sh
```

Contenu :
```bash
#!/bin/bash

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/mnt/synology/backups"
SOURCE_DB="linkedin_automation.db"

# Créer le dossier de backup si nécessaire
mkdir -p "$BACKUP_DIR"

# Copier la base de données
if [ -f "$SOURCE_DB" ]; then
    cp "$SOURCE_DB" "$BACKUP_DIR/linkedin_automation_${DATE}.db"
    echo "✅ Backup créé: linkedin_automation_${DATE}.db"
else
    echo "❌ Erreur: base de données introuvable"
    exit 1
fi

# Conserver uniquement les 30 derniers backups
cd "$BACKUP_DIR"
ls -t | tail -n +31 | xargs -r rm --

echo "✅ Backup terminé avec succès"
```

```bash
# Rendre exécutable
chmod +x ~/linkedin-birthday-auto/backup_to_nas.sh

# Ajouter au crontab (backup quotidien à 3h du matin)
crontab -e
```

Ajouter :
```bash
0 3 * * * /home/pi/linkedin-birthday-auto/backup_to_nas.sh >> /home/pi/linkedin-birthday-auto/logs/backup.log 2>&1
```

---

## 🍓 Installation sur Raspberry Pi 4

### Prérequis matériel

✅ **Configuration testée et validée :**
- Raspberry Pi 4 Model B - 4 Go RAM
- Carte microSD 32 Go (Classe 10 / UHS-I)
- Alimentation USB-C 5V/3A officielle
- Câble Ethernet (connexion Freebox)

### Installation OS (voir RASPBERRY_PI4_GUIDE.md)

Suivre le guide [RASPBERRY_PI4_GUIDE.md](RASPBERRY_PI4_GUIDE.md) jusqu'à l'étape 9.

### Configuration système optimisée pour Pi 4

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Docker (méthode officielle)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker pi

# Installer Docker Compose
sudo apt install -y docker-compose

# Redémarrer pour appliquer les changements
sudo reboot
```

### Cloner le projet

```bash
cd ~
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto
```

### Configuration spécifique Pi 4

La configuration dans `config/config.yaml` a été **pré-optimisée** pour Pi 4 avec :
- ✅ User-Agent unique (économie RAM)
- ✅ Viewport unique 1366x768
- ✅ Limites de messages réduites (10/jour, 50/semaine)
- ✅ Délais réduits (90-180s)
- ✅ Proxy désactivé (IP Freebox résidentielle)

**Aucun changement nécessaire** si vous utilisez l'infrastructure Pi 4/Freebox !

### Créer le fichier .env

```bash
nano .env
```

Contenu minimal :
```bash
# Identifiants LinkedIn
LINKEDIN_EMAIL=votre.email@example.com
LINKEDIN_PASSWORD=VotreMotDePasse

# Mode test (mettre false pour production)
DRY_RUN=true

# Headless obligatoire sur Pi 4
HEADLESS_BROWSER=true
```

### Lancer avec Docker Compose

```bash
# Build les images (prend 10-15 min sur Pi 4)
docker-compose -f docker-compose.queue.yml build

# Lancer les services
docker-compose -f docker-compose.queue.yml up -d

# Vérifier les logs
docker-compose -f docker-compose.queue.yml logs -f
```

**Consommation mémoire attendue :**
```
CONTAINER           CPU %    MEM USAGE / LIMIT
linkedin-bot-redis  0.5%     50MiB / 300MiB
linkedin-bot-worker 15%      850MiB / 1.2GiB
TOTAL:                       ~900MiB / 4GiB (22% de RAM utilisée)
```

---

## ⚡ Optimisations spécifiques

### Optimisation 1 : Swap sur SD card

Le Pi 4 avec 4 Go a assez de RAM, mais on peut augmenter le swap en sécurité :

```bash
# Arrêter le swap
sudo dphys-swapfile swapoff

# Éditer la config
sudo nano /etc/dphys-swapfile
```

Modifier :
```
CONF_SWAPSIZE=1024
```

```bash
# Recréer le swap
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Vérifier
free -h
```

### Optimisation 2 : Overclocking modéré (optionnel)

**⚠️ Nécessite un ventilateur !**

```bash
sudo nano /boot/config.txt
```

Ajouter :
```
# Overclocking modéré Pi 4
over_voltage=2
arm_freq=1750
gpu_freq=600
```

```bash
sudo reboot
```

### Optimisation 3 : Désactiver services inutiles

```bash
# Désactiver Bluetooth (si non utilisé)
sudo systemctl disable bluetooth
sudo systemctl stop bluetooth

# Désactiver WiFi (si Ethernet branché)
sudo rfkill block wifi

# Désactiver GUI (si Pi en headless)
sudo systemctl set-default multi-user.target
```

### Optimisation 4 : Logs rotatifs

```bash
sudo nano /etc/logrotate.d/linkedin-bot
```

Contenu :
```
/home/pi/linkedin-birthday-auto/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 pi pi
}
```

### Optimisation 5 : Température CPU

Surveiller la température :

```bash
# Script de monitoring
nano ~/check_temp.sh
```

Contenu :
```bash
#!/bin/bash
TEMP=$(vcgencmd measure_temp | egrep -o '[0-9]*\.[0-9]*')
echo "$(date): Temp CPU = ${TEMP}°C"

if (( $(echo "$TEMP > 75" | bc -l) )); then
    echo "⚠️ ALERTE: Température élevée!"
    # Optionnel: envoyer une notification
fi
```

```bash
chmod +x ~/check_temp.sh

# Ajouter au cron (toutes les heures)
crontab -e
```

Ajouter :
```bash
0 * * * * /home/pi/check_temp.sh >> /home/pi/temp.log
```

---

## 📊 Surveillance et maintenance

### Monitoring Docker

```bash
# Voir les stats en temps réel
docker stats

# Voir les logs
docker-compose -f docker-compose.queue.yml logs -f rq-worker

# Redémarrer un service
docker-compose -f docker-compose.queue.yml restart rq-worker
```

### Vérifier l'espace disque

```bash
# Espace total
df -h

# Nettoyer Docker
docker system prune -a --volumes

# Nettoyer apt
sudo apt clean
sudo apt autoremove -y
```

### Vérifier la mémoire

```bash
# Mémoire utilisée
free -h

# Top processes
htop
```

### Backup automatique vers Synology

Vérifier que les backups fonctionnent :

```bash
# Lister les backups sur NAS
ls -lh /mnt/synology/backups/

# Vérifier le dernier backup
ls -lt /mnt/synology/backups/ | head -5
```

---

## 🐛 Troubleshooting

### Problème : "Cannot connect to Docker daemon"

```bash
# Vérifier que Docker est lancé
sudo systemctl status docker

# Si arrêté, le démarrer
sudo systemctl start docker

# Vérifier les permissions
groups
# Doit contenir "docker"

# Si pas dans le groupe:
sudo usermod -aG docker pi
# Puis se déconnecter/reconnecter
```

### Problème : "Out of memory" sur Pi 4

```bash
# Vérifier la mémoire
free -h

# Arrêter les containers
docker-compose -f docker-compose.queue.yml down

# Vérifier les limites Docker
docker stats

# Réduire les limites dans docker-compose.queue.yml:
# memory: 1.2G → memory: 1.0G
```

### Problème : NAS Synology non accessible

```bash
# Ping le NAS
ping 192.168.1.X

# Vérifier le montage NFS
mount | grep synology

# Tester manuellement
sudo mount -t nfs 192.168.1.X:/volume1/LinkedInBot /mnt/synology

# Vérifier les permissions NFS sur Synology
# (voir section Configuration NAS)
```

### Problème : Bot ne se lance pas

```bash
# Vérifier les logs
docker-compose -f docker-compose.queue.yml logs rq-worker

# Erreurs communes:
# 1. Auth state manquant → Générer auth_state.json
# 2. Config invalide → Vérifier config/config.yaml
# 3. RAM insuffisante → Réduire max_messages_per_run

# Lancer en mode debug
docker-compose -f docker-compose.queue.yml run --rm rq-worker python main.py --dry-run
```

### Problème : Température CPU > 80°C

```bash
# Vérifier la température
vcgencmd measure_temp

# Solutions:
# 1. Ajouter un ventilateur
# 2. Améliorer la ventilation
# 3. Réduire l'overclocking (si activé)
# 4. Limiter la charge (réduire les limites Docker)
```

### Problème : SD card pleine

```bash
# Vérifier l'espace
df -h

# Trouver les gros fichiers
du -sh /* 2>/dev/null | sort -h

# Nettoyer Docker
docker system prune -a --volumes

# Nettoyer les logs
sudo journalctl --vacuum-time=3d

# Nettoyer apt
sudo apt clean && sudo apt autoremove -y
```

---

## 📈 Métriques de performance attendues

Sur Raspberry Pi 4 (4 Go) avec cette configuration :

| Métrique | Valeur Attendue |
|----------|----------------|
| **RAM utilisée (idle)** | ~200 Mo |
| **RAM utilisée (bot actif)** | ~900 Mo - 1.2 Go |
| **CPU utilisation (bot actif)** | 15-25% |
| **Température CPU** | 45-65°C (avec ventilateur) |
| **Temps de traitement** | ~30s par message |
| **Consommation électrique** | 3-5W (~1€/mois) |
| **Temps de build Docker** | 10-15 minutes |
| **Temps de démarrage bot** | 30-45 secondes |

---

## ✅ Checklist de production

Avant de passer en production (`DRY_RUN=false`) :

- [ ] Pi 4 configuré avec IP fixe sur Freebox
- [ ] NAS Synology accessible via NFS/SMB
- [ ] Docker et Docker Compose installés
- [ ] `config/config.yaml` vérifié (limites conservatrices)
- [ ] `.env` créé avec identifiants LinkedIn
- [ ] `auth_state.json` généré (voir RASPBERRY_PI4_GUIDE.md)
- [ ] Backups automatiques vers NAS configurés
- [ ] Monitoring température CPU actif
- [ ] Tests en mode `DRY_RUN=true` réussis
- [ ] Logs consultables et rotation configurée
- [ ] Docker limité à 1.2 Go RAM
- [ ] Cron job configuré pour exécution quotidienne

---

## 🎯 Configuration finale recommandée

**Crontab (exécution quotidienne à 9h) :**
```bash
crontab -e
```

```bash
# LinkedIn Bot - Exécution quotidienne
0 9 * * * cd /home/pi/linkedin-birthday-auto && docker-compose -f docker-compose.queue.yml up >> /home/pi/linkedin-birthday-auto/logs/cron.log 2>&1

# Backup vers NAS - 3h du matin
0 3 * * * /home/pi/linkedin-birthday-auto/backup_to_nas.sh >> /home/pi/linkedin-birthday-auto/logs/backup.log 2>&1

# Health check - toutes les heures
0 * * * * /home/pi/check_temp.sh >> /home/pi/temp.log
```

---

## 📞 Support

**Infrastructure spécifique :**
- Pi 4 : https://www.raspberrypi.com/documentation/
- Synology : https://www.synology.com/fr-fr/support
- Freebox : https://www.free.fr/assistance/

**Bot LinkedIn :**
- GitHub : https://github.com/GaspardD78/linkedin-birthday-auto
- Issues : https://github.com/GaspardD78/linkedin-birthday-auto/issues

---

**✅ Configuration validée pour :**
- Raspberry Pi 4 Model B (4 Go RAM)
- Synology DS213J
- Freebox Pop
- Debian 11 (Bullseye) / Raspberry Pi OS

**Date de dernière mise à jour :** 22 novembre 2025
