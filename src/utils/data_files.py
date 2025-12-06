"""
Utilitaires pour l'initialisation des fichiers de données.

Ce module centralise la logique d'initialisation des fichiers de configuration
et messages, évitant la duplication de code entre app.py et worker.py.
"""

import shutil
from pathlib import Path
from typing import Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)


def initialize_data_files(
    data_dir: Path = Path("/app/data"),
    config_dir: Path = Path("/app/config"),
    base_dir: Path = Path("/app")
) -> None:
    """
    Initialise les fichiers de données (messages.txt, late_messages.txt).

    Cette fonction copie les fichiers template depuis le répertoire base
    vers le répertoire de données s'ils n'existent pas déjà.

    Args:
        data_dir: Répertoire de destination des fichiers de données
        config_dir: Répertoire de configuration (non utilisé actuellement)
        base_dir: Répertoire de base contenant les templates

    Raises:
        Exception: Les erreurs sont loggées mais n'interrompent pas l'exécution
    """
    try:
        # Créer les répertoires s'ils n'existent pas
        data_dir.mkdir(parents=True, exist_ok=True)
        config_dir.mkdir(parents=True, exist_ok=True)

        # Paths des fichiers
        dest_messages = data_dir / "messages.txt"
        dest_late_messages = data_dir / "late_messages.txt"

        source_messages = base_dir / "messages.txt"
        source_late_messages = base_dir / "late_messages.txt"

        # Templates par défaut si les fichiers source n'existent pas
        default_messages = """Joyeux anniversaire {name} ! 🎉
J'espère que cette journée te sera mémorable.
Profite bien de ta journée !"""

        default_late_messages = """Salut {name} ! 🎂
J'espère que tu as passé un excellent anniversaire il y a {days_late} jour(s) !
Meilleurs vœux avec un peu de retard ! 😊"""

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
