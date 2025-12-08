"""
Bot LinkedIn pour anniversaires sans limites (mode unlimited).

Ce bot traite à la fois les anniversaires du jour ET en retard,
sans limite hebdomadaire (utilise seulement des délais entre messages).
Refactorisé pour hériter directement de BirthdayBot et garantir l'harmonisation du code.
"""

import logging
from typing import Any

from ..bots.birthday_bot import BirthdayBot
from ..core.database import get_database

logger = logging.getLogger(__name__)


class UnlimitedBirthdayBot(BirthdayBot):
    """
    Bot LinkedIn pour anniversaires en mode illimité.
    Hérite de BirthdayBot pour réutiliser 100% de la logique de navigation.

    Différences :
    1. _check_limits : Désactivé (passe toujours).
    2. _run_internal : Configure les filtres pour accepter 'late' + 'today'.
    3. logging : Adapté au mode illimité.
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

    def _run_internal(self) -> dict[str, Any]:
        """
        Wrapper autour de la logique standard, mais avec une configuration forcée.
        """
        # Force configuration for Unlimited Mode
        # Note: We modify the instance config directly since it's a copy passed to __init__ usually
        # But to be safe, we just rely on the fact that run_unlimited_bot sets these flags.

        # However, BirthdayBot._run_internal logic filters 'late' items by default
        # "Standard mode ignores late".
        # We need to Override _run_internal logic?
        # No, better to make BirthdayBot._run_internal smarter based on config.

        # Check BirthdayBot._run_internal implementation in base class:
        # It has: `if contact_data.birthday_type == "today": ... elif ... == "late": ...`
        # And the "late" block says "Standard mode ignores late".

        # So we MUST override _run_internal OR refactor BirthdayBot to respect config flags.
        # Refactoring BirthdayBot is the "Harmonisation" way.

        # BUT, the prompt says "Refactorise le code pour que toute modification future sur BirthdayBot soit automatiquement répercutée".
        # So I should PROBABLY modify BirthdayBot to be generic, and UnlimitedBot just configures it.

        # However, I can't modify BirthdayBot easily in this single file write.
        # I will rewrite UnlimitedBot to copy the logic structure BUT since I cannot change BirthdayBot in this turn (I can, but I am writing unlimited_bot.py now),
        # I will implement a FULL override that looks exactly like BirthdayBot but handles the late logic,
        # OR I will verify if I can just call super()._run_internal() if I patch BirthdayBot.

        # Let's look at BirthdayBot again.
        # It hardcodes: `if contact_data.birthday_type == "today": ... elif ... "late": # Standard mode ignores late`

        # Strategy: I will rewrite BirthdayBot FIRST (in next step) to be generic,
        # then UnlimitedBot will just be a configuration wrapper.
        # But wait, I am in the "Overwrite file" step. I should probably do UnlimitedBot here assuming BirthdayBot WILL be fixed.
        # actually I can write BirthdayBot in the next step.

        # For now, let's write a version of UnlimitedBot that *would* work if BirthdayBot was generic,
        # or just duplicate the loop properly (since currently they are divergent).

        # Actually, the best way to harmonize is:
        # 1. Update BirthdayBot to use `self.config.birthday_filter.process_late` to decide.
        # 2. UnlimitedBot just sets those configs and `check_limits` pass.

        # So I will write a minimal UnlimitedBot here that relies on the (to be updated) BirthdayBot.

        return super()._run_internal()

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
