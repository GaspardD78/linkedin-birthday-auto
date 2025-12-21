import shutil
import logging
from pathlib import Path
from datetime import datetime
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

def main():
    # 1. Backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_root = Path('backups') / f'backup_{timestamp}'

    # List of files to backup
    files_to_backup = [
        Path('data/bot.db'),
        Path('data/linkedin.db'),
        Path('.env.pi4.example'),
        Path('config/config.yaml')
    ]

    files_backed_up = []
    created_backup_dir = False

    for file_path in files_to_backup:
        if file_path.exists():
            if not created_backup_dir:
                backup_root.mkdir(parents=True, exist_ok=True)
                created_backup_dir = True

            # Maintain directory structure in backup
            dest = backup_root / file_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest)
            files_backed_up.append(str(file_path))

    if files_backed_up:
        logger.info(f"✓ Backup créé: {', '.join(files_backed_up)}")
    else:
        logger.info("ℹ Aucun fichier critique trouvé pour le backup.")

    # 2. Structure V2
    v2_root = Path('app_v2')
    directories = ['core', 'db', 'moteur', 'api', 'tests']

    for d in directories:
        dir_path = v2_root / d
        dir_path.mkdir(parents=True, exist_ok=True)
        # Create __init__.py in subdirectories to ensure git tracking
        (dir_path / '__init__.py').touch()

    (v2_root / '__init__.py').touch()

    logger.info("✓ Structure V2 prête")

if __name__ == '__main__':
    main()
