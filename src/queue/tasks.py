from typing import Optional, Dict, Any
from ..bots.birthday_bot import run_birthday_bot
from ..bots.unlimited_bot import run_unlimited_bot
from ..bots.visitor_bot import VisitorBot
from ..config.config_manager import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)

def run_bot_task(bot_mode: str = 'standard', dry_run: bool = False, max_days_late: int = 10) -> Dict[str, Any]:
    """Tâche pour le bot anniversaire"""
    logger.info("task_start", type="birthday", mode=bot_mode, dry_run=dry_run)
    try:
        if bot_mode == 'standard':
            return run_birthday_bot(dry_run=dry_run)
        elif bot_mode == 'unlimited':
            return run_unlimited_bot(dry_run=dry_run, max_days_late=max_days_late)
    except Exception as e:
        logger.error("task_failed", error=str(e))
        raise e

def run_profile_visit_task(dry_run: bool = False) -> Dict[str, Any]:
    """
    Tâche pour la visite de profils (V2 Native).

    Cette fonction utilise le VisitorBot V2 qui s'intègre nativement
    avec l'architecture V2 (browser manager, auth manager, config centralisée, etc.).

    Args:
        dry_run: Mode test sans visiter réellement les profils

    Returns:
        Dict contenant les résultats de l'exécution
    """
    logger.info("task_start", type="visit_profiles", dry_run=dry_run)

    try:
        # Charger la configuration
        config = get_config()

        # Override dry_run si nécessaire
        if dry_run:
            config.dry_run = True

        # Le context manager gère automatiquement setup/teardown du navigateur
        with VisitorBot(config=config) as bot:
            return bot.run()

    except Exception as e:
        logger.error("task_failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "bot_type": "visitor"
        }
