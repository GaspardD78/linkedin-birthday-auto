# 🚀 Guide d'Installation Simplifiée - LinkedIn Birthday Bot

## Problème Rencontré

Si vous voyez cette erreur lors de l'installation :

```
✘ Container bot-api Error
dependency failed to start: container bot-api is unhealthy
```

Ce guide vous aidera à résoudre ce problème et à installer correctement le bot.

## 🔍 Cause du Problème

Le conteneur `bot-api` échoue au healthcheck pour l'une de ces raisons :

1. **Curl non disponible** : L'image Docker n'a pas `curl` installé, mais le healthcheck l'utilise
2. **Démarrage lent** : L'API met plus de 30 secondes à démarrer (temps insuffisant pour le healthcheck)
3. **Problème de permissions** : La base de données SQLite n'est pas accessible

## ✅ Solution Rapide

### Option 1 : Utiliser le nouveau script simplifié (Recommandé)

Le nouveau script `setup_simplified.sh` résout automatiquement ces problèmes :

```bash
# 1. Arrêter les conteneurs existants
docker compose -f docker-compose.pi4-standalone.yml down

# 2. Lancer le nouveau script d'installation
./setup_simplified.sh
```

**Avantages** :
- ✅ Détection automatique de l'environnement
- ✅ Healthcheck optimisé (utilise Python au lieu de curl)
- ✅ Temps de démarrage augmenté (60s au lieu de 30s)
- ✅ Meilleure gestion des erreurs avec diagnostic automatique
- ✅ Configuration interactive guidée

### Option 2 : Corriger manuellement le healthcheck

Si vous préférez corriger uniquement le healthcheck sans tout réinstaller :

```bash
# 1. Exécuter le script de correction
./scripts/fix_api_healthcheck.sh
```

Ce script va :
1. Sauvegarder votre fichier docker-compose actuel
2. Remplacer le healthcheck basé sur `curl` par un healthcheck Python
3. Augmenter le temps d'attente (`start_period: 60s`)
4. Redéployer les conteneurs

### Option 3 : Diagnostic manuel

Pour comprendre exactement ce qui se passe :

```bash
# 1. Exécuter le script de diagnostic
./scripts/diagnose_api.sh
```

Le script va vous montrer :
- Les logs du conteneur bot-api
- L'état du healthcheck
- Les processus en cours
- La disponibilité de l'endpoint /health
- Les permissions de la base de données

## 📋 Étapes Détaillées

### 1. Nettoyage de l'Installation Existante

```bash
# Arrêter tous les conteneurs
docker compose -f docker-compose.pi4-standalone.yml down

# (Optionnel) Supprimer les volumes si vous voulez repartir de zéro
docker compose -f docker-compose.pi4-standalone.yml down -v
```

### 2. Utilisation du Script Simplifié

```bash
# S'assurer que le script est exécutable
chmod +x ./setup_simplified.sh

# Lancer l'installation
./setup_simplified.sh
```

Le script va vous guider à travers :

#### **Étape 0** : Détection de l'environnement
- Plateforme (Raspberry Pi, x86, etc.)
- Mémoire RAM disponible
- Espace disque

#### **Étape 1** : Vérification des prérequis
- Docker installé et fonctionnel
- Docker Compose V2
- Permissions Docker
- Espace disque suffisant

#### **Étape 2** : Configuration
- Fichier .env (créé automatiquement si absent)
- Paramètres du bot (mode, limites, etc.)
- Configuration SMTP optionnelle
- Génération automatique des secrets

#### **Étape 3** : Déploiement
- Téléchargement des images Docker
- Optimisation du healthcheck
- Démarrage des conteneurs

#### **Étape 4** : Validation
- Vérification de chaque service
- Diagnostic en cas d'erreur

### 3. Vérification Post-Installation

```bash
# Vérifier l'état des conteneurs
docker compose -f docker-compose.pi4-standalone.yml ps

# Tous les conteneurs doivent afficher "Up" et "healthy"
```

Sortie attendue :
```
NAME              STATUS                    PORTS
redis-bot         Up (healthy)
redis-dashboard   Up (healthy)
bot-api           Up (healthy)
dashboard         Up (healthy)              0.0.0.0:3000->3000/tcp
bot-worker        Up
```

## 🛠️ Dépannage

### Le bot-api est toujours "unhealthy"

1. **Vérifier les logs** :
```bash
docker logs bot-api --tail 50
```

2. **Vérifier l'endpoint manuellement** :
```bash
docker exec bot-api python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())"
```

3. **Augmenter encore plus le temps d'attente** :

Éditez `docker-compose.pi4-standalone.yml` :
```yaml
healthcheck:
  start_period: 120s  # Augmenter à 2 minutes
  retries: 10         # Plus de tentatives
```

### Base de données verrouillée

```bash
# Vérifier les permissions
ls -la data/linkedin.db

# Corriger si nécessaire
chmod 666 data/linkedin.db
chmod 777 data/
```

### Conteneurs qui redémarrent en boucle

```bash
# Voir pourquoi
docker compose -f docker-compose.pi4-standalone.yml logs -f
```

## 📊 Commandes Utiles

### Gestion des Conteneurs

```bash
# Voir l'état
docker compose -f docker-compose.pi4-standalone.yml ps

# Voir les logs en temps réel
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Logs d'un service spécifique
docker logs -f bot-api
docker logs -f dashboard

# Redémarrer un service
docker compose -f docker-compose.pi4-standalone.yml restart bot-api

# Redémarrer tous les services
docker compose -f docker-compose.pi4-standalone.yml restart

# Arrêter tous les services
docker compose -f docker-compose.pi4-standalone.yml stop

# Démarrer tous les services
docker compose -f docker-compose.pi4-standalone.yml start
```

### Diagnostic

```bash
# Diagnostic complet de l'API
./scripts/diagnose_api.sh

# Health check d'un conteneur
docker inspect bot-api --format='{{json .State.Health}}' | python3 -m json.tool

# Entrer dans un conteneur
docker exec -it bot-api /bin/bash
```

### Nettoyage

```bash
# Arrêter et supprimer les conteneurs
docker compose -f docker-compose.pi4-standalone.yml down

# Supprimer aussi les volumes (⚠️ perte de données!)
docker compose -f docker-compose.pi4-standalone.yml down -v

# Nettoyer les images inutilisées
docker image prune -a
```

## 🎯 Accès au Dashboard

Une fois l'installation réussie :

```
http://[IP_DE_VOTRE_PI]:3000
```

**Identifiants par défaut** (si non configurés dans .env) :
- Username : Voir `DASHBOARD_USER` dans `.env`
- Password : Voir `DASHBOARD_PASSWORD` dans `.env`

## 📝 Notes Importantes

1. **Premier démarrage** : Le dashboard peut mettre 1-2 minutes à être accessible la première fois (compilation Next.js)

2. **Healthcheck** : Le nouveau healthcheck utilise Python au lieu de curl, ce qui est plus fiable car Python est toujours présent dans l'image

3. **Temps de démarrage** : L'API a maintenant 60 secondes pour démarrer au lieu de 30 secondes

4. **Permissions** : Les dossiers `data/` et `logs/` doivent avoir les permissions 777 pour que SQLite fonctionne

5. **Sauvegarde** : Le script de correction crée une sauvegarde du docker-compose avant modification

## 🔄 Retour à la Version Précédente

Si vous avez utilisé le script de correction et voulez revenir en arrière :

```bash
# Restaurer la sauvegarde
cp docker-compose.pi4-standalone.yml.backup.* docker-compose.pi4-standalone.yml

# Redéployer
docker compose -f docker-compose.pi4-standalone.yml up -d --force-recreate
```

## 📞 Support

Si le problème persiste :

1. Exécutez le diagnostic complet :
```bash
./scripts/diagnose_api.sh > diagnostic.log 2>&1
```

2. Collectez les logs :
```bash
docker compose -f docker-compose.pi4-standalone.yml logs > all-logs.txt 2>&1
```

3. Créez une issue sur GitHub avec :
   - Le fichier `diagnostic.log`
   - Le fichier `all-logs.txt`
   - Votre plateforme (Raspberry Pi modèle, RAM, etc.)

## ✨ Améliorations de la Version 3.0

- ✅ Healthcheck robuste (Python au lieu de curl)
- ✅ Temps de démarrage adaptatif
- ✅ Diagnostic automatique en cas d'erreur
- ✅ Configuration interactive guidée
- ✅ Validation étape par étape
- ✅ Messages d'erreur plus clairs
- ✅ Gestion automatique des permissions
- ✅ Génération automatique des secrets

Profitez de votre bot LinkedIn Birthday ! 🎉
