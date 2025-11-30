"""
Configuration du logging structuré pour le bot LinkedIn.

Ce module utilise structlog pour générer des logs au format JSON,
facilitant l'intégration avec des systèmes comme Loki.
"""

import logging
import os
import sys
from pathlib import Path

import structlog


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """
    Configure le logging structuré.

    Args:
        log_level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
        log_file: Chemin vers un fichier de log optionnel
    """

    # Configuration de base de logging standard
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        # CORRECTION v2.1 : On force le nom de fichier exact pour le Dashboard
        # On ne rajoute plus le suffixe du service (worker, api, etc.)

        # Créer le répertoire parent si nécessaire
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(format="%(message)s", level=level, handlers=handlers)

    # Processeurs structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # En local : logs colorés. Avec fichier : JSON.
    if log_file:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Retourne un logger configuré.

    Args:
        name: Nom du logger (optionnel)

    Returns:
        Un logger structlog
    """
    return structlog.get_logger(name)
