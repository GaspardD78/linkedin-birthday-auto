"""APScheduler-based automation scheduler with RQ integration."""

import logging
import os
from typing import Optional, List, Union, Dict, Any
from datetime import datetime
import pytz

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from redis import Redis
from rq import Queue

from src.scheduler.models import (
    ScheduledJobConfig,
    JobExecutionLog,
    ScheduleType,
    BotType,
    BirthdayBotConfig,
    VisitorBotConfig
)
from src.scheduler.job_store import JobConfigStore, JobExecutionStore

logger = logging.getLogger(__name__)


class AutomationScheduler:
    """
    Manages automated scheduling of bot executions.

    This scheduler:
    - Uses APScheduler for reliable job scheduling
    - Persists jobs to SQLite
    - Executes jobs via RQ (Redis Queue)
    - Tracks execution history
    - Supports multiple schedule types (daily, weekly, interval, cron)

    Singleton pattern ensures only one scheduler instance per process.
    """

    _instance: Optional['AutomationScheduler'] = None

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the scheduler (only once due to singleton)."""
        if hasattr(self, '_initialized'):
            return

        self._initialized = True
        logger.info("Initializing AutomationScheduler...")

        # Job stores
        self.job_config_store = JobConfigStore()
        self.execution_store = JobExecutionStore()

        # RQ setup for job execution
        redis_host = os.getenv("REDIS_HOST", "redis-bot")
        redis_port = int(os.getenv("REDIS_PORT", 6379))

        try:
            self.redis_conn = Redis(host=redis_host, port=redis_port)
            self.job_queue = Queue("linkedin-bot", connection=self.redis_conn)
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            self.redis_conn = None
            self.job_queue = None

        # APScheduler configuration
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///data/scheduler_apscheduler.db')
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=3)
        }
        job_defaults = {
            'coalesce': True,         # Merge missed runs
            'max_instances': 1,       # One instance per job
            'misfire_grace_time': 3600  # 1h tolerance
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.timezone('Europe/Paris')
        )

        # Event listeners
        self.scheduler.add_listener(
            self._job_event_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )

        logger.info("AutomationScheduler initialized successfully")

    def start(self):
        """Start the scheduler and reload jobs from database."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("APScheduler started")

            # Reload jobs from database
            self._reload_jobs()

            logger.info("AutomationScheduler is now running")

    def shutdown(self, wait: bool = True):
        """
        Shutdown the scheduler.

        Args:
            wait: If True, wait for all jobs to finish before shutting down
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("AutomationScheduler shutdown complete")

    def _reload_jobs(self):
        """Reload all enabled jobs from database into APScheduler."""
        jobs = self.job_config_store.list_all(enabled_only=True)
        logger.info(f"Reloading {len(jobs)} enabled jobs from database")

        for job_config in jobs:
            try:
                self._schedule_job(job_config)
                logger.debug(f"Reloaded job: {job_config.name} ({job_config.id})")
            except Exception as e:
                logger.error(f"Failed to reload job {job_config.id}: {e}", exc_info=True)

        logger.info(f"Successfully reloaded {len(jobs)} jobs")

    def add_job(self, job_config: ScheduledJobConfig) -> ScheduledJobConfig:
        """
        Add a new scheduled job.

        Args:
            job_config: Job configuration

        Returns:
            Created job configuration
        """
        # Save to database
        saved_config = self.job_config_store.create(job_config)

        # Schedule in APScheduler if enabled
        if saved_config.enabled:
            self._schedule_job(saved_config)

        logger.info(f"Job created: {saved_config.name} ({saved_config.id})")
        return saved_config

    def update_job(self, job_id: str, updates: dict) -> Optional[ScheduledJobConfig]:
        """
        Update an existing job.

        Args:
            job_id: Job identifier
            updates: Dictionary of fields to update

        Returns:
            Updated job configuration or None if not found
        """
        # Update in database
        updated_config = self.job_config_store.update(job_id, updates)

        if not updated_config:
            return None

        # Re-sync with APScheduler
        try:
            self.scheduler.remove_job(job_id, jobstore='default')
        except Exception:
            pass  # Job might not exist in scheduler

        if updated_config.enabled:
            self._schedule_job(updated_config)

        logger.info(f"Job updated: {updated_config.name} ({job_id})")
        return updated_config

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.

        Args:
            job_id: Job identifier

        Returns:
            True if job was deleted, False if not found
        """
        # Remove from APScheduler
        try:
            self.scheduler.remove_job(job_id, jobstore='default')
        except Exception:
            pass  # Job might not exist in scheduler

        # Delete from database
        success = self.job_config_store.delete(job_id)

        if success:
            logger.info(f"Job deleted: {job_id}")

        return success

    def toggle_job(self, job_id: str, enabled: bool) -> Optional[ScheduledJobConfig]:
        """
        Enable or disable a job.

        Args:
            job_id: Job identifier
            enabled: True to enable, False to disable

        Returns:
            Updated job configuration or None if not found
        """
        return self.update_job(job_id, {"enabled": enabled})

    def run_job_now(self, job_id: str) -> bool:
        """
        Execute a job immediately (outside of schedule).

        Args:
            job_id: Job identifier

        Returns:
            True if job was queued, False if job not found or error
        """
        job_config = self.job_config_store.get(job_id)

        if not job_config:
            logger.error(f"Job not found: {job_id}")
            return False

        # Execute directly (bypass scheduler)
        self._execute_job(job_config)
        return True

    def get_job(self, job_id: str) -> Optional[ScheduledJobConfig]:
        """
        Retrieve a job configuration.

        Args:
            job_id: Job identifier

        Returns:
            Job configuration or None if not found
        """
        return self.job_config_store.get(job_id)

    def list_jobs(self, enabled_only: bool = False) -> List[ScheduledJobConfig]:
        """
        List all scheduled jobs.

        Args:
            enabled_only: If True, only return enabled jobs

        Returns:
            List of job configurations
        """
        return self.job_config_store.list_all(enabled_only=enabled_only)

    def get_job_history(self, job_id: str, limit: int = 50) -> List[JobExecutionLog]:
        """
        Get execution history for a job.

        Args:
            job_id: Job identifier
            limit: Maximum number of logs to return

        Returns:
            List of execution logs
        """
        return self.execution_store.get_by_job(job_id, limit=limit)

    def _schedule_job(self, job_config: ScheduledJobConfig):
        """
        Schedule a job in APScheduler.

        Args:
            job_config: Job configuration
        """
        trigger = self._create_trigger(job_config)

        if not trigger:
            logger.error(f"Cannot create trigger for job {job_config.id}")
            return

        # Schedule the job
        # FIX: Convert job_config to dict to avoid pickling issues with Pydantic/Threads
        # APScheduler uses pickle for serialization, and Pydantic v2 models or
        # objects with thread locks can cause issues. Passing raw dict is safer.
        job_config_dict = job_config.model_dump()

        self.scheduler.add_job(
            func=self._execute_job,
            trigger=trigger,
            args=[job_config_dict],
            id=job_config.id,
            name=job_config.name,
            replace_existing=True,
            max_instances=job_config.max_instances,
            misfire_grace_time=job_config.misfire_grace_time,
            coalesce=job_config.coalesce
        )

        # Update next_run_at in database
        ap_job = self.scheduler.get_job(job_config.id)
        if ap_job and ap_job.next_run_time:
            self.job_config_store.update(
                job_config.id,
                {"next_run_at": ap_job.next_run_time}
            )

        logger.debug(f"Scheduled job: {job_config.name} ({job_config.id})")

    def _create_trigger(self, job_config: ScheduledJobConfig):
        """
        Create an APScheduler trigger from job configuration.

        Args:
            job_config: Job configuration

        Returns:
            APScheduler trigger or None if invalid
        """
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

        logger.error(f"Unknown schedule type: {schedule_type}")
        return None

    def _execute_job(self, job_config: Union[ScheduledJobConfig, Dict[str, Any]]):
        """
        Execute a job by enqueuing it to RQ.

        Args:
            job_config: Job configuration (object or dict)
        """
        # FIX: Reconstruct model if dict is passed (from APScheduler serialization fix)
        if isinstance(job_config, dict):
            try:
                job_config = ScheduledJobConfig.model_validate(job_config)
            except Exception as e:
                logger.error(f"Failed to reconstruct job config from dict: {e}")
                return

        logger.info(f"Executing job: {job_config.name} ({job_config.id})")

        if not self.job_queue:
            logger.error("RQ queue not available, cannot execute job")
            return

        # Create execution log
        execution_log = JobExecutionLog(
            job_id=job_config.id,
            started_at=datetime.utcnow(),
            status="running"
        )
        execution_log = self.execution_store.create(execution_log)

        # Update job last_run
        self.job_config_store.update(
            job_config.id,
            {
                "last_run_at": datetime.utcnow(),
                "last_run_status": "running"
            }
        )

        try:
            # Enqueue to RQ based on bot type
            if job_config.bot_type == BotType.BIRTHDAY:
                bot_config = job_config.bot_config
                assert isinstance(bot_config, BirthdayBotConfig)

                # Determine bot_mode and max_days_late
                bot_mode = "unlimited" if bot_config.process_late else "standard"
                max_days = bot_config.max_days_late if bot_config.process_late else 0
                timeout = "180m" if bot_mode == "unlimited" else "30m"

                rq_job = self.job_queue.enqueue(
                    "src.queue.tasks.run_bot_task",
                    bot_mode=bot_mode,
                    dry_run=bot_config.dry_run,
                    max_days_late=max_days,
                    job_timeout=timeout,
                    meta={'job_type': 'birthday', 'scheduled_job_id': job_config.id}
                )

                logger.info(f"Birthday bot enqueued: RQ job {rq_job.id}")

            elif job_config.bot_type == BotType.VISITOR:
                bot_config = job_config.bot_config
                assert isinstance(bot_config, VisitorBotConfig)

                rq_job = self.job_queue.enqueue(
                    "src.queue.tasks.run_profile_visit_task",
                    dry_run=bot_config.dry_run,
                    limit=bot_config.limit,
                    job_timeout="45m",
                    meta={'job_type': 'visit', 'scheduled_job_id': job_config.id}
                )

                logger.info(f"Visitor bot enqueued: RQ job {rq_job.id}")

            # Update execution log to queued
            self.execution_store.update(
                execution_log.id,
                {
                    "status": "queued",
                    "result": {"rq_job_id": rq_job.id if rq_job else None}
                }
            )

            # Update job status
            self.job_config_store.update(
                job_config.id,
                {
                    "last_run_status": "queued"
                }
            )

        except Exception as e:
            logger.error(f"Job execution failed: {job_config.name}", exc_info=True)

            # Mark as failed
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

    def _job_event_listener(self, event):
        """
        Listen to APScheduler job events.

        Args:
            event: APScheduler event
        """
        logger.debug(f"APScheduler event: {event}")

        # Update next_run_at after execution
        if event.job_id:
            try:
                ap_job = self.scheduler.get_job(event.job_id)
                if ap_job and ap_job.next_run_time:
                    self.job_config_store.update(
                        event.job_id,
                        {"next_run_at": ap_job.next_run_time}
                    )
            except Exception as e:
                logger.warning(f"Failed to update next_run_at for {event.job_id}: {e}")
