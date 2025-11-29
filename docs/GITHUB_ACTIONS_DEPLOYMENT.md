# Déploiement via GitHub Actions (Recommandé pour Raspberry Pi 4)

## 🎯 Vue d'ensemble

Cette méthode utilise **GitHub Actions** pour construire les images Docker sur les serveurs GitHub, puis les distribue via **GitHub Container Registry (GHCR)**. Le Raspberry Pi 4 ne fait que télécharger les images pré-construites.

### Avantages vs Build Local

| Critère | Build Local | GitHub Actions (GHCR) |
|---------|-------------|----------------------|
| **Temps de déploiement** | 25-30 minutes | **2-3 minutes** ⚡ |
| **RAM consommée** | 900MB + Swap | **0 MB** ✅ |
| **Usure carte SD** | Très élevée (écritures intensives) | **Zéro** ✅ |
| **Risque OOM Kill** | Élevé | **Aucun** ✅ |
| **Scalabilité** | Chaque Pi doit builder | **Une image pour tous les Pi** ✅ |
| **Build reproductible** | Dépend de l'environnement Pi | **Toujours identique** ✅ |

## 🚀 Configuration Initiale (Une fois)

### 1. Vérifier que le workflow est activé

Le workflow GitHub Actions est dans `.github/workflows/build-images.yml`. Il se déclenche automatiquement sur :
- Push vers `main` ou `develop`
- Création de tags `v*`
- Manuellement via l'interface GitHub

### 2. Rendre les images publiques (Recommandé)

Pour éviter d'avoir à configurer l'authentification sur le Pi :

1. Allez sur votre dépôt GitHub
2. Cliquez sur **Packages** (côté droit)
3. Pour chaque package (`linkedin-birthday-auto-bot` et `linkedin-birthday-auto-dashboard`) :
   - Cliquez dessus
   - **Package settings** → **Change visibility** → **Public**

### 3. (Optionnel) Authentification pour repos privés

Si vos images restent privées, configurez l'authentification sur le Pi :

```bash
# Créer un token GitHub avec le scope 'read:packages'
# https://github.com/settings/tokens/new

# Se connecter au registry
docker login ghcr.io -u VOTRE_USERNAME
# Entrez le token comme mot de passe
```

## 📦 Déploiement sur Raspberry Pi 4

### Méthode 1 : Script automatisé (Recommandé)

```bash
# À la racine du projet
./scripts/deploy_pi4_pull.sh
```

**Durée** : ~2-3 minutes ⚡

### Méthode 2 : Manuel avec docker compose

```bash
# Pull des images depuis GHCR
docker compose -f docker-compose.pi4-standalone.yml pull

# Démarrage
docker compose -f docker-compose.pi4-standalone.yml up -d
```

## 🔄 Workflow de Développement

### Scénario 1 : Déployer la dernière version

```bash
# Sur votre machine de dev
git push origin main

# Attendez que GitHub Actions termine le build (~5 minutes)
# Vérifiez : https://github.com/VOTRE_USERNAME/linkedin-birthday-auto/actions

# Sur le Raspberry Pi
./scripts/deploy_pi4_pull.sh
```

### Scénario 2 : Déployer une version spécifique (tag)

```bash
# Sur votre machine de dev
git tag v1.2.0
git push origin v1.2.0

# Modifiez docker-compose.pi4-standalone.yml pour utiliser le tag
# Remplacez :latest par :v1.2.0

# Sur le Raspberry Pi
docker compose -f docker-compose.pi4-standalone.yml pull
docker compose -f docker-compose.pi4-standalone.yml up -d
```

### Scénario 3 : Build manuel via interface GitHub

1. Allez sur https://github.com/VOTRE_USERNAME/linkedin-birthday-auto/actions
2. Cliquez sur **Build and Push Docker Images**
3. Cliquez sur **Run workflow** (à droite)
4. Sélectionnez la branche
5. Cliquez sur **Run workflow**

## 🔍 Vérification des Builds

### Voir les builds en cours

```bash
# Via l'interface web
https://github.com/VOTRE_USERNAME/linkedin-birthday-auto/actions

# Ou avec GitHub CLI (si installé)
gh run list --workflow="build-images.yml"
gh run view <RUN_ID>
```

### Voir les images disponibles

```bash
# Via l'interface web
https://github.com/VOTRE_USERNAME?tab=packages

# Ou en local
docker images | grep ghcr.io
```

## 🐛 Dépannage

### Erreur : "pull access denied"

**Cause** : Image privée sans authentification

**Solution** :
1. Rendez l'image publique (voir section Configuration)
2. Ou configurez `docker login ghcr.io`

### Erreur : "manifest unknown"

**Cause** : L'image n'existe pas encore sur GHCR

**Solution** :
1. Vérifiez que GitHub Actions a bien terminé le build
2. Vérifiez le nom de l'image dans `docker-compose.pi4-standalone.yml`

### Build GitHub Actions échoue

**Solutions courantes** :
- Vérifiez les logs dans l'onglet Actions
- Vérifiez que les Dockerfiles sont corrects
- Vérifiez que les dépendances sont disponibles pour ARM64

### Le Pi ne peut pas télécharger les images

**Vérifications** :
```bash
# Tester la connexion à GHCR
docker pull ghcr.io/gaspardd78/linkedin-birthday-auto-bot:latest

# Vérifier les permissions Docker
docker ps

# Vérifier la connexion internet
ping github.com
```

## 📊 Comparaison des Scripts

### `deploy_pi4_pull.sh` (Nouveau - Recommandé)
- ✅ Télécharge les images pré-construites
- ✅ Rapide (2-3 minutes)
- ✅ Pas de compilation
- ✅ Préserve la carte SD
- ❌ Nécessite images sur GHCR

### `deploy_pi4_standalone.sh` (Ancien)
- ✅ Build tout localement
- ✅ Pas de dépendance externe
- ❌ Très lent (25-30 minutes)
- ❌ Use la carte SD
- ❌ Consomme beaucoup de RAM

**Recommandation** : Utilisez `deploy_pi4_pull.sh` pour les déploiements réguliers, et gardez `deploy_pi4_standalone.sh` uniquement pour les cas d'urgence sans connexion internet.

## 🔐 Sécurité

### Images Publiques
- Pas de secrets dans les Dockerfiles
- Les secrets sont passés via variables d'environnement au runtime
- Fichier `.env` créé localement sur le Pi

### Images Privées
- Authentification requise via token GitHub
- Token stocké dans `~/.docker/config.json`
- Utilisez des tokens avec le scope minimal (`read:packages`)

## 🎓 Ressources

- [Documentation GitHub Actions](https://docs.github.com/en/actions)
- [Documentation GHCR](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Multi-arch builds](https://docs.docker.com/build/building/multi-platform/)
