"""
Bot LinkedIn pour anniversaires sans limites (mode unlimited).

Ce bot traite à la fois les anniversaires du jour ET en retard,
sans limite hebdomadaire (utilise seulement des délais entre messages).
Refactorisé pour hériter directement de BirthdayBot et garantir l'harmonisation du code.
"""

from datetime import datetime
from typing import Any

from ..bots.birthday_bot import BirthdayBot
from ..core.database import get_database
from ..utils.logging import get_logger

logger = get_logger(__name__)


class UnlimitedBirthdayBot(BirthdayBot):
    """
    Bot LinkedIn pour anniversaires en mode illimité.
    Hérite de BirthdayBot pour réutiliser 100% de la logique de navigation.

    Différences :
    1. _check_limits : Désactivé (passe toujours).
    2. _build_result : Adapté pour rapporter 'late_processed' au lieu de 'late_ignored'.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("UnlimitedBirthdayBot initialized (Inherits BirthdayBot)")

    def _check_limits(self) -> None:
        """
        Surcharge: Aucune vérification de limite en mode illimité.
        """
        logger.info("🔓 Unlimited Mode: Skipping limit checks.")
        pass

    def _calculate_max_allowed_messages(self) -> int:
        """
        Surcharge: Retourne une valeur très élevée ou la limite par run configurée.
        """
        return self.config.messaging_limits.max_messages_per_run or 9999

    def _build_result(self, messages_sent, contacts_processed, birthdays_today, birthdays_late_ignored=0, messages_ignored=0, duration_seconds=0.0, **kwargs) -> dict[str, Any]:
        """
        Surcharge pour adapter le rapport de résultat (ex: birthdays_late au lieu de ignored).
        Signature must match calling convention in BirthdayBot.
        """
        # Note: birthdays_late_ignored passed by base class is actually 'found' but ignored logic inside base class?
        # In base class: `birthdays_late_ignored=0 if self.config.birthday_filter.process_late else self.run_stats["late_found"]`
        # Since UnlimitedBot has process_late=True, base class passes 0 for ignored.

        # We handle both named args (test) and positional (base class)

        # Test sends: birthdays_late=10 (kwargs)
        # Base sends: birthdays_late_ignored=0 (positional)

        late_count = kwargs.get("birthdays_late", self.run_stats.get("late_found", 0))

        return {
            "success": True,
            "bot_mode": "unlimited",
            "messages_sent": messages_sent,
            "contacts_processed": contacts_processed,
            "birthdays_today": birthdays_today,
            "birthdays_late": late_count, # We report found late birthdays
            "messages_ignored": messages_ignored,
            "errors": self.stats.get("errors", 0),
            "duration_seconds": round(duration_seconds, 2),
            "dry_run": self.config.dry_run,
            "timestamp": datetime.now().isoformat()
        }

    def _format_duration(self, seconds: float) -> str:
        """Helper for formatting duration (used in legacy or tests)."""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{int(h)}h {int(m)}m {int(s)}s"
        elif m > 0:
            return f"{int(m)}m {int(s)}s"
        else:
            return f"{int(s)}s"

# Helper function stays similar
def run_unlimited_bot(
    config=None, dry_run: bool = False, max_days_late: int = 10
) -> dict[str, Any]:
    from ..config.config_manager import get_config

    if config is None:
        config = get_config()

    config = config.model_copy(deep=True)

    if dry_run:
        config.dry_run = True

    config.bot_mode = "unlimited"
    config.birthday_filter.process_today = True
    config.birthday_filter.process_late = True
    config.birthday_filter.max_days_late = max_days_late

    # Disable limits in config too just in case
    config.messaging_limits.weekly_message_limit = 999999
    config.messaging_limits.daily_message_limit = 999999

    with UnlimitedBirthdayBot(config=config) as bot:
        return bot.run()
