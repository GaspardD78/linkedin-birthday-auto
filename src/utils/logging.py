"""
Configuration du logging structuré pour le bot LinkedIn.

Ce module utilise structlog pour générer des logs au format JSON,
facilitant l'intégration avec des systèmes comme Loki.
"""

import sys
import logging
import structlog
from typing import Any, Dict

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
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        format="%(message)s",
        level=level,
        handlers=handlers
    )

    # Processeurs structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Si on est en local (développement), on veut peut-être des logs colorés
    # Sinon (production/JSON), on utilise JSONRenderer
    # Pour simplifier ici, on va utiliser JSONRenderer si un fichier est spécifié,
    # ou ConsoleRenderer sinon.

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
