"""
JSON Stats Writer - Enregistre les statistiques d'exécution du bot en JSON.

Remplace Prometheus/Grafana pour une solution légère sur RPi4.
Les stats sont écrites dans un fichier JSON facilement consultable.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)


class StatsWriter:
    """
    Enregistre les statistiques d'exécution du bot dans un fichier JSON.

    Exemple de structure:
    {
        "last_run": "2025-12-20T14:30:00",
        "status": "success",
        "messages_sent": 5,
        "messages_failed": 0,
        "birthdays_today": 3,
        "birthdays_late": 2,
        "duration_seconds": 45,
        "next_run": "2025-12-21T09:00:00",
        "errors": []
    }
    """

    def __init__(self, stats_dir: str = None):
        """
        Initialize StatsWriter.

        Args:
            stats_dir: Répertoire pour stocker le fichier JSON stats.
                      Par défaut: ./logs
        """
        if stats_dir is None:
            stats_dir = "./logs"

        self.stats_dir = Path(stats_dir)
        self.stats_file = self.stats_dir / "bot_stats.json"

        # Créer le répertoire s'il n'existe pas
        self.stats_dir.mkdir(parents=True, exist_ok=True)

        # Initialiser le fichier s'il n'existe pas
        if not self.stats_file.exists():
            self._init_stats_file()

    def _init_stats_file(self) -> None:
        """Initialise le fichier de stats avec une structure vide."""
        initial_stats = {
            "last_run": None,
            "status": "pending",
            "messages_sent": 0,
            "messages_failed": 0,
            "birthdays_today": 0,
            "birthdays_late": 0,
            "duration_seconds": 0,
            "next_run": None,
            "errors": [],
            "created_at": datetime.now().isoformat()
        }
        self._write_stats(initial_stats)

    def update_run(
        self,
        status: str,
        messages_sent: int = 0,
        messages_failed: int = 0,
        birthdays_today: int = 0,
        birthdays_late: int = 0,
        duration_seconds: float = 0,
        next_run: Optional[str] = None,
        errors: Optional[list[str]] = None,
    ) -> None:
        """
        Met à jour les statistiques après une exécution du bot.

        Args:
            status: 'success', 'partial', 'failed'
            messages_sent: Nombre de messages envoyés
            messages_failed: Nombre de messages échoués
            birthdays_today: Anniversaires trouvés aujourd'hui
            birthdays_late: Anniversaires tardifs trouvés
            duration_seconds: Durée d'exécution en secondes
            next_run: Prochaine exécution (ISO format string)
            errors: Liste des erreurs rencontrées
        """
        try:
            stats = self._read_stats()

            stats.update({
                "last_run": datetime.now().isoformat(),
                "status": status,
                "messages_sent": messages_sent,
                "messages_failed": messages_failed,
                "birthdays_today": birthdays_today,
                "birthdays_late": birthdays_late,
                "duration_seconds": round(duration_seconds, 2),
                "next_run": next_run,
                "errors": errors or [],
                "updated_at": datetime.now().isoformat()
            })

            self._write_stats(stats)
            logger.info(f"Stats updated: {status} - {messages_sent} messages sent in {duration_seconds:.1f}s")

        except Exception as e:
            logger.error(f"Failed to update stats: {e}", exc_info=True)

    def record_error(self, error_message: str) -> None:
        """
        Enregistre une erreur dans les stats.

        Args:
            error_message: Message d'erreur à enregistrer
        """
        try:
            stats = self._read_stats()
            errors = stats.get("errors", [])

            # Ajouter l'erreur avec timestamp
            error_entry = {
                "timestamp": datetime.now().isoformat(),
                "message": str(error_message)
            }

            # Garder seulement les 10 dernières erreurs
            errors.append(error_entry)
            if len(errors) > 10:
                errors = errors[-10:]

            stats["errors"] = errors
            stats["updated_at"] = datetime.now().isoformat()

            self._write_stats(stats)

        except Exception as e:
            logger.error(f"Failed to record error in stats: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Récupère les stats actuelles."""
        try:
            return self._read_stats()
        except Exception as e:
            logger.error(f"Failed to read stats: {e}")
            return {}

    def _read_stats(self) -> dict[str, Any]:
        """Lit le fichier de stats en JSON."""
        if not self.stats_file.exists():
            self._init_stats_file()

        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Stats file corrupted, reinitializing...")
            self._init_stats_file()
            return self._read_stats()

    def _write_stats(self, stats: dict[str, Any]) -> None:
        """Écrit les stats dans le fichier JSON."""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write stats file: {e}")
