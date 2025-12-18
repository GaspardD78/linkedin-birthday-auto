# RAPPORT D'AUDIT DE SÉCURITÉ ET PERFORMANCE
## LinkedIn Birthday Auto - Raspberry Pi 4 (4GB RAM / 32GB SD)

**Date:** 2025-12-18
**Version analysée:** 2.3.0
**Environnement cible:** Raspberry Pi 4 (ARM64, 4GB RAM, 32GB SD)

---

## 🔴 PROBLÈMES CRITIQUES (9)

### 1. Grafana - Accès Admin Anonyme
**Fichier:** `docker-compose.pi4-standalone.yml:377-380`
```yaml
- GF_AUTH_ANONYMOUS_ENABLED=true
- GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
```
**Impact:** N'importe qui sur le réseau peut accéder à Grafana avec les droits **Admin** sans aucune authentification. Permet de modifier les dashboards, accéder aux données, et potentiellement exfiltrer des métriques sensibles.

---

### 2. Mode Privileged sur le Conteneur API
**Fichier:** `docker-compose.pi4-standalone.yml:135`
```yaml
privileged: true
```
**Impact:** Le conteneur API a accès **complet au kernel** et au host. Si le conteneur est compromis (via RCE ou autre), l'attaquant a **accès root au Raspberry Pi entier**. Les montages systemd (`/run/systemd`, `/var/run/dbus`) aggravent le risque.

---

### 3. CORS Permissif (Wildcard)
**Fichier:** `src/api/app.py:132-138`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # DANGEREUX
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
**Impact:** Avec `allow_credentials=True` ET `allow_origins=["*"]`, n'importe quel site web peut faire des requêtes authentifiées vers l'API. Vulnérabilité CSRF critique.

---

### 4. Injection de Commandes Potentielle - Sourcing Bot
**Fichier:** `src/api/routes/sourcing.py:541-558`
```python
cmd = [
    sys.executable,
    "-m", "src.bots.visitor_bot",
    "--keywords", *keywords,  # Données utilisateur non sanitisées
    "--location", location,    # Données utilisateur non sanitisées
    ...
]
result = subprocess.run(cmd, ...)
```
**Impact:** Si `keywords` ou `location` contiennent des caractères spéciaux malveillants, cela peut mener à une injection de commandes. Bien que `subprocess.run` avec liste soit plus sûr que `shell=True`, les arguments ne sont pas validés.

---

### 5. Node Exporter - Accès Root au Filesystem
**Fichier:** `docker-compose.pi4-standalone.yml:405-407`
```yaml
pid: host
volumes:
  - '/:/host:ro,rslave'
```
**Impact:** Node Exporter a accès en lecture à **tout le système de fichiers du host**. Si compromis, permet l'exfiltration de fichiers sensibles (clés SSH, configurations, données).

---

### 6. Endpoint /health Non Protégé
**Fichier:** `src/api/app.py:212-229`
```python
@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    # Aucune vérification d'API key
```
**Impact:** Fuite d'informations sur l'état du système, la version, l'uptime et la connectivité base de données. Utile pour le fingerprinting par un attaquant.

---

### 7. Endpoint Root (/) Non Protégé
**Fichier:** `src/api/app.py:201-208`
```python
@app.get("/", tags=["General"])
async def root():
    return {"name": "LinkedIn Automation API", "version": "2.3.0", ...}
```
**Impact:** Expose la version exacte de l'application, facilitant l'exploitation de vulnérabilités connues.

---

### 8. Import de pickle Non Utilisé (Risque Potentiel)
**Fichier:** `src/api/app.py:10`
```python
import pickle
```
**Impact:** `pickle` est un vecteur d'exécution de code arbitraire si utilisé pour désérialiser des données non fiables. Bien que non utilisé actuellement, sa présence est suspecte et risquée.

---

### 9. Secrets Potentiellement Exposés dans les Erreurs
**Fichier:** `src/api/app.py:141-147`
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        content={"detail": "Internal Server Error", "error": str(exc)},
    )
```
**Impact:** En mode debug ou si une exception contient des données sensibles (chemins, credentials), elles sont renvoyées au client.

---

## 🟠 PROBLÈMES MAJEURS (12)

### 1. Redis AOF avec Sync Fréquent - Usure SD Card
**Fichier:** `docker-compose.pi4-standalone.yml:47-50`
```yaml
--appendonly yes
--appendfsync everysec
```
**Impact:** Écriture disque **chaque seconde** sur la carte SD. Sur 32GB, avec une endurance de ~10,000 P/E cycles, cela peut user la carte en 2-3 ans d'utilisation intensive.

---

### 2. SQLite mmap_size Excessif (256MB)
**Fichier:** `src/core/database.py:119`
```python
conn.execute("PRAGMA mmap_size=268435456")  # 256MB
```
**Impact:** Sur un Pi4 avec 4GB RAM et ~2.2GB utilisés par les conteneurs, allouer 256MB de mmap peut provoquer du swap ou des OOM kills.

---

### 3. SQLite Cache Trop Grand (20MB par connexion)
**Fichier:** `src/core/database.py:113`
```python
conn.execute("PRAGMA cache_size=-5000")  # ~20MB
```
**Impact:** Avec plusieurs connexions thread-local (API + Worker), le cache total peut atteindre 80-100MB. Excessif pour le Pi4.

---

### 4. Prometheus - Rétention 15 Jours
**Fichier:** `docker-compose.pi4-standalone.yml:358`
```yaml
--storage.tsdb.retention.time=15d
```
**Impact:** Prometheus stocke les métriques pendant 15 jours. Avec node-exporter et les métriques applicatives, cela peut consommer 1-2GB sur la SD card.

---

### 5. Deux Instances Redis - Overhead Inutile
**Fichier:** `docker-compose.pi4-standalone.yml` (redis-bot + redis-dashboard)
**Impact:** 256MB + 64MB = 320MB de RAM pour deux Redis. Une seule instance avec des databases séparées (SELECT 0/1) suffirait.

---

### 6. pip install à Chaque Démarrage
**Fichier:** `docker-compose.pi4-standalone.yml:131-133`
```yaml
command: >
  sh -c "pip install -r /app/requirements.txt && ..."
```
**Impact:** À chaque restart du conteneur, pip vérifie et installe les dépendances. Lent (30-60s) et écrit sur la SD card. Inutile si l'image Docker est bien construite.

---

### 7. Volume redis-dashboard avec Persistence Désactivée
**Fichier:** `docker-compose.pi4-standalone.yml:97-98`
```yaml
volumes:
- redis-dashboard-data:/data  # Mais --appendonly no
```
**Impact:** Incohérence : volume créé mais persistence désactivée. Consomme de l'espace inutilement.

---

### 8. Logs JSON dans Docker - Écritures SD
**Fichier:** `docker-compose.pi4-standalone.yml:64-69, 219-225, 257-261`
```yaml
logging:
  driver: json-file
  options:
    max-size: 5m
    max-file: '2'
```
**Impact:** Chaque service écrit ses logs sur la SD. 7 services × 10MB max = 70MB, mais les écritures fréquentes usent la carte.

---

### 9. Timeouts Navigateur Très Longs (120s)
**Fichier:** `src/core/browser_manager.py:164-167`
```python
timeout = getattr(self.config, "timeout", 120000)  # 120s
self.page.set_default_timeout(timeout)
```
**Impact:** Un timeout de 2 minutes bloque le worker RQ. Si LinkedIn est lent ou down, le bot reste bloqué longtemps, consommant RAM et CPU.

---

### 10. Chromium RAM-Intensive sans Limite
**Fichier:** `src/core/browser_manager.py:77-104`
```python
"--max-old-space-size=1024",  # 1GB de heap V8
```
**Impact:** Chromium peut consommer jusqu'à 1GB+ de RAM. Sur un Pi4 avec d'autres services, cela peut provoquer des OOM kills.

---

### 11. Scheduler APScheduler - Fichier SQLite Séparé
**Fichier:** `src/scheduler/scheduler.py:234`
```python
'default': SQLAlchemyJobStore(url='sqlite:////app/data/scheduler_apscheduler.db')
```
**Impact:** Un deuxième fichier SQLite pour le scheduler. Double les écritures WAL et les checkpoints sur la SD card.

---

### 12. Playwright - Pas de Limite de Mémoire Conteneur
**Fichier:** `docker-compose.pi4-standalone.yml:213-219`
```yaml
deploy:
  resources:
    limits:
      cpus: '1.5'
    # Pas de limite mémoire !
```
**Impact:** Le worker peut consommer toute la RAM disponible, causant des OOM kills ou du swap agressif.

---

## 🟡 PROBLÈMES MINEURS (10)

### 1. Mot de Passe en Clair Supporté (Rétrocompatibilité)
**Fichier:** `dashboard/lib/auth.ts:73-78`
```typescript
if (!isPasswordHashed) {
    // Fallback pour rétrocompatibilité (mot de passe en clair)
    console.warn('⚠️  DASHBOARD_PASSWORD is not bcrypt-hashed!');
    return password === DEFAULT_PASSWORD;
}
```

---

### 2. Healthcheck Conteneur Bot-Worker Trop Espacé
**Fichier:** `docker-compose.pi4-standalone.yml:228-232`
```yaml
healthcheck:
  interval: 60s
  retries: 3
```
**Impact:** 3 minutes pour détecter un worker mort.

---

### 3. Timeout Git Pull dans Deployment (30s)
**Fichier:** `src/api/routes/deployment.py:490-491`
```python
result = subprocess.run(["git", "pull"], timeout=30)
```
**Impact:** Sur une connexion lente du Pi4, 30s peut ne pas suffire pour un pull avec beaucoup de changements.

---

### 4. Absence de Rate Limiting sur /metrics Prometheus
**Fichier:** `src/api/app.py:193-197`
```python
app.mount("/metrics", metrics_app)  # Pas de protection
```

---

### 5. Hardcoded User-Agent Obsolète
**Fichier:** `src/core/browser_manager.py:295`
```python
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/120.0.0.0"
```
**Impact:** Chrome 120 est daté (Décembre 2023). LinkedIn peut détecter un navigateur obsolète.

---

### 6. Terminal Execute - Mock Outputs en Production
**Fichier:** `dashboard/app/api/terminal/execute/route.ts:52-93`
**Impact:** Les commandes "restart", "status", etc. retournent des données mockées, pas l'état réel.

---

### 7. Absence de Validation sur schedule_config dans Scheduler
**Fichier:** `src/scheduler/scheduler.py:515-540`
```python
return CronTrigger.from_crontab(cron_expr, timezone='Europe/Paris')
```
**Impact:** Expression cron non validée. Une expression malformée peut crasher le scheduler.

---

### 8. Journal Mode WAL Non Vérifié au Démarrage
**Fichier:** `src/core/database.py:107`
```python
conn.execute("PRAGMA journal_mode=WAL")
# Pas de vérification du retour
```

---

### 9. Manque de Jitter dans les Retries Redis
**Fichier:** `src/api/routes/bot_control.py:56-61`
```python
wait=wait_exponential(multiplier=1, min=2, max=10)
# Pas de jitter - thundering herd possible
```

---

### 10. Chemins Hardcodés
**Fichier:** `src/core/auth_manager.py:145`
```python
writable_auth_file = Path("/app/data/auth_state.json")
```
**Impact:** Non-flexible pour les tests ou configurations alternatives.

---

## 📊 RÉSUMÉ DES RISQUES

| Sévérité | Nombre | Impact Principal |
|----------|--------|------------------|
| 🔴 CRITIQUE | 9 | Sécurité compromise, accès non autorisé |
| 🟠 MAJEUR | 12 | Usure SD card, performances dégradées, OOM |
| 🟡 MINEUR | 10 | Dette technique, maintenance difficile |

---

## 🎯 ACTIONS PRIORITAIRES RECOMMANDÉES

### Priorité 1 - IMMÉDIAT (Sécurité critique)
1. Désactiver l'accès anonyme Grafana (`GF_AUTH_ANONYMOUS_ENABLED=false`)
2. Retirer `privileged: true` du conteneur API
3. Restreindre CORS aux origines connues (domaine du dashboard uniquement)
4. Supprimer l'import `pickle` non utilisé

### Priorité 2 - URGENT (Sécurité importante)
5. Valider/sanitiser les entrées utilisateur dans le sourcing bot
6. Ajouter protection API_KEY sur `/health` et `/`
7. Ne pas exposer les messages d'erreur complets aux clients

### Priorité 3 - IMPORTANT (Performance/Durabilité)
8. Réduire `appendfsync` Redis à `no` ou utiliser tmpfs pour Redis
9. Réduire `mmap_size` SQLite à 64MB max
10. Limiter la mémoire du conteneur bot-worker à 1GB
11. Fusionner les deux instances Redis en une seule
12. Retirer le pip install du démarrage des conteneurs

### Priorité 4 - AMÉLIORATION (Optimisations)
13. Réduire la rétention Prometheus à 7 jours
14. Mettre à jour le User-Agent Chrome
15. Ajouter du jitter aux retries Redis
16. Valider les expressions cron avant enregistrement

---

## 📋 CHECKLIST DE VALIDATION

- [ ] Grafana : accès anonyme désactivé
- [ ] Conteneur API : mode privileged retiré
- [ ] CORS : origines restreintes
- [ ] Endpoints publics : protégés par API_KEY
- [ ] Redis : appendfsync optimisé ou tmpfs
- [ ] SQLite : mmap réduit
- [ ] Bot-worker : limite mémoire définie
- [ ] Erreurs : messages génériques en production

---

*Rapport généré par audit automatisé - Décembre 2025*
