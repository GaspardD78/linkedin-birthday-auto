"""
Maintenance automatique de la base de données SQLite.

Ce module implémente un scheduler pour exécuter des tâches de maintenance
périodiques sur la base SQLite, notamment le VACUUM hebdomadaire.
"""

import schedule
import threading
import time
from datetime import datetime

from ..core.database import get_database
from ..utils.logging import get_logger

logger = get_logger(__name__)


def run_vacuum():
    """
    Exécute un VACUUM sur la base de données SQLite.

    Le VACUUM compacte la base de données, libère l'espace disque inutilisé
    et améliore les performances des requêtes.
    """
    try:
        logger.info("🧹 Starting scheduled VACUUM operation...")
        db = get_database()

        # Vérifier si le VACUUM est nécessaire
        if db.should_vacuum():
            start_time = time.time()
            db.vacuum()
            duration = time.time() - start_time

            logger.info(f"✅ VACUUM completed successfully in {duration:.2f}s")
        else:
            logger.info("ℹ️  VACUUM skipped - not needed yet")

    except Exception as e:
        logger.error(f"❌ Scheduled VACUUM failed: {e}", exc_info=True)


def run_scheduler_loop():
    """
    Boucle d'exécution du scheduler.

    Cette fonction tourne en continu dans un thread daemon et exécute
    les tâches planifiées.
    """
    logger.info("📅 Database maintenance scheduler started")

    while True:
        try:
            schedule.run_pending()
            time.sleep(3600)  # Check toutes les heures
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
            time.sleep(3600)  # Continue même en cas d'erreur


def start_maintenance_scheduler():
    """
    Démarre le scheduler de maintenance de la base de données.

    Cette fonction doit être appelée au démarrage de l'application
    (dans le worker ou l'API).

    Le scheduler exécute:
    - VACUUM tous les dimanches à 3h du matin
    """
    # Planifier le VACUUM hebdomadaire
    schedule.every().sunday.at("03:00").do(run_vacuum)

    logger.info("📅 Scheduled maintenance:")
    logger.info("  - VACUUM: Every Sunday at 03:00 AM")

    # Démarrer le thread scheduler (daemon pour qu'il se termine avec l'app)
    scheduler_thread = threading.Thread(
        target=run_scheduler_loop,
        daemon=True,
        name="DatabaseMaintenanceScheduler"
    )
    scheduler_thread.start()

    logger.info("✅ Database maintenance scheduler initialized")
