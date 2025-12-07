"""
Bot LinkedIn pour anniversaires avec limites (mode standard).

Ce bot traite UNIQUEMENT les anniversaires du jour et respecte les limites
hebdomadaires configurées pour éviter la détection LinkedIn.
"""

from datetime import datetime
import random
import time
from typing import Any

from playwright.sync_api import Locator

from ..core.base_bot import BaseLinkedInBot, ContactData
from ..core.database import get_database
from ..monitoring.metrics import RUN_DURATION_SECONDS
from ..utils.exceptions import DailyLimitReachedError, MessageSendError, WeeklyLimitReachedError
from ..utils.logging import get_logger

logger = get_logger(__name__)


class BirthdayBot(BaseLinkedInBot):
    """
    Bot LinkedIn pour anniversaires en mode standard.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = None
        self.run_stats = {
            "today_found": 0,
            "late_found": 0,
            "sent": 0,
            "ignored_limit": 0
        }

        logger.info("BirthdayBot initialized - Processing TODAY's birthdays only")

    def run(self) -> dict[str, Any]:
        return super().run()

    def _run_internal(self) -> dict[str, Any]:
        """
        Exécute le bot pour envoyer des messages d'anniversaire.
        Utilise le générateur 'Process-As-You-Go' pour fiabilité maximale.
        """
        start_time = time.time()

        logger.info("═" * 70)
        logger.info("🎂 Starting BirthdayBot (Standard Mode)")
        logger.info("═" * 70)
        logger.info(
            "configuration",
            dry_run=self.config.dry_run,
            weekly_limit=self.config.messaging_limits.weekly_message_limit,
            mode="TODAY's birthdays only",
        )
        logger.info("═" * 70)

        # Initialiser la database si activée
        if self.config.database.enabled:
            try:
                self.db = get_database(self.config.database.db_path)
            except Exception as e:
                logger.warning(f"Database unavailable: {e}", exc_info=True)
                self.db = None

        self._check_limits()

        if not self.check_login_status():
            return self._build_error_result("Login verification failed")

        max_allowed = self._calculate_max_allowed_messages()
        logger.info(f"✅ Budget for this run: {max_allowed} messages")

        # ITERATION DU FLUX (Generator Pattern)
        # On parcourt les contacts un par un (Process-As-You-Go)
        # Le générateur gère le scroll et l'extraction sûre
        for contact_data, contact_locator in self.yield_birthday_contacts():

            try:
                if contact_data.birthday_type == "today":
                    self.run_stats["today_found"] += 1

                    # Vérifier quota (FILTRE AVANT ACTION)
                    if self.run_stats["sent"] < max_allowed:

                        # APPEL MÉTHODE ROBUSTE (Capable de gérer Locator OU Fallback URL)
                        # On passe 'contact_locator' (le Locator du générateur)
                        # S'il est valide, c'est instantané. Sinon, process_birthday_contact gère.
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
                        logger.debug("Limit reached for this run, ignoring remaining 'today' items.")

                elif contact_data.birthday_type == "late":
                    self.run_stats["late_found"] += 1
                    # Standard mode ignores late

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
            sent=f"{self.run_stats['sent']}/{max_allowed}",
            ignored_limit=self.run_stats["ignored_limit"],
            duration=f"{duration:.1f}s",
        )
        logger.info("═" * 70)

        return self._build_result(
            messages_sent=self.run_stats["sent"],
            contacts_processed=self.stats["contacts_processed"],
            birthdays_today=self.run_stats["today_found"],
            birthdays_late_ignored=self.run_stats["late_found"],
            messages_ignored=self.run_stats["ignored_limit"],
            duration_seconds=duration,
        )

    def _check_limits(self) -> None:
        """Vérifie que les limites globales ne sont pas atteintes."""
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
            "bot_mode": "standard",
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
            "bot_mode": "standard",
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
    with BirthdayBot(config=config) as bot:
        return bot.run()
