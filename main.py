#!/usr/bin/env python3
"""
Point d'entrée principal pour LinkedIn Birthday Auto Bot v2.0.

Ce fichier unifie tous les modes d'exécution du bot :
- Mode bot direct (standard ou unlimited)
- Mode API REST (FastAPI)
- Mode validation (config check)

Usage:
    # Mode bot standard (anniversaires du jour uniquement)
    python main.py bot

    # Mode bot unlimited (aujourd'hui + retard)
    python main.py bot --mode unlimited --max-days-late 10

    # Mode dry-run (test sans envoyer)
    python main.py bot --dry-run

    # Mode API REST
    python main.py api

    # Validation seule
    python main.py validate

    # Avec config custom
    python main.py bot --config ./my_config.yaml

    # Mode debug
    python main.py bot --debug

    # Aide complète
    python main.py --help
"""

import argparse
import logging
import os
import secrets
from pathlib import Path
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config_manager import ConfigManager
from src.core.database import get_database
from src.utils.exceptions import LinkedInBotError, is_critical_error


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Configure le logging.

    Args:
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Chemin du fichier de log (optionnel)
    """
    Path("logs").mkdir(exist_ok=True)

    handlers = [logging.StreamHandler()]

    # Use RotatingFileHandler to prevent SD card saturation
    # 10MB per file, max 3 files = 30MB total
    if log_file:
        handlers.append(RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=3
        ))
    else:
        handlers.append(RotatingFileHandler(
            "logs/linkedin_bot.log", maxBytes=10*1024*1024, backupCount=3
        ))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def ensure_api_key() -> None:
    """
    Checks for API_KEY in .env, generates if missing or default.
    Hardening Step 1.2: Prevent default keys in production.
    """
    logger = logging.getLogger("security_hardening")
    env_path = Path(".env")
    current_key = os.getenv("API_KEY")

    # List of known weak defaults to reject
    weak_defaults = ["internal_secret_key", "CHANGE_ME", "default"]

    needs_new_key = False

    if not current_key:
        logger.warning("⚠️ API_KEY is missing from environment.")
        needs_new_key = True
    elif current_key in weak_defaults:
        logger.warning(f"⚠️ API_KEY is set to insecure default: '{current_key}'")
        needs_new_key = True

    if needs_new_key:
        new_key = secrets.token_hex(32)
        logger.warning("🔐 Generating new secure API_KEY...")

        # Read existing .env content if it exists
        lines = []
        if env_path.exists():
            try:
                with open(env_path, "r") as f:
                    lines = f.readlines()
            except Exception as e:
                logger.error(f"Failed to read .env file: {e}")

        # Remove existing API_KEY line if present
        lines = [line for line in lines if not line.strip().startswith("API_KEY=")]

        # Ensure previous line ends with newline if list is not empty
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"

        # Append new key
        lines.append(f"API_KEY={new_key}\n")

        # Write back to .env
        try:
            with open(env_path, "w") as f:
                f.writelines(lines)

            # Update current process environment so immediate usage works
            os.environ["API_KEY"] = new_key

            logger.warning("═" * 60)
            logger.warning("🛑 SECURITY ALERT: NEW API KEY GENERATED")
            logger.warning("═" * 60)
            logger.warning(f"New API_KEY has been written to {env_path.absolute()}")
            # Mask the key in logs (show first 8 and last 4 chars)
            masked_key = f"{new_key[:8]}...{new_key[-4:]}"
            logger.warning(f"KEY: {masked_key}")
            logger.warning("👉 Please update your Dashboard configuration or .env file with this key.")
            logger.warning("═" * 60)

        except Exception as e:
            logger.error(f"❌ Failed to write new API_KEY to .env: {e}")
            logger.error(f"   You MUST set API_KEY={new_key} manually.")


def ensure_jwt_secret() -> None:
    """
    Validates JWT_SECRET is set and has minimum strength.
    Hardening Step 1.3: Prevent weak session keys.
    """
    logger = logging.getLogger("security_hardening")

    jwt_secret = os.getenv("JWT_SECRET")

    if not jwt_secret:
        logger.error("❌ JWT_SECRET is missing from environment")
        new_secret = secrets.token_hex(32)  # 64 chars
        logger.error(f"   Generate with: JWT_SECRET={new_secret}")
        raise RuntimeError(
            "JWT_SECRET environment variable is REQUIRED but not set. "
            f"Please set it to: JWT_SECRET={new_secret}"
        )

    if len(jwt_secret) < 32:
        logger.error(f"❌ JWT_SECRET is too weak ({len(jwt_secret)} chars, need minimum 32)")
        raise RuntimeError(
            f"JWT_SECRET must be at least 32 characters long (currently {len(jwt_secret)} chars)"
        )

    logger.info(f"✅ JWT_SECRET validated (length={len(jwt_secret)} chars, sufficient)")


def print_banner(config) -> None:
    """Affiche la bannière de démarrage."""
    logger = logging.getLogger(__name__)

    logger.info("═" * 70)
    logger.info("🎂 LinkedIn Birthday Auto Bot v2.0")
    logger.info("═" * 70)
    logger.info(f"Mode: {config.bot_mode}")
    logger.info(f"Dry Run: {config.dry_run}")
    logger.info("═" * 70)


def print_config_summary(config) -> None:
    """Affiche un résumé de la configuration."""
    logger = logging.getLogger(__name__)

    logger.info("\n📋 Configuration Summary:")
    logger.info(f"   Browser headless: {config.browser.headless}")
    logger.info(f"   Weekly limit: {config.messaging_limits.weekly_message_limit}")
    logger.info(
        f"   Daily window: {config.scheduling.daily_start_hour}h-{config.scheduling.daily_end_hour}h"
    )
    logger.info(f"   Process today: {config.birthday_filter.process_today}")
    logger.info(f"   Process late: {config.birthday_filter.process_late}")

    if config.birthday_filter.process_late:
        logger.info(f"   Max days late: {config.birthday_filter.max_days_late}")

    logger.info(f"   Database: {config.database.enabled}")
    logger.info(f"   Proxy: {config.proxy.enabled}")

    if config.delays:
        logger.info(
            f"   Delays: {config.delays.min_delay_seconds}-{config.delays.max_delay_seconds}s"
        )


def print_database_stats(config) -> None:
    """Affiche les statistiques de la database."""
    logger = logging.getLogger(__name__)

    if not config.database.enabled:
        return

    try:
        db = get_database(config.database.db_path)
        stats = db.get_statistics(days=30)

        logger.info("\n📊 Last 30 days stats:")
        logger.info(f"   Messages sent: {stats['messages']['total']}")
        logger.info(f"   Unique contacts: {stats['contacts']['unique']}")
        logger.info(f"   Profile visits: {stats['profile_visits']['total']}")

        # Afficher les limites hebdomadaires
        weekly_count = db.get_weekly_message_count()
        weekly_limit = config.messaging_limits.weekly_message_limit
        logger.info(f"   This week: {weekly_count}/{weekly_limit} messages")

    except Exception as e:
        logger.warning(f"⚠️ Database stats not available: {e}")


def validate_command(args) -> int:
    """
    Valide la configuration.

    Args:
        args: Arguments de la ligne de commande

    Returns:
        Code de sortie (0 = succès, 1 = erreur)
    """
    logger = logging.getLogger(__name__)

    try:
        # Charger la configuration
        config_manager = ConfigManager.get_instance(config_path=args.config)
        config = config_manager.config

        print_banner(config)

        # Valider la configuration
        if not config_manager.validate():
            logger.error("❌ Configuration validation failed")
            return 1

        logger.info("✅ Configuration is valid")

        # Vérifier l'authentification
        from src.core.auth_manager import validate_auth

        if not validate_auth():
            logger.warning("⚠️ No valid authentication found")
            logger.warning("   Set LINKEDIN_AUTH_STATE or create auth_state.json")
        else:
            logger.info("✅ Authentication available")

        print_config_summary(config)
        print_database_stats(config)

        logger.info("\n" + "═" * 70)
        logger.info("✅ All validations passed - ready to run bot")
        logger.info("═" * 70)

        return 0

    except Exception as e:
        logger.exception(f"❌ Validation failed: {e}")
        return 1


def bot_command(args) -> int:
    """
    Exécute le bot.

    Args:
        args: Arguments de la ligne de commande

    Returns:
        Code de sortie (0 = succès, 1 = erreur)
    """
    logger = logging.getLogger(__name__)

    try:
        # Charger la configuration
        config_manager = ConfigManager.get_instance(config_path=args.config)
        config = config_manager.config

        # Appliquer les overrides CLI
        if args.dry_run:
            config.dry_run = True

        if args.mode:
            config.bot_mode = args.mode

        if args.max_days_late is not None:
            config.birthday_filter.max_days_late = args.max_days_late

        if args.headless is not None:
            config.browser.headless = args.headless

        print_banner(config)

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

        print_config_summary(config)
        print_database_stats(config)

        logger.info("\n" + "═" * 70)
        logger.info(f"🚀 Starting bot in {config.bot_mode} mode...")
        logger.info("═" * 70 + "\n")

        # Sélectionner le bon bot
        if config.bot_mode == "standard":
            from src.bots.birthday_bot import BirthdayBot

            bot_class = BirthdayBot
        elif config.bot_mode == "unlimited":
            from src.bots.unlimited_bot import UnlimitedBirthdayBot

            bot_class = UnlimitedBirthdayBot
        else:
            logger.error(f"❌ Unknown bot mode: {config.bot_mode}")
            return 1

        # Exécuter le bot
        with bot_class(config=config) as bot:
            results = bot.run()

        # Afficher les résultats
        logger.info("\n" + "═" * 70)
        logger.info("📊 EXECUTION SUMMARY")
        logger.info("═" * 70)
        logger.info(f"Success: {results.get('success', False)}")
        logger.info(f"Bot Mode: {results.get('bot_mode', 'unknown')}")
        logger.info(f"Messages Sent: {results.get('messages_sent', 0)}")
        logger.info(f"Contacts Processed: {results.get('contacts_processed', 0)}")
        logger.info(f"Errors: {results.get('errors', 0)}")
        logger.info(f"Duration: {results.get('duration_seconds', 0):.1f}s")
        logger.info(f"Dry Run: {results.get('dry_run', False)}")
        logger.info("═" * 70)

        if not results.get("success", False):
            logger.error(f"❌ Bot execution failed: {results.get('error', 'Unknown error')}")
            return 1

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


def visit_command(args) -> int:
    """
    Exécute le bot de visite de profils.

    Args:
        args: Arguments de la ligne de commande

    Returns:
        Code de sortie (0 = succès, 1 = erreur)
    """
    logger = logging.getLogger(__name__)

    try:
        # Charger la configuration
        config_manager = ConfigManager.get_instance(config_path=args.config)
        config = config_manager.config

        # Appliquer les overrides CLI
        if args.dry_run:
            config.dry_run = True

        if args.headless is not None:
            config.browser.headless = args.headless

        # Override keywords et location si fournis
        if args.keywords:
            config.visitor.keywords = args.keywords

        if args.location:
            config.visitor.location = args.location

        if args.profiles_per_run is not None:
            config.visitor.limits.profiles_per_run = args.profiles_per_run

        logger.info("═" * 70)
        logger.info("🔍 LinkedIn Profile Visitor Bot v2.0")
        logger.info("═" * 70)
        logger.info(f"Keywords: {config.visitor.keywords}")
        logger.info(f"Location: {config.visitor.location}")
        logger.info(f"Profiles per run: {config.visitor.limits.profiles_per_run}")
        logger.info(f"Dry Run: {config.dry_run}")
        logger.info("═" * 70)

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

        logger.info("\n" + "═" * 70)
        logger.info("🚀 Starting VisitorBot...")
        logger.info("═" * 70 + "\n")

        # Exécuter le bot
        from src.bots.visitor_bot import VisitorBot

        with VisitorBot(config=config) as bot:
            results = bot.run()

        # Afficher les résultats
        logger.info("\n" + "═" * 70)
        logger.info("📊 EXECUTION SUMMARY")
        logger.info("═" * 70)
        logger.info(f"Success: {results.get('success', False)}")
        logger.info(f"Profiles Visited: {results.get('profiles_visited', 0)}")
        logger.info(f"Profiles Attempted: {results.get('profiles_attempted', 0)}")
        logger.info(f"Profiles Failed: {results.get('profiles_failed', 0)}")
        logger.info(f"Success Rate: {results.get('success_rate', 0):.1f}%")
        logger.info(f"Pages Scraped: {results.get('pages_scraped', 0)}")
        logger.info(f"Duration: {results.get('duration_seconds', 0):.1f}s")
        logger.info(f"Dry Run: {results.get('dry_run', False)}")
        logger.info("═" * 70)

        if not results.get("success", False):
            logger.error(f"❌ Bot execution failed: {results.get('error', 'Unknown error')}")
            return 1

        return 0

    except LinkedInBotError as e:
        logger.error(f"❌ LinkedIn Bot Error: {e}")
        logger.error(f"   Error Code: {e.error_code}")
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


def api_command(args) -> int:
    """
    Démarre le serveur API REST.

    Args:
        args: Arguments de la ligne de commande

    Returns:
        Code de sortie (0 = succès, 1 = erreur)
    """
    logger = logging.getLogger(__name__)

    try:
        logger.info("═" * 70)
        logger.info("🌐 LinkedIn Birthday Bot - API Mode")
        logger.info("═" * 70)
        logger.info(f"Host: {args.host}")
        logger.info(f"Port: {args.port}")
        logger.info(f"Reload: {args.reload}")
        logger.info("═" * 70)

        # Import et lancement de l'API
        import uvicorn

        uvicorn.run(
            "src.api.app:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level.lower(),
        )

        return 0

    except ImportError:
        logger.error("❌ FastAPI/uvicorn not installed")
        logger.error("   Install with: pip install fastapi uvicorn")
        return 1

    except Exception as e:
        logger.exception(f"❌ API server error: {e}")
        return 1


def main() -> int:
    """
    Point d'entrée principal avec CLI complète.

    Returns:
        Code de sortie (0 = succès, 1 = erreur)
    """
    parser = argparse.ArgumentParser(
        description="LinkedIn Birthday Auto Bot v2.0 - Automate birthday messages on LinkedIn",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run standard bot (today's birthdays only)
  python main.py bot

  # Run unlimited bot (today + late birthdays)
  python main.py bot --mode unlimited --max-days-late 10

  # Dry-run mode (test without sending)
  python main.py bot --dry-run

  # Run profile visitor bot
  python main.py visit --keywords python developer --location France

  # Profile visitor in dry-run mode
  python main.py visit --dry-run --profiles-per-run 10

  # Start API server
  python main.py api

  # Validate configuration
  python main.py validate

  # With custom config file
  python main.py bot --config ./my_config.yaml

For more information, see: https://github.com/GaspardD78/linkedin-birthday-auto
        """,
    )

    # Arguments globaux
    parser.add_argument(
        "--config", type=str, default=None, help="Path to config file (default: config/config.yaml)"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Path to log file (default: logs/linkedin_bot.log)",
    )

    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode (equivalent to --log-level DEBUG)"
    )

    # Sous-commandes
    subparsers = parser.add_subparsers(dest="command", help="Command to execute", required=True)

    # Commande: validate
    validate_parser = subparsers.add_parser(
        "validate", help="Validate configuration and authentication"
    )

    # Commande: bot
    bot_parser = subparsers.add_parser("bot", help="Run the birthday bot")

    bot_parser.add_argument(
        "--mode",
        type=str,
        choices=["standard", "unlimited"],
        default=None,
        help="Bot mode (default: from config file)",
    )

    bot_parser.add_argument(
        "--dry-run", action="store_true", help="Test mode - do not send real messages"
    )

    bot_parser.add_argument(
        "--max-days-late",
        type=int,
        default=None,
        help="Maximum days late for unlimited mode (default: from config)",
    )

    bot_parser.add_argument(
        "--headless",
        type=lambda x: x.lower() in ["true", "1", "yes"],
        default=None,
        help="Run browser in headless mode (true/false)",
    )

    # Commande: visit
    visit_parser = subparsers.add_parser("visit", help="Run the profile visitor bot")

    visit_parser.add_argument(
        "--dry-run", action="store_true", help="Test mode - do not visit real profiles"
    )

    visit_parser.add_argument(
        "--keywords",
        nargs="+",
        type=str,
        default=None,
        help="Keywords for profile search (e.g., --keywords python developer)",
    )

    visit_parser.add_argument(
        "--location",
        type=str,
        default=None,
        help='Location for profile search (e.g., --location "France")',
    )

    visit_parser.add_argument(
        "--profiles-per-run",
        type=int,
        default=None,
        help="Number of profiles to visit per run (default: from config)",
    )

    visit_parser.add_argument(
        "--headless",
        type=lambda x: x.lower() in ["true", "1", "yes"],
        default=None,
        help="Run browser in headless mode (true/false)",
    )

    # Commande: api
    api_parser = subparsers.add_parser("api", help="Start the REST API server")

    api_parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="API server host (default: 0.0.0.0)"
    )

    api_parser.add_argument(
        "--port", type=int, default=8000, help="API server port (default: 8000)"
    )

    api_parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )

    # Parse arguments
    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.debug else args.log_level
    setup_logging(log_level, args.log_file)

    # Ensure Security Hardening
    ensure_api_key()
    ensure_jwt_secret()

    # Exécuter la commande appropriée
    if args.command == "validate":
        return validate_command(args)
    elif args.command == "bot":
        return bot_command(args)
    elif args.command == "visit":
        return visit_command(args)
    elif args.command == "api":
        return api_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
