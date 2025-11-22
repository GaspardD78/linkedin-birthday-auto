"""
Client Prometheus pour l'export des métriques.
"""

import os
from prometheus_client import start_http_server, write_to_textfile, CollectorRegistry, REGISTRY
from .metrics import (
    MESSAGES_SENT_TOTAL,
    BIRTHDAYS_PROCESSED,
    RUN_DURATION_SECONDS,
    WEEKLY_LIMIT_REMAINING
)
from ..utils.logging import get_logger

logger = get_logger(__name__)

class PrometheusClient:
    """
    Gère l'export des métriques Prometheus.
    """

    def __init__(self, port: int = 9090, metrics_dir: str = None):
        """
        Initialise le client Prometheus.

        Args:
            port: Port pour le serveur HTTP (mode serveur)
            metrics_dir: Dossier pour écrire les fichiers .prom (mode texte)
        """
        self.port = port
        self.metrics_dir = metrics_dir
        self.registry = REGISTRY

    def start_server(self):
        """Démarre le serveur de métriques HTTP."""
        try:
            start_http_server(self.port)
            logger.info("metrics_server_started", port=self.port)
        except Exception as e:
            logger.error("metrics_server_failed", error=str(e))

    def write_metrics(self):
        """Écrit les métriques dans un fichier (pour Node Exporter)."""
        if not self.metrics_dir:
            return

        try:
            path = os.path.join(self.metrics_dir, "linkedin_bot.prom")
            write_to_textfile(path, self.registry)
            logger.debug("metrics_written_to_file", path=path)
        except Exception as e:
            logger.error("metrics_write_failed", error=str(e))
