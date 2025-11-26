# 🚀 Guide de déploiement Pi4 + Freebox Pop (Standalone)

Configuration simplifiée sans dépendance Synology NAS.

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Prérequis](#prérequis)
- [Architecture](#architecture)
- [Installation rapide](#installation-rapide)
- [Configuration détaillée](#configuration-détaillée)
- [Dépannage](#dépannage)
- [Maintenance](#maintenance)

---

## 🎯 Vue d'ensemble

Ce guide vous permet de déployer le bot LinkedIn Birthday sur un **Raspberry Pi 4** connecté à une **Freebox Pop**, sans utiliser de NAS Synology.

### Avantages de cette configuration

✅ **Simple** : Tout fonctionne sur le Pi4
✅ **IP résidentielle** : Via la Freebox Pop (légitime pour LinkedIn)
✅ **Économique** : Pas besoin de NAS externe
✅ **Faible consommation** : ~5W pour le Pi4
✅ **Toujours disponible** : Le Pi4 reste allumé 24/7

### Services déployés

- **Bot Worker** : Automatisation LinkedIn avec Playwright
- **Dashboard** : Interface web Next.js sur port 3000
- **Redis** : Queue pour les tâches (bot) + cache (dashboard)
- **SQLite** : Base de données locale partagée

---

## ⚙️ Prérequis

### Matériel

| Composant | Spécification |
|-----------|---------------|
| **Raspberry Pi** | Pi 4 Model B - **4GB RAM minimum** |
| **Carte SD** | 32GB minimum, Classe 10 (UHS-1 recommandé) |
| **Alimentation** | USB-C 5V/3A officielle Raspberry Pi |
| **Boîtier** | Avec ventilation (recommandé) |
| **Box Internet** | Freebox Pop ou autre box française |

### Logiciels

- **Raspberry Pi OS** : Lite (64-bit) recommandé
- **Docker** : Version 20.10+
- **Docker Compose** : Version 2.0+
- **Git** : Pour cloner le repo

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│         INTERNET (Freebox Pop)             │
│       IP Résidentielle Française           │
└────────────────┬────────────────────────────┘
                 │
        Réseau Local 192.168.1.0/24
                 │
        ┌────────▼─────────┐
        │  Raspberry Pi 4  │
        │    (4GB RAM)     │
        ├──────────────────┤
        │ ┌──────────────┐ │
        │ │ Bot Worker   │ │  LinkedIn automation
        │ │ (1.2GB RAM)  │ │  + Playwright
        │ └──────────────┘ │
        │ ┌──────────────┐ │
        │ │  Dashboard   │ │  Next.js (port 3000)
        │ │  (1GB RAM)   │ │  + API REST
        │ └──────────────┘ │
        │ ┌──────────────┐ │
        │ │Redis Bot     │ │  RQ Queue (256MB)
        │ │Redis Dash    │ │  Cache (128MB)
        │ └──────────────┘ │
        │ ┌──────────────┐ │
        │ │   SQLite     │ │  Base de données
        │ │  (local)     │ │  ./data/linkedin.db
        │ └──────────────┘ │
        └──────────────────┘

Utilisation mémoire: ~3.15GB / 4GB (79%)
```

---

## 🚀 Installation rapide

### 1. Préparer le Raspberry Pi 4

#### a) Installer Raspberry Pi OS

```bash
# 1. Télécharger Raspberry Pi Imager
# https://www.raspberrypi.com/software/

# 2. Flasher la carte SD avec:
#    - OS: Raspberry Pi OS Lite (64-bit)
#    - Configurer SSH, WiFi/Ethernet, utilisateur

# 3. Insérer la SD et démarrer le Pi4

# 4. Se connecter en SSH
ssh pi@192.168.1.X  # Remplacer X par l'IP du Pi
```

#### b) Mettre à jour le système

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl
```

#### c) Installer Docker

```bash
# Installation Docker (méthode officielle)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker $USER

# Déconnexion/reconnexion nécessaire
exit
# Reconnectez-vous en SSH
```

#### d) Vérifier Docker

```bash
docker --version
docker compose version

# Test
docker run hello-world
```

### 2. Cloner le dépôt

```bash
cd ~
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto
```

### 3. Configurer l'environnement

```bash
# Copier le template de configuration
cp .env.pi4 .env

# Éditer si nécessaire (optionnel)
nano .env
```

### 4. Déployer avec le script automatique

```bash
# Lancer le script de déploiement
./scripts/deploy_pi4_standalone.sh
```

Le script va :
- ✅ Vérifier les prérequis (Docker, RAM, disque)
- ✅ Créer les répertoires nécessaires
- ✅ Construire les images Docker (10-15 min)
- ✅ Démarrer tous les services
- ✅ Vérifier que tout fonctionne

### 5. Accéder au dashboard

```bash
# Récupérer l'IP du Pi4
hostname -I

# Accéder au dashboard depuis un navigateur:
# http://192.168.1.X:3000
```

**Connexion au dashboard** :
1. Ouvrez un navigateur et allez à `http://192.168.1.X:3000` (remplacez X par l'IP de votre Pi4)
2. Le dashboard est accessible directement sans authentification

---

## 🔧 Configuration détaillée

### Configuration Freebox Pop

#### 1. Attribuer une IP fixe au Pi4

1. Accéder à l'interface Freebox : http://mafreebox.freebox.fr
2. Aller dans **Paramètres réseau** > **DHCP**
3. Trouver le Pi4 dans la liste des clients
4. Cliquer sur **"Bail statique"**
5. Choisir une IP (ex: `192.168.1.50`)
6. Sauvegarder

#### 2. Vérifier l'IP résidentielle

```bash
# Sur le Pi4, vérifier l'IP publique
curl ifconfig.me

# Doit retourner une IP française résidentielle
# Exemple: 90.XX.XX.XX (Free, Orange, SFR, etc.)
```

### Configuration du bot

#### Fichier `config/config.yaml`

```yaml
version: "2.0.1"
dry_run: false
bot_mode: "standard"

browser:
  headless: true          # Obligatoire sur Pi4 sans écran
  slow_mo: [50, 100]
  locale: "fr-FR"
  timezone: "Europe/Paris"
  user_agents:
    - "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36"
  viewport_sizes:
    - width: 1366
      height: 768

messaging_limits:
  max_messages_per_run: 10
  weekly_message_limit: 50
  daily_message_limit: 10

delays:
  min_delay_seconds: 90    # 1.5 minutes
  max_delay_seconds: 180   # 3 minutes
```

### Authentification LinkedIn

```bash
# Se connecter au container du bot
docker exec -it linkedin-bot-worker bash

# Lancer l'authentification manuelle
python -m src.auth.manual_auth

# Suivre les instructions pour vous connecter
# Le fichier auth_state.json sera créé/mis à jour
```

---

## 📊 Gestion des services

### Commandes Docker Compose

```bash
# Démarrer tous les services
docker compose -f docker-compose.pi4-standalone.yml up -d

# Arrêter tous les services
docker compose -f docker-compose.pi4-standalone.yml down

# Redémarrer un service spécifique
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker

# Voir les logs en temps réel
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Voir les logs d'un service
docker compose -f docker-compose.pi4-standalone.yml logs -f dashboard

# Voir le statut des services
docker compose -f docker-compose.pi4-standalone.yml ps

# Voir l'utilisation des ressources
docker stats
```

### Redémarrage après modification

```bash
# Après modification du code
docker compose -f docker-compose.pi4-standalone.yml up -d --build

# Après modification de la config
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker
```

---

## 🔍 Vérification du déploiement

### Script de vérification

```bash
# Utiliser le script de vérification
./scripts/verify_rpi_docker.sh
```

Ce script vérifie :
- ✅ Info système (CPU, RAM, disque)
- ✅ Installation Docker
- ✅ Fichiers de configuration
- ✅ Statut des containers
- ✅ Connectivité réseau
- ✅ Logs et statistiques

### Vérifications manuelles

```bash
# 1. Vérifier que tous les containers tournent
docker ps

# Devrait montrer:
# - linkedin-bot-worker
# - linkedin-dashboard
# - linkedin-bot-redis
# - linkedin-dashboard-redis

# 2. Vérifier la santé des services
docker inspect linkedin-bot-redis | grep -A5 Health
docker inspect linkedin-dashboard | grep -A5 Health

# 3. Tester le dashboard
curl http://localhost:3000/api/health

# 4. Vérifier la base de données
ls -lh data/linkedin.db

# 5. Vérifier les logs
tail -f logs/*.log
```

---

## 🐛 Dépannage

### Problèmes courants

#### 1. "Cannot connect to the Docker daemon"

```bash
# Vérifier que Docker est démarré
sudo systemctl status docker

# Redémarrer Docker si nécessaire
sudo systemctl restart docker

# Vérifier que l'utilisateur est dans le groupe docker
groups | grep docker

# Si absent, ajouter et se reconnecter
sudo usermod -aG docker $USER
exit
# Reconnectez-vous
```

#### 2. "Out of memory" / Container killed

```bash
# Vérifier la RAM disponible
free -h

# Vérifier l'utilisation par les containers
docker stats

# Si nécessaire, réduire les limites dans docker-compose.pi4-standalone.yml
# Exemple: Bot Worker 1.2GB → 1GB, Dashboard 1GB → 800MB
```

#### 3. Dashboard inaccessible (port 3000)

```bash
# Vérifier que le container dashboard tourne
docker ps | grep dashboard

# Vérifier les logs
docker logs linkedin-dashboard

# Vérifier que le port n'est pas déjà utilisé
sudo netstat -tlnp | grep 3000

# Tester depuis le Pi4
curl http://localhost:3000

# Vérifier le firewall (si activé)
sudo ufw status
sudo ufw allow 3000/tcp
```

#### 4. Bot Worker crash au démarrage

```bash
# Voir les logs détaillés
docker logs linkedin-bot-worker

# Problèmes courants:
# - Fichier config/config.yaml manquant
# - Format config.yaml invalide
# - Dépendances Python manquantes

# Vérifier la config
cat config/config.yaml

# Reconstruire l'image
docker compose -f docker-compose.pi4-standalone.yml build --no-cache bot-worker
docker compose -f docker-compose.pi4-standalone.yml up -d bot-worker
```

#### 5. Redis warning "vm.overcommit_memory"

```bash
# Sur l'hôte Pi4, exécuter:
sudo sysctl vm.overcommit_memory=1

# Pour rendre permanent:
echo "vm.overcommit_memory = 1" | sudo tee -a /etc/sysctl.conf
```

#### 6. Build Docker très lent sur Pi4

C'est normal ! La construction peut prendre 10-20 minutes sur ARM64.

```bash
# Astuce: Build en arrière-plan
docker compose -f docker-compose.pi4-standalone.yml build &

# Surveiller la progression
docker ps -a
docker logs -f <container_id>
```

---

## 🔒 Sécurité

### Accès externe sécurisé (optionnel)

Pour accéder au dashboard depuis l'extérieur, **ne PAS** ouvrir le port 3000 sur la Freebox.

#### Option 1: VPN Wireguard (recommandé)

```bash
# Installer Wireguard sur le Pi4
sudo apt install wireguard

# Configurer Wireguard
# (Voir guide complet: docs/WIREGUARD_SETUP.md)
```

#### Option 2: SSH Tunnel

```bash
# Depuis votre PC à distance
ssh -L 3000:localhost:3000 pi@<IP_PUBLIQUE_FREEBOX>

# Accéder au dashboard sur:
# http://localhost:3000
```

### Mises à jour de sécurité

```bash
# Mettre à jour le système régulièrement
sudo apt update && sudo apt upgrade -y

# Mettre à jour Docker
sudo apt install docker-ce docker-ce-cli

# Mettre à jour les images
docker compose -f docker-compose.pi4-standalone.yml pull
docker compose -f docker-compose.pi4-standalone.yml up -d
```

---

## 🔄 Maintenance

### Sauvegardes

```bash
# Sauvegarde manuelle de la base de données
cp data/linkedin.db data/linkedin.db.backup.$(date +%Y%m%d)

# Sauvegarde automatique (cron)
crontab -e

# Ajouter cette ligne pour sauvegarde quotidienne à 3h
0 3 * * * cp ~/linkedin-birthday-auto/data/linkedin.db ~/linkedin-birthday-auto/data/linkedin.db.backup.$(date +\%Y\%m\%d)

# Conserver seulement les 30 dernières sauvegardes
0 4 * * * find ~/linkedin-birthday-auto/data/ -name "linkedin.db.backup.*" -mtime +30 -delete
```

### Nettoyage Docker

```bash
# Supprimer les images inutilisées
docker image prune -a

# Supprimer les volumes inutilisés
docker volume prune

# Supprimer les containers arrêtés
docker container prune

# Tout nettoyer (attention !)
docker system prune -a --volumes
```

### Monitoring

```bash
# Utilisation en temps réel
docker stats

# Logs des dernières 24h
docker compose -f docker-compose.pi4-standalone.yml logs --since 24h

# Espace disque utilisé par Docker
docker system df
```

### Mise à jour du bot

```bash
cd ~/linkedin-birthday-auto

# Récupérer les dernières modifications
git pull origin main

# Reconstruire et redémarrer
docker compose -f docker-compose.pi4-standalone.yml up -d --build
```

---

## 📈 Optimisations

### Améliorer les performances

```bash
# 1. Activer le swap si nécessaire (si RAM insuffisante)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Changer CONF_SWAPSIZE=100 à CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# 2. Overclock modéré du Pi4 (optionnel)
sudo nano /boot/config.txt
# Ajouter:
# over_voltage=2
# arm_freq=1750
# gpu_freq=600

# 3. Réduire la température (ventilation)
# Installer un ventilateur actif ou un boîtier avec dissipateur

# 4. Utiliser une SD rapide
# UHS-1 U3 ou mieux, A2 (Application Performance Class 2)
```

### Réduire l'utilisation mémoire

Si vous avez moins de 4GB de RAM :

```yaml
# Dans docker-compose.pi4-standalone.yml

bot-worker:
  deploy:
    resources:
      limits:
        memory: 1G      # Réduit de 1.2GB
      reservations:
        memory: 600M    # Réduit de 800MB

dashboard:
  deploy:
    resources:
      limits:
        memory: 800M    # Réduit de 1GB
      reservations:
        memory: 400M    # Réduit de 600MB
```

---

## 📚 Ressources

### Documentation

- [Guide Pi4 complet](RASPBERRY_PI4_GUIDE.md)
- [Troubleshooting Pi4](docs/RASPBERRY_PI_TROUBLESHOOTING.md)
- [Architecture du bot](ARCHITECTURE.md)
- [Déploiement général](DEPLOYMENT.md)

### Commandes utiles

```bash
# Alias pratiques (ajouter à ~/.bashrc)
alias dc='docker compose -f docker-compose.pi4-standalone.yml'
alias dcup='docker compose -f docker-compose.pi4-standalone.yml up -d'
alias dcdown='docker compose -f docker-compose.pi4-standalone.yml down'
alias dclogs='docker compose -f docker-compose.pi4-standalone.yml logs -f'
alias dcstats='docker stats'

# Recharger le .bashrc
source ~/.bashrc

# Utilisation:
dcup        # Démarrer
dclogs      # Voir les logs
dcdown      # Arrêter
```

---

## ❓ FAQ

**Q: Puis-je utiliser un Pi3 ou Pi Zero ?**
R: Non recommandé. Le Pi4 4GB est le minimum pour faire tourner Chromium + Next.js confortablement.

**Q: Faut-il vraiment 4GB de RAM ?**
R: Oui, fortement recommandé. Avec 2GB, le système risque d'être instable.

**Q: Puis-je utiliser WiFi au lieu d'Ethernet ?**
R: Oui, mais Ethernet est plus stable pour un serveur 24/7.

**Q: Comment changer le port du dashboard ?**
R: Modifiez `DASHBOARD_PORT=3000` dans le fichier `.env`, puis redémarrez.

**Q: Où sont stockées les données ?**
R: Base de données : `./data/linkedin.db`, Logs : `./logs/`

**Q: Comment migrer depuis Synology MySQL vers SQLite ?**
R: Utilisez `./scripts/migrate_mysql_to_sqlite.sh` (si disponible) ou exportez/importez manuellement.

**Q: Le bot consomme combien d'électricité ?**
R: Environ 5-10W (0.15€/jour à 0.20€/kWh), soit ~4€/mois.

---

## 🎉 Félicitations !

Votre bot LinkedIn Birthday tourne maintenant sur votre Pi4 + Freebox Pop !

### Prochaines étapes

1. ✅ Accédez au dashboard : http://192.168.1.X:3000
2. ✅ Authentifiez-vous sur LinkedIn
3. ✅ Configurez les limites de messages
4. ✅ Testez en mode `dry_run: true`
5. ✅ Activez le mode production `dry_run: false`

### Support

- 📖 Documentation : [README.md](README.md)
- 🐛 Issues : [GitHub Issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)
- 💬 Discussions : [GitHub Discussions](https://github.com/GaspardD78/linkedin-birthday-auto/discussions)

---

**Bon anniversaires automatiques ! 🎂🎉**
