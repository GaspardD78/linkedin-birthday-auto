"""
Worker RQ pour traiter les tâches en arrière-plan.

Ce module initialise et lance un Worker RQ (Redis Queue) qui écoute sur la file 'linkedin-bot'.
Il est responsable de l'exécution asynchrone des tâches lourdes (bots Playwright)
pour ne pas bloquer l'API principale.

Architecture:
- Connecté à Redis (défini par REDIS_HOST/PORT).
- Consomme les jobs de la queue 'linkedin-bot'.
- Chaque job est exécuté dans un processus forké (par défaut dans RQ sous Unix),
  ce qui garantit une isolation de la mémoire parfaite pour Playwright.

Usage:
    python -m src.queue.worker
"""

import os
import sys

from redis import Redis
from rq import Connection, Queue, Worker

from ..monitoring.tracing import setup_tracing
from ..utils.logging import get_logger, setup_logging

# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
QUEUES = ["linkedin-bot"]

# Configuration du logging avec fichier pour Docker
# Le worker écrit dans le même fichier de log que l'API (géré par rotation externe ou Docker)
LOG_FILE = os.getenv("LOG_FILE", "/app/logs/linkedin_bot.log")
setup_logging(log_level="INFO", log_file=LOG_FILE)
logger = get_logger("worker")


# 🚀 Refactored: use shared data_files module (no more duplication)
from ..utils.data_files import initialize_data_files


def start_worker():
    """
    Démarre le worker RQ.

    Cette fonction :
    1. Initialise les fichiers de données (messages).
    2. Configure le tracing et le logging.
    3. Établit la connexion Redis.
    4. Lance la boucle principale du Worker qui attend et traite les jobs.
    """
    # Initialiser les fichiers de données avant de démarrer
    initialize_data_files()

    # 🚀 Démarrer le scheduler de maintenance de la base de données
    from ..utils.database_maintenance import start_maintenance_scheduler
    start_maintenance_scheduler()

    logger.info("starting_worker", redis_host=REDIS_HOST, queues=QUEUES)

    # Initialisation du tracing (OpenTelemetry) si activé
    setup_tracing(service_name="linkedin-bot-worker")

    try:
        redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)

        with Connection(redis_conn):
            # Le Worker écoute sur les queues définies.
            # RQ gère le cycle de vie des jobs (succès, échec, retry).
            worker = Worker(map(Queue, QUEUES))
            worker.work()

    except Exception as e:
        logger.error("worker_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    start_worker()
