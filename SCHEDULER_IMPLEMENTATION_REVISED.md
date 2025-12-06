# Plan d'Implémentation Révisé - Scheduler d'Automatisations

## 🔄 Révisions basées sur feedback utilisateur

### **1. Birthday Bot vs Unlimited Bot**

**Constat** : Le "Unlimited Bot" n'est pas un bot séparé, c'est le Birthday Bot avec des paramètres différents :
- `process_late: true`
- `max_days_late: N` (ex: 7 jours)

**Impact sur l'architecture** :

#### Avant (incorrect)
```python
# 3 types de bots séparés
class BotType(str, Enum):
    BIRTHDAY = "birthday"
    VISITOR = "visitor"
    UNLIMITED = "unlimited"  # ❌ Redondant
```

#### Après (correct)
```python
# 2 types de bots seulement
class BotType(str, Enum):
    BIRTHDAY = "birthday"
    VISITOR = "visitor"

# Configuration du Birthday Bot
class BirthdayBotConfig(BaseModel):
    dry_run: bool = False  # Production par défaut
    process_late: bool = False  # Anniversaires en retard
    max_days_late: int = 7  # Si process_late=True
    max_messages_per_run: int = 10
```

#### UI Impact

**Dashboard Widget** :
```
┌─ Birthday Bot ─────────────────────────┐
│ ✓ Activé                                │
│ 📅 Quotidien à 08:00                    │
│ 🎂 Mode: Standard + Retards (max 7j)   │  ← Indication visuelle
│ ⏭ Prochaine: Demain 08:00              │
│ ✅ Dernière: Success (12 sent)          │
│ [▶ Run Now] [⏸ Pause] [✏ Edit]        │
└─────────────────────────────────────────┘
```

**Settings - Job Configuration** :
```
🤖 Birthday Bot Configuration
┌────────────────────────────────────────┐
│ Basic Settings                          │
│ ☑ Process late birthdays               │  ← Checkbox
│   Max days late: [7] jours             │  ← Input (si checked)
│                                         │
│ Limits                                  │
│ Messages per run: [10]                 │
│ Daily limit: [10]                      │
│ Weekly limit: [50]                     │
└────────────────────────────────────────┘
```

---

### **2. Dry-run inversé**

**Constat** : Le dry-run doit être **désactivé par défaut** (mode production), avec possibilité de l'activer.

**Impact sur l'architecture** :

#### Modèle de données
```python
class ScheduledJobConfig(BaseModel):
    # Bot configuration
    bot_config: Dict[str, Any] = Field(default_factory=dict)
    # Exemple:
    # {
    #   "dry_run": False,  # ← Production par défaut
    #   "process_late": True,
    #   "max_days_late": 7
    # }
```

#### UI Impact

**Settings - Job Form** :
```
🤖 Bot Configuration
┌────────────────────────────────────────┐
│ Execution Mode                          │
│ ☐ Enable Dry-Run Mode (Test)          │  ← Unchecked par défaut
│                                         │
│ ⚠️  Dry-run disabled: Bot will send    │  ← Warning si unchecked
│    real messages. Ensure config is     │
│    correct before enabling schedule.   │
└────────────────────────────────────────┘
```

**Dashboard Widget - Indicator** :
```
┌─ Birthday Bot ─────────────────────────┐
│ ✓ Activé                                │
│ 🚀 Production Mode                      │  ← Badge rouge si dry_run=false
│ 📅 Quotidien à 08:00                    │
│ [▶ Run Now] [⏸ Pause] [✏ Edit]        │
└─────────────────────────────────────────┘

OU si dry_run=true :

┌─ Birthday Bot ─────────────────────────┐
│ ✓ Activé                                │
│ 🧪 Test Mode (Dry-run)                 │  ← Badge orange
│ 📅 Quotidien à 08:00                    │
│ [▶ Run Now] [⏸ Pause] [✏ Edit]        │
└─────────────────────────────────────────┘
```

---

## 📋 Plan d'Implémentation Révisé

### **Phase 1 : Backend Core**

#### 1.1 Modèles de données

**Fichier** : `src/scheduler/models.py`

```python
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from uuid import uuid4

class ScheduleType(str, Enum):
    """Types de planification"""
    DAILY = "daily"
    WEEKLY = "weekly"
    INTERVAL = "interval"
    CRON = "cron"

class BotType(str, Enum):
    """Types de bots (2 seulement)"""
    BIRTHDAY = "birthday"
    VISITOR = "visitor"

class BirthdayBotConfig(BaseModel):
    """Configuration spécifique Birthday Bot"""
    dry_run: bool = False  # Production par défaut
    process_late: bool = False  # Traiter les retards
    max_days_late: int = Field(default=7, ge=1, le=365)  # Max jours retard
    max_messages_per_run: Optional[int] = Field(default=10, ge=1)

    @field_validator('max_days_late')
    @classmethod
    def validate_max_days(cls, v, info):
        """Valide max_days_late uniquement si process_late=True"""
        if not info.data.get('process_late') and v != 7:
            # Reset à default si process_late=False
            return 7
        return v

class VisitorBotConfig(BaseModel):
    """Configuration spécifique Visitor Bot"""
    dry_run: bool = False  # Production par défaut
    limit: int = Field(default=50, ge=1, le=500)  # Profils par run

class ScheduledJobConfig(BaseModel):
    """Configuration complète d'un job planifié"""

    # Identité
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    bot_type: BotType

    # Activation
    enabled: bool = True

    # Planification
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any] = Field(default_factory=dict)

    # Configuration du bot (typée selon bot_type)
    bot_config: BirthdayBotConfig | VisitorBotConfig

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # État d'exécution
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    next_run_at: Optional[datetime] = None

    # Options APScheduler
    max_instances: int = 1
    misfire_grace_time: int = 3600
    coalesce: bool = True

    @field_validator('bot_config', mode='before')
    @classmethod
    def validate_bot_config(cls, v, info):
        """Convertit dict en modèle typé selon bot_type"""
        if isinstance(v, dict):
            bot_type = info.data.get('bot_type')
            if bot_type == BotType.BIRTHDAY:
                return BirthdayBotConfig(**v)
            elif bot_type == BotType.VISITOR:
                return VisitorBotConfig(**v)
        return v

class JobExecutionLog(BaseModel):
    """Log d'exécution d'un job"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str  # running, success, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    messages_sent: int = 0
    profiles_visited: int = 0
```

#### 1.2 Scheduler Core (inchangé)

Le `AutomationScheduler` reste identique (voir `AUTOMATION_SCHEDULER_PLAN.md`).

#### 1.3 API Routes

**Fichier** : `src/api/routes/scheduler_routes.py`

```python
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel

from src.scheduler.scheduler import AutomationScheduler
from src.scheduler.models import (
    ScheduledJobConfig,
    JobExecutionLog,
    BotType,
    ScheduleType,
    BirthdayBotConfig,
    VisitorBotConfig
)

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

# DTOs
class CreateJobRequest(BaseModel):
    name: str
    description: Optional[str] = None
    bot_type: BotType
    enabled: bool = True
    schedule_type: ScheduleType
    schedule_config: dict

    # Bot config (sera validé selon bot_type)
    bot_config: dict

class UpdateJobRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    schedule_type: Optional[ScheduleType] = None
    schedule_config: Optional[dict] = None
    bot_config: Optional[dict] = None

scheduler = AutomationScheduler()

@router.get("/jobs", response_model=List[ScheduledJobConfig])
async def list_jobs(enabled_only: bool = False):
    """Liste tous les jobs planifiés"""
    return scheduler.list_jobs(enabled_only=enabled_only)

@router.post("/jobs", response_model=ScheduledJobConfig, status_code=status.HTTP_201_CREATED)
async def create_job(request: CreateJobRequest):
    """Crée un nouveau job planifié"""

    # Valider bot_config selon bot_type
    if request.bot_type == BotType.BIRTHDAY:
        bot_config = BirthdayBotConfig(**request.bot_config)
    elif request.bot_type == BotType.VISITOR:
        bot_config = VisitorBotConfig(**request.bot_config)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bot_type: {request.bot_type}"
        )

    job_config = ScheduledJobConfig(
        name=request.name,
        description=request.description,
        bot_type=request.bot_type,
        enabled=request.enabled,
        schedule_type=request.schedule_type,
        schedule_config=request.schedule_config,
        bot_config=bot_config
    )

    return scheduler.add_job(job_config)

@router.put("/jobs/{job_id}", response_model=ScheduledJobConfig)
async def update_job(job_id: str, request: UpdateJobRequest):
    """Met à jour un job existant"""
    updates = request.dict(exclude_unset=True)

    # Si bot_config est fourni, valider selon le bot_type existant
    if 'bot_config' in updates:
        existing_job = scheduler.get_job(job_id)
        if not existing_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        if existing_job.bot_type == BotType.BIRTHDAY:
            updates['bot_config'] = BirthdayBotConfig(**updates['bot_config'])
        elif existing_job.bot_type == BotType.VISITOR:
            updates['bot_config'] = VisitorBotConfig(**updates['bot_config'])

    job = scheduler.update_job(job_id, updates)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    return job

@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str):
    """Supprime un job"""
    success = scheduler.delete_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

@router.post("/jobs/{job_id}/toggle", response_model=ScheduledJobConfig)
async def toggle_job(job_id: str, enabled: bool):
    """Active/désactive un job"""
    job = scheduler.toggle_job(job_id, enabled)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    return job

@router.post("/jobs/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_job_now(job_id: str):
    """Exécute immédiatement un job"""
    success = scheduler.run_job_now(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    return {"message": f"Job {job_id} queued for immediate execution"}

@router.get("/jobs/{job_id}/history", response_model=List[JobExecutionLog])
async def get_job_history(job_id: str, limit: int = 50):
    """Récupère l'historique d'exécution d'un job"""
    return scheduler.get_job_history(job_id, limit=limit)
```

---

### **Phase 2 : Frontend - Settings Tab**

#### 2.1 Types TypeScript

**Fichier** : `dashboard/types/automation.ts`

```typescript
export type BotType = 'birthday' | 'visitor';

export type ScheduleType = 'daily' | 'weekly' | 'interval' | 'cron';

export interface BirthdayBotConfig {
  dry_run: boolean;
  process_late: boolean;
  max_days_late: number;
  max_messages_per_run?: number;
}

export interface VisitorBotConfig {
  dry_run: boolean;
  limit: number;
}

export interface ScheduleConfig {
  // Daily
  hour?: number;
  minute?: number;

  // Weekly
  day_of_week?: string; // "mon,wed,fri"

  // Interval
  hours?: number;
  minutes?: number;

  // Cron
  cron_expression?: string;
}

export interface ScheduledJob {
  id: string;
  name: string;
  description?: string;
  bot_type: BotType;
  enabled: boolean;
  schedule_type: ScheduleType;
  schedule_config: ScheduleConfig;
  bot_config: BirthdayBotConfig | VisitorBotConfig;
  created_at: string;
  updated_at: string;
  last_run_at?: string;
  last_run_status?: 'success' | 'failed' | 'running';
  last_run_error?: string;
  next_run_at?: string;
}

export interface JobExecutionLog {
  id: string;
  job_id: string;
  started_at: string;
  finished_at?: string;
  status: 'running' | 'success' | 'failed';
  result?: any;
  error?: string;
  messages_sent: number;
  profiles_visited: number;
}
```

#### 2.2 Composant SchedulerSettings

**Fichier** : `dashboard/components/automation/SchedulerSettings.tsx`

```typescript
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, RefreshCw } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { ScheduledJob } from '@/types/automation';
import JobList from './JobList';
import JobCreateDialog from './JobCreateDialog';

export function SchedulerSettings() {
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const { toast } = useToast();

  const loadJobs = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/scheduler/jobs');
      if (!response.ok) throw new Error('Failed to load jobs');
      const data = await response.json();
      setJobs(data);
    } catch (error) {
      toast({
        title: 'Erreur',
        description: 'Impossible de charger les planifications',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-200">
            Planifications Automatiques
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Configurez les horaires d'exécution des bots
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={loadJobs}
            variant="outline"
            size="sm"
            className="border-slate-700"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualiser
          </Button>
          <Button
            onClick={() => setIsCreateDialogOpen(true)}
            size="sm"
            className="bg-purple-600 hover:bg-purple-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Nouvelle planification
          </Button>
        </div>
      </div>

      {/* Job List */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Jobs planifiés</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-slate-400">
              Chargement...
            </div>
          ) : (
            <JobList jobs={jobs} onRefresh={loadJobs} />
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <JobCreateDialog
        open={isCreateDialogOpen}
        onClose={() => setIsCreateDialogOpen(false)}
        onSuccess={() => {
          setIsCreateDialogOpen(false);
          loadJobs();
        }}
      />
    </div>
  );
}
```

#### 2.3 Formulaire de création/édition

**Fichier** : `dashboard/components/automation/JobForm.tsx`

```typescript
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AlertTriangle } from 'lucide-react';
import { BotType, ScheduleType, BirthdayBotConfig, VisitorBotConfig } from '@/types/automation';

interface JobFormProps {
  onSubmit: (data: any) => void;
  initialData?: any;
  loading?: boolean;
}

export function JobForm({ onSubmit, initialData, loading }: JobFormProps) {
  const [botType, setBotType] = useState<BotType>(initialData?.bot_type || 'birthday');
  const [scheduleType, setScheduleType] = useState<ScheduleType>(initialData?.schedule_type || 'daily');

  // Birthday Bot Config
  const [dryRun, setDryRun] = useState(initialData?.bot_config?.dry_run ?? false);
  const [processLate, setProcessLate] = useState(initialData?.bot_config?.process_late ?? false);
  const [maxDaysLate, setMaxDaysLate] = useState(initialData?.bot_config?.max_days_late ?? 7);
  const [maxMessagesPerRun, setMaxMessagesPerRun] = useState(initialData?.bot_config?.max_messages_per_run ?? 10);

  // Visitor Bot Config
  const [visitorLimit, setVisitorLimit] = useState(initialData?.bot_config?.limit ?? 50);

  // Schedule Config
  const [hour, setHour] = useState(initialData?.schedule_config?.hour ?? 8);
  const [minute, setMinute] = useState(initialData?.schedule_config?.minute ?? 0);
  const [dayOfWeek, setDayOfWeek] = useState(initialData?.schedule_config?.day_of_week ?? 'mon');
  const [intervalHours, setIntervalHours] = useState(initialData?.schedule_config?.hours ?? 2);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Build schedule_config
    let schedule_config: any = {};
    if (scheduleType === 'daily') {
      schedule_config = { hour, minute };
    } else if (scheduleType === 'weekly') {
      schedule_config = { hour, minute, day_of_week: dayOfWeek };
    } else if (scheduleType === 'interval') {
      schedule_config = { hours: intervalHours, minutes: 0 };
    }

    // Build bot_config
    let bot_config: any = {};
    if (botType === 'birthday') {
      bot_config = {
        dry_run: dryRun,
        process_late: processLate,
        max_days_late: processLate ? maxDaysLate : 7,
        max_messages_per_run: maxMessagesPerRun,
      };
    } else if (botType === 'visitor') {
      bot_config = {
        dry_run: dryRun,
        limit: visitorLimit,
      };
    }

    onSubmit({
      bot_type: botType,
      schedule_type: scheduleType,
      schedule_config,
      bot_config,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">

      {/* Bot Type */}
      <div className="space-y-2">
        <Label>Type de Bot</Label>
        <Select value={botType} onValueChange={(v) => setBotType(v as BotType)}>
          <SelectTrigger className="bg-slate-800 border-slate-700">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="birthday">🎂 Birthday Bot</SelectItem>
            <SelectItem value="visitor">👥 Visitor Bot</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Schedule Type */}
      <div className="space-y-2">
        <Label>Fréquence</Label>
        <Select value={scheduleType} onValueChange={(v) => setScheduleType(v as ScheduleType)}>
          <SelectTrigger className="bg-slate-800 border-slate-700">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="daily">📅 Quotidien</SelectItem>
            <SelectItem value="weekly">📆 Hebdomadaire</SelectItem>
            <SelectItem value="interval">⏱️ Intervalle</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Schedule Config */}
      {scheduleType === 'daily' && (
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Heure</Label>
            <Input
              type="number"
              min="0"
              max="23"
              value={hour}
              onChange={(e) => setHour(Number(e.target.value))}
              className="bg-slate-800 border-slate-700"
            />
          </div>
          <div className="space-y-2">
            <Label>Minute</Label>
            <Input
              type="number"
              min="0"
              max="59"
              value={minute}
              onChange={(e) => setMinute(Number(e.target.value))}
              className="bg-slate-800 border-slate-700"
            />
          </div>
        </div>
      )}

      {scheduleType === 'weekly' && (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Jour de la semaine</Label>
            <Select value={dayOfWeek} onValueChange={setDayOfWeek}>
              <SelectTrigger className="bg-slate-800 border-slate-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="mon">Lundi</SelectItem>
                <SelectItem value="tue">Mardi</SelectItem>
                <SelectItem value="wed">Mercredi</SelectItem>
                <SelectItem value="thu">Jeudi</SelectItem>
                <SelectItem value="fri">Vendredi</SelectItem>
                <SelectItem value="sat">Samedi</SelectItem>
                <SelectItem value="sun">Dimanche</SelectItem>
                <SelectItem value="mon,wed,fri">Lun/Mer/Ven</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Heure</Label>
              <Input
                type="number"
                min="0"
                max="23"
                value={hour}
                onChange={(e) => setHour(Number(e.target.value))}
                className="bg-slate-800 border-slate-700"
              />
            </div>
            <div className="space-y-2">
              <Label>Minute</Label>
              <Input
                type="number"
                min="0"
                max="59"
                value={minute}
                onChange={(e) => setMinute(Number(e.target.value))}
                className="bg-slate-800 border-slate-700"
              />
            </div>
          </div>
        </div>
      )}

      {scheduleType === 'interval' && (
        <div className="space-y-2">
          <Label>Intervalle (heures)</Label>
          <Input
            type="number"
            min="1"
            max="24"
            value={intervalHours}
            onChange={(e) => setIntervalHours(Number(e.target.value))}
            className="bg-slate-800 border-slate-700"
          />
          <p className="text-xs text-slate-400">
            Le bot s'exécutera toutes les {intervalHours} heure(s)
          </p>
        </div>
      )}

      {/* Bot Config - Birthday */}
      {botType === 'birthday' && (
        <div className="space-y-4 p-4 rounded-lg bg-slate-800/50 border border-slate-700">
          <h4 className="font-medium text-slate-200">Configuration Birthday Bot</h4>

          {/* Dry Run */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Mode Test (Dry-Run)</Label>
              <p className="text-xs text-slate-400">
                Simulation sans envoi réel de messages
              </p>
            </div>
            <Switch
              checked={dryRun}
              onCheckedChange={setDryRun}
              className="data-[state=checked]:bg-amber-500"
            />
          </div>

          {/* Warning si Production */}
          {!dryRun && (
            <div className="flex items-start gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/30">
              <AlertTriangle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h5 className="text-sm font-semibold text-red-400">Mode Production</h5>
                <p className="text-xs text-red-200/80 mt-1">
                  Le bot enverra de vrais messages. Vérifiez la configuration.
                </p>
              </div>
            </div>
          )}

          {/* Process Late */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Traiter les anniversaires en retard</Label>
              <p className="text-xs text-slate-400">
                Envoyer des messages pour les anniversaires passés
              </p>
            </div>
            <Switch
              checked={processLate}
              onCheckedChange={setProcessLate}
            />
          </div>

          {/* Max Days Late */}
          {processLate && (
            <div className="space-y-2">
              <Label>Retard maximum (jours)</Label>
              <Input
                type="number"
                min="1"
                max="365"
                value={maxDaysLate}
                onChange={(e) => setMaxDaysLate(Number(e.target.value))}
                className="bg-slate-800 border-slate-700"
              />
              <p className="text-xs text-slate-400">
                Messages envoyés jusqu'à {maxDaysLate} jours après l'anniversaire
              </p>
            </div>
          )}

          {/* Max Messages */}
          <div className="space-y-2">
            <Label>Messages maximum par exécution</Label>
            <Input
              type="number"
              min="1"
              max="100"
              value={maxMessagesPerRun}
              onChange={(e) => setMaxMessagesPerRun(Number(e.target.value))}
              className="bg-slate-800 border-slate-700"
            />
          </div>
        </div>
      )}

      {/* Bot Config - Visitor */}
      {botType === 'visitor' && (
        <div className="space-y-4 p-4 rounded-lg bg-slate-800/50 border border-slate-700">
          <h4 className="font-medium text-slate-200">Configuration Visitor Bot</h4>

          {/* Dry Run */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Mode Test (Dry-Run)</Label>
              <p className="text-xs text-slate-400">
                Simulation sans visites réelles
              </p>
            </div>
            <Switch
              checked={dryRun}
              onCheckedChange={setDryRun}
              className="data-[state=checked]:bg-amber-500"
            />
          </div>

          {/* Limit */}
          <div className="space-y-2">
            <Label>Profils à visiter par exécution</Label>
            <Input
              type="number"
              min="1"
              max="500"
              value={visitorLimit}
              onChange={(e) => setVisitorLimit(Number(e.target.value))}
              className="bg-slate-800 border-slate-700"
            />
          </div>
        </div>
      )}

      {/* Submit */}
      <div className="flex justify-end gap-2 pt-4 border-t border-slate-700">
        <Button
          type="submit"
          disabled={loading}
          className="bg-purple-600 hover:bg-purple-700"
        >
          {loading ? 'Enregistrement...' : 'Enregistrer'}
        </Button>
      </div>
    </form>
  );
}
```

---

### **Phase 3 : Frontend - Dashboard Widget**

**Fichier** : `dashboard/components/automation/ScheduledJobsWidget.tsx`

```typescript
'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Clock, Play, Pause, Edit, Settings, Calendar } from 'lucide-react';
import Link from 'next/link';
import { ScheduledJob, BirthdayBotConfig } from '@/types/automation';
import { useToast } from '@/hooks/use-toast';
import { formatDistanceToNow } from 'date-fns';
import { fr } from 'date-fns/locale';

export function ScheduledJobsWidget() {
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [loading, setLoading] = useState<string | null>(null);
  const { toast } = useToast();

  const loadJobs = async () => {
    try {
      const response = await fetch('/api/scheduler/jobs?enabled_only=false');
      if (!response.ok) throw new Error('Failed to load jobs');
      const data = await response.json();
      setJobs(data);
    } catch (error) {
      console.error('Failed to load jobs', error);
    }
  };

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const handleToggle = async (jobId: string, enabled: boolean) => {
    setLoading(jobId);
    try {
      const response = await fetch(`/api/scheduler/jobs/${jobId}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });

      if (!response.ok) throw new Error('Failed to toggle job');

      toast({
        title: enabled ? 'Planification activée' : 'Planification en pause',
        description: enabled ? 'Le job va s\'exécuter selon le planning' : 'Le job ne s\'exécutera plus automatiquement',
      });

      loadJobs();
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Erreur',
        description: 'Impossible de modifier la planification',
      });
    } finally {
      setLoading(null);
    }
  };

  const handleRunNow = async (jobId: string) => {
    setLoading(`run-${jobId}`);
    try {
      const response = await fetch(`/api/scheduler/jobs/${jobId}/run`, {
        method: 'POST',
      });

      if (!response.ok) throw new Error('Failed to run job');

      toast({
        title: 'Exécution lancée',
        description: 'Le bot va démarrer immédiatement',
      });
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Erreur',
        description: 'Impossible de lancer le bot',
      });
    } finally {
      setLoading(null);
    }
  };

  const JobCard = ({ job }: { job: ScheduledJob }) => {
    const isBirthdayBot = job.bot_type === 'birthday';
    const botConfig = job.bot_config as BirthdayBotConfig;

    const colorClasses = {
      birthday: {
        gradient: 'from-pink-900/20 to-slate-900',
        border: 'border-pink-700/40',
        icon: job.enabled ? 'text-pink-400' : 'text-slate-400',
        badge: job.enabled ? 'bg-pink-600' : 'bg-slate-700',
      },
      visitor: {
        gradient: 'from-emerald-900/20 to-slate-900',
        border: 'border-emerald-700/40',
        icon: job.enabled ? 'text-emerald-400' : 'text-slate-400',
        badge: job.enabled ? 'bg-emerald-600' : 'bg-slate-700',
      },
    }[job.bot_type];

    const formatSchedule = () => {
      if (job.schedule_type === 'daily') {
        return `Quotidien à ${String(job.schedule_config.hour).padStart(2, '0')}:${String(job.schedule_config.minute).padStart(2, '0')}`;
      } else if (job.schedule_type === 'weekly') {
        return `${job.schedule_config.day_of_week} à ${job.schedule_config.hour}:${String(job.schedule_config.minute).padStart(2, '0')}`;
      } else if (job.schedule_type === 'interval') {
        return `Toutes les ${job.schedule_config.hours}h`;
      }
      return 'Non planifié';
    };

    return (
      <Card className={`bg-gradient-to-br ${colorClasses.gradient} ${colorClasses.border} transition-all hover:shadow-lg`}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar className={`h-4 w-4 ${colorClasses.icon}`} />
              <CardTitle className="text-sm text-slate-200">{job.name}</CardTitle>
            </div>
            <Badge className={colorClasses.badge}>
              {job.enabled ? 'Activé' : 'Désactivé'}
            </Badge>
          </div>
          {job.description && (
            <CardDescription className="text-xs mt-1">{job.description}</CardDescription>
          )}
        </CardHeader>

        <CardContent className="space-y-3">
          {/* Schedule Info */}
          <div className="text-xs space-y-1">
            <div className="flex items-center gap-2 text-slate-300">
              <Clock className="h-3 w-3" />
              {formatSchedule()}
            </div>

            {/* Birthday Bot specific info */}
            {isBirthdayBot && botConfig.process_late && (
              <div className="text-slate-400">
                + Retards (max {botConfig.max_days_late}j)
              </div>
            )}

            {/* Dry-run indicator */}
            {job.bot_config.dry_run ? (
              <Badge variant="outline" className="text-xs border-amber-500/50 text-amber-400">
                🧪 Test Mode
              </Badge>
            ) : (
              <Badge variant="outline" className="text-xs border-red-500/50 text-red-400">
                🚀 Production
              </Badge>
            )}
          </div>

          {/* Next/Last Run */}
          <div className="text-xs text-slate-400 space-y-1">
            {job.next_run_at && job.enabled && (
              <div>⏭ Prochaine: {formatDistanceToNow(new Date(job.next_run_at), { addSuffix: true, locale: fr })}</div>
            )}
            {job.last_run_at && (
              <div>
                {job.last_run_status === 'success' ? '✅' : '❌'} Dernière:{' '}
                {formatDistanceToNow(new Date(job.last_run_at), { addSuffix: true, locale: fr })}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleRunNow(job.id)}
              disabled={loading === `run-${job.id}`}
              className="flex-1 border-slate-700 text-xs"
            >
              <Play className="h-3 w-3 mr-1" />
              Run Now
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleToggle(job.id, !job.enabled)}
              disabled={loading === job.id}
              className="flex-1 border-slate-700 text-xs"
            >
              {job.enabled ? (
                <>
                  <Pause className="h-3 w-3 mr-1" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="h-3 w-3 mr-1" />
                  Enable
                </>
              )}
            </Button>
            <Link href={`/settings?tab=automation&job=${job.id}`}>
              <Button
                size="sm"
                variant="outline"
                className="border-slate-700 text-xs"
              >
                <Edit className="h-3 w-3" />
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  };

  if (jobs.length === 0) {
    return (
      <Card className="w-full bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-200">
            <Clock className="h-5 w-5 text-purple-500" />
            Planifications Automatiques
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Calendar className="h-12 w-12 mx-auto text-slate-600 mb-4" />
            <p className="text-slate-400 mb-4">Aucune planification configurée</p>
            <Link href="/settings?tab=automation">
              <Button className="bg-purple-600 hover:bg-purple-700">
                <Settings className="h-4 w-4 mr-2" />
                Configurer les planifications
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full bg-slate-900 border-slate-800">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <Clock className="h-5 w-5 text-purple-500" />
              Planifications Automatiques
            </CardTitle>
            <CardDescription className="mt-1">
              Vue d'ensemble des automatisations planifiées
            </CardDescription>
          </div>
          <Link href="/settings?tab=automation">
            <Button variant="outline" size="sm" className="border-slate-700">
              <Settings className="h-4 w-4 mr-2" />
              Configurer
            </Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
```

---

### **Phase 4 : Intégration**

#### 4.1 Settings Page

**Fichier** : `dashboard/app/settings/page.tsx`

```diff
+ import { SchedulerSettings } from "@/components/automation/SchedulerSettings"

  <Tabs value={activeTab} onValueChange={setActiveTab}>
    <TabsList>
      <TabsTrigger value="global">Global</TabsTrigger>
      <TabsTrigger value="birthday">Birthday Bot</TabsTrigger>
      <TabsTrigger value="visitor">Visitor Bot</TabsTrigger>
+     <TabsTrigger value="automation">Automation</TabsTrigger>
      <TabsTrigger value="advanced">Advanced</TabsTrigger>
    </TabsList>

    <TabsContent value="global">...</TabsContent>
    <TabsContent value="birthday">...</TabsContent>
    <TabsContent value="visitor">...</TabsContent>
+   <TabsContent value="automation">
+     <SchedulerSettings />
+   </TabsContent>
    <TabsContent value="advanced">...</TabsContent>
  </Tabs>
```

#### 4.2 Dashboard Page

**Fichier** : `dashboard/app/(dashboard)/page.tsx`

```diff
+ import { ScheduledJobsWidget } from "@/components/automation/ScheduledJobsWidget"

  <SystemStatusHero />
  <AutomationServicesControl />
+ <ScheduledJobsWidget />
  <WorkerManagementPanel />
```

---

## ✅ Résumé des changements

### Modèle de données
- ✅ 2 types de bots seulement (Birthday, Visitor)
- ✅ Birthday Bot avec option `process_late` et `max_days_late`
- ✅ `dry_run: false` par défaut (production mode)

### UI/UX
- ✅ Widget Dashboard affiche mode "Standard" ou "Standard + Retards"
- ✅ Badge Production/Test visible
- ✅ Warning si dry-run désactivé
- ✅ Settings avec switch "Process late birthdays"

### Cohérence
- ✅ Pas de confusion Birthday vs Unlimited
- ✅ Configuration claire et explicite
- ✅ Warnings appropriés en mode production

---

**Validation** : Ce plan révisé correspond-il à vos attentes ?
