#!/usr/bin/env python3
"""
Script d'initialisation des fichiers de données.

Crée les fichiers messages.txt et late_messages.txt avec des templates par défaut
si ils n'existent pas déjà.

Usage:
    python scripts/init_data_files.py
"""

import shutil
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging import get_logger, setup_logging

setup_logging(log_level="INFO")
logger = get_logger(__name__)


# Templates par défaut (utilisés uniquement en fallback)
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


def copy_or_create_file(source_path: Path, dest_path: Path, fallback_content: str, description: str):
    """Copie un fichier source vers destination, ou crée avec contenu fallback s'il n'existe pas."""
    # Ne rien faire si le fichier de destination existe déjà
    if dest_path.exists():
        logger.info(f"ℹ️  {description} existe déjà: {dest_path}")
        return

    # Essayer de copier depuis le fichier source (dans l'image Docker)
    if source_path.exists():
        try:
            shutil.copy2(source_path, dest_path)
            logger.info(f"✅ Copié {description} personnalisé depuis {source_path} vers {dest_path}")
            return
        except Exception as e:
            logger.warning(f"⚠️  Impossible de copier {source_path}: {e}")

    # Fallback: créer avec contenu par défaut
    dest_path.write_text(fallback_content, encoding="utf-8")
    logger.info(f"✅ Créé {description} avec template par défaut: {dest_path}")


def init_data_files():
    """Initialise tous les fichiers de données requis."""
    logger.info("=" * 70)
    logger.info("🚀 Initialisation des fichiers de données")
    logger.info("=" * 70)

    # Créer répertoire data
    ensure_data_directory()

    # Chemins des fichiers sources (dans l'image Docker, copiés depuis la racine du repo)
    source_messages = Path("/app/messages.txt")
    source_late_messages = Path("/app/late_messages.txt")

    # Chemins des fichiers de destination
    dest_messages = Path("/app/data/messages.txt")
    dest_late_messages = Path("/app/data/late_messages.txt")

    # Copier ou créer messages.txt
    copy_or_create_file(
        source_messages,
        dest_messages,
        DEFAULT_MESSAGES,
        "Messages d'anniversaire"
    )

    # Copier ou créer late_messages.txt
    copy_or_create_file(
        source_late_messages,
        dest_late_messages,
        DEFAULT_LATE_MESSAGES,
        "Messages de retard"
    )

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
