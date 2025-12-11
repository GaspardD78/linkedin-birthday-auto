"""
Wrapper synchrone pour le service de notifications.

Permet aux bots (qui sont synchrones) d'envoyer des notifications email
sans avoir à gérer l'asyncio.
"""

import asyncio
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from .notification_service import NotificationService
from ..core.database import Database

logger = logging.getLogger(__name__)

# Executor global pour les opérations async
_executor = ThreadPoolExecutor(max_workers=1)


def _run_async(coro):
    """Exécute une coroutine de manière synchrone."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"Error running async notification: {e}")
        return None
    finally:
        loop.close()


class SyncNotificationService:
    """
    Service de notification synchrone pour les bots.

    Wraps the async NotificationService for use in synchronous bot code.
    """

    def __init__(self, db_path: str = "/app/data/linkedin.db"):
        """
        Initialise le service de notification synchrone.

        Args:
            db_path: Chemin vers la base de données
        """
        self.db = Database(db_path)
        self._service = NotificationService(self.db)

    def is_enabled(self) -> bool:
        """Vérifie si les notifications sont activées."""
        try:
            settings = self._service.get_settings()
            return settings.get("email_enabled", False)
        except Exception:
            return False

    def notify_error(self, error_message: str, error_details: Optional[str] = None) -> bool:
        """
        Envoie une notification d'erreur de manière synchrone.

        Args:
            error_message: Message d'erreur principal
            error_details: Détails supplémentaires

        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            _run_async(self._service.notify_error(error_message, error_details))
            return True
        except Exception as e:
            logger.warning(f"Failed to send error notification: {e}")
            return False

    def notify_success(self, message_count: int) -> bool:
        """
        Envoie une notification de succès de manière synchrone.

        Args:
            message_count: Nombre de messages envoyés

        Returns:
            True si envoyé avec succès, False sinon
        """
        try:
            _run_async(self._service.notify_success(message_count))
            return True
        except Exception as e:
            logger.warning(f"Failed to send success notification: {e}")
            return False

    def notify_bot_start(self) -> bool:
        """Envoie une notification de démarrage du bot."""
        try:
            _run_async(self._service.notify_bot_start())
            return True
        except Exception as e:
            logger.warning(f"Failed to send bot start notification: {e}")
            return False

    def notify_bot_stop(self) -> bool:
        """Envoie une notification d'arrêt du bot."""
        try:
            _run_async(self._service.notify_bot_stop())
            return True
        except Exception as e:
            logger.warning(f"Failed to send bot stop notification: {e}")
            return False

    def notify_cookies_expiry(self) -> bool:
        """Envoie une notification d'expiration des cookies."""
        try:
            _run_async(self._service.notify_cookies_expiry())
            return True
        except Exception as e:
            logger.warning(f"Failed to send cookies expiry notification: {e}")
            return False

    def notify_linkedin_blocked(self, reason: str = "Unknown") -> bool:
        """
        Envoie une notification de blocage LinkedIn.

        Args:
            reason: Raison du blocage (captcha, restriction, etc.)

        Returns:
            True si envoyé avec succès, False sinon
        """
        error_message = f"⚠️ LinkedIn a détecté une activité suspecte: {reason}"
        error_details = (
            "Action requise: Connectez-vous manuellement à LinkedIn pour "
            "vérifier l'état de votre compte et résoudre tout challenge de sécurité."
        )
        return self.notify_error(error_message, error_details)


# Singleton pour accès global
_notification_service: Optional[SyncNotificationService] = None


def get_sync_notification_service(db_path: str = "/app/data/linkedin.db") -> SyncNotificationService:
    """
    Retourne l'instance singleton du service de notification synchrone.

    Args:
        db_path: Chemin vers la base de données

    Returns:
        Instance du service de notification
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = SyncNotificationService(db_path)
    return _notification_service
