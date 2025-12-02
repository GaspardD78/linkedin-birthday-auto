#!/usr/bin/env python3
"""
Script d'initialisation des fichiers de données.

Crée les fichiers messages.txt et late_messages.txt avec des templates par défaut
si ils n'existent pas déjà.

Usage:
    python scripts/init_data_files.py
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging import get_logger, setup_logging

setup_logging(log_level="INFO")
logger = get_logger(__name__)


DEFAULT_MESSAGES = """Joyeux anniversaire {name} ! 🎂
Bon anniversaire {name} ! J'espère que tu passes une excellente journée 🎉
Meilleurs vœux pour ton anniversaire {name} ! 🎈"""

DEFAULT_LATE_MESSAGES = """Bon anniversaire (un peu en retard) {name} ! 🎂
Désolé pour le retard {name}, meilleurs vœux pour ton anniversaire ! 🎉
Mieux vaut tard que jamais : bon anniversaire {name} ! 🎈"""


def ensure_data_directory():
    """Crée le répertoire /app/data s'il n'existe pas."""
    data_dir = Path("/app/data")
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Créé répertoire: {data_dir}")
    else:
        logger.info(f"ℹ️  Répertoire existe déjà: {data_dir}")


def create_default_file(file_path: Path, content: str, description: str):
    """Crée un fichier avec contenu par défaut s'il n'existe pas."""
    if not file_path.exists():
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"✅ Créé {description}: {file_path}")
    else:
        logger.info(f"ℹ️  {description} existe déjà: {file_path}")


def init_data_files():
    """Initialise tous les fichiers de données requis."""
    logger.info("=" * 70)
    logger.info("🚀 Initialisation des fichiers de données")
    logger.info("=" * 70)

    # Créer répertoire data
    ensure_data_directory()

    # Créer messages.txt
    messages_file = Path("/app/data/messages.txt")
    create_default_file(messages_file, DEFAULT_MESSAGES, "Messages d'anniversaire")

    # Créer late_messages.txt
    late_messages_file = Path("/app/data/late_messages.txt")
    create_default_file(late_messages_file, DEFAULT_LATE_MESSAGES, "Messages retard")

    logger.info("=" * 70)
    logger.info("✅ Initialisation terminée avec succès")
    logger.info("=" * 70)
    logger.info("")
    logger.info("📝 Prochaines étapes:")
    logger.info("  1. Éditer /app/data/messages.txt pour personnaliser les messages")
    logger.info("  2. Éditer /app/data/late_messages.txt pour messages de retard")
    logger.info("  3. Utiliser {name} dans les messages pour personnalisation")
    logger.info("")


if __name__ == "__main__":
    try:
        init_data_files()
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation: {e}", exc_info=True)
        sys.exit(1)
