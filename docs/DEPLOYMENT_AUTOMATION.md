# Système de Déploiement et Maintenance Automatisé

Ce document décrit le système de déploiement et maintenance automatisé ajouté au LinkedIn Birthday Auto Bot.

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Widget Dashboard](#widget-dashboard)
- [Endpoints API](#endpoints-api)
- [Script de déploiement](#script-de-déploiement)
- [Bouton d'arrêt d'urgence](#bouton-darrêt-durgence)
- [Tâches de maintenance](#tâches-de-maintenance)
- [Sécurité](#sécurité)

## 🎯 Vue d'ensemble

Le système de déploiement et maintenance automatisé fournit :

1. **Surveillance des services** : Monitoring en temps réel de l'état des services Docker (API, Worker, Redis, Dashboard)
2. **Gestion des jobs** : Visualisation et gestion des jobs RQ (en attente, en cours, terminés, échoués)
3. **Maintenance automatisée** : Nettoyage des logs, queue, jobs terminés, optimisation de la base de données
4. **Déploiement simplifié** : Script automatique pour git pull, rebuild et restart des services
5. **Arrêt d'urgence** : Bouton pour arrêter immédiatement tous les workers actifs

## 📊 Widget Dashboard

### Emplacement

Le widget "Déploiement & Maintenance" est situé dans la colonne de droite du dashboard principal, entre "System Health" et "Top 5 Contacts".

### Sections du Widget

#### 1. Services Docker

Affiche l'état de chaque service :

- ✅ **Running** : Service opérationnel
- ⏹️ **Stopped** : Service arrêté
- ⚠️ **Error** : Service en erreur

Services surveillés :
- Redis Bot (queue)
- Bot Worker (RQ worker)
- API (FastAPI)
- Dashboard (Next.js)

#### 2. Jobs RQ

Statistiques sur les jobs :

- **En attente** : Jobs dans la queue
- **En cours** : Jobs actuellement exécutés
- **Terminés** : Jobs complétés avec succès (10 derniers)
- **Échoués** : Jobs en erreur (10 derniers)

#### 3. Actions de Maintenance

Boutons pour :

- **Nettoyer Logs** : Garde uniquement les 1000 dernières lignes de logs
- **Vider Queue** : Supprime tous les jobs en attente
- **Jobs Terminés** : Nettoie les jobs terminés et échoués de Redis
- **Optimiser DB** : Exécute VACUUM sur la base SQLite

#### 4. Actions de Déploiement

- **Git Pull** : Récupère les dernières modifications depuis le repository
- **Rebuild/Restart** : Instructions pour exécuter depuis l'hôte Docker

### Rafraîchissement

- **Automatique** : Toutes les 10 secondes
- **Manuel** : Bouton "Rafraîchir les données"

## 🔌 Endpoints API

### Python API (FastAPI)

Base URL : `http://linkedin-bot-api:8000/deployment`

#### GET /deployment/services/status

Récupère le statut de tous les services.

**Réponse** :
```json
{
  "services": [
    {
      "name": "Redis Bot",
      "status": "running",
      "uptime": "N/A"
    }
  ],
  "timestamp": "2025-11-28T10:30:00"
}
```

#### GET /deployment/jobs

Liste tous les jobs RQ.

**Réponse** :
```json
{
  "queued": [...],
  "started": [...],
  "finished": [...],
  "failed": [...],
  "total": 15
}
```

#### POST /deployment/maintenance

Exécute une action de maintenance.

**Requête** :
```json
{
  "action": "clean_logs" | "clean_queue" | "clean_finished_jobs" | "vacuum_db"
}
```

**Réponse** :
```json
{
  "action": "clean_logs",
  "status": "success",
  "message": "Logs nettoyés (5000 -> 1000 lignes)",
  "details": {
    "size_before_mb": 10.5,
    "size_after_mb": 2.1,
    "lines_removed": 4000
  }
}
```

#### POST /deployment/deploy

Exécute une action de déploiement.

**Requête** :
```json
{
  "action": "pull" | "rebuild" | "restart" | "full_deploy",
  "service": "api" | "worker" | "dashboard" (optionnel)
}
```

**Réponse** :
```json
{
  "action": "pull",
  "status": "success",
  "message": "Code mis à jour depuis Git",
  "output": "Already up to date."
}
```

### Next.js API Routes

Base URL : `http://localhost:3000/api/deployment`

Routes proxy vers l'API Python :

- `GET /api/deployment/services` → `/deployment/services/status`
- `GET /api/deployment/jobs` → `/deployment/jobs`
- `POST /api/deployment/maintenance` → `/deployment/maintenance`
- `POST /api/deployment/deploy` → `/deployment/deploy`

## 🚀 Script de Déploiement

### Utilisation

```bash
# Déploiement complet (pull + rebuild + restart)
./scripts/deploy.sh

# Redémarrer uniquement le worker
./scripts/deploy.sh --no-pull --no-rebuild --service bot-worker

# Mise à jour du code sans rebuild
./scripts/deploy.sh --no-rebuild

# Aide
./scripts/deploy.sh --help
```

### Options

- `--no-pull` : Ne pas faire de git pull
- `--no-rebuild` : Ne pas rebuild les images Docker
- `--service NAME` : Redémarrer uniquement le service spécifié
- `--help` : Afficher l'aide

### Fonctionnalités

Le script automatise :

1. **Git pull** : Récupère les dernières modifications
2. **Stash automatique** : Sauvegarde les modifications locales
3. **Rebuild Docker** : Reconstruit les images
4. **Restart services** : Redémarre les services
5. **Health check** : Vérifie que les services sont opérationnels
6. **Logs** : Affiche les logs récents

## ⏹️ Bouton d'Arrêt d'Urgence

### Fonctionnement

Le bouton d'arrêt d'urgence (dans le widget "Contrôle des Scripts") :

1. **Annule** tous les jobs en cours d'exécution
2. **Vide** la queue des jobs en attente
3. **Retourne** un rapport détaillé :
   - Nombre de jobs annulés
   - Nombre de jobs supprimés de la queue
   - Total des jobs arrêtés

### Code Backend

Implémenté dans `src/api/app.py:460-541` :

```python
@app.post("/stop", tags=["Bot"])
async def stop_bot(authenticated: bool = Depends(verify_api_key)):
    """Arrête tous les bots actifs."""
    # 1. Annuler tous les jobs en cours
    started_registry = StartedJobRegistry('linkedin-bot', connection=redis_conn)
    for job_id in started_registry.get_job_ids():
        job = Job.fetch(job_id, connection=redis_conn)
        job.cancel()

    # 2. Vider la queue
    for job_id in job_queue.job_ids:
        job = Job.fetch(job_id, connection=redis_conn)
        job.delete()

    job_queue.empty()
```

### Tests

Pour vérifier que le bouton fonctionne :

1. Lancer un job (Birthday ou Visitor)
2. Cliquer sur "Arrêt d'Urgence"
3. Vérifier dans les logs que les jobs sont bien annulés
4. Vérifier dans le widget "Jobs RQ" que les queues sont vides

## 🧹 Tâches de Maintenance

### clean_logs

Nettoie les fichiers de logs anciens.

**Comportement** :
- Garde uniquement les 1000 dernières lignes
- Calcule et retourne la taille avant/après
- Fichier : `/app/logs/linkedin_bot.log`

**Exemple** :
```bash
curl -X POST http://localhost:8000/deployment/maintenance \
  -H "X-API-Key: internal_secret_key" \
  -H "Content-Type: application/json" \
  -d '{"action": "clean_logs"}'
```

### clean_queue

Vide complètement la queue Redis des jobs en attente.

**Comportement** :
- Supprime tous les jobs de la queue `linkedin-bot`
- Retourne le nombre de jobs supprimés

### clean_finished_jobs

Supprime les jobs terminés et échoués de Redis.

**Comportement** :
- Nettoie les registres `FinishedJobRegistry` et `FailedJobRegistry`
- Garde uniquement les jobs en cours et en attente
- Libère de la mémoire Redis

### vacuum_db

Optimise la base de données SQLite.

**Comportement** :
- Exécute `VACUUM` sur la base SQLite
- Défragmente et récupère l'espace disque
- Améliore les performances des requêtes

## 🔒 Sécurité

### Authentification

Tous les endpoints de déploiement et maintenance nécessitent une authentification via API Key :

```python
@router.post("/maintenance")
async def run_maintenance(
    request: MaintenanceRequest,
    authenticated: bool = Depends(verify_api_key)
):
```

### Configuration

La clé API est configurée dans les variables d'environnement :

```yaml
# docker-compose.pi4-standalone.yml
environment:
  - API_KEY=internal_secret_key
  - BOT_API_KEY=internal_secret_key
```

⚠️ **IMPORTANT** : Changez cette clé en production !

### Limitations

Les actions de déploiement (rebuild, restart) nécessitent d'être exécutées depuis l'hôte Docker car :

1. Le conteneur n'a pas accès au Docker daemon de l'hôte
2. Cela évite les risques de sécurité (privilege escalation)
3. Utilisez le script `scripts/deploy.sh` pour ces opérations

### Bonnes Pratiques

1. **Changez l'API Key** en production
2. **Limitez l'accès** au dashboard (firewall, VPN)
3. **Surveillez les logs** après chaque maintenance
4. **Testez** les actions sur un environnement de dev d'abord
5. **Backupez** la base de données avant VACUUM

## 📝 Dépendances

### Python

Ajout de `httpx` dans `requirements.txt` :

```txt
httpx==0.25.2
```

### Next.js

Aucune dépendance supplémentaire requise.

## 🐛 Troubleshooting

### Le widget ne charge pas

1. Vérifier que l'API Python est accessible :
   ```bash
   curl http://localhost:8000/health
   ```

2. Vérifier les logs du dashboard :
   ```bash
   docker compose logs dashboard
   ```

3. Vérifier la configuration des variables d'environnement

### Les actions de maintenance échouent

1. Vérifier les permissions sur les fichiers :
   ```bash
   ls -la /app/logs/linkedin_bot.log
   ```

2. Vérifier que Redis est accessible :
   ```bash
   docker compose exec redis-bot redis-cli ping
   ```

3. Vérifier les logs de l'API :
   ```bash
   docker compose logs api
   ```

### Le script de déploiement échoue

1. Vérifier que Docker Compose est installé :
   ```bash
   docker compose version
   ```

2. Vérifier les permissions du script :
   ```bash
   chmod +x scripts/deploy.sh
   ```

3. Exécuter avec plus de verbosité :
   ```bash
   bash -x scripts/deploy.sh
   ```

## 📚 Ressources

- [Documentation RQ](https://python-rq.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Next.js API Routes](https://nextjs.org/docs/api-routes/introduction)

## 🔄 Mises à jour futures

Améliorations possibles :

1. **Webhooks** : Notification Slack/Discord lors des déploiements
2. **Rollback automatique** : Revenir à la version précédente en cas d'échec
3. **Blue-Green Deployment** : Déploiement sans interruption de service
4. **Health checks avancés** : Vérification de la cohérence des données
5. **Backup automatique** : Sauvegarde avant chaque déploiement
6. **Monitoring Prometheus** : Métriques détaillées des déploiements
