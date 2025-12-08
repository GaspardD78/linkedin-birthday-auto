"""
Bot LinkedIn pour anniversaires sans limites (mode unlimited).

Ce bot traite à la fois les anniversaires du jour ET en retard,
sans limite hebdomadaire (utilise seulement des délais entre messages).
"""

from datetime import datetime
import logging
import random
import time
from typing import Any

from ..core.base_bot import BaseLinkedInBot
from ..core.database import get_database
from ..utils.exceptions import MessageSendError

logger = logging.getLogger(__name__)


class UnlimitedBirthdayBot(BaseLinkedInBot):
    """
    Bot LinkedIn pour anniversaires en mode illimité.

    Caractéristiques :
    - Traite les anniversaires du jour ET en retard (configurable)
    - Pas de limite hebdomadaire
    - Utilise des délais entre messages pour éviter la détection
    - Idéal pour rattraper un backlog d'anniversaires

    ⚠️  AVERTISSEMENT ⚠️
    Ce mode peut envoyer beaucoup de messages d'un coup.
    LinkedIn peut détecter un comportement anormal.
    Utilisez avec prudence et configurez des délais suffisants.
    """

    def __init__(self, *args, **kwargs):
        """Initialise l'UnlimitedBirthdayBot."""
        super().__init__(*args, **kwargs)
        self.db = None

        logger.info(
            "UnlimitedBirthdayBot initialized - " "Processing TODAY + LATE birthdays (NO limits)"
        )

    def run(self) -> dict[str, Any]:
        return super().run()

    def _run_internal(self) -> dict[str, Any]:
        """
        Exécute le bot pour envoyer des messages d'anniversaire (unlimited).
        """
        start_time = time.time()

        logger.info("═" * 70)
        logger.info("🎂 Starting UnlimitedBirthdayBot (Unlimited Mode)")
        logger.info("═" * 70)
        logger.info(f"Dry Run: {self.config.dry_run}")
        logger.info(f"Process Today: {self.config.birthday_filter.process_today}")
        logger.info(f"Process Late: {self.config.birthday_filter.process_late}")
        logger.info(f"Max Days Late: {self.config.birthday_filter.max_days_late}")
        logger.info("⚠️  WARNING: NO weekly limit - could send many messages!")
        logger.info("═" * 70)

        # Initialiser la database si activée
        if self.config.database.enabled:
            try:
                self.db = get_database(self.config.database.db_path)
            except Exception as e:
                logger.warning(f"Database unavailable: {e}", exc_info=True)
                self.db = None

        # Vérifier la connexion LinkedIn
        if not self.check_login_status():
            return self._build_error_result("Login verification failed")

        logger.info("🚀 Starting birthday stream processing...")

        birthdays_today = 0
        birthdays_late = 0
        messages_ignored = 0

        # Reset stats for this run
        self.stats["messages_sent"] = 0
        self.stats["contacts_processed"] = 0
        self.stats["errors"] = 0

        try:
            for contact_data, locator in self.yield_birthday_contacts():
                is_eligible = False

                # Stats collecting
                if contact_data.birthday_type == "today":
                    birthdays_today += 1
                elif contact_data.birthday_type == "late":
                    birthdays_late += 1

                # Filtering logic
                if contact_data.birthday_type == "today":
                    if self.config.birthday_filter.process_today:
                        is_eligible = True
                elif contact_data.birthday_type == "late":
                    if self.config.birthday_filter.process_late:
                        # Allow late birthdays up to configured max
                        if contact_data.days_late <= self.config.birthday_filter.max_days_late:
                            is_eligible = True

                if not is_eligible:
                    messages_ignored += 1
                    logger.info(f"⏭️  Skipping {contact_data.name} (Not eligible: {contact_data.birthday_type}, {contact_data.days_late} days)")
                    continue

                # Processing
                try:
                    logger.info(f"Processing contact: {contact_data.name} (Type: {contact_data.birthday_type})")

                    # Use standard processing method (same as BirthdayBot)
                    success = self.process_birthday_contact(contact_data, locator=locator)

                    self.stats["contacts_processed"] += 1

                    if success:
                        self.stats["messages_sent"] += 1

                        # Simulation d'activité humaine occasionnelle
                        if random.random() < 0.3:
                            self.simulate_human_activity()

                        # Pause entre messages (CRITICAL in unlimited mode)
                        self._wait_between_messages()

                except MessageSendError as e:
                    logger.error(f"Failed to send message to {contact_data.name}: {e}")
                    self.stats["errors"] += 1

        except Exception as e:
            logger.error(f"Critical error during stream processing: {e}", exc_info=True)
            self.stats["errors"] += 1

        # Résumé final
        duration = time.time() - start_time

        logger.info("")
        logger.info("═" * 70)
        logger.info("✅ UnlimitedBirthdayBot execution completed")
        logger.info("═" * 70)
        logger.info(f"Messages sent: {self.stats['messages_sent']}")
        logger.info(f"Contacts processed: {self.stats['contacts_processed']}")
        logger.info(f"Birthdays detected: {birthdays_today} today, {birthdays_late} late")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Duration: {self._format_duration(duration)}")
        logger.info("═" * 70)

        return self._build_result(
            messages_sent=self.stats["messages_sent"],
            contacts_processed=self.stats["contacts_processed"],
            birthdays_today=birthdays_today,
            birthdays_late=birthdays_late,
            messages_ignored=messages_ignored,
            duration_seconds=duration,
        )

    def _format_duration(self, seconds: float) -> str:
        """Formate une durée en secondes."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    def _wait_between_messages(self) -> None:
        """Attend un délai humanisé entre deux messages."""
        if self.config.dry_run:
            # Délai court en mode dry-run
            delay = random.randint(2, 5)
            logger.info(f"⏸️  Pause (dry-run): {delay}s")
            time.sleep(delay)
        else:
            # Délai normal configuré
            delay = random.randint(
                self.config.delays.min_delay_seconds, self.config.delays.max_delay_seconds
            )
            minutes = delay // 60
            seconds = delay % 60
            logger.info(f"⏸️  Pause: {minutes}m {seconds}s")
            time.sleep(delay)

    def _build_result(
        self,
        messages_sent: int,
        contacts_processed: int,
        birthdays_today: int,
        birthdays_late: int,
        messages_ignored: int,
        duration_seconds: float,
    ) -> dict[str, Any]:
        """Construit le dictionnaire de résultats."""
        return {
            "success": True,
            "bot_mode": "unlimited",
            "messages_sent": messages_sent,
            "contacts_processed": contacts_processed,
            "birthdays_today": birthdays_today,
            "birthdays_late": birthdays_late,
            "messages_ignored": messages_ignored,
            "errors": self.stats["errors"],
            "duration_seconds": round(duration_seconds, 2),
            "dry_run": self.config.dry_run,
            "timestamp": datetime.now().isoformat(),
        }

    def _build_error_result(self, error_message: str) -> dict[str, Any]:
        """Construit un résultat d'erreur."""
        return {
            "success": False,
            "bot_mode": "unlimited",
            "error": error_message,
            "messages_sent": 0,
            "contacts_processed": 0,
            "timestamp": datetime.now().isoformat(),
        }


# Helper function pour usage simplifié
def run_unlimited_bot(
    config=None, dry_run: bool = False, max_days_late: int = 10
) -> dict[str, Any]:
    """
    Fonction helper pour exécuter l'UnlimitedBirthdayBot facilement.
    """
    from ..config.config_manager import get_config

    if config is None:
        config = get_config()

    # FIX: Créer une COPIE de la config pour éviter de polluer le singleton
    config = config.model_copy(deep=True)

    if dry_run:
        config.dry_run = True

    config.bot_mode = "unlimited"
    config.birthday_filter.process_today = True
    config.birthday_filter.process_late = True
    config.birthday_filter.max_days_late = max_days_late

    with UnlimitedBirthdayBot(config=config) as bot:
        return bot.run()
