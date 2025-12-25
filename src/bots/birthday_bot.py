"""
Bot LinkedIn pour anniversaires avec limites (mode standard).

Ce bot traite les anniversaires en fonction de la configuration.
"""

import asyncio
from datetime import datetime
import random
import time
from typing import Any

from playwright.sync_api import Locator

from ..core.base_bot import BaseLinkedInBot, ContactData
from ..core.database import get_database
from ..monitoring.metrics import RUN_DURATION_SECONDS
from ..monitoring.stats_writer import StatsWriter
from ..services.notification_service import NotificationService
from ..utils.exceptions import DailyLimitReachedError, MessageSendError, WeeklyLimitReachedError
from ..utils.logging import get_logger

logger = get_logger(__name__)


class BirthdayBot(BaseLinkedInBot):
    """
    Bot LinkedIn pour anniversaires.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = None
        self.stats_writer = StatsWriter(stats_dir=self.config.paths.logs_dir)
        self.run_stats = {
            "today_found": 0,
            "late_found": 0,
            "sent": 0,
            "ignored_limit": 0
        }
        self._notification_tasks = []

        logger.info(f"BirthdayBot initialized (Mode: {self.config.bot_mode})")

    def run(self) -> dict[str, Any]:
        return super().run()

    def _run_internal(self) -> dict[str, Any]:
        """
        Exécute le bot pour envoyer des messages d'anniversaire.
        Utilise le générateur 'Process-As-You-Go' pour fiabilité maximale.
        """
        start_time = time.time()
        notification_service = None

        logger.info("═" * 70)
        logger.info(f"🎂 Starting BirthdayBot ({self.config.bot_mode})")
        logger.info("═" * 70)
        logger.info(
            "configuration",
            dry_run=self.config.dry_run,
            weekly_limit=self.config.messaging_limits.weekly_message_limit,
            process_today=self.config.birthday_filter.process_today,
            process_late=self.config.birthday_filter.process_late,
        )
        logger.info("═" * 70)

        # Initialiser la database si activée
        if self.config.database.enabled:
            try:
                self.db = get_database(self.config.database.db_path)
                # Initialize notification service with the database
                notification_service = NotificationService(self.db)
            except Exception as e:
                logger.warning(f"Database unavailable: {e}", exc_info=True)
                self.db = None

        try:
            self._check_limits()

            if not self.check_login_status():
                error_result = self._build_error_result("Login verification failed")
                # Send error notification
                if notification_service:
                    self._send_notification_sync(
                        notification_service.notify_error,
                        "Login verification failed",
                        "The bot could not verify login status on LinkedIn."
                    )
                return error_result

            max_allowed = self._calculate_max_allowed_messages()
            logger.info(f"✅ Budget for this run: {max_allowed} messages")

            # ITERATION DU FLUX (Generator Pattern)
            for contact_data, contact_locator in self.yield_birthday_contacts():

                try:
                    should_process = False

                    if contact_data.birthday_type == "today":
                        self.run_stats["today_found"] += 1
                        if self.config.birthday_filter.process_today:
                            should_process = True
                    elif contact_data.birthday_type == "late":
                        self.run_stats["late_found"] += 1
                        if self.config.birthday_filter.process_late:
                             if contact_data.days_late <= self.config.birthday_filter.max_days_late:
                                should_process = True
                             else:
                                logger.debug(f"Skipping late contact (Too old: {contact_data.days_late} days)")

                    if should_process:
                        # Vérifier quota (FILTRE AVANT ACTION)
                        if self.run_stats["sent"] < max_allowed:

                            # APPEL MÉTHODE ROBUSTE
                            success = self.process_birthday_contact(contact_data, locator=contact_locator)

                            if success:
                                self.run_stats["sent"] += 1
                                self.stats["messages_sent"] += 1
                                self.stats["contacts_processed"] += 1

                                if random.random() < 0.3:
                                    self.simulate_human_activity()
                                self._wait_between_messages()
                            else:
                                self.stats["errors"] += 1
                        else:
                            self.run_stats["ignored_limit"] += 1
                            logger.debug("Limit reached for this run, ignoring remaining items.")
                    else:
                        # Not eligible based on config
                        pass

                except Exception as e:
                    logger.error(f"Error in main loop for {contact_data.name}: {e}")
                    self.stats["errors"] += 1
                    continue

            duration = time.time() - start_time
            RUN_DURATION_SECONDS.observe(duration)

            logger.info("")
            logger.info("═" * 70)
            logger.info("✅ BirthdayBot execution completed")
            logger.info("═" * 70)
            logger.info(
                "execution_stats",
                found_today=self.run_stats["today_found"],
                found_late=self.run_stats["late_found"],
                sent=f"{self.run_stats['sent']}/{max_allowed}",
                ignored_limit=self.run_stats["ignored_limit"],
                duration=f"{duration:.1f}s",
            )
            logger.info("═" * 70)

            # Record stats to JSON file
            self.stats_writer.update_run(
                status="success",
                messages_sent=self.run_stats["sent"],
                messages_failed=self.stats.get("errors", 0),
                birthdays_today=self.run_stats["today_found"],
                birthdays_late=self.run_stats["late_found"],
                duration_seconds=duration,
                errors=[]
            )

            result = self._build_result(
                messages_sent=self.run_stats["sent"],
                contacts_processed=self.stats["contacts_processed"],
                birthdays_today=self.run_stats["today_found"],
                birthdays_late_ignored=0 if self.config.birthday_filter.process_late else self.run_stats["late_found"],
                messages_ignored=self.run_stats["ignored_limit"],
                duration_seconds=duration,
            )

            # Send success notification
            if notification_service:
                self._send_notification_sync(
                    notification_service.notify_success,
                    self.run_stats["sent"]
                )

            return result

        except Exception as e:
            duration = time.time() - start_time
            error_message = str(e)
            logger.error(f"Fatal error in BirthdayBot: {error_message}", exc_info=True)

            # Record error to JSON file
            self.stats_writer.update_run(
                status="failed",
                messages_sent=self.run_stats["sent"],
                messages_failed=self.stats.get("errors", 0),
                birthdays_today=self.run_stats["today_found"],
                birthdays_late=self.run_stats["late_found"],
                duration_seconds=duration,
                errors=[error_message]
            )

            # Send error notification
            if notification_service:
                self._send_notification_sync(
                    notification_service.notify_error,
                    error_message,
                    f"Duration before failure: {duration:.1f}s"
                )

            return self._build_error_result(error_message)

    def _send_notification_sync(self, async_func, *args, **kwargs):
        """
        Helper method to run async notification functions from sync code.
        Safe against garbage collection and race conditions.

        Tasks are stored and cleaned up in cleanup_notification_tasks() only,
        not on every call (avoiding O(n) overhead).

        Args:
            async_func: The async notification function to call
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
        """
        try:
            # Try to get the running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, create a task and keep a reference
                task = asyncio.create_task(async_func(*args, **kwargs))

                # Add done callback to log errors
                def log_error(t):
                    try:
                        t.result()
                    except Exception as err:
                        logger.error(f"Notification task failed: {err}", exc_info=True)

                task.add_done_callback(log_error)
                self._notification_tasks.append(task)

            except RuntimeError:
                # No running event loop, create one with timeout safety
                try:
                    asyncio.run(asyncio.wait_for(async_func(*args, **kwargs), timeout=10.0))
                except asyncio.TimeoutError:
                    logger.error("Notification sending timed out (10s)")
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")

    def cleanup_notification_tasks(self) -> None:
        """
        Wait for pending notification tasks to complete.
        Called during teardown to ensure notifications are sent before shutdown.
        """
        pending = [t for t in self._notification_tasks if not t.done()]
        if not pending:
            return

        logger.info(f"Waiting for {len(pending)} pending notification(s)...")
        try:
            # We need an event loop to wait for these tasks
            try:
                loop = asyncio.get_running_loop()
                # Use asyncio.wait to wait for all pending tasks with timeout
                done, still_pending = loop.run_until_complete(asyncio.wait(pending, timeout=5.0))

                if still_pending:
                    logger.warning(f"{len(still_pending)} notification tasks timed out and were abandoned.")
                    # Log which tasks are still pending
                    for task in still_pending:
                        logger.debug(f"Pending task: {task.get_name()}")

            except RuntimeError as e:
                # No running event loop (teardown is sync)
                logger.debug(f"No running event loop during teardown: {e}")
        except Exception as e:
            logger.warning(f"Error waiting for notifications: {e}")

    def teardown(self) -> None:
        """Override teardown to ensure notifications are sent."""
        self.cleanup_notification_tasks()
        super().teardown()

    def _check_limits(self) -> None:
        """
        Vérifie que les limites globales ne sont pas atteintes.

        Phase 3 (INC #2) - Source of Truth for Messaging Limits:
        - LIMITS (policy): Defined in config.yaml (messaging_limits section)
        - COUNTERS (current state): Tracked in database (birthday_messages table)
        - This design separates concerns: config = rules, db = tracking

        Note: UnlimitedBirthdayBot overrides these limits programmatically (sets to 999999),
        which is intentional for unlimited mode and documented in unlimited_bot.py.
        """
        if not self.db: return

        weekly_count = self.db.get_weekly_message_count()
        weekly_limit = self.config.messaging_limits.weekly_message_limit

        if weekly_count >= weekly_limit:
            raise WeeklyLimitReachedError(current=weekly_count, limit=weekly_limit)

        daily_limit = self.config.messaging_limits.daily_message_limit
        if daily_limit:
            daily_count = self.db.get_daily_message_count()
            if daily_count >= daily_limit:
                raise DailyLimitReachedError(current=daily_count, limit=daily_limit)

    def _calculate_max_allowed_messages(self) -> int:
        """Calcule le nombre maximum de messages autorisés pour cette exécution."""
        max_allowed = self.config.messaging_limits.max_messages_per_run or 9999

        if self.db:
            weekly_count = self.db.get_weekly_message_count()
            weekly_limit = self.config.messaging_limits.weekly_message_limit
            max_allowed = min(max_allowed, max(0, weekly_limit - weekly_count))

            daily_limit = self.config.messaging_limits.daily_message_limit
            if daily_limit:
                daily_count = self.db.get_daily_message_count()
                max_allowed = min(max_allowed, max(0, daily_limit - daily_count))

        return max_allowed

    def _wait_between_messages(self) -> None:
        """Attend un délai humanisé entre deux messages."""
        if self.config.dry_run:
            delay = random.randint(2, 5)
            logger.info(f"⏸️  Pause (dry-run): {delay}s")
            time.sleep(delay)
        else:
            delay = random.randint(
                self.config.delays.min_delay_seconds, self.config.delays.max_delay_seconds
            )
            minutes = delay // 60
            seconds = delay % 60
            logger.info(f"⏸️  Pause: {minutes}m {seconds}s")
            time.sleep(delay)

    def _build_result(self, messages_sent, contacts_processed, birthdays_today, birthdays_late_ignored, messages_ignored, duration_seconds) -> dict[str, Any]:
        return {
            "success": True,
            "bot_mode": self.config.bot_mode,
            "messages_sent": messages_sent,
            "contacts_processed": contacts_processed,
            "birthdays_today": birthdays_today,
            "birthdays_late_ignored": birthdays_late_ignored,
            "messages_ignored": messages_ignored,
            "errors": self.stats["errors"],
            "duration_seconds": round(duration_seconds, 2),
            "dry_run": self.config.dry_run,
            "timestamp": datetime.now().isoformat(),
        }

    def _build_error_result(self, error_message: str) -> dict[str, Any]:
        return {
            "success": False,
            "bot_mode": self.config.bot_mode,
            "error": error_message,
            "messages_sent": 0,
            "contacts_processed": 0,
            "timestamp": datetime.now().isoformat(),
        }

def run_birthday_bot(config=None, dry_run: bool = False) -> dict[str, Any]:
    from ..config.config_manager import get_config
    if config is None: config = get_config()
    config = config.model_copy(deep=True)
    if dry_run: config.dry_run = True
    # Default for BirthdayBot is ONLY today
    config.bot_mode = "standard"
    config.birthday_filter.process_today = True
    config.birthday_filter.process_late = False

    with BirthdayBot(config=config) as bot:
        return bot.run()
