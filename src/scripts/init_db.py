"""
Script d'initialisation de la base de données.
Utilisé par le setup.sh pour garantir que les tables sont créées.
"""
import sys
import os
import logging

# Ensure the project root is in sys.path
sys.path.append(os.getcwd())

from src.core.database import get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    logger.info("Initializing database...")
    try:
        # data/ directory should be mounted or present
        db_path = "data/linkedin.db"

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database
        db = get_database(db_path)

        # Explicitly call init_database (though __init__ calls it, being explicit is safe)
        db.init_database()

        logger.info("Database initialized successfully.")
        return 0
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(init_db())
