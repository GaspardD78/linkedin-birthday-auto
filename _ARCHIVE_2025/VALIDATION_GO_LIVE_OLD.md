# 🚀 Validation Go Live - Corrections SSL & Data Sync

Ce document décrit les corrections apportées pour résoudre les problèmes bloquants du Go Live et les procédures de validation.

## 📋 Résumé des Problèmes Résolus

### ✅ Problème 1 : Échec SSL (Permissions .env)
**Symptôme** : `grep: .env: Permission non accordée` lors de l'exécution de `setup_letsencrypt.sh`

**Cause** : Le fichier `.env` appartient à `root` et n'est pas lisible par l'utilisateur normal

**Solution Implémentée** :
1. **Détection précoce** : Vérification de la lisibilité de `.env` avant le grep (ligne 46-55)
2. **Messages d'erreur explicites** avec 3 solutions proposées
3. **Script de maintenance** : `scripts/fix_permissions.sh` pour correction automatisée

### ✅ Problème 2 : Rupture Data Sync (Endpoints manquants)
**Symptôme** : `404 Not Found` sur `POST /config/messages`

**Cause** : Aucun endpoint API pour gérer les fichiers `messages.txt` et `late_messages.txt`

**Solution Implémentée** :
1. **Nouveau router** : `src/api/routes/config_routes.py`
2. **I/O asynchrone** avec `aiofiles` (optimisé RPi4)
3. **4 endpoints REST** pour gestion complète des messages
4. **Enregistrement** dans `src/api/app.py` (ligne 171)

---

## 🔧 Fichiers Modifiés/Créés

### 📝 Scripts Shell

#### 1. `scripts/setup_letsencrypt.sh` (MODIFIÉ)
**Ligne 46-55** : Ajout de la vérification de lisibilité du `.env`

```bash
# Vérification des permissions de lecture sur .env
if [[ ! -r "$ENV_FILE" ]]; then
    log_error "Permissions insuffisantes pour lire $ENV_FILE"
    log_info "Solutions possibles:"
    log_info "  1. Relancez ce script avec sudo"
    log_info "  2. Ou corrigez les permissions: sudo chown \$USER:\$USER .env"
    log_info "  3. Ou utilisez: sudo ./scripts/fix_permissions.sh"
    exit 1
fi
```

#### 2. `scripts/fix_permissions.sh` (CRÉÉ)
**Script complet de maintenance** pour corriger tous les problèmes de permissions

**Fonctionnalités** :
- Détection automatique de l'utilisateur réel (via `$SUDO_USER`)
- Correction propriétaire du projet entier
- Sécurisation `.env` (600)
- Permissions dossiers critiques (data, logs, config, certbot)
- Validation automatique des corrections

**Usage** :
```bash
sudo ./scripts/fix_permissions.sh
```

### 🐍 Backend Python

#### 3. `requirements.txt` (MODIFIÉ)
**Ligne 23** : Ajout de `aiofiles~=23.2.1`

#### 4. `src/api/routes/config_routes.py` (CRÉÉ)
**Nouveau router** pour la gestion des messages

**Endpoints implémentés** :
```
GET  /config/messages         → Lit messages.txt
POST /config/messages         → Met à jour messages.txt
GET  /config/late-messages    → Lit late_messages.txt
POST /config/late-messages    → Met à jour late_messages.txt
GET  /config/messages/health  → Vérifie l'accessibilité des fichiers
```

**Architecture** :
- ✅ I/O asynchrone avec `aiofiles` (pas de blocage Event Loop)
- ✅ Validation Pydantic (min 1 caractère, max 50KB)
- ✅ Sécurité par API Key
- ✅ Backup automatique (.bak) avant mise à jour
- ✅ Gestion d'erreurs détaillée (404, 403, 500)
- ✅ Métadonnées (lines_count, size_bytes)

#### 5. `src/api/app.py` (MODIFIÉ)
**Ligne 170-171** : Enregistrement du nouveau router

```python
# 1b. Configuration & Messages
include_safe("src.api.routes.config_routes", "router")
```

---

## ✅ Checklist de Validation

### 🔐 Validation SSL (Problème 1)

#### Test 1 : Script fix_permissions.sh
```bash
# 1. Simuler le problème (optionnel)
sudo chown root:root .env

# 2. Exécuter le script de correction
sudo ./scripts/fix_permissions.sh

# ✅ Attendu :
# - Propriétaire restauré vers votre utilisateur
# - Message "Permissions Corrigées avec Succès"
```

#### Test 2 : setup_letsencrypt.sh sans sudo
```bash
# 3. Vérifier que le script peut lire .env
./scripts/setup_letsencrypt.sh --staging

# ✅ Attendu :
# - Pas d'erreur "Permission non accordée"
# - Domaine extrait correctement depuis .env
# - Script s'exécute jusqu'aux vérifications DNS
```

#### Test 3 : Détection erreur permissions
```bash
# 4. Simuler le problème pour tester la détection
sudo chown root:root .env
./scripts/setup_letsencrypt.sh

# ✅ Attendu :
# - Erreur détectée AVANT le grep
# - Message explicite avec 3 solutions proposées
# - Exit code 1
```

---

### 📊 Validation Data Sync (Problème 2)

#### Test 1 : Démarrage Docker
```bash
# 1. Rebuilder les conteneurs avec la nouvelle dépendance aiofiles
docker compose -f docker-compose.pi4-standalone.yml down
docker compose -f docker-compose.pi4-standalone.yml up -d

# 2. Vérifier les logs API
docker compose -f docker-compose.pi4-standalone.yml logs api | grep config_routes

# ✅ Attendu :
# - "✅ Router included: src.api.routes.config_routes"
# - Pas d'erreur ImportError ou AttributeError
```

#### Test 2 : Health Check Messages
```bash
# 3. Tester l'endpoint de santé
curl -X GET "http://localhost:8000/config/messages/health" \
  -H "X-API-Key: VOTRE_API_KEY"

# ✅ Attendu :
# {
#   "status": "healthy",
#   "data_dir": "/app/data",
#   "files": {
#     "messages.txt": {
#       "exists": true,
#       "readable": true,
#       "size_bytes": 1227
#     },
#     "late_messages.txt": {
#       "exists": true,
#       "readable": true,
#       "size_bytes": 1636
#     }
#   }
# }
```

#### Test 3 : GET /config/messages
```bash
# 4. Lire le contenu de messages.txt
curl -X GET "http://localhost:8000/config/messages" \
  -H "X-API-Key: VOTRE_API_KEY"

# ✅ Attendu :
# {
#   "content": "Joyeux anniversaire, {name} ! ...",
#   "file_path": "/app/data/messages.txt",
#   "lines_count": 8,
#   "size_bytes": 1227
# }
```

#### Test 4 : POST /config/messages
```bash
# 5. Mettre à jour messages.txt
curl -X POST "http://localhost:8000/config/messages" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: VOTRE_API_KEY" \
  -d '{
    "content": "Joyeux anniversaire, {name} ! Test de mise à jour.\nLigne 2."
  }'

# ✅ Attendu :
# {
#   "status": "success",
#   "message": "Fichier messages.txt mis à jour avec succès",
#   "file_path": "/app/data/messages.txt",
#   "lines_count": 2,
#   "backup_created": true
# }

# 6. Vérifier la sauvegarde
docker compose -f docker-compose.pi4-standalone.yml exec api ls -la /app/data/*.bak

# ✅ Attendu :
# - Fichier messages.txt.bak existe
```

#### Test 5 : Validation Pydantic
```bash
# 7. Tester la validation (contenu vide)
curl -X POST "http://localhost:8000/config/messages" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: VOTRE_API_KEY" \
  -d '{"content": "   \n\n   "}'

# ✅ Attendu :
# HTTP 422 Unprocessable Entity
# {
#   "detail": [
#     {
#       "msg": "Le fichier doit contenir au moins un message",
#       "type": "value_error"
#     }
#   ]
# }
```

#### Test 6 : Late Messages
```bash
# 8. Vérifier le fonctionnement identique pour late_messages
curl -X GET "http://localhost:8000/config/late-messages" \
  -H "X-API-Key: VOTRE_API_KEY"

# ✅ Attendu : Contenu de late_messages.txt avec métadonnées
```

---

## 🔍 Vérifications Finales

### Persistance des Données

```bash
# 1. Arrêter les conteneurs
docker compose -f docker-compose.pi4-standalone.yml down

# 2. Modifier messages.txt directement
echo "Test persistance" > data/messages.txt

# 3. Redémarrer
docker compose -f docker-compose.pi4-standalone.yml up -d

# 4. Vérifier via API
curl -X GET "http://localhost:8000/config/messages" \
  -H "X-API-Key: VOTRE_API_KEY"

# ✅ Attendu : Contenu "Test persistance" visible via API
```

### Permissions Après Redémarrage

```bash
# 5. Vérifier que les permissions restent correctes
ls -la data/*.txt

# ✅ Attendu : Propriétaire = votre utilisateur, pas root
```

### Intégration Dashboard

Si le dashboard utilise ces endpoints :

```bash
# 6. Vérifier les logs dashboard
docker compose -f docker-compose.pi4-standalone.yml logs dashboard | grep -i "config/messages"

# ✅ Attendu : Pas d'erreur 404, appels API réussis
```

---

## 🐛 Troubleshooting

### Erreur : aiofiles not found

**Symptôme** : `ModuleNotFoundError: No module named 'aiofiles'`

**Solution** :
```bash
# Rebuilder l'image ou installer manuellement dans le conteneur
docker compose -f docker-compose.pi4-standalone.yml exec api pip install aiofiles~=23.2.1
docker compose -f docker-compose.pi4-standalone.yml restart api
```

### Erreur : Permission denied (403)

**Symptôme** : API retourne 403 lors de GET/POST /config/messages

**Solution** :
```bash
sudo ./scripts/fix_permissions.sh
docker compose -f docker-compose.pi4-standalone.yml restart api
```

### Erreur : File not found (404)

**Symptôme** : API retourne 404 sur /config/messages

**Cause** : Volume Docker mal monté ou fichiers manquants

**Solution** :
```bash
# Vérifier le montage du volume
docker compose -f docker-compose.pi4-standalone.yml exec api ls -la /app/data/

# Si vide, vérifier que les fichiers existent localement
ls -la data/

# Si manquants, les créer
touch data/messages.txt data/late_messages.txt
sudo ./scripts/fix_permissions.sh
docker compose -f docker-compose.pi4-standalone.yml restart api
```

---

## 📊 Métriques de Succès

Toutes ces conditions doivent être **VRAIES** pour valider le Go Live :

- ✅ `./scripts/setup_letsencrypt.sh` s'exécute sans erreur de permissions
- ✅ `GET /config/messages` retourne HTTP 200 avec contenu
- ✅ `POST /config/messages` met à jour le fichier avec succès
- ✅ `GET /config/late-messages` retourne HTTP 200 avec contenu
- ✅ `POST /config/late-messages` met à jour le fichier avec succès
- ✅ Les fichiers `.txt` persistent après redémarrage des conteneurs
- ✅ Les sauvegardes `.bak` sont créées automatiquement
- ✅ Le dashboard ne renvoie plus de 404 sur les routes de configuration

---

## 🚀 Go Live Checklist

Une fois les validations passées :

```bash
# 1. Corriger les permissions (si besoin)
sudo ./scripts/fix_permissions.sh

# 2. Redémarrer l'infrastructure
docker compose -f docker-compose.pi4-standalone.yml down
docker compose -f docker-compose.pi4-standalone.yml up -d

# 3. Attendre que tous les services soient healthy
docker compose -f docker-compose.pi4-standalone.yml ps

# 4. Vérifier les routes enregistrées
docker compose -f docker-compose.pi4-standalone.yml logs api | grep "Registered Routes"

# 5. Test SSL (si domaine configuré)
./scripts/setup_letsencrypt.sh --staging  # Test d'abord
./scripts/setup_letsencrypt.sh             # Prod après validation

# 6. Test fonctionnel complet
curl -X GET "http://localhost:8000/config/messages/health" -H "X-API-Key: $API_KEY"
curl -X GET "https://votre-domaine.com/api/config/messages" -H "X-API-Key: $API_KEY"
```

---

## 📚 Références

### Fichiers Modifiés
- `scripts/setup_letsencrypt.sh` → Ligne 46-55 (vérification permissions)
- `scripts/fix_permissions.sh` → Nouveau fichier (maintenance)
- `requirements.txt` → Ligne 23 (aiofiles)
- `src/api/routes/config_routes.py` → Nouveau router (448 lignes)
- `src/api/app.py` → Ligne 171 (include router)

### Documentation Technique
- **aiofiles** : https://github.com/Tinche/aiofiles
- **FastAPI File I/O** : https://fastapi.tiangolo.com/async/
- **Docker Volumes** : Voir `docker-compose.pi4-standalone.yml` lignes 156, 212, 293

### Support
Pour tout problème persistant :
1. Vérifier les logs : `docker compose logs api`
2. Exécuter : `sudo ./scripts/fix_permissions.sh`
3. Redémarrer : `docker compose restart api`
4. Si erreur 404 persiste, vérifier que le router est bien enregistré dans app.py

---

**Version** : 1.0
**Date** : 2025-12-17
**Auteur** : Expert DevOps & Backend Python (Claude)
**Status** : ✅ PRÊT POUR GO LIVE
