# Proposition UX/UI : Intégration du Scheduler d'Automatisations

## 🎯 Objectif

Intégrer la planification des automatisations **sans complexifier le Dashboard**, en restant cohérent avec l'architecture UI/UX existante.

---

## 📊 Analyse de l'existant

### Architecture actuelle du Dashboard

```
/dashboard (Page principale)
├── SystemStatusHero (Hero section)
├── AutomationServicesControl (Services systemd/RQ - Full width)
├── WorkerManagementPanel (Gestion workers - Full width)
├── Grid Layout (8/12 + 4/12)
    ├── BotControlPanel (Contrôles manuels des bots)
    ├── KPICards
    ├── WeeklyLimitWidget
    ├── ActivityMonitor
    ├── TopContactsWidget
    └── RecentErrorsWidget
```

### Points clés observés

1. **BotControlPanel** : Permet de lancer manuellement 3 bots (Birthday, Unlimited, Visitor)
2. **AutomationServicesControl** : Gère les services systemd mais PAS la planification
3. **Settings** : Système d'onglets (Global, Birthday, Visitor, Advanced YAML, Messages)
4. **Design** : Cards avec gradients, dark theme, badges colorés

---

## ✨ Proposition : Approche Hybride

### **1. Dashboard : Widget Compact "Scheduled Jobs"**

Ajouter un **nouveau composant léger** entre `AutomationServicesControl` et `WorkerManagementPanel`.

#### Emplacement dans le Dashboard

```diff
  /dashboard/app/(dashboard)/page.tsx

  <SystemStatusHero />
  <AutomationServicesControl />
+ <ScheduledJobsWidget />
  <WorkerManagementPanel />
```

#### Design du Widget

```
┌─────────────────────────────────────────────────────────────────┐
│ 🕐 Planifications Automatiques                   [⚙ Configure]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ Birthday Bot ─────────────────┐  ┌─ Visitor Bot ───────┐   │
│  │ ✓ Activé                        │  │ □ Désactivé         │   │
│  │ 📅 Quotidien à 08:00            │  │ 📅 Lun/Mer à 14:00  │   │
│  │ ⏭ Prochaine exécution: Demain  │  │ ⏭ -                 │   │
│  │ ✅ Dernière: Success (2h ago)   │  │ ⏸ Dernière: -       │   │
│  │                                  │  │                     │   │
│  │ [▶ Run Now] [⏸ Pause] [✏ Edit] │  │ [▶ Enable] [✏ Edit] │   │
│  └──────────────────────────────────┘  └─────────────────────┘   │
│                                                                  │
│  ┌─ Unlimited Bot ─────────────────┐                            │
│  │ ✓ Activé                        │  [+ Ajouter nouveau job]   │
│  │ 📅 Toutes les 2h (08:00-19:00) │                            │
│  │ ⏭ Prochaine: Dans 45 min       │                            │
│  │ ✅ Dernière: Success (1h ago)   │                            │
│  │                                  │                            │
│  │ [▶ Run Now] [⏸ Pause] [✏ Edit] │                            │
│  └──────────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

#### Caractéristiques du Widget

- **Vue compacte** : Affiche uniquement les jobs configurés (max 4 cards en grid)
- **Actions rapides** :
  - `▶ Run Now` : Exécution immédiate (comme BotControlPanel)
  - `⏸ Pause` : Désactive temporairement le job
  - `✏ Edit` : Ouvre le modal d'édition rapide ou redirige vers Settings
- **Indicateurs visuels** :
  - Badge "Activé/Désactivé"
  - Prochaine exécution (relative time)
  - Statut dernière exécution (Success/Failed avec timestamp)
- **Bouton "Configure"** : Redirige vers `/settings?tab=automation`

#### Avantages

- ✅ **Intégration naturelle** : Même style que `AutomationServicesControl`
- ✅ **Pas de navigation supplémentaire** : Tout visible depuis le Dashboard
- ✅ **Contrôle rapide** : Pause/Resume/Run sans quitter la page
- ✅ **Simplicité** : Affiche seulement l'essentiel

---

### **2. Settings : Nouvel onglet "Automation"**

Ajouter un **6ème onglet** dans `/settings` pour la configuration avancée.

#### Emplacement dans Settings

```diff
  /dashboard/app/settings/page.tsx

  <Tabs>
    <TabsList>
      <TabsTrigger value="global">Global</TabsTrigger>
      <TabsTrigger value="birthday">Birthday Bot</TabsTrigger>
      <TabsTrigger value="visitor">Visitor Bot</TabsTrigger>
+     <TabsTrigger value="automation">Automation</TabsTrigger>
      <TabsTrigger value="advanced">Advanced</TabsTrigger>
    </TabsList>
```

#### Design de l'onglet Automation

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚙ Settings > Automation                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📋 Scheduled Jobs                           [+ New Schedule]   │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  ┌─ Job #1: Birthday Bot - Daily ──────────────────────────┐    │
│  │ Status: ✓ Enabled           Created: 2025-01-15        │    │
│  │ Bot Type: Birthday          Last Run: 2h ago (Success)  │    │
│  │                                                          │    │
│  │ ⏰ Schedule Configuration                                │    │
│  │ ┌──────────────────────────────────────────────────┐    │    │
│  │ │ Type: [Daily ▼]                                  │    │    │
│  │ │ Time: [08]:[00]                                  │    │    │
│  │ │ Timezone: Europe/Paris                           │    │    │
│  │ └──────────────────────────────────────────────────┘    │    │
│  │                                                          │    │
│  │ 🤖 Bot Configuration                                     │    │
│  │ ┌──────────────────────────────────────────────────┐    │    │
│  │ │ [x] Dry Run                                      │    │    │
│  │ │ [x] Process Late (max 7 days)                    │    │    │
│  │ │ Max messages per run: [10]                       │    │    │
│  │ └──────────────────────────────────────────────────┘    │    │
│  │                                                          │    │
│  │ [Save Changes]  [Delete Job]  [View History]            │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ Job #2: Visitor Bot - Weekly ───────────────────────────┐   │
│  │ Status: □ Disabled          Created: 2025-01-10         │   │
│  │ ... (collapsed)                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  📊 Execution History (Last 50 runs)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Date/Time         │ Job           │ Status  │ Details    │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ 2025-01-15 08:00 │ Birthday Bot  │ Success │ 12 sent    │   │
│  │ 2025-01-14 08:00 │ Birthday Bot  │ Success │ 8 sent     │   │
│  │ 2025-01-13 14:00 │ Visitor Bot   │ Failed  │ Error: ... │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### Sections de l'onglet

1. **Liste des jobs** (Accordion/Collapsible)
   - Chaque job est éditable in-place
   - Configuration complète (schedule + bot params)
   - Boutons : Save, Delete, View History

2. **Création de job** (Modal ou section dépliable)
   - Wizard en 3 étapes :
     1. Choix du bot type (Birthday/Visitor/Unlimited)
     2. Configuration du schedule (Daily/Weekly/Interval/Cron)
     3. Paramètres du bot (dry-run, limits, etc.)

3. **Historique global** (Table)
   - 50 dernières exécutions
   - Filtres par job, status, date
   - Export CSV

#### Avantages

- ✅ **Cohérent** : Suit le pattern existant (onglets dans Settings)
- ✅ **Découplé** : Configuration avancée séparée du Dashboard
- ✅ **Complet** : Tous les paramètres disponibles
- ✅ **Historique** : Vue consolidée des exécutions

---

### **3. Composants partagés**

Pour éviter la duplication, créer des composants réutilisables :

#### Structure des fichiers

```
dashboard/components/automation/
├── ScheduledJobsWidget.tsx      (Widget Dashboard - Vue compacte)
├── SchedulerSettings.tsx         (Settings Tab - Vue complète)
├── JobCard.tsx                   (Card individuelle job)
├── JobForm.tsx                   (Formulaire création/édition)
├── ScheduleEditor.tsx            (Éditeur de planification)
├── JobHistoryTable.tsx           (Table historique)
└── QuickActions.tsx              (Boutons Run/Pause/Edit)
```

#### Réutilisation

- `JobCard.tsx` utilisé à la fois dans Widget ET Settings
- `ScheduleEditor.tsx` partagé (UI différente mais logique identique)
- `QuickActions.tsx` pour boutons cohérents

---

## 🎨 Cohérence visuelle

### Palette de couleurs (existante)

```typescript
const scheduleColors = {
  birthday: {
    gradient: 'from-pink-900/20 to-slate-900',
    border: 'border-pink-700/40',
    icon: 'text-pink-400',
    button: 'bg-pink-600 hover:bg-pink-700'
  },
  unlimited: {
    gradient: 'from-indigo-900/20 to-slate-900',
    border: 'border-indigo-700/40',
    icon: 'text-indigo-400',
    button: 'bg-indigo-600 hover:bg-indigo-700'
  },
  visitor: {
    gradient: 'from-emerald-900/20 to-slate-900',
    border: 'border-emerald-700/40',
    icon: 'text-emerald-400',
    button: 'bg-emerald-600 hover:bg-emerald-700'
  },
  // Nouveau : pour le scheduler lui-même
  scheduler: {
    gradient: 'from-purple-900/20 to-slate-900',
    border: 'border-purple-700/40',
    icon: 'text-purple-400',
    button: 'bg-purple-600 hover:bg-purple-700'
  }
}
```

### Icônes (Lucide React)

```typescript
import {
  Clock,        // Scheduler général
  Calendar,     // Planification quotidienne/hebdomadaire
  Timer,        // Intervalle
  PlayCircle,   // Run Now
  PauseCircle,  // Pause job
  Edit,         // Éditer
  Trash2,       // Supprimer
  CheckCircle,  // Success
  XCircle,      // Failed
  AlertCircle,  // Warning
} from "lucide-react"
```

---

## 📱 Responsive Design

### Dashboard Widget

- **Desktop** : Grid 3 colonnes (Birthday | Unlimited | Visitor)
- **Tablet** : Grid 2 colonnes
- **Mobile** : 1 colonne, carousels ou stack

### Settings Tab

- **Desktop** : Jobs en accordion, historique en table
- **Tablet** : Même layout, scrollable
- **Mobile** : Cards empilées, historique en liste

---

## 🔄 Flux utilisateur

### Scénario 1 : Créer une planification rapide

```
Dashboard > ScheduledJobsWidget > [+ Ajouter nouveau job]
  ↓
Modal : Quick Setup
  1. Select Bot Type: [Birthday ▼]
  2. Schedule: Daily at [08:00]
  3. [Create]
  ↓
Job créé et affiché dans le Widget
```

### Scénario 2 : Configuration avancée

```
Dashboard > ScheduledJobsWidget > [⚙ Configure]
  ↓
Settings > Automation Tab
  ↓
Job List > [+ New Schedule]
  ↓
Wizard complet (3 étapes)
  ↓
Job créé et visible Dashboard + Settings
```

### Scénario 3 : Pause temporaire

```
Dashboard > ScheduledJobsWidget > Job Card > [⏸ Pause]
  ↓
Confirmation : "Pause Birthday Bot schedule?"
  ↓
Job désactivé (badge "Disabled", next run = "-")
```

### Scénario 4 : Exécution manuelle

```
Dashboard > ScheduledJobsWidget > Job Card > [▶ Run Now]
  ↓
Toast : "Birthday Bot queued for execution"
  ↓
BotControlPanel affiche le job en cours
  ↓
Après exécution : Last Run updated dans ScheduledJobsWidget
```

---

## 🚀 Plan d'implémentation simplifié

### Phase 1 : Backend (inchangé)

- APScheduler + SQLite
- API `/scheduler/*` endpoints
- Intégration RQ queue

### Phase 2 : Settings Tab (prioritaire)

1. Créer `/dashboard/components/automation/SchedulerSettings.tsx`
2. Ajouter onglet "Automation" dans `/settings/page.tsx`
3. Implémenter CRUD complet (Create, Read, Update, Delete jobs)
4. Historique d'exécution

### Phase 3 : Dashboard Widget (simplifié)

1. Créer `/dashboard/components/automation/ScheduledJobsWidget.tsx`
2. Afficher uniquement jobs actifs (enabled)
3. Actions rapides : Run Now, Pause, Edit (→ redirige vers Settings)
4. Intégrer dans `/dashboard/app/(dashboard)/page.tsx`

### Phase 4 : Composants partagés

1. Extraire `JobCard.tsx` (réutilisé Widget + Settings)
2. `ScheduleEditor.tsx` (dropdown Daily/Weekly/Interval/Cron)
3. `JobHistoryTable.tsx` (table avec filters)

### Phase 5 : Polish

1. Animations (transitions, hover effects)
2. Toast notifications
3. Confirmations (delete, pause)
4. Loading states
5. Error handling

---

## ✅ Checklist de cohérence

- [x] Utilise les composants UI existants (Card, Button, Badge, Tabs)
- [x] Suit la palette de couleurs actuelle
- [x] Intègre les icônes Lucide React cohérentes
- [x] Respecte le dark theme (slate-900, gradients)
- [x] Pas de nouvelle page séparée (Widget + Settings Tab)
- [x] Actions rapides depuis Dashboard
- [x] Configuration avancée dans Settings
- [x] Responsive (mobile, tablet, desktop)
- [x] Accessibilité (labels, ARIA)
- [x] Performance (polling optimisé, pas de re-renders inutiles)

---

## 📊 Comparaison : Avant / Après

### Avant

```
Dashboard:
  - BotControlPanel : Lancement MANUEL uniquement
  - AutomationServicesControl : Services systemd (pas de planification)

Settings:
  - Configuration statique (limits, delays, etc.)
  - Aucune planification
```

### Après

```
Dashboard:
  - BotControlPanel : Lancement MANUEL (inchangé)
  - ScheduledJobsWidget : Vue compacte des planifications
    → Actions rapides : Run Now, Pause, Edit
  - AutomationServicesControl : Services systemd (inchangé)

Settings:
  - Automation Tab : Configuration complète des schedules
    → CRUD jobs, historique, wizard
  - Configuration statique (inchangée)
```

---

## 🎯 Résultat final

### Dashboard simple et puissant

- **Monitoring** : Voit d'un coup d'œil les jobs planifiés
- **Contrôle rapide** : Pause/Resume/Run sans navigation
- **Pas de complexité** : Widget compact (3-4 cards max)

### Settings exhaustifs

- **Configuration avancée** : Tous les paramètres disponibles
- **Historique** : Traçabilité complète
- **Wizards** : Création guidée

### Cohérence totale

- **Même style** : Cards, gradients, badges
- **Même UX** : Tabs, modals, toasts
- **Même pattern** : Composants réutilisés

---

## ❓ Questions ouvertes

1. **Modal vs Redirect** : Pour "Edit" depuis le Widget, ouvrir un modal ou rediriger vers Settings ?
   - **Recommandation** : Modal pour éditions rapides (toggle dry-run, change time), redirect pour modifications complexes

2. **Jobs par défaut** : Créer automatiquement 3 jobs (Birthday, Unlimited, Visitor) désactivés au premier lancement ?
   - **Recommandation** : Oui, pré-configurés mais disabled, avec bouton "Quick Enable"

3. **Limite de jobs** : Autoriser plusieurs schedules pour le même bot type ?
   - **Recommandation** : Non au début (1 job par bot type), mais architecturer pour l'évolution

4. **Dry-run dans schedule** : Le scheduler utilise le dry-run du job ou celui du BotControlPanel ?
   - **Recommandation** : Chaque job a son propre dry-run (indépendant)

---

## 🔗 Liens vers implémentation

- **Backend** : Voir `AUTOMATION_SCHEDULER_PLAN.md`
- **Frontend Widget** : À créer dans `/dashboard/components/automation/ScheduledJobsWidget.tsx`
- **Frontend Settings** : À créer dans `/dashboard/components/automation/SchedulerSettings.tsx`
- **API Routes** : À créer dans `/dashboard/app/api/scheduler/[...path]/route.ts`

---

## ✨ Points forts de cette approche

1. **Non-invasif** : N'altère pas l'existant, ajoute seulement 1 widget + 1 onglet
2. **Progressif** : Peut être implémenté phase par phase
3. **Cohérent** : Réutilise 100% du design system actuel
4. **Flexible** : Facile d'ajouter des features (notifications, webhooks, etc.)
5. **Performant** : Polling optimisé, pas de surcharge
6. **Accessible** : Contrôle rapide (Dashboard) + avancé (Settings)

---

**Validation requise** : Cette proposition vous convient-elle avant de commencer l'implémentation ?
