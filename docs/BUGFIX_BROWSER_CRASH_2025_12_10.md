# Bugfix: Browser Crash "Target Closed" - 2025-12-10

## Problème

Le bot LinkedIn (birthday et unlimited) crashait systématiquement avec l'erreur :
```
Page.goto: Target page, context or browser has been closed
```

Cette erreur se produisait lors de `check_login_status()`, environ 50-60 secondes après le démarrage du bot.

## Analyse de la Cause Racine

Plusieurs problèmes combinés causaient le crash :

### 1. Limite de Mémoire Docker Insuffisante (PROBLÈME PRINCIPAL)
- Le conteneur `bot-worker` avait une limite de **1200M**
- Le navigateur Chromium utilisait **512MB** (`--max-old-space-size=512`)
- Python + Playwright + overhead utilisaient ~300-400MB
- **Total : ~900-1000MB**, proche de la limite de 1200M
- Lors de pics de mémoire (navigation, parsing DOM), le conteneur dépassait la limite
- Docker OOM killer tuait le navigateur → erreur "Target closed"

### 2. Vérification de Connectivité Problématique
- `_check_connectivity()` faisait un `goto` vers Google.com AVANT LinkedIn
- Ce goto supplémentaire augmentait la consommation mémoire
- Pouvait causer des crashes ou timeouts

### 3. Paramètres Navigateur Trop Restrictifs
- `--renderer-process-limit=1` : trop restrictif, causait des instabilités
- `--max-old-space-size=512` : insuffisant pour les pages modernes LinkedIn
- Timeouts de 60s-90s : insuffisants sur Pi4

### 4. wait_until="domcontentloaded" Lent
- Attente complète du parsing DOM
- Augmentait le temps de navigation et la mémoire utilisée
- Timeout possible sur systèmes lents

## Solutions Implémentées

### 1. Augmentation Limite Mémoire Docker ✅
**Fichier :** `docker-compose.pi4-standalone.yml`
```yaml
memory: 1200M → 1800M
memswap_limit: 1400M → 2000M
```
- Permet au navigateur d'utiliser 1024MB
- Laisse ~600-800MB pour Python/Playwright
- Marge de sécurité pour pics de mémoire

### 2. Suppression Vérification Connectivité ✅
**Fichier :** `src/core/base_bot.py:140-155`
- Supprimé l'appel à `_check_connectivity()` dans `check_login_status()`
- Vérification directe de l'état du navigateur
- Ajout de vérification `browser.is_connected()`
- Logs plus détaillés pour diagnostic

### 3. Augmentation Ressources Navigateur ✅
**Fichier :** `src/core/browser_manager.py:76-104`
```python
# Avant
--renderer-process-limit=1
--max-old-space-size=512

# Après
--renderer-process-limit=2
--max-old-space-size=1024
--js-flags=--max-old-space-size=1024
```
- Plus de stabilité avec 2 processus renderer
- 1024MB heap V8 pour pages modernes
- Flag JS supplémentaire pour garantir la limite

### 4. Augmentation Timeouts ✅
**Fichiers :** `src/core/base_bot.py` et `src/core/browser_manager.py`
```python
# Avant
timeout = 60000  # 60s
launch_timeout = 60000

# Après
timeout = 120000  # 120s
launch_timeout = 120000
```
- Plus de temps pour navigation sur Pi4
- Timeout page : 120s
- Timeout lancement navigateur : 120s

### 5. Optimisation Navigation ✅
**Fichier :** `src/core/base_bot.py:175-181`
```python
# Avant
self.page.goto(..., wait_until="domcontentloaded")

# Après
self.page.goto(..., wait_until="commit")
time.sleep(2)
```
- `wait_until="commit"` : plus rapide, attend juste le commit réseau
- Économise mémoire en ne parsant pas tout le DOM
- Sleep 2s pour stabiliser la page

### 6. Meilleure Gestion Erreurs ✅
**Fichier :** `src/core/base_bot.py:204-223`
- Diagnostic automatique de l'état du navigateur en cas d'erreur
- Logs détaillés avec `exc_info=True`
- Vérification `browser.is_connected()` avant navigation
- Messages d'erreur plus clairs

## Résultats Attendus

Après ces correctifs :
- ✅ Le navigateur ne devrait plus crasher par manque de mémoire
- ✅ Navigation plus rapide et stable
- ✅ Meilleure utilisation des ressources Pi4
- ✅ Messages d'erreur plus clairs pour diagnostic

## Tests Recommandés

1. **Test Navigation Standard :**
   ```bash
   docker compose -f docker-compose.pi4-standalone.yml restart bot-worker
   # Vérifier les logs : docker compose -f docker-compose.pi4-standalone.yml logs -f bot-worker
   ```

2. **Test Mémoire :**
   ```bash
   docker stats bot-worker
   # Vérifier que la mémoire reste < 1600M
   ```

3. **Test Fonctionnel :**
   - Déclencher un job birthday via le dashboard
   - Vérifier que le bot navigue vers LinkedIn sans crash
   - Vérifier que les messages sont envoyés

## Monitoring

Pour surveiller la santé du système après le déploiement :

```bash
# Logs en temps réel
docker compose -f docker-compose.pi4-standalone.yml logs -f bot-worker

# Utilisation mémoire
docker stats bot-worker

# Santé du conteneur
docker inspect bot-worker | jq '.[0].State.Health'
```

## Rollback (si nécessaire)

Si les changements causent des problèmes :

```bash
git revert HEAD
docker compose -f docker-compose.pi4-standalone.yml up -d --build
```

## Notes

- Ces changements sont spécifiques au Pi4
- Sur systèmes avec plus de RAM, les limites peuvent être augmentées
- Sur systèmes avec moins de RAM, revenir aux limites précédentes
- Monitoring régulier recommandé pendant 1-2 semaines

## Auteur

Claude AI - 2025-12-10

## Références

- Issue originale : Logs d'erreur "Target closed"
- Playwright Docs : https://playwright.dev/docs/api/class-browsertype#browser-type-launch
- Docker Memory Management : https://docs.docker.com/config/containers/resource_constraints/
