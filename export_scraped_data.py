#!/usr/bin/env python3
"""
Script pour exporter les données scrapées des profils LinkedIn vers un fichier CSV.

Usage:
    python export_scraped_data.py [output_file.csv]

Si aucun fichier n'est spécifié, le fichier sera nommé 'scraped_profiles_YYYY-MM-DD.csv'
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from src.core.database import get_database
from src.utils.logging import get_logger

logger = get_logger(__name__)


def export_scraped_profiles(output_path: str = None) -> None:
    """
    Exporte tous les profils scrapés vers un fichier CSV.

    Args:
        output_path: Chemin du fichier CSV de sortie (optionnel)
    """
    try:
        # Initialiser la base de données
        db = get_database()

        # Générer un nom de fichier par défaut si nécessaire
        if not output_path:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            output_path = f"scraped_profiles_{timestamp}.csv"

        # Exporter les données
        logger.info(f"Exporting scraped profiles to {output_path}...")
        result_path = db.export_scraped_data_to_csv(output_path)

        # Statistiques
        scraped_profiles = db.get_all_scraped_profiles()
        count = len(scraped_profiles)

        print("\n" + "=" * 70)
        print("✅ Export successful!")
        print("=" * 70)
        print(f"📊 Total profiles exported: {count}")
        print(f"📁 Output file: {result_path}")
        print("=" * 70)

        if count > 0:
            print("\nSample data (first 3 profiles):")
            for i, profile in enumerate(scraped_profiles[:3], 1):
                print(
                    f"  {i}. {profile['full_name']} - {profile['current_company']} "
                    f"({profile['relationship_level']})"
                )
            print()

    except Exception as e:
        logger.error(f"Failed to export scraped profiles: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def main():
    """Point d'entrée principal du script."""
    parser = argparse.ArgumentParser(
        description="Export scraped LinkedIn profiles to CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export with default filename (scraped_profiles_YYYY-MM-DD.csv)
  python export_scraped_data.py

  # Export to a specific file
  python export_scraped_data.py my_profiles.csv

  # Export to a specific directory
  python export_scraped_data.py exports/profiles.csv
        """,
    )

    parser.add_argument(
        "output_file",
        nargs="?",
        default=None,
        help="Output CSV file path (default: scraped_profiles_YYYY-MM-DD.csv)",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics only (don't export)",
    )

    args = parser.parse_args()

    # Mode statistiques uniquement
    if args.stats:
        try:
            db = get_database()
            scraped_profiles = db.get_all_scraped_profiles()
            count = len(scraped_profiles)

            print("\n" + "=" * 70)
            print("📊 Scraped Profiles Statistics")
            print("=" * 70)
            print(f"Total profiles in database: {count}")

            if count > 0:
                # Statistiques par entreprise
                companies = {}
                for profile in scraped_profiles:
                    company = profile.get("current_company", "Unknown")
                    companies[company] = companies.get(company, 0) + 1

                print("\nTop 5 companies:")
                for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True)[
                    :5
                ]:
                    print(f"  - {company}: {count} profiles")

                # Statistiques par niveau de relation
                relationships = {}
                for profile in scraped_profiles:
                    rel = profile.get("relationship_level", "Unknown")
                    relationships[rel] = relationships.get(rel, 0) + 1

                print("\nRelationship levels:")
                for rel, count in sorted(relationships.items(), key=lambda x: x[1], reverse=True):
                    print(f"  - {rel}: {count} profiles")

            print("=" * 70)
            print()

        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    else:
        # Mode export
        export_scraped_profiles(args.output_file)


if __name__ == "__main__":
    main()
