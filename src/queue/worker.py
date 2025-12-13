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
import time

from redis import Redis
from rq import Connection, Queue, Worker
from redis.exceptions import ConnectionError as RedisConnectionError

from ..monitoring.tracing import setup_tracing
from ..utils.logging import get_logger, setup_logging
from ..utils.data_files import initialize_data_files
from ..utils.database_maintenance import start_maintenance_scheduler

# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
QUEUES = ["linkedin-bot"]

# Configuration du logging avec fichier pour Docker
LOG_FILE = os.getenv("LOG_FILE", "/app/logs/linkedin_bot.log")
setup_logging(log_level="INFO", log_file=LOG_FILE)
logger = get_logger("worker")


def start_worker():
    """
    Démarre le worker RQ avec gestion d'erreurs robuste.
    """
    initialize_data_files()
    start_maintenance_scheduler()

    logger.info("starting_worker", redis_host=REDIS_HOST, queues=QUEUES)
    setup_tracing(service_name="linkedin-bot-worker")

    retry_count = 0
    max_retries = 10

    while True:
        try:
            redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)
            # Test connexion
            redis_conn.ping()

            with Connection(redis_conn):
                worker = Worker(map(Queue, QUEUES))
                worker.work()

        except RedisConnectionError:
            retry_count += 1
            wait_time = min(retry_count * 2, 30)
            logger.error(f"Redis connection failed. Retrying in {wait_time}s ({retry_count}/{max_retries})...")
            if retry_count > max_retries:
                logger.critical("Max retries reached for Redis connection. Exiting.")
                sys.exit(1)
            time.sleep(wait_time)

        except Exception as e:
            logger.error("worker_crashed_unexpectedly", error=str(e))
            # On attend un peu avant de redémarrer pour éviter une boucle rapide en cas d'erreur fatale
            time.sleep(5)
            # On ne sort pas, on tente de redémarrer le worker (sauf si c'est une SystemExit)
            # rq.Worker gère déjà les exceptions des jobs, ici on attrape les crashs du processus worker lui-même

if __name__ == "__main__":
    start_worker()
