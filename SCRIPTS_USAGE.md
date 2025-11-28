# 📜 Guide d'utilisation des scripts - LinkedIn Birthday Auto Bot v2.0

Ce guide décrit les scripts disponibles pour le déploiement, la mise à jour et la maintenance du bot
LinkedIn Birthday Auto en version 2.0.

______________________________________________________________________

## 📋 Vue d'ensemble

Le projet utilise maintenant une architecture moderne avec :

- **Point d'entrée unifié** : `main.py` (CLI riche)
- **Scripts de déploiement optimisés** : Pour Raspberry Pi 4
- **Dashboard moderne** : Next.js dans `dashboard/`
- **Architecture modulaire** : Code dans `src/`

______________________________________________________________________

## 🚀 Scripts de Déploiement

### 1. Déploiement Raspberry Pi 4 Standalone

**Script** : `scripts/deploy_pi4_standalone.sh`

**Description** : Script de déploiement complet optimisé pour Raspberry Pi 4 (4GB RAM). Déploie
l'architecture standalone : Bot Worker + Dashboard + Redis + SQLite.

**Fonctionnalités** :

- ✅ Vérifications système approfondies (RAM, SWAP, disque, Docker)
- ✅ Configuration automatique de l'environnement
- ✅ Patching automatique des dépendances Dashboard
- ✅ Build optimisé avec gestion de la mémoire
- ✅ Vérifications post-déploiement

**Prérequis** :

- Raspberry Pi 4 avec 4GB RAM
- Docker Compose V2 installé
- SWAP configuré (≥ 2GB pour build Dashboard)
- Espace disque ≥ 5GB

**Usage** :

```bash
# Déploiement complet (première installation)
./scripts/deploy_pi4_standalone.sh

# Le script va :
# 1. Vérifier le système (Docker, RAM, SWAP, disque)
# 2. Créer et configurer l'environnement (.env, dossiers)
# 3. Patcher les fichiers Dashboard si nécessaire
# 4. Arrêter les conteneurs existants
# 5. Builder les images Docker (Bot Worker + Dashboard)
# 6. Démarrer les services
# 7. Vérifier l'état des conteneurs

# Accès dashboard : http://<IP_PI>:3000
```

**Temps estimé** : ~15-20 minutes (build Dashboard)

______________________________________________________________________

### 2. Mise à jour du déploiement

**Script** : `scripts/update_deployment_pi4.sh`

**Description** : Script de mise à jour incrémentale sans reconstruction complète. Applique les
nouvelles configurations et redémarre les conteneurs.

**Fonctionnalités** :

- ✅ Sauvegarde automatique des données (DB + config)
- ✅ Recréation des conteneurs avec nouvelles limites
- ✅ Pas de rebuild des images (gain de temps)
- ✅ Vérification santé des services
- ✅ Migration DB si nécessaire

**Usage** :

```bash
# Après avoir fait un git pull
git pull origin main
./scripts/update_deployment_pi4.sh

# Le script va :
# 1. Sauvegarder la base de données
# 2. Recréer les conteneurs avec nouvelles config
# 3. Vérifier la santé des services
# 4. Afficher les statistiques ressources
```

**Temps estimé** : ~2-3 minutes

______________________________________________________________________

## 🧹 Scripts de Nettoyage

### 3. Nettoyage périodique

**Script** : `scripts/cleanup_pi4.sh`

**Description** : Nettoyage périodique pour économiser l'espace disque sur carte SD.

**Actions** :

- 🗑️ Supprime images Docker > 7 jours
- 🗑️ Supprime logs applicatifs > 30 jours
- 🗑️ Supprime screenshots > 7 jours
- 🗑️ Nettoie cache Python (__pycache__, \*.pyc)
- 🗑️ Nettoie cache APT (si sudo)
- 🗑️ Nettoie journaux système > 7 jours (si sudo)

**Usage** :

```bash
# Sans sudo (nettoyage partiel)
./scripts/cleanup_pi4.sh

# Avec sudo (nettoyage complet)
sudo ./scripts/cleanup_pi4.sh
```

**Fréquence recommandée** : Hebdomadaire

**Automatisation avec cron** :

```bash
# Ajouter au crontab
crontab -e

# Exécution tous les dimanches à 3h du matin
0 3 * * 0 cd /path/to/linkedin-birthday-auto && sudo ./scripts/cleanup_pi4.sh
```

______________________________________________________________________

### 4. Nettoyage complet (réinstallation)

**Script** : `scripts/full_cleanup_deployment.sh`

**Description** : Nettoyage COMPLET des déploiements précédents. Supprime TOUS les conteneurs,
réseaux et images liés au projet.

⚠️ **ATTENTION** : Ce script remet le système "à propre" avant une réinstallation. Les données
persistantes (dossier `data/`, `config/`) sont conservées.

**Actions** :

- 🗑️ Arrêt et suppression de TOUS les conteneurs du projet
- 🗑️ Suppression de TOUTES les images Docker du projet
- 🗑️ Suppression des volumes Docker
- 🗑️ Nettoyage des processus zombies Python
- 🗑️ Suppression des fichiers temporaires (__pycache__, .next)

**Usage** :

```bash
# Mode interactif (demande confirmation)
./scripts/full_cleanup_deployment.sh

# Mode force (pas de confirmation)
./scripts/full_cleanup_deployment.sh -y
```

**Quand l'utiliser** :

- Avant une réinstallation complète
- En cas de problèmes de conteneurs corrompus
- Pour libérer beaucoup d'espace disque

______________________________________________________________________

## 🔧 Scripts de Maintenance

### 5. Vérification du déploiement

**Script** : `scripts/verify_rpi_docker.sh`

**Description** : Vérifie que le déploiement Docker fonctionne correctement.

**Vérifications** :

- ✅ Docker installé et fonctionnel
- ✅ Conteneurs en cours d'exécution
- ✅ Health checks des services
- ✅ Connectivité réseau

**Usage** :

```bash
./scripts/verify_rpi_docker.sh
```

______________________________________________________________________

### 6. Monitoring des ressources

**Script** : `scripts/monitor_pi4_resources.sh`

**Description** : Affiche l'utilisation des ressources en temps réel.

**Affiche** :

- 📊 Utilisation CPU/RAM des conteneurs
- 📊 Mémoire système (RAM + SWAP)
- 📊 Température CPU
- 📊 Espace disque

**Usage** :

```bash
# Affichage unique
./scripts/monitor_pi4_resources.sh

# Monitoring continu (toutes les 5 secondes)
watch -n 5 ./scripts/monitor_pi4_resources.sh
```

______________________________________________________________________

### 7. Redémarrage de tous les services

**Script** : `scripts/restart-all-pi4.sh`

**Description** : Redémarre tous les services Docker du projet.

**Usage** :

```bash
./scripts/restart-all-pi4.sh
```

______________________________________________________________________

### 8. Rebuild du Dashboard

**Script** : `scripts/rebuild-dashboard-pi4.sh`

**Description** : Rebuild uniquement le Dashboard (sans toucher au Bot Worker).

**Usage** :

```bash
./scripts/rebuild-dashboard-pi4.sh

# Utile après modifications du code Dashboard
```

______________________________________________________________________

## 🎯 Workflows Recommandés

### Installation initiale

```bash
# 1. Cloner le projet
git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
cd linkedin-birthday-auto

# 2. Déployer
./scripts/deploy_pi4_standalone.sh

# 3. Vérifier
./scripts/verify_rpi_docker.sh

# 4. Accéder au dashboard
# http://<IP_PI>:3000
```

______________________________________________________________________

### Mise à jour régulière

```bash
# 1. Récupérer les dernières modifications
git pull origin main

# 2. Mettre à jour le déploiement
./scripts/update_deployment_pi4.sh

# 3. Vérifier
docker compose -f docker-compose.pi4-standalone.yml logs -f
```

______________________________________________________________________

### Maintenance hebdomadaire

```bash
# 1. Nettoyage périodique
sudo ./scripts/cleanup_pi4.sh

# 2. Vérifier les ressources
./scripts/monitor_pi4_resources.sh

# 3. Vérifier les logs
docker compose -f docker-compose.pi4-standalone.yml logs --tail=100
```

______________________________________________________________________

### En cas de problème

```bash
# 1. Vérifier l'état des services
./scripts/verify_rpi_docker.sh

# 2. Consulter les logs
docker compose -f docker-compose.pi4-standalone.yml logs -f

# 3. Redémarrer les services
./scripts/restart-all-pi4.sh

# 4. Si problème persiste : nettoyage complet + redéploiement
./scripts/full_cleanup_deployment.sh -y
./scripts/deploy_pi4_standalone.sh
```

______________________________________________________________________

## 📝 Commandes Docker Compose Utiles

```bash
# Démarrer les services
docker compose -f docker-compose.pi4-standalone.yml up -d

# Arrêter les services
docker compose -f docker-compose.pi4-standalone.yml down

# Voir les logs en temps réel
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Voir les logs d'un service spécifique
docker compose -f docker-compose.pi4-standalone.yml logs -f bot-worker
docker compose -f docker-compose.pi4-standalone.yml logs -f dashboard

# Redémarrer un service
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker

# Voir l'état des services
docker compose -f docker-compose.pi4-standalone.yml ps

# Voir les stats ressources
docker stats

# Rebuild un service spécifique
docker compose -f docker-compose.pi4-standalone.yml build bot-worker
docker compose -f docker-compose.pi4-standalone.yml up -d bot-worker
```

______________________________________________________________________

## 🔍 Monitoring et Logs

### Logs applicatifs

```bash
# Logs du bot
docker compose -f docker-compose.pi4-standalone.yml logs -f bot-worker

# Logs du dashboard
docker compose -f docker-compose.pi4-standalone.yml logs -f dashboard

# Logs Redis
docker compose -f docker-compose.pi4-standalone.yml logs -f redis-bot
```

### Base de données SQLite

```bash
# Accéder à la base de données
sqlite3 data/linkedin.db

# Statistiques
sqlite3 data/linkedin.db "SELECT COUNT(*) FROM birthday_messages WHERE DATE(timestamp) = DATE('now');"
```

______________________________________________________________________

## 📚 Documentation Complémentaire

- **[README.md](README.md)** - Vue d'ensemble du projet
- **[SETUP_PI4_FREEBOX.md](SETUP_PI4_FREEBOX.md)** - Guide de déploiement Pi4 complet
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture détaillée
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Guide de déploiement général
- **[docs/RASPBERRY_PI_DOCKER_SETUP.md](docs/RASPBERRY_PI_DOCKER_SETUP.md)** - Installation Docker
  sur Pi
- **[docs/RASPBERRY_PI_TROUBLESHOOTING.md](docs/RASPBERRY_PI_TROUBLESHOOTING.md)** - Dépannage Pi

______________________________________________________________________

## ⚠️ Notes Importantes

### Ressources Raspberry Pi 4

Les limites suivantes sont configurées dans `docker-compose.pi4-standalone.yml` :

| Service         | RAM Limite | CPU Limite |
| --------------- | ---------- | ---------- |
| Bot Worker      | 900M       | 1.5 cores  |
| Dashboard       | 700M       | 1.0 cores  |
| Redis Bot       | 300M       | 0.5 cores  |
| Redis Dashboard | 300M       | 0.5 cores  |

### SWAP

Le Dashboard Next.js nécessite au moins **2GB de SWAP** pour le build.

Configuration SWAP :

```bash
# Vérifier le SWAP actuel
free -h

# Configurer 2GB de SWAP
sudo dphys-swapfile swapoff
sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

______________________________________________________________________

**Dernière mise à jour** : 28 novembre 2025 **Version** : 2.0.0
