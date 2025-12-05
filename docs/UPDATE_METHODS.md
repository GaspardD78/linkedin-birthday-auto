# Méthodes de mise à jour sans tout reconstruire

Ce document décrit comment mettre à jour le code du bot sans reconstruire complètement les images Docker.

## 🎯 Résumé rapide

| Méthode | Cas d'usage | Temps | Build requis |
|---------|-------------|-------|--------------|
| **Hot-reload (dev)** | Développement local | Instantané | ❌ Non |
| **Pull images** | Production | ~1 min | ✅ Oui (GitHub Actions) |
| **Restart conteneur** | Config/messages modifiés | ~10 sec | ❌ Non |

---

## 📦 Méthode 1 : Mode développement avec hot-reload (Recommandé pour dev)

### Configuration

Le fichier `docker-compose.dev.yml` monte le code source dans les conteneurs :

```bash
# Démarrer en mode développement
./scripts/update_without_rebuild.sh dev

# Ou manuellement :
docker compose -f docker-compose.pi4-standalone.yml -f docker-compose.dev.yml up -d
```

### Avantages
- ✅ Modifications du code **instantanément** prises en compte
- ✅ L'API redémarre automatiquement (hot-reload avec `--reload`)
- ✅ Pas besoin de reconstruire les images
- ✅ Idéal pour le développement et le debugging

### Limitations
- ⚠️ Le worker ne se recharge pas automatiquement (redémarrer avec `docker restart bot-worker`)
- ⚠️ Ne pas utiliser en production (volumes en lecture seule)

### Workflow typique

```bash
# 1. Modifier le code (ex: src/core/auth_manager.py)
vim src/core/auth_manager.py

# 2a. Pour l'API : Les changements sont automatiques ✨

# 2b. Pour le worker : Redémarrer le conteneur
docker restart bot-worker

# 3. Vérifier les logs
docker logs -f bot-worker --tail 50
```

---

## 🚀 Méthode 2 : Pull des images depuis GHCR (Production)

### Prérequis

Les images doivent être construites et poussées sur GitHub Container Registry via GitHub Actions.

### Workflow

```bash
# 1. Pousser le code sur GitHub
git push origin claude/fix-playwright-context-error-01BsuPM4oxJPuVfiDWhqSrLe

# 2. Attendre que GitHub Actions construise les images
# Vérifier : https://github.com/GaspardD78/linkedin-birthday-auto/actions

# 3. Mettre à jour les conteneurs
./scripts/update_without_rebuild.sh prod

# Ou manuellement :
docker compose -f docker-compose.pi4-standalone.yml pull api bot-worker
docker compose -f docker-compose.pi4-standalone.yml up -d api bot-worker
```

### Avantages
- ✅ Déploiement propre et testé
- ✅ Images versionnées et traçables
- ✅ Pas de compilation locale sur le Pi4
- ✅ Rollback facile avec les tags d'images

### Temps estimé
- Build GitHub Actions : ~5-10 minutes
- Pull + restart : ~1-2 minutes

---

## ⚡ Méthode 3 : Restart simple (Config/Messages seulement)

Si vous modifiez uniquement des fichiers de **configuration** ou de **messages** (qui sont montés comme volumes), un simple restart suffit :

```bash
# Modifier la config
vim config/config.yaml

# Redémarrer les conteneurs
docker compose -f docker-compose.pi4-standalone.yml restart api bot-worker

# Ou juste le worker
docker restart bot-worker
```

### Fichiers concernés
- `config/config.yaml` - Configuration du bot
- `config/messages/` - Templates de messages
- Les fichiers dans `/app/data/` via le volume `shared-data`

---

## 🛠️ Dépannage

### Les changements ne sont pas pris en compte

```bash
# Vérifier que le code source est bien monté (mode dev)
docker exec bot-worker ls -la /app/src/core/

# Vérifier les logs pour les erreurs de syntaxe
docker logs bot-worker --tail 50

# Forcer un redémarrage complet
docker compose -f docker-compose.pi4-standalone.yml restart
```

### Erreur "cannot pull image"

Les images GHCR ne sont pas encore disponibles. Options :

1. **Attendre** que GitHub Actions finisse le build
2. **Construire localement** (déconseillé sur Pi4) :
   ```bash
   docker build -t ghcr.io/gaspardd78/linkedin-birthday-auto-bot:latest -f Dockerfile.multiarch .
   ```

### Le worker ne voit pas les changements de code

En mode développement, le worker ne recharge pas automatiquement. Redémarrer :

```bash
docker restart bot-worker
```

---

## 📊 Comparaison des temps

| Opération | Temps |
|-----------|-------|
| Modification code + hot-reload API | < 1 seconde |
| Modification code + restart worker | ~10 secondes |
| Pull nouvelle image + restart | ~1-2 minutes |
| Build GitHub Actions complet | ~5-10 minutes |
| Build local + restart (Pi4) | ~15-20 minutes ⚠️ |

---

## 💡 Recommandations

### Pour le développement
1. Utiliser `docker-compose.dev.yml` avec le code monté
2. Modifier le code localement
3. Redémarrer le worker si nécessaire
4. Tester avec `pytest` avant de pousser

### Pour la production
1. Tester en local avec mode dev
2. Pousser sur GitHub
3. Vérifier le build GitHub Actions
4. Pull et restart en production

### Pour les hotfixes urgents
1. Mode dev pour tester rapidement
2. Une fois validé, pousser sur GitHub
3. Attendre le build
4. Déployer en production via pull

---

## 🔗 Liens utiles

- [GitHub Actions Workflows](../.github/workflows/)
- [Configuration Docker Compose](../docker-compose.pi4-standalone.yml)
- [Configuration dev](../docker-compose.dev.yml)
- [Script de mise à jour](../scripts/update_without_rebuild.sh)
