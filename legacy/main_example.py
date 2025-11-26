#!/usr/bin/env python3
"""
Point d'entrée principal pour LinkedIn Birthday Auto Bot v2.0.

Ce fichier démontre l'utilisation de la nouvelle architecture modulaire.

Usage:
    # Mode standard (avec limites)
    python main_example.py

    # Mode dry-run (test sans envoyer)
    LINKEDIN_BOT_DRY_RUN=true python main_example.py

    # Avec config custom
    LINKEDIN_BOT_CONFIG_PATH=./my_config.yaml python main_example.py

    # Debug mode
    LINKEDIN_BOT_DEBUG_LOG_LEVEL=DEBUG python main_example.py
"""

import sys
import logging
from pathlib import Path

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config_manager import ConfigManager
from src.utils.exceptions import LinkedInBotError, is_critical_error
from src.core.database import get_database


def setup_logging(log_level: str = "INFO") -> None:
    """Configure le logging."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/linkedin_bot.log"),
            logging.StreamHandler()
        ]
    )


def main() -> int:
    """
    Point d'entrée principal.

    Returns:
        Code de sortie (0 = succès, 1 = erreur)
    """
    # Charger la configuration
    config_manager = ConfigManager.get_instance()
    config = config_manager.config

    # Setup logging
    Path("logs").mkdir(exist_ok=True)
    setup_logging(config.debug.log_level)
    logger = logging.getLogger(__name__)

    logger.info("═" * 70)
    logger.info("LinkedIn Birthday Auto Bot v2.0")
    logger.info("═" * 70)
    logger.info(f"Mode: {config.bot_mode}")
    logger.info(f"Dry Run: {config.dry_run}")
    logger.info(f"Config: {config_manager._config_path or 'defaults'}")
    logger.info("═" * 70)

    # Exemple d'utilisation : pour l'instant, juste valider la config
    try:
        logger.info("✅ Configuration loaded successfully")

        # Valider la configuration
        if not config_manager.validate():
            logger.error("❌ Configuration validation failed")
            return 1

        # Vérifier l'authentification
        from src.core.auth_manager import validate_auth
        if not validate_auth():
            logger.error("❌ No valid authentication found")
            logger.error("   Please set LINKEDIN_AUTH_STATE or create auth_state.json")
            return 1

        logger.info("✅ Authentication available")

        # Afficher un résumé de la config
        logger.info("\n📋 Configuration Summary:")
        logger.info(f"   Browser headless: {config.browser.headless}")
        logger.info(f"   Weekly limit: {config.messaging_limits.weekly_message_limit}")
        logger.info(f"   Daily window: {config.scheduling.daily_start_hour}h-{config.scheduling.daily_end_hour}h")
        logger.info(f"   Process today: {config.birthday_filter.process_today}")
        logger.info(f"   Process late: {config.birthday_filter.process_late}")
        logger.info(f"   Database: {config.database.enabled}")
        logger.info(f"   Proxy: {config.proxy.enabled}")

        # Test database si activée
        if config.database.enabled:
            try:
                db = get_database(config.database.db_path)
                stats = db.get_statistics(days=30)
                logger.info(f"\n📊 Last 30 days stats:")
                logger.info(f"   Messages sent: {stats['messages']['total']}")
                logger.info(f"   Unique contacts: {stats['contacts']['unique']}")
                logger.info(f"   Profile visits: {stats['profile_visits']['total']}")
            except Exception as e:
                logger.warning(f"⚠️ Database stats not available: {e}")

        logger.info("\n" + "═" * 70)
        logger.info("✅ All systems operational - ready to run bot")
        logger.info("═" * 70)

        # NOTE: Pour exécuter le bot réellement, décommentez ci-dessous
        # et créez une implémentation concrète (BirthdayBot, UnlimitedBot)
        #
        # from src.bots.birthday_bot import BirthdayBot
        #
        # with BirthdayBot(config=config) as bot:
        #     results = bot.run()
        #     logger.info(f"✅ Bot execution completed: {results}")

        return 0

    except LinkedInBotError as e:
        logger.error(f"❌ LinkedIn Bot Error: {e}")
        logger.error(f"   Error Code: {e.error_code.name}")
        logger.error(f"   Recoverable: {e.recoverable}")

        if is_critical_error(e):
            logger.critical("🚨 Critical error detected - immediate intervention required")

        return 1

    except KeyboardInterrupt:
        logger.info("\n⏸️  Bot interrupted by user")
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
