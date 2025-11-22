"""
Définition des tâches RQ (Redis Queue) pour le bot LinkedIn.
"""

from typing import Optional, Dict, Any
import time
from ..bots.birthday_bot import run_birthday_bot
# from ..bots.unlimited_bot import run_unlimited_bot # To be implemented if needed
from ..utils.logging import get_logger
from ..monitoring.metrics import RUN_DURATION_SECONDS

logger = get_logger(__name__)

def run_bot_task(bot_mode: str = 'standard', dry_run: bool = False, config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Tâche RQ pour exécuter le bot.

    Args:
        bot_mode: 'standard' ou 'unlimited'
        dry_run: Mode test
        config: Configuration override (dictionnaire)

    Returns:
        Résultats de l'exécution
    """
    job_id = "unknown"
    try:
        from rq import get_current_job
        job = get_current_job()
        if job:
            job_id = job.id
    except ImportError:
        pass

    logger.info("starting_bot_task", job_id=job_id, mode=bot_mode, dry_run=dry_run)

    start_time = time.time()

    try:
        # Configuration override handling would go here if we were passing a dict
        # For now we assume standard config loading inside run_birthday_bot

        if bot_mode == 'standard':
            result = run_birthday_bot(dry_run=dry_run)
        # elif bot_mode == 'unlimited':
        #     result = run_unlimited_bot(dry_run=dry_run)
        else:
            raise ValueError(f"Unknown bot mode: {bot_mode}")

        duration = time.time() - start_time
        logger.info("bot_task_completed", job_id=job_id, duration=duration, success=True)
        return result

    except Exception as e:
        duration = time.time() - start_time
        logger.error("bot_task_failed", job_id=job_id, error=str(e), duration=duration)
        raise e
