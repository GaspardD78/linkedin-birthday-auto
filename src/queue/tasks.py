import sys
import subprocess
from typing import Optional, Dict, Any
from ..bots.birthday_bot import run_birthday_bot
from ..bots.unlimited_bot import run_unlimited_bot
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
    """Tâche pour la visite de profils (Wrapper du script legacy)"""
    logger.info("task_start", type="visit_profiles", dry_run=dry_run)

    # Commande pour lancer le script legacy
    cmd = [sys.executable, "legacy/visit_profiles.py"]

    # On passe les variables d'env nécessaires
    import os
    env = os.environ.copy()
    env.update({"DRY_RUN": str(dry_run).lower(), "HEADLESS": "true"})

    try:
        # Exécution du script
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)

        if result.returncode == 0:
            logger.info("visit_profiles_success", output=result.stdout)
            return {"success": True, "logs": result.stdout}
        else:
            logger.error("visit_profiles_failed", error=result.stderr, stdout=result.stdout)
            return {"success": False, "error": result.stderr, "logs": result.stdout}

    except Exception as e:
        logger.error("task_execution_error", error=str(e))
        return {"success": False, "error": str(e)}
