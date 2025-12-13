# Plan d'Implémentation - Scheduler d'Automatisations

## Vue d'ensemble

Ce document détaille le plan d'implémentation pour ajouter une interface de planification des automatisations dans le Dashboard LinkedIn Birthday Bot.

## Architecture proposée

### Option retenue : **Scheduler Intégré avec APScheduler**

#### Pourquoi APScheduler ?
- ✅ Pure Python, pas de dépendance externe (Redis, Celery Beat)
- ✅ Support de multiples JobStores (SQLite, Redis, MongoDB)
- ✅ Triggers flexibles (cron, interval, date)
- ✅ Persistent entre redémarrages
- ✅ Léger et performant
- ✅ Intégration facile avec FastAPI

---

## Phase 1 : Backend Scheduler Core

### 1.1 Installation des dépendances

**Fichier :** `requirements.txt`

```diff
+ apscheduler==3.10.4
+ pytz==2024.1
```

### 1.2 Modèle de données

**Fichier :** `src/scheduler/models.py`

```python
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import uuid4

class ScheduleType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    INTERVAL = "interval"
    CRON = "cron"
    MANUAL = "manual"

class BotType(str, Enum):
    BIRTHDAY = "birthday"
    VISITOR = "visitor"

class ScheduledJobConfig(BaseModel):
    """Configuration pour un job planifié"""

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
    # Exemples de schedule_config:
    # Daily: {"hour": 8, "minute": 0}
    # Weekly: {"day_of_week": "mon,wed,fri", "hour": 14, "minute": 30}
    # Interval: {"hours": 2, "minutes": 0}
    # Cron: {"cron_expression": "0 8-18 * * 1-5"}

    # Configuration du bot
    bot_config: Dict[str, Any] = Field(default_factory=dict)
    # Exemples:
    # Birthday: {"dry_run": false, "max_days_late": 7, "process_late": true}
    # Visitor: {"dry_run": false, "limit": 50}

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "system"

    # État d'exécution
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None  # success, failed, running
    last_run_error: Optional[str] = None
    next_run_at: Optional[datetime] = None

    # Options avancées
    max_instances: int = 1  # Pas de jobs concurrents
    misfire_grace_time: int = 3600  # 1h de tolérance
    coalesce: bool = True  # Fusionner les exécutions manquées

class JobExecutionLog(BaseModel):
    """Log d'exécution d'un job"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str  # running, success, failed, cancelled
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    messages_sent: int = 0
    profiles_visited: int = 0
```

### 1.3 Scheduler Core

**Fichier :** `src/scheduler/scheduler.py`

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
import logging
from typing import Optional, List
from datetime import datetime
import pytz

from src.scheduler.models import ScheduledJobConfig, JobExecutionLog, ScheduleType, BotType
from src.scheduler.job_store import JobConfigStore, JobExecutionStore
from src.queue.queue_manager import QueueManager

logger = logging.getLogger(__name__)

class AutomationScheduler:
    """Gestionnaire de planification des automatisations"""

    _instance: Optional['AutomationScheduler'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True

        # Job stores
        self.job_config_store = JobConfigStore()
        self.execution_store = JobExecutionStore()

        # Queue manager pour exécution
        self.queue_manager = QueueManager()

        # APScheduler configuration
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///data/scheduler.db')
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=3)
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 3600
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.timezone('Europe/Paris')
        )

        # Event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )

    def start(self):
        """Démarre le scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Automation scheduler started")

            # Recharger les jobs depuis la DB
            self._reload_jobs()

    def shutdown(self):
        """Arrête le scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Automation scheduler stopped")

    def _reload_jobs(self):
        """Recharge tous les jobs actifs depuis la DB"""
        jobs = self.job_config_store.list_all()
        for job_config in jobs:
            if job_config.enabled:
                self._schedule_job(job_config)

    def add_job(self, job_config: ScheduledJobConfig) -> ScheduledJobConfig:
        """Ajoute un nouveau job planifié"""
        # Sauvegarder en DB
        saved_config = self.job_config_store.create(job_config)

        # Planifier si activé
        if saved_config.enabled:
            self._schedule_job(saved_config)

        logger.info(f"Job created: {saved_config.name} ({saved_config.id})")
        return saved_config

    def update_job(self, job_id: str, updates: dict) -> Optional[ScheduledJobConfig]:
        """Met à jour un job existant"""
        # Mettre à jour en DB
        updated_config = self.job_config_store.update(job_id, updates)

        if not updated_config:
            return None

        # Resynchroniser avec APScheduler
        self.scheduler.remove_job(job_id, jobstore='default')

        if updated_config.enabled:
            self._schedule_job(updated_config)

        logger.info(f"Job updated: {updated_config.name} ({job_id})")
        return updated_config

    def delete_job(self, job_id: str) -> bool:
        """Supprime un job"""
        # Retirer d'APScheduler
        try:
            self.scheduler.remove_job(job_id, jobstore='default')
        except Exception:
            pass

        # Supprimer de la DB
        success = self.job_config_store.delete(job_id)

        if success:
            logger.info(f"Job deleted: {job_id}")

        return success

    def toggle_job(self, job_id: str, enabled: bool) -> Optional[ScheduledJobConfig]:
        """Active/désactive un job"""
        return self.update_job(job_id, {"enabled": enabled})

    def run_job_now(self, job_id: str) -> bool:
        """Exécute immédiatement un job (hors planification)"""
        job_config = self.job_config_store.get(job_id)

        if not job_config:
            logger.error(f"Job not found: {job_id}")
            return False

        # Exécuter directement
        self._execute_job(job_config)
        return True

    def get_job(self, job_id: str) -> Optional[ScheduledJobConfig]:
        """Récupère un job par ID"""
        return self.job_config_store.get(job_id)

    def list_jobs(self, enabled_only: bool = False) -> List[ScheduledJobConfig]:
        """Liste tous les jobs"""
        jobs = self.job_config_store.list_all()

        if enabled_only:
            jobs = [j for j in jobs if j.enabled]

        return jobs

    def get_job_history(self, job_id: str, limit: int = 50) -> List[JobExecutionLog]:
        """Récupère l'historique d'exécution d'un job"""
        return self.execution_store.get_by_job(job_id, limit=limit)

    def _schedule_job(self, job_config: ScheduledJobConfig):
        """Planifie un job dans APScheduler"""
        trigger = self._create_trigger(job_config)

        if not trigger:
            logger.error(f"Cannot create trigger for job {job_config.id}")
            return

        self.scheduler.add_job(
            func=self._execute_job,
            trigger=trigger,
            args=[job_config],
            id=job_config.id,
            name=job_config.name,
            replace_existing=True,
            max_instances=job_config.max_instances,
            misfire_grace_time=job_config.misfire_grace_time,
            coalesce=job_config.coalesce
        )

        # Mettre à jour next_run
        job = self.scheduler.get_job(job_config.id)
        if job:
            self.job_config_store.update(
                job_config.id,
                {"next_run_at": job.next_run_time}
            )

    def _create_trigger(self, job_config: ScheduledJobConfig):
        """Crée un trigger APScheduler depuis la config"""
        schedule_type = job_config.schedule_type
        config = job_config.schedule_config

        if schedule_type == ScheduleType.DAILY:
            return CronTrigger(
                hour=config.get('hour', 8),
                minute=config.get('minute', 0),
                timezone='Europe/Paris'
            )

        elif schedule_type == ScheduleType.WEEKLY:
            return CronTrigger(
                day_of_week=config.get('day_of_week', 'mon'),
                hour=config.get('hour', 8),
                minute=config.get('minute', 0),
                timezone='Europe/Paris'
            )

        elif schedule_type == ScheduleType.INTERVAL:
            return IntervalTrigger(
                hours=config.get('hours', 1),
                minutes=config.get('minutes', 0),
                timezone='Europe/Paris'
            )

        elif schedule_type == ScheduleType.CRON:
            cron_expr = config.get('cron_expression')
            if cron_expr:
                return CronTrigger.from_crontab(cron_expr, timezone='Europe/Paris')

        return None

    def _execute_job(self, job_config: ScheduledJobConfig):
        """Exécute un job (envoie au RQ)"""
        logger.info(f"Executing job: {job_config.name} ({job_config.id})")

        # Créer log d'exécution
        execution_log = JobExecutionLog(
            job_id=job_config.id,
            started_at=datetime.utcnow(),
            status="running"
        )
        execution_log = self.execution_store.create(execution_log)

        # Mettre à jour le job
        self.job_config_store.update(
            job_config.id,
            {
                "last_run_at": datetime.utcnow(),
                "last_run_status": "running"
            }
        )

        try:
            # Envoyer au RQ
            if job_config.bot_type == BotType.BIRTHDAY:
                job = self.queue_manager.enqueue_bot_run(
                    bot_mode=job_config.bot_config.get('bot_mode', 'standard'),
                    dry_run=job_config.bot_config.get('dry_run', False),
                    max_days_late=job_config.bot_config.get('max_days_late', 0)
                )

            elif job_config.bot_type == BotType.VISITOR:
                job = self.queue_manager.enqueue_profile_visit(
                    dry_run=job_config.bot_config.get('dry_run', False),
                    limit=job_config.bot_config.get('limit', 50)
                )

            # Job enqueued successfully
            self.execution_store.update(
                execution_log.id,
                {
                    "status": "queued",
                    "result": {"rq_job_id": job.id if job else None}
                }
            )

            logger.info(f"Job enqueued: {job_config.name}")

        except Exception as e:
            logger.error(f"Job execution failed: {job_config.name}", exc_info=True)

            # Marquer comme échoué
            self.execution_store.update(
                execution_log.id,
                {
                    "status": "failed",
                    "finished_at": datetime.utcnow(),
                    "error": str(e)
                }
            )

            self.job_config_store.update(
                job_config.id,
                {
                    "last_run_status": "failed",
                    "last_run_error": str(e)
                }
            )

    def _job_executed_listener(self, event):
        """Listener pour les événements de jobs"""
        logger.info(f"Job event: {event}")

        # Mettre à jour next_run_at
        if event.job_id:
            job = self.scheduler.get_job(event.job_id)
            if job:
                self.job_config_store.update(
                    event.job_id,
                    {"next_run_at": job.next_run_time}
                )
```

### 1.4 Job Store (Persistance)

**Fichier :** `src/scheduler/job_store.py`

```python
from typing import List, Optional
from datetime import datetime
import sqlite3
import json
from pathlib import Path

from src.scheduler.models import ScheduledJobConfig, JobExecutionLog

class JobConfigStore:
    """Store pour les configurations de jobs"""

    def __init__(self, db_path: str = "data/scheduler_config.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialise la base de données"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    bot_type TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    schedule_type TEXT NOT NULL,
                    schedule_config TEXT NOT NULL,
                    bot_config TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    last_run_at TEXT,
                    last_run_status TEXT,
                    last_run_error TEXT,
                    next_run_at TEXT,
                    max_instances INTEGER DEFAULT 1,
                    misfire_grace_time INTEGER DEFAULT 3600,
                    coalesce INTEGER DEFAULT 1
                )
            """)
            conn.commit()

    def create(self, job_config: ScheduledJobConfig) -> ScheduledJobConfig:
        """Crée un nouveau job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO scheduled_jobs VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                job_config.id,
                job_config.name,
                job_config.description,
                job_config.bot_type.value,
                int(job_config.enabled),
                job_config.schedule_type.value,
                json.dumps(job_config.schedule_config),
                json.dumps(job_config.bot_config),
                job_config.created_at.isoformat(),
                job_config.updated_at.isoformat(),
                job_config.created_by,
                job_config.last_run_at.isoformat() if job_config.last_run_at else None,
                job_config.last_run_status,
                job_config.last_run_error,
                job_config.next_run_at.isoformat() if job_config.next_run_at else None,
                job_config.max_instances,
                job_config.misfire_grace_time,
                int(job_config.coalesce)
            ))
            conn.commit()

        return job_config

    def get(self, job_id: str) -> Optional[ScheduledJobConfig]:
        """Récupère un job par ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM scheduled_jobs WHERE id = ?",
                (job_id,)
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_model(row)

    def list_all(self) -> List[ScheduledJobConfig]:
        """Liste tous les jobs"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM scheduled_jobs ORDER BY created_at DESC")
            rows = cursor.fetchall()

        return [self._row_to_model(row) for row in rows]

    def update(self, job_id: str, updates: dict) -> Optional[ScheduledJobConfig]:
        """Met à jour un job"""
        updates['updated_at'] = datetime.utcnow().isoformat()

        # Convertir en colonnes SQL
        set_clauses = []
        values = []

        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")

            if isinstance(value, dict):
                values.append(json.dumps(value))
            elif isinstance(value, bool):
                values.append(int(value))
            elif isinstance(value, datetime):
                values.append(value.isoformat())
            else:
                values.append(value)

        values.append(job_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE scheduled_jobs SET {', '.join(set_clauses)} WHERE id = ?",
                values
            )
            conn.commit()

        return self.get(job_id)

    def delete(self, job_id: str) -> bool:
        """Supprime un job"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))
            conn.commit()

        return cursor.rowcount > 0

    def _row_to_model(self, row: sqlite3.Row) -> ScheduledJobConfig:
        """Convertit une ligne SQL en modèle"""
        return ScheduledJobConfig(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            bot_type=row['bot_type'],
            enabled=bool(row['enabled']),
            schedule_type=row['schedule_type'],
            schedule_config=json.loads(row['schedule_config']),
            bot_config=json.loads(row['bot_config']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            created_by=row['created_by'],
            last_run_at=datetime.fromisoformat(row['last_run_at']) if row['last_run_at'] else None,
            last_run_status=row['last_run_status'],
            last_run_error=row['last_run_error'],
            next_run_at=datetime.fromisoformat(row['next_run_at']) if row['next_run_at'] else None,
            max_instances=row['max_instances'],
            misfire_grace_time=row['misfire_grace_time'],
            coalesce=bool(row['coalesce'])
        )


class JobExecutionStore:
    """Store pour les logs d'exécution"""

    def __init__(self, db_path: str = "data/scheduler_config.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialise la table des exécutions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_executions (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    messages_sent INTEGER DEFAULT 0,
                    profiles_visited INTEGER DEFAULT 0,
                    FOREIGN KEY (job_id) REFERENCES scheduled_jobs(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_job_id
                ON job_executions(job_id)
            """)
            conn.commit()

    def create(self, execution: JobExecutionLog) -> JobExecutionLog:
        """Enregistre une nouvelle exécution"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO job_executions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution.id,
                execution.job_id,
                execution.started_at.isoformat(),
                execution.finished_at.isoformat() if execution.finished_at else None,
                execution.status,
                json.dumps(execution.result) if execution.result else None,
                execution.error,
                execution.messages_sent,
                execution.profiles_visited
            ))
            conn.commit()

        return execution

    def update(self, execution_id: str, updates: dict) -> Optional[JobExecutionLog]:
        """Met à jour une exécution"""
        set_clauses = []
        values = []

        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")

            if isinstance(value, dict):
                values.append(json.dumps(value))
            elif isinstance(value, datetime):
                values.append(value.isoformat())
            else:
                values.append(value)

        values.append(execution_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE job_executions SET {', '.join(set_clauses)} WHERE id = ?",
                values
            )
            conn.commit()

        return self.get(execution_id)

    def get(self, execution_id: str) -> Optional[JobExecutionLog]:
        """Récupère une exécution par ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM job_executions WHERE id = ?",
                (execution_id,)
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_model(row)

    def get_by_job(self, job_id: str, limit: int = 50) -> List[JobExecutionLog]:
        """Récupère les exécutions d'un job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM job_executions
                   WHERE job_id = ?
                   ORDER BY started_at DESC
                   LIMIT ?""",
                (job_id, limit)
            )
            rows = cursor.fetchall()

        return [self._row_to_model(row) for row in rows]

    def _row_to_model(self, row: sqlite3.Row) -> JobExecutionLog:
        """Convertit une ligne SQL en modèle"""
        return JobExecutionLog(
            id=row['id'],
            job_id=row['job_id'],
            started_at=datetime.fromisoformat(row['started_at']),
            finished_at=datetime.fromisoformat(row['finished_at']) if row['finished_at'] else None,
            status=row['status'],
            result=json.loads(row['result']) if row['result'] else None,
            error=row['error'],
            messages_sent=row['messages_sent'],
            profiles_visited=row['profiles_visited']
        )
```

---

## Phase 2 : API Routes

**Fichier :** `src/api/routes/scheduler_routes.py`

```python
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel

from src.scheduler.scheduler import AutomationScheduler
from src.scheduler.models import ScheduledJobConfig, JobExecutionLog

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

# DTOs
class CreateJobRequest(BaseModel):
    name: str
    description: Optional[str] = None
    bot_type: str
    enabled: bool = True
    schedule_type: str
    schedule_config: dict
    bot_config: dict

class UpdateJobRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    schedule_type: Optional[str] = None
    schedule_config: Optional[dict] = None
    bot_config: Optional[dict] = None

# Scheduler instance
scheduler = AutomationScheduler()

@router.get("/jobs", response_model=List[ScheduledJobConfig])
async def list_jobs(enabled_only: bool = False):
    """Liste tous les jobs planifiés"""
    return scheduler.list_jobs(enabled_only=enabled_only)

@router.get("/jobs/{job_id}", response_model=ScheduledJobConfig)
async def get_job(job_id: str):
    """Récupère un job par ID"""
    job = scheduler.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    return job

@router.post("/jobs", response_model=ScheduledJobConfig, status_code=status.HTTP_201_CREATED)
async def create_job(request: CreateJobRequest):
    """Crée un nouveau job planifié"""
    job_config = ScheduledJobConfig(
        name=request.name,
        description=request.description,
        bot_type=request.bot_type,
        enabled=request.enabled,
        schedule_type=request.schedule_type,
        schedule_config=request.schedule_config,
        bot_config=request.bot_config
    )

    return scheduler.add_job(job_config)

@router.put("/jobs/{job_id}", response_model=ScheduledJobConfig)
async def update_job(job_id: str, request: UpdateJobRequest):
    """Met à jour un job existant"""
    updates = request.dict(exclude_unset=True)

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

**Intégration dans `src/api/app.py` :**

```python
from src.api.routes.scheduler_routes import router as scheduler_router

# Ajouter après les autres routers
app.include_router(scheduler_router)
```

---

## Phase 3 : Dashboard Frontend

### 3.1 Page Automation Scheduler

**Fichier :** `dashboard/app/automation/page.tsx`

```typescript
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, RefreshCw } from 'lucide-react';
import JobList from '@/components/automation/JobList';
import JobEditDialog from '@/components/automation/JobEditDialog';
import { ScheduledJob } from '@/types/automation';
import { useToast } from '@/hooks/use-toast';

export default function AutomationSchedulerPage() {
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingJob, setEditingJob] = useState<ScheduledJob | null>(null);
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
        title: 'Error',
        description: 'Failed to load scheduled jobs',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const handleCreateJob = () => {
    setEditingJob(null);
    setIsCreateDialogOpen(true);
  };

  const handleEditJob = (job: ScheduledJob) => {
    setEditingJob(job);
    setIsCreateDialogOpen(true);
  };

  const handleDeleteJob = async (jobId: string) => {
    if (!confirm('Are you sure you want to delete this job?')) return;

    try {
      const response = await fetch(`/api/scheduler/jobs/${jobId}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete job');

      toast({
        title: 'Success',
        description: 'Job deleted successfully',
      });

      loadJobs();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete job',
        variant: 'destructive',
      });
    }
  };

  const handleToggleJob = async (jobId: string, enabled: boolean) => {
    try {
      const response = await fetch(`/api/scheduler/jobs/${jobId}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });

      if (!response.ok) throw new Error('Failed to toggle job');

      toast({
        title: 'Success',
        description: `Job ${enabled ? 'enabled' : 'disabled'} successfully`,
      });

      loadJobs();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to toggle job',
        variant: 'destructive',
      });
    }
  };

  const handleRunNow = async (jobId: string) => {
    try {
      const response = await fetch(`/api/scheduler/jobs/${jobId}/run`, {
        method: 'POST',
      });

      if (!response.ok) throw new Error('Failed to run job');

      toast({
        title: 'Success',
        description: 'Job queued for execution',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to run job',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Automation Scheduler</h1>
          <p className="text-muted-foreground mt-2">
            Configure and manage automated bot executions
          </p>
        </div>

        <div className="flex gap-2">
          <Button onClick={loadJobs} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={handleCreateJob}>
            <Plus className="h-4 w-4 mr-2" />
            New Job
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Scheduled Jobs</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">Loading...</div>
          ) : (
            <JobList
              jobs={jobs}
              onEdit={handleEditJob}
              onDelete={handleDeleteJob}
              onToggle={handleToggleJob}
              onRunNow={handleRunNow}
            />
          )}
        </CardContent>
      </Card>

      <JobEditDialog
        open={isCreateDialogOpen}
        onClose={() => setIsCreateDialogOpen(false)}
        job={editingJob}
        onSave={() => {
          setIsCreateDialogOpen(false);
          loadJobs();
        }}
      />
    </div>
  );
}
```

### 3.2 Composant Liste de Jobs

**Fichier :** `dashboard/components/automation/JobList.tsx`

```typescript
import { ScheduledJob } from '@/types/automation';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Play, Edit, Trash2, Clock, Calendar } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface JobListProps {
  jobs: ScheduledJob[];
  onEdit: (job: ScheduledJob) => void;
  onDelete: (jobId: string) => void;
  onToggle: (jobId: string, enabled: boolean) => void;
  onRunNow: (jobId: string) => void;
}

export default function JobList({
  jobs,
  onEdit,
  onDelete,
  onToggle,
  onRunNow,
}: JobListProps) {
  if (jobs.length === 0) {
    return (
      <div className="text-center py-12">
        <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <p className="text-muted-foreground">No scheduled jobs configured</p>
        <p className="text-sm text-muted-foreground mt-2">
          Click "New Job" to create your first automation
        </p>
      </div>
    );
  }

  const formatSchedule = (job: ScheduledJob) => {
    const { schedule_type, schedule_config } = job;

    if (schedule_type === 'daily') {
      return `Daily at ${schedule_config.hour}:${String(schedule_config.minute).padStart(2, '0')}`;
    } else if (schedule_type === 'weekly') {
      return `Weekly (${schedule_config.day_of_week}) at ${schedule_config.hour}:${String(schedule_config.minute).padStart(2, '0')}`;
    } else if (schedule_type === 'interval') {
      return `Every ${schedule_config.hours}h ${schedule_config.minutes}m`;
    } else if (schedule_type === 'cron') {
      return schedule_config.cron_expression;
    }

    return 'Manual';
  };

  const formatNextRun = (nextRun: string | null) => {
    if (!nextRun) return 'N/A';

    const date = new Date(nextRun);
    return date.toLocaleString();
  };

  const getStatusBadge = (status: string | null) => {
    if (!status) return <Badge variant="secondary">Never run</Badge>;

    if (status === 'success') return <Badge variant="success">Success</Badge>;
    if (status === 'failed') return <Badge variant="destructive">Failed</Badge>;
    if (status === 'running') return <Badge variant="default">Running</Badge>;

    return <Badge variant="secondary">{status}</Badge>;
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Status</TableHead>
          <TableHead>Name</TableHead>
          <TableHead>Bot Type</TableHead>
          <TableHead>Schedule</TableHead>
          <TableHead>Next Run</TableHead>
          <TableHead>Last Status</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {jobs.map((job) => (
          <TableRow key={job.id}>
            <TableCell>
              <Switch
                checked={job.enabled}
                onCheckedChange={(enabled) => onToggle(job.id, enabled)}
              />
            </TableCell>
            <TableCell className="font-medium">
              <div>
                {job.name}
                {job.description && (
                  <p className="text-sm text-muted-foreground">{job.description}</p>
                )}
              </div>
            </TableCell>
            <TableCell>
              <Badge variant="outline">{job.bot_type}</Badge>
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                {formatSchedule(job)}
              </div>
            </TableCell>
            <TableCell>{formatNextRun(job.next_run_at)}</TableCell>
            <TableCell>{getStatusBadge(job.last_run_status)}</TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onRunNow(job.id)}
                  title="Run now"
                >
                  <Play className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onEdit(job)}
                  title="Edit"
                >
                  <Edit className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onDelete(job.id)}
                  title="Delete"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

### 3.3 Types TypeScript

**Fichier :** `dashboard/types/automation.ts`

```typescript
export interface ScheduledJob {
  id: string;
  name: string;
  description?: string;
  bot_type: 'birthday' | 'visitor';
  enabled: boolean;
  schedule_type: 'daily' | 'weekly' | 'interval' | 'cron' | 'manual';
  schedule_config: Record<string, any>;
  bot_config: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by: string;
  last_run_at?: string;
  last_run_status?: string;
  last_run_error?: string;
  next_run_at?: string;
  max_instances: number;
  misfire_grace_time: number;
  coalesce: boolean;
}

export interface JobExecutionLog {
  id: string;
  job_id: string;
  started_at: string;
  finished_at?: string;
  status: 'running' | 'success' | 'failed' | 'cancelled';
  result?: Record<string, any>;
  error?: string;
  messages_sent: number;
  profiles_visited: number;
}
```

### 3.4 API Route Next.js

**Fichier :** `dashboard/app/api/scheduler/[...path]/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.API_KEY;

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const searchParams = request.nextUrl.searchParams;

  try {
    const response = await fetch(
      `${API_BASE_URL}/scheduler/${path}?${searchParams.toString()}`,
      {
        headers: {
          'X-API-Key': API_KEY || '',
        },
      }
    );

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch from backend' },
      { status: 500 }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const body = await request.json();

  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY || '',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to post to backend' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const body = await request.json();

  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/${path}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY || '',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to update backend' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');

  try {
    const response = await fetch(`${API_BASE_URL}/scheduler/${path}`, {
      method: 'DELETE',
      headers: {
        'X-API-Key': API_KEY || '',
      },
    });

    if (response.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to delete from backend' },
      { status: 500 }
    );
  }
}
```

---

## Phase 4 : Démarrage du Scheduler

**Fichier :** `src/api/app.py`

```python
from contextlib import asynccontextmanager
from src.scheduler.scheduler import AutomationScheduler

scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager pour FastAPI"""
    global scheduler

    # Startup
    scheduler = AutomationScheduler()
    scheduler.start()
    logger.info("Automation scheduler started")

    yield

    # Shutdown
    if scheduler:
        scheduler.shutdown()
        logger.info("Automation scheduler stopped")

# Créer l'app avec lifespan
app = FastAPI(
    title="LinkedIn Birthday Bot API",
    version="2.0.0",
    lifespan=lifespan
)
```

---

## Phase 5 : Tests

**Fichier :** `tests/test_scheduler.py`

```python
import pytest
from datetime import datetime, timedelta
from src.scheduler.scheduler import AutomationScheduler
from src.scheduler.models import ScheduledJobConfig, ScheduleType, BotType

@pytest.fixture
def scheduler():
    s = AutomationScheduler()
    s.start()
    yield s
    s.shutdown()

def test_create_daily_job(scheduler):
    """Test création d'un job quotidien"""
    job_config = ScheduledJobConfig(
        name="Test Daily Birthday",
        bot_type=BotType.BIRTHDAY,
        schedule_type=ScheduleType.DAILY,
        schedule_config={"hour": 8, "minute": 0},
        bot_config={"dry_run": True}
    )

    created = scheduler.add_job(job_config)

    assert created.id is not None
    assert created.enabled is True
    assert created.next_run_at is not None

def test_update_job(scheduler):
    """Test mise à jour d'un job"""
    job = scheduler.add_job(ScheduledJobConfig(
        name="Test Job",
        bot_type=BotType.BIRTHDAY,
        schedule_type=ScheduleType.DAILY,
        schedule_config={"hour": 8, "minute": 0},
        bot_config={}
    ))

    updated = scheduler.update_job(job.id, {"name": "Updated Job"})

    assert updated.name == "Updated Job"

def test_toggle_job(scheduler):
    """Test activation/désactivation"""
    job = scheduler.add_job(ScheduledJobConfig(
        name="Test Toggle",
        bot_type=BotType.VISITOR,
        schedule_type=ScheduleType.WEEKLY,
        schedule_config={"day_of_week": "mon", "hour": 10, "minute": 0},
        bot_config={}
    ))

    disabled = scheduler.toggle_job(job.id, False)
    assert disabled.enabled is False

    enabled = scheduler.toggle_job(job.id, True)
    assert enabled.enabled is True

def test_delete_job(scheduler):
    """Test suppression de job"""
    job = scheduler.add_job(ScheduledJobConfig(
        name="Test Delete",
        bot_type=BotType.BIRTHDAY,
        schedule_type=ScheduleType.DAILY,
        schedule_config={"hour": 8, "minute": 0},
        bot_config={}
    ))

    success = scheduler.delete_job(job.id)
    assert success is True

    retrieved = scheduler.get_job(job.id)
    assert retrieved is None
```

---

## Résumé

Cette implémentation fournit:

1. **Scheduler robuste** : APScheduler avec persistance SQLite
2. **API complète** : CRUD sur les jobs + exécution manuelle
3. **Dashboard UI** : Interface intuitive pour gérer les automatisations
4. **Historique** : Logs d'exécution pour chaque job
5. **Flexibilité** : Support daily/weekly/interval/cron
6. **Intégration** : Utilise le système RQ existant

**Prochaines étapes** : Voulez-vous que je commence l'implémentation ?
