"""
Bot LinkedIn pour anniversaires avec limites (mode standard).

Ce bot traite UNIQUEMENT les anniversaires du jour et respecte les limites
hebdomadaires configurées pour éviter la détection LinkedIn.
"""

from datetime import datetime
import random
import time
from typing import Any

from ..core.base_bot import BaseLinkedInBot
from ..core.database import get_database
from ..monitoring.metrics import RUN_DURATION_SECONDS
from ..utils.exceptions import DailyLimitReachedError, MessageSendError, WeeklyLimitReachedError
from ..utils.logging import get_logger

logger = get_logger(__name__)


class BirthdayBot(BaseLinkedInBot):
    """
    Bot LinkedIn pour anniversaires en mode standard.

    Caractéristiques :
    - Traite UNIQUEMENT les anniversaires du jour
    - Ignore les anniversaires en retard
    - Respecte les limites hebdomadaires/quotidiennes
    - Idéal pour usage quotidien automatisé via cron/GitHub Actions

    Configuration recommandée :
    ```yaml
    bot_mode: "standard"
    birthday_filter:
      process_today: true
      process_late: false
    messaging_limits:
      weekly_message_limit: 80
      daily_message_limit: null
    ```

    Exemples:
        >>> from src.bots.birthday_bot import BirthdayBot
        >>> from src.config import get_config
        >>>
        >>> config = get_config()
        >>> with BirthdayBot(config=config) as bot:
        >>>     results = bot.run()
        >>>     print(f"Messages envoyés : {results['messages_sent']}")
    """

    def __init__(self, *args, **kwargs):
        """Initialise le BirthdayBot."""
        super().__init__(*args, **kwargs)
        self.db = None

        logger.info("BirthdayBot initialized - Processing TODAY's birthdays only")

    def run(self) -> dict[str, Any]:
        return super().run()

    def _run_internal(self) -> dict[str, Any]:
        """
        Exécute le bot pour envoyer des messages d'anniversaire.

        Workflow:
        1. Vérification des limites (hebdomadaire/quotidienne)
        2. Navigation vers la page anniversaires
        3. Extraction et classification des contacts
        4. Filtrage (garde seulement "today")
        5. Envoi des messages avec délais humanisés
        6. Enregistrement en base de données

        Returns:
            Dict contenant les statistiques d'exécution :
            {
                'messages_sent': int,
                'contacts_processed': int,
                'birthdays_today': int,
                'birthdays_late_ignored': int,
                'errors': int,
                'duration_seconds': float
            }

        Raises:
            WeeklyLimitReachedError: Si la limite hebdomadaire est atteinte
            DailyLimitReachedError: Si la limite quotidienne est atteinte
            SessionExpiredError: Si la session LinkedIn a expiré
        """
        start_time = time.time()

        logger.info("═" * 70)
        logger.info("🎂 Starting BirthdayBot (Standard Mode)")
        logger.info("═" * 70)
        logger.info(
            "configuration",
            dry_run=self.config.dry_run,
            weekly_limit=self.config.messaging_limits.weekly_message_limit,
            mode="TODAY's birthdays only",
        )
        logger.info("═" * 70)

        # Initialiser la database si activée
        if self.config.database.enabled:
            try:
                self.db = get_database(self.config.database.db_path)
            except Exception as e:
                logger.warning(f"Database unavailable: {e}", exc_info=True)
                self.db = None

        # Vérifier les limites avant de commencer
        self._check_limits()

        # Vérifier la connexion LinkedIn
        if not self.check_login_status():
            return self._build_error_result("Login verification failed")

        # Obtenir tous les contacts d'anniversaire
        birthdays = self.get_birthday_contacts()

        total_today = len(birthdays["today"])
        total_late = len(birthdays["late"])

        logger.info(f"📊 Found {total_today} birthdays today")
        logger.info(f"⏭️  Ignoring {total_late} late birthdays (standard mode)")

        # Vérifier qu'il y a des anniversaires à traiter
        if total_today == 0:
            logger.info("ℹ️  No birthdays today - nothing to do")
            return self._build_result(
                messages_sent=0,
                contacts_processed=0,
                birthdays_today=0,
                birthdays_late_ignored=total_late,
                messages_ignored=0,
                duration_seconds=time.time() - start_time,
            )

        # Calculer combien on peut envoyer (respecter les limites)
        max_to_send = self._calculate_max_messages_to_send(total_today)

        if max_to_send == 0:
            logger.warning("⚠️  Cannot send any messages due to limits")
            return self._build_result(
                messages_sent=0,
                contacts_processed=0,
                birthdays_today=total_today,
                birthdays_late_ignored=total_late,
                messages_ignored=total_today,  # Tous les anniversaires sont ignorés
                duration_seconds=time.time() - start_time,
            )

        logger.info(f"✅ Will process {max_to_send}/{total_today} birthdays (limit)")

        # Traiter les anniversaires du jour
        contacts_to_process = birthdays["today"][:max_to_send]

        # Comptabiliser les messages ignorés (contacts non traités à cause des limites)
        messages_ignored = total_today - len(contacts_to_process)
        if messages_ignored > 0:
            logger.info(f"⚠️  {messages_ignored} birthdays ignored due to limits")

        for i, contact in enumerate(contacts_to_process):
            try:
                # Envoyer le message
                success = self.send_birthday_message(contact, is_late=False, days_late=0)

                if success:
                    self.stats["messages_sent"] += 1

                    # Simulation d'activité humaine occasionnelle
                    if random.random() < 0.3:
                        self.simulate_human_activity()

                    # Pause entre messages (sauf le dernier)
                    if i < len(contacts_to_process) - 1:
                        self._wait_between_messages()

                self.stats["contacts_processed"] += 1

            except MessageSendError as e:
                logger.error(f"Failed to send message: {e}")
                self.stats["errors"] += 1
                continue

        # Résumé final
        duration = time.time() - start_time
        RUN_DURATION_SECONDS.observe(duration)

        logger.info("")
        logger.info("═" * 70)
        logger.info("✅ BirthdayBot execution completed")
        logger.info("═" * 70)
        logger.info(
            "execution_stats",
            messages_sent=f"{self.stats['messages_sent']}/{max_to_send}",
            contacts_processed=self.stats["contacts_processed"],
            errors=self.stats["errors"],
            duration=f"{duration:.1f}s",
        )
        logger.info("═" * 70)

        return self._build_result(
            messages_sent=self.stats["messages_sent"],
            contacts_processed=self.stats["contacts_processed"],
            birthdays_today=total_today,
            birthdays_late_ignored=total_late,
            messages_ignored=messages_ignored,
            duration_seconds=duration,
        )

    def _check_limits(self) -> None:
        """
        Vérifie que les limites hebdomadaires et quotidiennes ne sont pas atteintes.

        Raises:
            WeeklyLimitReachedError: Si limite hebdomadaire atteinte
            DailyLimitReachedError: Si limite quotidienne atteinte
        """
        if not self.db:
            logger.warning("⚠️  Database unavailable - skipping limit checks")
            return

        # Vérifier limite hebdomadaire
        weekly_count = self.db.get_weekly_message_count()
        weekly_limit = self.config.messaging_limits.weekly_message_limit

        logger.info(f"📊 Weekly messages: {weekly_count}/{weekly_limit}")

        if weekly_count >= weekly_limit:
            raise WeeklyLimitReachedError(current=weekly_count, limit=weekly_limit)

        # Vérifier limite quotidienne si configurée
        daily_limit = self.config.messaging_limits.daily_message_limit
        if daily_limit:
            daily_count = self.db.get_daily_message_count()
            logger.info(f"📊 Daily messages: {daily_count}/{daily_limit}")

            if daily_count >= daily_limit:
                raise DailyLimitReachedError(current=daily_count, limit=daily_limit)

    def _calculate_max_messages_to_send(self, contacts_count: int) -> int:
        """
        Calcule le nombre maximum de messages à envoyer.

        Prend en compte :
        - Limite hebdomadaire restante
        - Limite quotidienne restante
        - Limite par exécution (max_messages_per_run)
        - Nombre de contacts disponibles

        Args:
            contacts_count: Nombre total de contacts à traiter

        Returns:
            Nombre maximum de messages à envoyer
        """
        max_to_send = contacts_count

        # Limite par exécution
        if self.config.messaging_limits.max_messages_per_run:
            max_to_send = min(max_to_send, self.config.messaging_limits.max_messages_per_run)

        # Limite hebdomadaire
        if self.db:
            weekly_count = self.db.get_weekly_message_count()
            weekly_limit = self.config.messaging_limits.weekly_message_limit
            weekly_remaining = max(0, weekly_limit - weekly_count)
            max_to_send = min(max_to_send, weekly_remaining)

            # Limite quotidienne
            daily_limit = self.config.messaging_limits.daily_message_limit
            if daily_limit:
                daily_count = self.db.get_daily_message_count()
                daily_remaining = max(0, daily_limit - daily_count)
                max_to_send = min(max_to_send, daily_remaining)

        return max_to_send

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
                self.config.delays.min_delay_seconds, self.config.delays.max_delay_seconds
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
        birthdays_late_ignored: int,
        messages_ignored: int,
        duration_seconds: float,
    ) -> dict[str, Any]:
        """Construit le dictionnaire de résultats."""
        return {
            "success": True,
            "bot_mode": "standard",
            "messages_sent": messages_sent,
            "contacts_processed": contacts_processed,
            "birthdays_today": birthdays_today,
            "birthdays_late_ignored": birthdays_late_ignored,
            "messages_ignored": messages_ignored,
            "errors": self.stats["errors"],
            "duration_seconds": round(duration_seconds, 2),
            "dry_run": self.config.dry_run,
            "timestamp": datetime.now().isoformat(),
        }

    def _build_error_result(self, error_message: str) -> dict[str, Any]:
        """Construit un résultat d'erreur."""
        return {
            "success": False,
            "bot_mode": "standard",
            "error": error_message,
            "messages_sent": 0,
            "contacts_processed": 0,
            "timestamp": datetime.now().isoformat(),
        }


# Helper function pour usage simplifié
def run_birthday_bot(config=None, dry_run: bool = False) -> dict[str, Any]:
    """
    Fonction helper pour exécuter le BirthdayBot facilement.

    Args:
        config: Configuration (ou None pour config par défaut)
        dry_run: Override du mode dry-run

    Returns:
        Résultats de l'exécution

    Exemples:
        >>> from src.bots.birthday_bot import run_birthday_bot
        >>>
        >>> # Mode dry-run
        >>> results = run_birthday_bot(dry_run=True)
        >>> print(f"Sent {results['messages_sent']} messages")
        >>>
        >>> # Mode production
        >>> results = run_birthday_bot()
    """
    from ..config.config_manager import get_config

    if config is None:
        config = get_config()

    # FIX: Créer une COPIE de la config pour éviter de polluer le singleton
    config = config.model_copy(deep=True)

    if dry_run:
        config.dry_run = True

    with BirthdayBot(config=config) as bot:
        return bot.run()
