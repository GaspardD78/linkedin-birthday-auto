# 🛠️ Scripts de Déploiement et Maintenance - Raspberry Pi 4

Ce dossier contient tous les scripts nécessaires pour déployer, vérifier, nettoyer et maintenir le LinkedIn Birthday Bot sur Raspberry Pi 4.

---

## 📋 Table des matières

- [Scripts de Déploiement](#-scripts-de-déploiement)
- [Scripts de Maintenance](#-scripts-de-maintenance)
- [Scripts de Vérification](#-scripts-de-vérification)
- [Workflows Recommandés](#-workflows-recommandés)
- [Dépannage](#-dépannage)

---

## 🚀 Scripts de Déploiement

### `easy_deploy.sh` ⭐ **RECOMMANDÉ**

**Orchestrateur intelligent** qui simplifie le déploiement complet en 4 étapes automatisées.

**Usage:**
```bash
./scripts/easy_deploy.sh
```

**Ce qu'il fait:**
1. **Vérification initiale** - Lance `verify_rpi_docker.sh` pour analyser l'état du système
2. **Nettoyage conditionnel** - Propose d'exécuter `full_cleanup_deployment.sh` si installation détectée
3. **Déploiement** - Exécute `deploy_pi4_standalone.sh` pour construire et lancer les services
4. **Vérification finale** - Relance `verify_rpi_docker.sh` et affiche l'URL d'accès

**Avantages:**
- ✅ Gestion automatique des permissions d'exécution
- ✅ Interface interactive avec confirmations
- ✅ Rapport détaillé de chaque étape
- ✅ Gestion d'erreurs robuste
- ✅ Affichage de l'URL du dashboard et commandes utiles

**Quand l'utiliser:**
- 🆕 **Première installation** sur un Raspberry Pi 4 neuf
- 🔄 **Réinstallation complète** après problèmes
- 🎯 **Mise à jour majeure** nécessitant un rebuild complet

---

### `deploy_pi4_standalone.sh`

Script de déploiement complet optimisé pour Raspberry Pi 4 (4GB RAM).

**Usage:**
```bash
./scripts/deploy_pi4_standalone.sh
```

**Ce qu'il fait:**
1. Vérifications système (Docker, espace disque, SWAP, RAM)
2. Configuration de l'environnement (.env, dossiers, permissions)
3. Vérification des fichiers requis (dashboard, auth_state.json)
4. Nettoyage préalable des conteneurs existants
5. Construction des images Docker (Bot Worker + Dashboard)
6. Démarrage des services (bot-worker, dashboard, redis×2)
7. Vérification finale de l'état des services

**Configuration requise:**
- **SWAP:** Minimum 2GB (pour compilation Next.js)
- **Disque:** Minimum 5GB disponibles
- **RAM:** Recommandé 4GB

**Durée estimée:** 15-20 minutes (première fois)

**Quand l'utiliser:**
- Déploiement initial
- Reconstruction complète après modifications du code
- Après un nettoyage manuel

---

## 🧹 Scripts de Maintenance

### `full_cleanup_deployment.sh`

Script de nettoyage **intelligent et approfondi** pour libérer de l'espace disque et éviter la surcharge mémoire.

**Usage:**
```bash
# Mode interactif (demande confirmation)
./scripts/full_cleanup_deployment.sh

# Mode automatique (pas de confirmation)
./scripts/full_cleanup_deployment.sh -y

# Mode nettoyage approfondi (inclut cache Docker, node_modules)
./scripts/full_cleanup_deployment.sh -y --deep
```

**Modes de nettoyage:**

#### Mode Standard (`-y`)
- ✅ Arrêt et suppression de tous les conteneurs du projet
- ✅ Suppression de toutes les images Docker du projet
- ✅ Nettoyage des volumes Docker orphelins
- ✅ Nettoyage des réseaux Docker non utilisés
- ✅ Suppression des images intermédiaires (dangling)
- ✅ Arrêt des processus Python zombies
- ✅ Suppression des fichiers temporaires (__pycache__, .next, *.pyc)

#### Mode Approfondi (`--deep`)
Tout ce qui précède **PLUS:**
- ⚠️ Nettoyage complet du cache Docker (build cache)
- ⚠️ Suppression de TOUTES les images Docker non utilisées
- ⚠️ Suppression de tous les node_modules
- ⚠️ Nettoyage du cache npm

**Analyse préliminaire:**
Le script effectue une analyse complète AVANT le nettoyage:
- 📊 Espace disque actuel
- 📦 Conteneurs détectés (avec noms)
- 🖼️ Images Docker du projet (avec tailles)
- 💾 Volumes et images dangling
- 🧠 Mémoire disponible
- 📈 Estimation de l'espace qui sera libéré

**Rapport final:**
- 💾 Espace disque réellement libéré
- ✅ Résumé des opérations effectuées
- 📊 Espace disque disponible après nettoyage

**Conservation des données:**
⚠️ **Les données suivantes sont TOUJOURS conservées:**
- `data/` (base de données SQLite)
- `config/` (fichiers de configuration)
- `auth_state.json` (session LinkedIn)

**Quand l'utiliser:**
- Avant une réinstallation complète
- Quand l'espace disque est faible (< 2GB)
- Après des erreurs de build Docker
- Pour nettoyer après des tests/développements
- Mode `--deep` : uniquement en cas de problèmes d'espace critiques

**Espace typiquement libéré:**
- Mode standard: 1-4GB
- Mode `--deep`: 3-8GB

---

## ✅ Scripts de Vérification

### `verify_rpi_docker.sh`

Script de vérification complète de l'installation Docker sur Raspberry Pi.

**Usage:**
```bash
./scripts/verify_rpi_docker.sh
```

**Ce qu'il vérifie (7 étapes):**

1. **Informations système**
   - Modèle de Raspberry Pi
   - Architecture (ARM)
   - Mémoire disponible
   - Espace disque

2. **Installation Docker**
   - Docker installé et version
   - Docker Compose V2 installé
   - Docker daemon actif

3. **Configuration Docker Compose**
   - Fichier `docker-compose.pi4-standalone.yml` présent
   - Fichiers requis (Dockerfile, auth_state.json)

4. **État des conteneurs**
   - Redis container (redis-bot) en cours d'exécution
   - Worker container (bot-worker) en cours d'exécution

5. **Santé Redis**
   - Connectivité Redis (PING)
   - Version Redis
   - Utilisation mémoire
   - Nombre de clés

6. **Santé Worker**
   - Logs du worker (détection d'erreurs)
   - Connexion Redis du worker

7. **Avertissements attendus**
   - Warning Redis memory overcommit (normal sur RPi)

**Code de sortie:**
- `0` : Tout est OK
- `>0` : Nombre d'erreurs détectées

**Quand l'utiliser:**
- Après un déploiement (vérification)
- En cas de comportement anormal
- Pour diagnostiquer des problèmes
- Monitoring régulier de l'état

**Exemple de sortie:**
```
✓ All checks passed! Your setup is ready.
```

---

## 🎯 Workflows Recommandés

### 🆕 Première Installation

```bash
# 1. Méthode simple (RECOMMANDÉE)
./scripts/easy_deploy.sh

# OU 2. Méthode manuelle
./scripts/deploy_pi4_standalone.sh
./scripts/verify_rpi_docker.sh
```

---

### 🔄 Réinstallation Complète

```bash
# 1. Méthode simple (RECOMMANDÉE)
./scripts/easy_deploy.sh
# → Répondre "o" quand demandé de faire un nettoyage

# OU 2. Méthode manuelle
./scripts/full_cleanup_deployment.sh -y
./scripts/deploy_pi4_standalone.sh
./scripts/verify_rpi_docker.sh
```

---

### 🧹 Nettoyage Simple (problèmes mineurs)

```bash
# Nettoyage standard
./scripts/full_cleanup_deployment.sh -y

# Puis redéployer
./scripts/deploy_pi4_standalone.sh
```

---

### 🔥 Nettoyage Approfondi (espace disque critique)

```bash
# Nettoyage approfondi + rebuild complet
./scripts/full_cleanup_deployment.sh -y --deep
./scripts/deploy_pi4_standalone.sh
```

---

### 📊 Vérification Rapide de l'État

```bash
# Vérifier que tout fonctionne
./scripts/verify_rpi_docker.sh

# Voir les logs en temps réel
docker compose -f docker-compose.pi4-standalone.yml logs -f
```

---

### 🔧 Mise à jour du Code (après git pull)

```bash
# Si changements dans le code Python ou le Dashboard
./scripts/full_cleanup_deployment.sh -y
./scripts/deploy_pi4_standalone.sh

# Si juste changements de config
docker compose -f docker-compose.pi4-standalone.yml restart
```

---

## 🆘 Dépannage

### Le déploiement échoue lors du build du Dashboard

**Symptôme:** Erreur "JavaScript heap out of memory" ou "killed"

**Cause:** SWAP insuffisant ou inactif

**Solution:**
```bash
# Vérifier le SWAP
free -h

# Si SWAP < 2GB, le reconfigurer
sudo dphys-swapfile swapoff
sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

---

### Le script easy_deploy.sh ne détecte pas les conteneurs

**Symptôme:** Dit "Aucun conteneur détecté" alors qu'ils existent

**Cause:** Noms de conteneurs différents

**Solution:**
```bash
# Vérifier les conteneurs existants
docker ps -a

# Nettoyer manuellement si nécessaire
docker rm -f $(docker ps -a -q)

# Puis relancer
./scripts/easy_deploy.sh
```

---

### Erreur "Permission denied" lors de l'exécution

**Symptôme:** `bash: ./scripts/xxx.sh: Permission denied`

**Cause:** Script non exécutable

**Solution:**
```bash
# Rendre le script exécutable
chmod +x ./scripts/xxx.sh

# Ou utiliser bash directement
bash ./scripts/xxx.sh
```

**Note:** Le script `easy_deploy.sh` gère automatiquement les permissions !

---

### Le nettoyage ne libère pas assez d'espace

**Symptôme:** Toujours peu d'espace après `full_cleanup_deployment.sh`

**Solution:**
```bash
# 1. Utiliser le mode --deep
./scripts/full_cleanup_deployment.sh -y --deep

# 2. Nettoyer les logs système (optionnel)
sudo journalctl --vacuum-time=7d

# 3. Nettoyer APT cache
sudo apt-get clean
sudo apt-get autoremove

# 4. Vérifier l'espace
df -h
```

---

### Les conteneurs ne démarrent pas après le déploiement

**Symptôme:** `verify_rpi_docker.sh` montre des erreurs

**Solution:**
```bash
# 1. Vérifier les logs
docker compose -f docker-compose.pi4-standalone.yml logs

# 2. Redémarrer les services
docker compose -f docker-compose.pi4-standalone.yml restart

# 3. Si problème persiste, rebuild
./scripts/full_cleanup_deployment.sh -y
./scripts/deploy_pi4_standalone.sh
```

---

## 📚 Documentation Connexe

- **[../README.md](../README.md)** - Documentation principale du projet
- **[../docs/RPI_QUICKSTART.md](../docs/RPI_QUICKSTART.md)** - Guide de démarrage rapide Raspberry Pi
- **[../deployment/README.md](../deployment/README.md)** - Configuration systemd et automatisation

---

## 🔗 Ressources Utiles

**Commandes Docker utiles:**
```bash
# Voir les conteneurs
docker ps -a

# Voir les images
docker images

# Voir l'utilisation disque Docker
docker system df

# Logs d'un conteneur
docker logs <nom-conteneur> -f

# Statistiques temps réel
docker stats
```

**Commandes système Raspberry Pi:**
```bash
# Température CPU
vcgencmd measure_temp

# Utilisation mémoire
free -h

# Espace disque
df -h

# Processus consommant le plus de RAM
ps aux --sort=-%mem | head -10
```

---

**Version:** 2.0.0
**Dernière mise à jour:** 2024-11-28
**Optimisé pour:** Raspberry Pi 4 (4GB RAM)
