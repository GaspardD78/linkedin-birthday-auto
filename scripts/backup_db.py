#!/usr/bin/env python3
"""
Script de backup pour la base de données SQLite (WAL-compatible).
Ce script exécute une commande 'VACUUM INTO' pour créer une copie cohérente
de la base de données même pendant son utilisation.

La copie est générée dans le dossier /app/data/backups/ (ou le dossier configuré).
Le fichier généré est nommé 'linkedin_backup_latest.db' pour faciliter la sync Google Drive.
Une copie horodatée est également conservée.
"""

import sqlite3
import os
import shutil
from datetime import datetime
from pathlib import Path
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - backup - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("backup")

def perform_backup(db_path: str, backup_dir: str):
    """
    Exécute le backup SQLite.
    """
    db_file = Path(db_path)
    if not db_file.exists():
        logger.error(f"❌ Database file not found at {db_path}")
        sys.exit(1)

    # Créer le dossier backup s'il n'existe pas
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)

    # Noms des fichiers
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename_timestamped = f"linkedin_backup_{timestamp}.db"
    backup_filename_latest = "linkedin_backup_latest.db"

    target_file_timestamped = backup_path / backup_filename_timestamped
    target_file_latest = backup_path / backup_filename_latest

    logger.info(f"📦 Starting backup of {db_path}...")

    try:
        # Connexion à la DB source
        # Utilisation de VACUUM INTO pour un backup sûr avec WAL
        conn = sqlite3.connect(str(db_file))

        # Exécuter VACUUM INTO
        query = f"VACUUM INTO '{str(target_file_timestamped)}'"
        conn.execute(query)
        conn.close()

        logger.info(f"✅ Timestamped backup created at {target_file_timestamped}")

        # Copier vers 'latest' pour la sync Google Drive
        shutil.copy2(target_file_timestamped, target_file_latest)
        logger.info(f"✅ 'Latest' backup updated at {target_file_latest}")

        # Nettoyage des vieux backups (garder 7 derniers jours)
        cleanup_old_backups(backup_path)

    except sqlite3.Error as e:
        logger.error(f"❌ SQLite error during backup: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error during backup: {e}")
        sys.exit(1)

def cleanup_old_backups(backup_path: Path, days_to_keep: int = 7):
    """
    Supprime les fichiers de backup vieux de plus de N jours.
    """
    now = datetime.now().timestamp()
    cutoff = now - (days_to_keep * 86400)

    deleted_count = 0

    for file in backup_path.glob("linkedin_backup_*.db"):
        if file.name == "linkedin_backup_latest.db":
            continue

        if file.stat().st_mtime < cutoff:
            try:
                file.unlink()
                deleted_count += 1
                logger.debug(f"🗑️ Deleted old backup: {file.name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete {file.name}: {e}")

    if deleted_count > 0:
        logger.info(f"🧹 Cleaned up {deleted_count} old backup files.")

if __name__ == "__main__":
    # Configuration par défaut
    DB_PATH = "/app/data/linkedin.db"
    BACKUP_DIR = "/app/data/backups"

    # Overrides via env vars (compatible docker-compose)
    if os.getenv("DB_PATH"):
        DB_PATH = os.getenv("DB_PATH")

    if os.getenv("BACKUP_DIR"):
        BACKUP_DIR = os.getenv("BACKUP_DIR")

    perform_backup(DB_PATH, BACKUP_DIR)
