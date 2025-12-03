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


def initialize_data_files():
    """
    Initialise les fichiers de données (messages.txt, late_messages.txt).

    Cette fonction est appelée au démarrage du worker pour s'assurer que les fichiers
    de messages existent dans /app/data/ avant que le bot ne tente de les lire.
    Elle copie les fichiers personnalisés depuis la racine du projet si disponibles,
    ou crée des fichiers avec des templates par défaut.
    """
    try:
        # Import local pour éviter les dépendances circulaires
        from pathlib import Path
        import shutil

        # Chemins des fichiers sources (dans l'image Docker)
        source_messages = Path("/app/messages.txt")
        source_late_messages = Path("/app/late_messages.txt")

        # Chemins de destination
        dest_messages = Path("/app/data/messages.txt")
        dest_late_messages = Path("/app/data/late_messages.txt")

        # Créer le répertoire data s'il n'existe pas
        dest_messages.parent.mkdir(parents=True, exist_ok=True)

        # Templates par défaut (utilisés uniquement en fallback)
        default_messages = """Joyeux anniversaire {name} ! 🎂
Bon anniversaire {name} ! J'espère que tu passes une excellente journée 🎉
Meilleurs vœux pour ton anniversaire {name} ! 🎈"""

        default_late_messages = """Bon anniversaire (un peu en retard) {name} ! 🎂
Désolé pour le retard {name}, meilleurs vœux pour ton anniversaire ! 🎉
Mieux vaut tard que jamais : bon anniversaire {name} ! 🎈"""

        # Initialiser messages.txt
        if not dest_messages.exists():
            if source_messages.exists():
                shutil.copy2(source_messages, dest_messages)
                logger.info(f"✅ Copié messages personnalisés depuis {source_messages}")
            else:
                dest_messages.write_text(default_messages, encoding="utf-8")
                logger.info("✅ Créé messages.txt avec template par défaut")

        # Initialiser late_messages.txt
        if not dest_late_messages.exists():
            if source_late_messages.exists():
                shutil.copy2(source_late_messages, dest_late_messages)
                logger.info(f"✅ Copié messages de retard personnalisés depuis {source_late_messages}")
            else:
                dest_late_messages.write_text(default_late_messages, encoding="utf-8")
                logger.info("✅ Créé late_messages.txt avec template par défaut")

    except Exception as e:
        logger.warning(f"⚠️  Erreur lors de l'initialisation des fichiers de données: {e}")


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
