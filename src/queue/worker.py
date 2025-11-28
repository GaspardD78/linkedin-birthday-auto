"""
Worker RQ pour traiter les tâches en arrière-plan.
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
LOG_FILE = os.getenv("LOG_FILE", "/app/logs/linkedin_bot.log")
setup_logging(log_level="INFO", log_file=LOG_FILE)
logger = get_logger("worker")


def start_worker():
    """Démarre le worker RQ."""
    logger.info("starting_worker", redis_host=REDIS_HOST, queues=QUEUES)

    setup_tracing(service_name="linkedin-bot-worker")

    try:
        redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)

        with Connection(redis_conn):
            worker = Worker(map(Queue, QUEUES))
            worker.work()

    except Exception as e:
        logger.error("worker_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    start_worker()
