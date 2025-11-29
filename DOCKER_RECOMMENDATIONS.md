# Recommandations Docker pour Raspberry Pi 4

Ce document décrit les modifications Docker recommandées pour améliorer la stabilité et les performances du bot sur Raspberry Pi 4.

## 1. Augmentation de la mémoire RAM pour bot-worker

**Problème**: La limite actuelle de 900 Mo est insuffisante pour Chromium + LinkedIn
**Solution**: Augmenter à 1.5 Go

### Modification à apporter dans `docker-compose.pi4-standalone.yml`:

```yaml
bot-worker:
  # ... autres configurations ...
  deploy:
    resources:
      limits:
        memory: 1500M  # Était: 900M
        cpus: '1.0'
      reservations:
        cpus: '0.5'
        memory: 750M   # Était: 450M
```

**Impact**:
- ✅ Réduit les risques de crash silencieux de Chromium
- ✅ Améliore la stabilité lors du chargement de pages lourdes
- ⚠️ Requiert au moins 2 Go de RAM libre sur le Pi 4

## 2. Montage du code source pour développement

**Problème**: Les modifications de code ne sont pas prises en compte sans rebuild complet
**Solution**: Monter le dossier `./src` en volume

### Modification à apporter dans `docker-compose.pi4-standalone.yml`:

```yaml
bot-worker:
  # ... autres configurations ...
  volumes:
    - ./data:/app/data
    - ./config:/app/config
    - ./logs:/app/logs
    - ./src:/app/src  # NOUVEAU: Monte le code source en live

api:
  # ... autres configurations ...
  volumes:
    - ./data:/app/data
    - ./config:/app/config
    - ./logs:/app/logs
    - ./src:/app/src  # NOUVEAU: Monte le code source en live
```

**Impact**:
- ✅ Les modifications de code sont instantanées (redémarrage du conteneur suffit)
- ✅ Gain de temps pendant le développement/debug
- ⚠️ Ne PAS utiliser en production (risque de modification accidentelle)

## 3. Configuration DNS Google (Optionnel)

**Problème**: Problèmes de résolution DNS avec certains routeurs
**Solution**: Forcer l'utilisation des DNS Google

### Modification à apporter dans `docker-compose.pi4-standalone.yml`:

```yaml
bot-worker:
  # ... autres configurations ...
  dns:
    - 8.8.8.8
    - 8.8.4.4

api:
  # ... autres configurations ...
  dns:
    - 8.8.8.8
    - 8.8.4.4
```

**Impact**:
- ✅ Résolution DNS plus fiable
- ✅ Diagnostics réseau plus faciles
- ℹ️ Optionnel si votre réseau local fonctionne correctement

## 4. Application des modifications

### Option A: Modifications manuelles
1. Éditez `docker-compose.pi4-standalone.yml`
2. Appliquez les changements ci-dessus
3. Redémarrez les services:
   ```bash
   docker-compose -f docker-compose.pi4-standalone.yml down
   docker-compose -f docker-compose.pi4-standalone.yml up -d
   ```

### Option B: Utiliser le fichier de patch
Si un fichier `docker-compose.pi4-standalone.yml.patch` est fourni:
```bash
patch -p0 < docker-compose.pi4-standalone.yml.patch
docker-compose -f docker-compose.pi4-standalone.yml down
docker-compose -f docker-compose.pi4-standalone.yml up -d
```

## Vérification

Après application des modifications, vérifiez:

1. **Mémoire allouée**:
   ```bash
   docker stats bot-worker --no-stream
   ```
   Vous devriez voir `LIMIT` à 1.5 GiB

2. **Volumes montés**:
   ```bash
   docker inspect bot-worker | grep -A 10 Mounts
   ```
   Vous devriez voir `/app/src` dans la liste

3. **DNS configurés**:
   ```bash
   docker exec bot-worker cat /etc/resolv.conf
   ```
   Vous devriez voir `nameserver 8.8.8.8`

## Notes importantes

- ⚠️ **RAM requise**: Avec ces modifications, votre Pi 4 devrait avoir au minimum 2 Go de RAM libre
- ⚠️ **Environnement de développement**: Le montage de `./src` est idéal pour le développement mais à éviter en production
- ✅ **Compatibilité**: Ces modifications sont compatibles avec les corrections de code appliquées dans `src/core/`

## Résumé des corrections combinées

Les corrections de **code** (auth_manager.py, base_bot.py, browser_manager.py) + les corrections **Docker** forment une solution complète:

| Aspect | Correction Code | Correction Docker |
|--------|----------------|------------------|
| Cookies expirés | ✅ Nettoyage auto | - |
| Timeouts | ✅ 60s→90s, 15s→30s | - |
| Détection login | ✅ Fallbacks multiples | - |
| GPU Pi 4 | ✅ `--disable-gpu` | - |
| RAM | - | ✅ 900M→1.5G |
| Développement | - | ✅ Volume ./src |
| Réseau | ✅ Check connectivité | ✅ DNS Google |

**Recommandation**: Appliquer **les deux** ensembles de corrections pour une solution optimale.
