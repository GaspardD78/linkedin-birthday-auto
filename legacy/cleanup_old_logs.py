#!/usr/bin/env python3
"""
Script pour nettoyer les anciens fichiers de log obsolètes
"""

import os
import sys

# Liste des fichiers de log valides (actuellement utilisés)
VALID_LOG_FILES = [
    'birthday_wisher.log',
    'visit_profiles.log',
    'dashboard.log'
]

def cleanup_old_logs(dry_run=False):
    """
    Nettoie les anciens fichiers de log qui ne sont plus utilisés

    Args:
        dry_run: Si True, affiche seulement ce qui serait supprimé sans le faire
    """
    log_dir = 'logs'

    if not os.path.exists(log_dir):
        print(f"Le répertoire '{log_dir}' n'existe pas")
        return

    # Lister tous les fichiers .log
    all_log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]

    if not all_log_files:
        print(f"Aucun fichier de log trouvé dans '{log_dir}'")
        return

    print(f"Fichiers de log trouvés: {len(all_log_files)}")
    print(f"Fichiers de log valides: {VALID_LOG_FILES}\n")

    # Identifier les fichiers obsolètes
    obsolete_files = [f for f in all_log_files if f not in VALID_LOG_FILES]

    if not obsolete_files:
        print("✅ Aucun fichier de log obsolète trouvé")
        return

    print(f"Fichiers de log obsolètes trouvés: {len(obsolete_files)}")

    for file in obsolete_files:
        file_path = os.path.join(log_dir, file)
        file_size = os.path.getsize(file_path)

        if dry_run:
            print(f"  [DRY RUN] Supprimerait: {file} ({file_size} bytes)")
        else:
            try:
                os.remove(file_path)
                print(f"  ✅ Supprimé: {file} ({file_size} bytes)")
            except Exception as e:
                print(f"  ❌ Erreur lors de la suppression de {file}: {e}")

    if dry_run:
        print("\n⚠️  Mode DRY RUN - Aucun fichier n'a été supprimé")
        print("Exécutez sans --dry-run pour supprimer les fichiers")
    else:
        print(f"\n✅ Nettoyage terminé - {len(obsolete_files)} fichier(s) supprimé(s)")

if __name__ == "__main__":
    # Vérifier si --dry-run est passé en argument
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("=== Mode DRY RUN ===\n")

    cleanup_old_logs(dry_run=dry_run)
