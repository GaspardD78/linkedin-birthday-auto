from typing import Any, Optional

from ..bots.birthday_bot import run_birthday_bot
from ..bots.unlimited_bot import run_unlimited_bot
from ..bots.visitor_bot import VisitorBot
from ..config.config_manager import get_config
from ..utils.logging import get_logger
from ..utils.exceptions import InvalidAuthStateError

logger = get_logger(__name__)


def run_bot_task(
    bot_mode: str = "standard", dry_run: bool = False, max_days_late: int = 10
) -> dict[str, Any]:
    """Tâche pour le bot anniversaire"""
    logger.info("task_start", type="birthday", mode=bot_mode, dry_run=dry_run)
    try:
        if bot_mode == "standard":
            return run_birthday_bot(dry_run=dry_run)
        elif bot_mode == "unlimited":
            return run_unlimited_bot(dry_run=dry_run, max_days_late=max_days_late)
        else:
            error_msg = f"Invalid bot_mode: {bot_mode}. Must be 'standard' or 'unlimited'."
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "bot_type": "birthday"}
    except InvalidAuthStateError:
        # FIX: Handle missing authentication gracefully
        error_msg = "Impossible de démarrer le bot : fichier d'authentification manquant. Veuillez vous connecter via le tableau de bord."
        logger.error(f"task_auth_error: {error_msg}")
        return {"success": False, "error": error_msg, "bot_type": "birthday"}
    except Exception as e:
        logger.error("task_failed", error=str(e), exc_info=True)
        raise


def run_profile_visit_task(
    dry_run: bool = False, limit: Optional[int] = None
) -> dict[str, Any]:
    """
    Tâche pour la visite de profils (V2 Native).

    Cette fonction utilise le VisitorBot V2 qui s'intègre nativement
    avec l'architecture V2 (browser manager, auth manager, config centralisée, etc.).

    Args:
        dry_run: Mode test sans visiter réellement les profils
        limit: Nombre maximum de profils à visiter. Override la valeur de config.visitor.limits.profiles_per_run (Optionnel)

    Returns:
        Dict contenant les résultats de l'exécution
    """
    logger.info("task_start", type="visit_profiles", dry_run=dry_run, limit=limit)

    try:
        # Charger la configuration
        config = get_config()

        # Override dry_run si nécessaire
        if dry_run:
            config.dry_run = True

        # Logger si on override la limite de profils
        if limit is not None and limit != config.visitor.limits.profiles_per_run:
            logger.info(
                f"Overriding profiles limit: {config.visitor.limits.profiles_per_run} → {limit}"
            )

        # Le context manager gère automatiquement setup/teardown du navigateur
        with VisitorBot(config=config, profiles_limit_override=limit) as bot:
            return bot.run()

    except InvalidAuthStateError:
        # FIX: Handle missing authentication gracefully
        error_msg = "Impossible de démarrer le bot : fichier d'authentification manquant. Veuillez vous connecter via le tableau de bord."
        logger.error(f"task_auth_error: {error_msg}")
        return {"success": False, "error": error_msg, "bot_type": "visitor"}
    except Exception as e:
        logger.error("task_failed", error=str(e), exc_info=True)
        return {"success": False, "error": str(e), "bot_type": "visitor"}


def run_visitor_task(
    keywords: list[str],
    location: str,
    limit: int = 10,
    campaign_id: int = None,
    dry_run: bool = False
) -> dict[str, Any]:
    """
    Task to run the VisitorBot for a specific campaign.
    Wraps the VisitorBot with campaign context.
    """
    logger.info("task_start", type="visitor_campaign", campaign_id=campaign_id)
    try:
        config = get_config()

        # Override config with campaign parameters
        config.visitor.keywords = keywords
        config.visitor.location = location
        if dry_run:
            config.dry_run = True

        with VisitorBot(
            config=config,
            profiles_limit_override=limit,
            campaign_id=campaign_id
        ) as bot:
            return bot.run()

    except InvalidAuthStateError:
        error_msg = "Authentication missing. Please login via Dashboard."
        logger.error(f"task_auth_error: {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        logger.error("task_failed", error=str(e), exc_info=True)
        return {"success": False, "error": str(e)}
