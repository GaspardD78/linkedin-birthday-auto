# Page "Vue d'ensemble" - Documentation d'Implémentation

## 📋 Vue d'ensemble

La page "Vue d'ensemble" (`/overview`) est une nouvelle fonctionnalité du dashboard qui permet de piloter et suivre l'activité du bot LinkedIn de manière centralisée et intuitive.

## ✨ Fonctionnalités

### 1. Affichage du Statut du Bot

La page affiche en temps réel le statut global du bot :
- **Actif** : Un ou plusieurs jobs sont en cours d'exécution
- **Arrêté** : Aucun job en cours

Le statut est rafraîchi automatiquement toutes les 5 secondes.

### 2. Informations du Dernier Run

Affiche les détails du dernier run exécuté :
- Date et heure locale du run
- Nombre de messages envoyés
- Nombre de messages ignorés
- Nombre d'erreurs rencontrées
- Statut final (succès/erreur)

### 3. Prochain Run Planifié

Indique si un run automatique est planifié :
- Actuellement : "Mode manuel uniquement"
- Mention de l'état de l'auto-run (activé/désactivé)

### 4. Actions Rapides

Trois boutons permettent de contrôler le bot :

#### a) **Lancer un run maintenant**
- Démarre immédiatement un run du bot d'anniversaire
- Désactivé si un job est déjà en cours
- Utilise l'API `POST /api/bot/action` avec `action: 'start'`

#### b) **Toggle pause/réactivation auto-run**
- Active ou désactive l'exécution automatique des runs
- État persisté localement (à implémenter côté backend pour persistance globale)
- Toggle visuel avec icône Play/Pause

#### c) **Arrêter le run en cours** ⭐ (Nouvelle fonctionnalité)
- **Visible uniquement** quand un job est actif
- Permet d'arrêter proprement le job en cours
- Gestion de l'état de chargement pendant l'arrêt
- Confirmation via toast notification

### 5. Résumé des 7 Derniers Jours

Affiche un résumé agrégé de l'activité :
- **Messages envoyés** : Total hebdomadaire
- **Profils visités** : Total hebdomadaire
- **Erreurs** : Total hebdomadaire

Détail jour par jour avec :
- Date au format local (jour/mois)
- Nombre de messages, visites et erreurs par jour

### 6. Logs Récents

Affiche les 20 dernières lignes de logs :
- Logs formatés en mode console
- Scroll automatique
- Bouton "Voir plus" redirigeant vers `/logs`

## 🔧 Implémentation Technique

### Architecture Backend → Frontend

```
Frontend (Next.js)          Backend (FastAPI)              Worker (RQ)
     │                            │                            │
     ├─ GET /api/bot/status ──────▶ GET /bot/status           │
     │  (Récupère statut)           (Route granulaire)        │
     │                            │                            │
     ├─ POST /api/bot/action ─────▶ POST /bot/start-birthday ─▶ Job enqueued
     │  { action: 'start' }         (Démarre le bot)           │
     │                            │                            │
     └─ POST /api/bot/action ─────▶ POST /bot/stop ───────────▶ Job.cancel()
        { action: 'stop',           (Arrête le job)
          job_id: 'xxx' }
```

### Bouton "Arrêter le run en cours" - Fonctionnement Détaillé

#### 1. Détection du Job Actif

```typescript
// dashboard/app/(dashboard)/overview/page.tsx

const isJobRunning = botStatus && botStatus.active_jobs.length > 0
const currentJob = isJobRunning ? botStatus.active_jobs[0] : null
```

Le composant interroge l'API `/api/bot/status` toutes les 5 secondes pour obtenir :
- Liste des jobs actifs (`active_jobs`)
- Liste des jobs en queue (`queued_jobs`)
- Statut du worker

#### 2. Affichage Conditionnel

```typescript
<Button
  onClick={handleStopJob}
  disabled={!isJobRunning || loading === 'stop'}
  variant="destructive"
>
  Arrêter le run en cours
</Button>
```

Le bouton est :
- **Visible** : Toujours affiché pour clarté de l'interface
- **Désactivé** : Quand aucun job n'est actif
- **Actif** : Uniquement quand `isJobRunning === true`

#### 3. Appel API d'Arrêt

```typescript
const handleStopJob = async () => {
  if (!currentJob) return

  setLoading('stop')
  try {
    // Appel API avec job_id spécifique
    await stopBot(undefined, currentJob.id)

    toast({
      title: "Arrêt demandé",
      description: "La demande d'arrêt a été envoyée au bot."
    })

    await fetchData() // Rafraîchit le statut
  } catch (error) {
    toast({ variant: "destructive", title: "Erreur", description: error.message })
  } finally {
    setLoading(null)
  }
}
```

#### 4. Proxy Next.js (Correction Appliquée)

**Fichier** : `dashboard/app/api/bot/action/route.ts`

```typescript
else if (action === 'stop') {
  // Utiliser le endpoint granulaire /bot/stop
  endpoint = '/bot/stop';
  payload = {};

  // Ajouter job_type si fourni (arrêt par type)
  if (body.job_type) {
    payload.job_type = body.job_type;
  }

  // Ajouter job_id si fourni (arrêt par ID spécifique)
  if (body.job_id) {
    payload.job_id = body.job_id;
  }
}
```

**Avant** : Le proxy appelait `/stop` (arrêt d'urgence de TOUS les jobs)
**Après** : Le proxy appelle `/bot/stop` avec `job_id` (arrêt granulaire)

#### 5. Backend FastAPI - Route Granulaire

**Fichier** : `src/api/routes/bot_control.py`

La route `/bot/stop` (lignes 147-208) gère trois modes d'arrêt :

```python
@router.post("/bot/stop")
async def stop_bot(request: StopRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Arrête les bots de manière granulaire.

    Modes :
    1. job_id fourni → Arrête ce job spécifique
    2. job_type fourni → Arrête tous les jobs de ce type
    3. Aucun paramètre → Arrêt d'urgence (tous les jobs)
    """

    # Mode 1 : Arrêt par ID
    if request.job_id:
        job = Job.fetch(request.job_id, connection=redis_conn)
        job.cancel()
        return {"status": "success", "message": f"Job {request.job_id} stopped"}

    # Mode 2 : Arrêt par type
    if request.job_type:
        for job in all_jobs:
            if job.meta.get('job_type') == request.job_type:
                job.cancel()
        return {"status": "success", "stopped_count": stopped_count}

    # Mode 3 : Arrêt d'urgence (tous)
    for job in all_jobs:
        job.cancel()
    return {"status": "success", "stopped_count": stopped_count}
```

#### 6. Worker RQ - Annulation du Job

**Fichier** : `src/queue/worker.py` et `src/queue/tasks.py`

Lorsque `job.cancel()` est appelé :
1. RQ marque le job comme "canceled"
2. Le worker détecte l'état et arrête l'exécution
3. Le job passe de `started` à `canceled`
4. La mémoire est libérée proprement

**Note** : RQ gère automatiquement l'annulation. Le code du bot n'a pas besoin de vérifier périodiquement un flag d'arrêt, car RQ tue le processus du worker de manière propre.

### Gestion des États

Le composant gère plusieurs états :
- `loading` : Indique quelle action est en cours (`'start'`, `'stop'`, `null`)
- `botStatus` : Statut complet des jobs (active, queued)
- `lastRun` : Informations du dernier run
- `weekSummary` : Données des 7 derniers jours
- `recentLogs` : Logs récents
- `autoRunEnabled` : État du toggle auto-run

### Rafraîchissement Automatique

```typescript
useEffect(() => {
  fetchData() // Appel initial
  const interval = setInterval(fetchData, 5000) // Toutes les 5s
  return () => clearInterval(interval) // Cleanup
}, [])
```

## 🎨 Design et UX

### Feedback Utilisateur

1. **Toast Notifications** :
   - Succès : "Bot démarré", "Arrêt demandé"
   - Erreur : Message d'erreur détaillé

2. **États de Chargement** :
   - Icône spinner pendant les opérations
   - Boutons désactivés pendant le chargement

3. **Indicateurs Visuels** :
   - Badge "Running" animé quand un job est actif
   - Icônes colorées pour les différents statuts
   - Couleurs sémantiques (vert=succès, rouge=erreur, bleu=info)

### Responsive Design

- Layout adaptatif avec grilles CSS
- Mobile-first avec breakpoints MD et LG
- Scroll automatique pour les logs

## 🚀 Utilisation

### Accès à la Page

1. Connectez-vous au dashboard
2. Cliquez sur "Vue d'ensemble" dans le menu latéral
3. La page se charge avec toutes les données en temps réel

### Arrêter un Run en Cours

1. Vérifiez que le badge "Running" est affiché
2. Le bouton "Arrêter le run en cours" devient actif (rouge)
3. Cliquez sur le bouton
4. Confirmation via toast : "Demande d'arrêt envoyée…"
5. Le statut se rafraîchit automatiquement (5s max)
6. Le badge passe à "Idle" quand l'arrêt est effectif

### Sécurité

- ✅ Authentification requise (JWT token)
- ✅ Vérification API key côté backend
- ✅ Arrêt propre sans corruption de données
- ✅ Logs de toutes les actions d'arrêt

## 📊 APIs Utilisées

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/bot/status` | GET | Récupère le statut détaillé des jobs |
| `/api/bot/action` | POST | Démarre ou arrête un bot |
| `/api/history?days=7` | GET | Récupère l'historique des 7 derniers jours |
| `/api/logs?limit=20` | GET | Récupère les 20 derniers logs |
| `/api/stats` | GET | Récupère les statistiques globales |

## 🔄 Flux Complet d'Arrêt

```
1. User clique sur "Arrêter le run en cours"
   ↓
2. handleStopJob() appelé
   ↓
3. POST /api/bot/action { action: 'stop', job_id: 'xxx' }
   ↓
4. Proxy Next.js → POST /bot/stop { job_id: 'xxx' }
   ↓
5. FastAPI récupère le job via RQ
   ↓
6. job.cancel() appelé
   ↓
7. RQ marque le job comme "canceled"
   ↓
8. Worker arrête l'exécution proprement
   ↓
9. Frontend rafraîchit le statut (5s max)
   ↓
10. Badge passe à "Idle", bouton se désactive
```

## 🛠️ Maintenance et Extension

### Ajouter la Persistance de l'Auto-Run

Actuellement, le toggle auto-run est local. Pour le rendre global :

1. Ajouter une table `settings` dans SQLite :
   ```sql
   CREATE TABLE settings (
     key TEXT PRIMARY KEY,
     value TEXT NOT NULL
   );
   ```

2. Créer une API `/api/settings` (GET/POST)

3. Implémenter un scheduler (APScheduler, cron, etc.)

### Améliorer la Détection du Dernier Run

Actuellement, le dernier run est déduit de l'historique. Pour plus de précision :

1. Ajouter une table `runs` dans SQLite avec :
   - `run_id`, `start_time`, `end_time`, `status`, `messages_sent`, `errors`

2. Créer une API `/api/runs/latest`

3. Mettre à jour le composant pour utiliser cette API

## 🐛 Dépannage

### Le bouton ne s'active pas

- Vérifiez que l'API `/api/bot/status` retourne des `active_jobs`
- Vérifiez la console du navigateur pour les erreurs
- Vérifiez que le job RQ est bien dans le registry `started`

### L'arrêt ne fonctionne pas

- Vérifiez les logs du backend : `/app/logs/linkedin_bot.log`
- Vérifiez que Redis est accessible
- Vérifiez que le worker RQ est démarré

### Le statut ne se rafraîchit pas

- Vérifiez l'intervalle de 5 secondes dans `useEffect`
- Vérifiez que l'API est accessible
- Vérifiez la console pour les erreurs réseau

## 📝 Changelog

### Version 1.0.0 (2025-12-03)

- ✅ Création de la page "Vue d'ensemble" (`/overview`)
- ✅ Ajout du bouton "Arrêter le run en cours"
- ✅ Correction du proxy Next.js pour supporter `job_id`
- ✅ Affichage du statut en temps réel
- ✅ Résumé des 7 derniers jours
- ✅ Logs récents avec bouton "Voir plus"
- ✅ Actions rapides (start, stop, toggle auto-run)
- ✅ Documentation complète

## 🤝 Contribution

Pour modifier cette page :

1. Fichier principal : `dashboard/app/(dashboard)/overview/page.tsx`
2. Sidebar : `dashboard/components/layout/Sidebar.tsx`
3. Proxy API : `dashboard/app/api/bot/action/route.ts`
4. Backend : `src/api/routes/bot_control.py`

---

**Auteur** : Claude
**Date** : 2025-12-03
**Version** : 1.0.0
