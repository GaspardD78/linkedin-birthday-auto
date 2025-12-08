"""SQLite persistence layer for scheduled jobs and execution logs."""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from src.scheduler.models import (
    ScheduledJobConfig,
    JobExecutionLog,
    BotType,
    ScheduleType,
    BirthdayBotConfig,
    VisitorBotConfig
)

logger = logging.getLogger(__name__)


class JobConfigStore:
    """Store for scheduled job configurations."""

    def __init__(self, db_path: str = "data/scheduler_config.db"):
        """
        Initialize the job config store.

        Args:
            db_path: Path to SQLite database file (default: data/scheduler_config.db)
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"JobConfigStore initialized with database: {db_path}")

    def _init_db(self):
        """Initialize the database schema."""
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

            # Create index for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_enabled
                ON scheduled_jobs(enabled)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_bot_type
                ON scheduled_jobs(bot_type)
            """)

            conn.commit()
            logger.debug("Database schema initialized")

    def create(self, job_config: ScheduledJobConfig) -> ScheduledJobConfig:
        """
        Create a new scheduled job.

        Args:
            job_config: Job configuration to create

        Returns:
            Created job configuration

        Raises:
            sqlite3.IntegrityError: If job with same ID already exists
        """
        with sqlite3.connect(self.db_path) as conn:
            # Serialize bot_config to JSON
            bot_config_json = job_config.bot_config.model_dump_json()

            conn.execute("""
                INSERT INTO scheduled_jobs VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                job_config.id,
                job_config.name,
                job_config.description,
                job_config.bot_type,
                int(job_config.enabled),
                job_config.schedule_type,
                json.dumps(job_config.schedule_config),
                bot_config_json,
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

        logger.info(f"Created job: {job_config.name} ({job_config.id})")
        return job_config

    def get(self, job_id: str) -> Optional[ScheduledJobConfig]:
        """
        Retrieve a job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job configuration or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM scheduled_jobs WHERE id = ?",
                (job_id,)
            )
            row = cursor.fetchone()

        if not row:
            logger.debug(f"Job not found: {job_id}")
            return None

        return self._row_to_model(row)

    def list_all(self, enabled_only: bool = False) -> List[ScheduledJobConfig]:
        """
        List all scheduled jobs.

        Args:
            enabled_only: If True, only return enabled jobs

        Returns:
            List of job configurations
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if enabled_only:
                query = "SELECT * FROM scheduled_jobs WHERE enabled = 1 ORDER BY created_at DESC"
                cursor = conn.execute(query)
            else:
                query = "SELECT * FROM scheduled_jobs ORDER BY created_at DESC"
                cursor = conn.execute(query)

            rows = cursor.fetchall()

        jobs = [self._row_to_model(row) for row in rows]
        logger.debug(f"Listed {len(jobs)} jobs (enabled_only={enabled_only})")
        return jobs

    def update(self, job_id: str, updates: dict) -> Optional[ScheduledJobConfig]:
        """
        Update a job configuration.

        Args:
            job_id: Job identifier
            updates: Dictionary of fields to update

        Returns:
            Updated job configuration or None if not found
        """
        # Always update updated_at
        updates['updated_at'] = datetime.utcnow().isoformat()

        # Convert values for SQL
        set_clauses = []
        values = []

        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")

            # Serialize complex types
            if isinstance(value, dict):
                values.append(json.dumps(value))
            elif isinstance(value, (BirthdayBotConfig, VisitorBotConfig)):
                values.append(value.model_dump_json())
            elif isinstance(value, bool):
                values.append(int(value))
            elif isinstance(value, datetime):
                values.append(value.isoformat())
            elif isinstance(value, (BotType, ScheduleType)):
                values.append(value.value)
            else:
                values.append(value)

        values.append(job_id)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"UPDATE scheduled_jobs SET {', '.join(set_clauses)} WHERE id = ?",
                values
            )
            conn.commit()

            if cursor.rowcount == 0:
                logger.warning(f"Job not found for update: {job_id}")
                return None

        logger.info(f"Updated job: {job_id} with {len(updates)} fields")
        return self.get(job_id)

    def delete(self, job_id: str) -> bool:
        """
        Delete a job.

        Args:
            job_id: Job identifier

        Returns:
            True if job was deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))
            conn.commit()

        success = cursor.rowcount > 0
        if success:
            logger.info(f"Deleted job: {job_id}")
        else:
            logger.warning(f"Job not found for deletion: {job_id}")

        return success

    def _row_to_model(self, row: sqlite3.Row) -> ScheduledJobConfig:
        """
        Convert a database row to ScheduledJobConfig model.

        Args:
            row: SQLite row

        Returns:
            Parsed job configuration
        """
        # Parse bot_config based on bot_type
        bot_type = BotType(row['bot_type'])
        bot_config_dict = json.loads(row['bot_config'])

        if bot_type == BotType.BIRTHDAY:
            bot_config = BirthdayBotConfig(**bot_config_dict)
        elif bot_type == BotType.VISITOR:
            bot_config = VisitorBotConfig(**bot_config_dict)
        else:
            raise ValueError(f"Unknown bot_type: {bot_type}")

        return ScheduledJobConfig(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            bot_type=bot_type,
            enabled=bool(row['enabled']),
            schedule_type=ScheduleType(row['schedule_type']),
            schedule_config=json.loads(row['schedule_config']),
            bot_config=bot_config,
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
    """Store for job execution logs."""

    def __init__(self, db_path: str = "data/scheduler_config.db"):
        """
        Initialize the execution log store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()
        logger.info(f"JobExecutionStore initialized with database: {db_path}")

    def _init_db(self):
        """Initialize the execution logs table."""
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

            # Index for faster queries by job_id
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_job_id
                ON job_executions(job_id)
            """)

            # Index for queries by date
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_started_at
                ON job_executions(started_at DESC)
            """)

            conn.commit()
            logger.debug("Execution logs schema initialized")

    def create(self, execution: JobExecutionLog) -> JobExecutionLog:
        """
        Create a new execution log.

        Args:
            execution: Execution log to create

        Returns:
            Created execution log
        """
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

        logger.debug(f"Created execution log: {execution.id} for job {execution.job_id}")
        return execution

    def update(self, execution_id: str, updates: dict) -> Optional[JobExecutionLog]:
        """
        Update an execution log.

        Args:
            execution_id: Execution log identifier
            updates: Dictionary of fields to update

        Returns:
            Updated execution log or None if not found
        """
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
            cursor = conn.execute(
                f"UPDATE job_executions SET {', '.join(set_clauses)} WHERE id = ?",
                values
            )
            conn.commit()

            if cursor.rowcount == 0:
                logger.warning(f"Execution log not found for update: {execution_id}")
                return None

        logger.debug(f"Updated execution log: {execution_id}")
        return self.get(execution_id)

    def get(self, execution_id: str) -> Optional[JobExecutionLog]:
        """
        Retrieve an execution log by ID.

        Args:
            execution_id: Execution log identifier

        Returns:
            Execution log or None if not found
        """
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
        """
        Retrieve execution logs for a specific job.

        Args:
            job_id: Job identifier
            limit: Maximum number of logs to return (default: 50)

        Returns:
            List of execution logs, ordered by started_at DESC
        """
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

        logs = [self._row_to_model(row) for row in rows]
        logger.debug(f"Retrieved {len(logs)} execution logs for job {job_id}")
        return logs

    def get_recent(self, limit: int = 100) -> List[JobExecutionLog]:
        """
        Retrieve recent execution logs across all jobs.

        Args:
            limit: Maximum number of logs to return (default: 100)

        Returns:
            List of execution logs, ordered by started_at DESC
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM job_executions
                   ORDER BY started_at DESC
                   LIMIT ?""",
                (limit,)
            )
            rows = cursor.fetchall()

        logs = [self._row_to_model(row) for row in rows]
        logger.debug(f"Retrieved {len(logs)} recent execution logs")
        return logs

    def _row_to_model(self, row: sqlite3.Row) -> JobExecutionLog:
        """
        Convert a database row to JobExecutionLog model.

        Args:
            row: SQLite row

        Returns:
            Parsed execution log
        """
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
