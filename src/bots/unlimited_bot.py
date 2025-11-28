"""
Bot LinkedIn pour anniversaires sans limites (mode unlimited).

Ce bot traite à la fois les anniversaires du jour ET en retard,
sans limite hebdomadaire (utilise seulement des délais entre messages).
"""

import logging
import random
import time
from typing import Dict, Any, List
from datetime import datetime

from ..core.base_bot import BaseLinkedInBot
from ..core.database import get_database
from ..utils.exceptions import MessageSendError

logger = logging.getLogger(__name__)


class UnlimitedBirthdayBot(BaseLinkedInBot):
    """
    Bot LinkedIn pour anniversaires en mode illimité.

    Caractéristiques :
    - Traite les anniversaires du jour ET en retard (configurable)
    - Pas de limite hebdomadaire
    - Utilise des délais entre messages pour éviter la détection
    - Idéal pour rattraper un backlog d'anniversaires

    ⚠️  AVERTISSEMENT ⚠️
    Ce mode peut envoyer beaucoup de messages d'un coup.
    LinkedIn peut détecter un comportement anormal.
    Utilisez avec prudence et configurez des délais suffisants.

    Configuration recommandée :
    ```yaml
    bot_mode: "unlimited"
    birthday_filter:
      process_today: true
      process_late: true
      max_days_late: 10
    delays:
      min_delay_seconds: 180  # 3 minutes minimum
      max_delay_seconds: 420  # 7 minutes maximum
    ```

    Exemples:
        >>> from src.bots.unlimited_bot import UnlimitedBirthdayBot
        >>> from src.config import get_config
        >>>
        >>> config = get_config()
        >>> config.bot_mode = "unlimited"
        >>> config.birthday_filter.max_days_late = 10
        >>>
        >>> with UnlimitedBirthdayBot(config=config) as bot:
        >>>     results = bot.run()
        >>>     print(f"Messages envoyés : {results['messages_sent']}")
    """

    def __init__(self, *args, **kwargs):
        """Initialise l'UnlimitedBirthdayBot."""
        super().__init__(*args, **kwargs)
        self.db = None

        logger.info(
            "UnlimitedBirthdayBot initialized - "
            "Processing TODAY + LATE birthdays (NO limits)"
        )

    def run(self) -> Dict[str, Any]:
        return super().run()

    def _run_internal(self) -> Dict[str, Any]:
        """
        Exécute le bot pour envoyer des messages d'anniversaire (unlimited).

        Workflow:
        1. Navigation vers la page anniversaires
        2. Extraction et classification des contacts
        3. Filtrage selon configuration (today + late jusqu'à max_days_late)
        4. Envoi des messages avec délais humanisés
        5. Enregistrement en base de données

        Returns:
            Dict contenant les statistiques d'exécution :
            {
                'messages_sent': int,
                'contacts_processed': int,
                'birthdays_today': int,
                'birthdays_late': int,
                'errors': int,
                'duration_seconds': float
            }

        Raises:
            SessionExpiredError: Si la session LinkedIn a expiré
        """
        start_time = time.time()

        logger.info("═" * 70)
        logger.info("🎂 Starting UnlimitedBirthdayBot (Unlimited Mode)")
        logger.info("═" * 70)
        logger.info(f"Dry Run: {self.config.dry_run}")
        logger.info(f"Process Today: {self.config.birthday_filter.process_today}")
        logger.info(f"Process Late: {self.config.birthday_filter.process_late}")
        logger.info(f"Max Days Late: {self.config.birthday_filter.max_days_late}")
        logger.info(f"Delays: {self.config.delays.min_delay_seconds}-{self.config.delays.max_delay_seconds}s")
        logger.info("⚠️  WARNING: NO weekly limit - could send many messages!")
        logger.info("═" * 70)

        # Initialiser la database si activée
        if self.config.database.enabled:
            try:
                self.db = get_database(self.config.database.db_path)
            except Exception as e:
                logger.warning(f"Database unavailable: {e}")
                self.db = None

        # Vérifier la connexion LinkedIn
        if not self.check_login_status():
            return self._build_error_result("Login verification failed")

        # Obtenir tous les contacts d'anniversaire
        birthdays = self.get_birthday_contacts()

        total_today = len(birthdays['today'])
        total_late = len(birthdays['late'])

        logger.info(f"📊 Found {total_today} birthdays today")
        logger.info(f"📊 Found {total_late} late birthdays")

        # Construire la liste des contacts à traiter
        contacts_to_process = []

        # Ajouter les anniversaires du jour
        if self.config.birthday_filter.process_today:
            for contact in birthdays['today']:
                contacts_to_process.append((contact, False, 0))
            logger.info(f"✅ Will process {total_today} birthdays from today")
        else:
            logger.info(f"⏭️  Skipping {total_today} birthdays from today (disabled)")

        # Ajouter les anniversaires en retard
        if self.config.birthday_filter.process_late:
            late_count = 0
            for contact, days_late in birthdays['late']:
                # Respecter max_days_late
                if days_late <= self.config.birthday_filter.max_days_late:
                    contacts_to_process.append((contact, True, days_late))
                    late_count += 1
            logger.info(f"✅ Will process {late_count} late birthdays (up to {self.config.birthday_filter.max_days_late} days)")
        else:
            logger.info(f"⏭️  Skipping {total_late} late birthdays (disabled)")

        total_to_process = len(contacts_to_process)

        if total_to_process == 0:
            logger.info("ℹ️  No birthdays to process")
            return self._build_result(
                messages_sent=0,
                contacts_processed=0,
                birthdays_today=total_today,
                birthdays_late=total_late,
                duration_seconds=time.time() - start_time
            )

        logger.info(f"")
        logger.info(f"🚀 Processing {total_to_process} total contacts...")
        logger.info(f"⏱️  Estimated duration: {self._estimate_duration(total_to_process)}")
        logger.info("")

        # Traiter tous les contacts
        for i, (contact, is_late, days_late) in enumerate(contacts_to_process, 1):
            try:
                logger.info(f"[{i}/{total_to_process}] Processing contact...")

                # Envoyer le message
                success = self.send_birthday_message(
                    contact,
                    is_late=is_late,
                    days_late=days_late
                )

                if success:
                    self.stats['messages_sent'] += 1

                    # Simulation d'activité humaine occasionnelle
                    if random.random() < 0.3:
                        self.simulate_human_activity()

                    # Pause entre messages (sauf le dernier)
                    if i < total_to_process:
                        self._wait_between_messages()

                self.stats['contacts_processed'] += 1

            except MessageSendError as e:
                logger.error(f"Failed to send message: {e}")
                self.stats['errors'] += 1
                continue

        # Résumé final
        duration = time.time() - start_time

        logger.info("")
        logger.info("═" * 70)
        logger.info("✅ UnlimitedBirthdayBot execution completed")
        logger.info("═" * 70)
        logger.info(f"Messages sent: {self.stats['messages_sent']}/{total_to_process}")
        logger.info(f"Contacts processed: {self.stats['contacts_processed']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Duration: {self._format_duration(duration)}")
        logger.info("═" * 70)

        return self._build_result(
            messages_sent=self.stats['messages_sent'],
            contacts_processed=self.stats['contacts_processed'],
            birthdays_today=total_today,
            birthdays_late=total_late,
            duration_seconds=duration
        )

    def _estimate_duration(self, contact_count: int) -> str:
        """
        Estime la durée totale d'exécution.

        Args:
            contact_count: Nombre de contacts à traiter

        Returns:
            String formatée (ex: "1h 30m")
        """
        avg_delay = (self.config.delays.min_delay_seconds + self.config.delays.max_delay_seconds) / 2

        if self.config.dry_run:
            avg_delay = 3  # 3 secondes en dry-run

        total_seconds = contact_count * avg_delay
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    def _format_duration(self, seconds: float) -> str:
        """
        Formate une durée en secondes.

        Args:
            seconds: Durée en secondes

        Returns:
            String formatée (ex: "1h 30m 45s")
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    def _wait_between_messages(self) -> None:
        """Attend un délai humanisé entre deux messages."""
        if self.config.dry_run:
            # Délai court en mode dry-run
            delay = random.randint(2, 5)
            logger.info(f"⏸️  Pause (dry-run): {delay}s")
            time.sleep(delay)
        else:
            # Délai normal configuré
            delay = random.randint(
                self.config.delays.min_delay_seconds,
                self.config.delays.max_delay_seconds
            )
            minutes = delay // 60
            seconds = delay % 60
            logger.info(f"⏸️  Pause: {minutes}m {seconds}s")
            time.sleep(delay)

    def _build_result(
        self,
        messages_sent: int,
        contacts_processed: int,
        birthdays_today: int,
        birthdays_late: int,
        duration_seconds: float
    ) -> Dict[str, Any]:
        """Construit le dictionnaire de résultats."""
        return {
            'success': True,
            'bot_mode': 'unlimited',
            'messages_sent': messages_sent,
            'contacts_processed': contacts_processed,
            'birthdays_today': birthdays_today,
            'birthdays_late': birthdays_late,
            'errors': self.stats['errors'],
            'duration_seconds': round(duration_seconds, 2),
            'dry_run': self.config.dry_run,
            'timestamp': datetime.now().isoformat()
        }

    def _build_error_result(self, error_message: str) -> Dict[str, Any]:
        """Construit un résultat d'erreur."""
        return {
            'success': False,
            'bot_mode': 'unlimited',
            'error': error_message,
            'messages_sent': 0,
            'contacts_processed': 0,
            'timestamp': datetime.now().isoformat()
        }


# Helper function pour usage simplifié
def run_unlimited_bot(config=None, dry_run: bool = False, max_days_late: int = 10) -> Dict[str, Any]:
    """
    Fonction helper pour exécuter l'UnlimitedBirthdayBot facilement.

    Args:
        config: Configuration (ou None pour config par défaut)
        dry_run: Override du mode dry-run
        max_days_late: Nombre maximum de jours de retard à traiter

    Returns:
        Résultats de l'exécution

    Exemples:
        >>> from src.bots.unlimited_bot import run_unlimited_bot
        >>>
        >>> # Mode dry-run avec max 7 jours de retard
        >>> results = run_unlimited_bot(dry_run=True, max_days_late=7)
        >>> print(f"Sent {results['messages_sent']} messages")
        >>>
        >>> # Mode production avec max 10 jours
        >>> results = run_unlimited_bot(max_days_late=10)
    """
    from ..config import get_config

    if config is None:
        config = get_config()

    if dry_run:
        config.dry_run = True

    config.bot_mode = "unlimited"
    config.birthday_filter.process_today = True
    config.birthday_filter.process_late = True
    config.birthday_filter.max_days_late = max_days_late

    with UnlimitedBirthdayBot(config=config) as bot:
        return bot.run()
