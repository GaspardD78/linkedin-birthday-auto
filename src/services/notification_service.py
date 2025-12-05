"""
Service de notifications par email.

Gère l'envoi de notifications par email via SMTP pour les événements importants du bot.
Supporte les configurations SMTP standard (Gmail, Outlook, etc.)
"""

import logging
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
import aiosmtplib
from email_validator import validate_email, EmailNotValidError

from ..core.database import Database

logger = logging.getLogger(__name__)


class NotificationService:
    """Service de gestion des notifications par email."""

    def __init__(self, db: Database):
        """
        Initialise le service de notifications.

        Args:
            db: Instance de la base de données
        """
        self.db = db
        self._smtp_config: Optional[Dict[str, Any]] = None

    def get_settings(self) -> Dict[str, Any]:
        """
        Récupère les paramètres de notification depuis la base de données.

        Returns:
            Dictionnaire avec les paramètres de notification
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notification_settings ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()

            if row:
                return {
                    "email_enabled": bool(row["email_enabled"]),
                    "email_address": row["email_address"],
                    "notify_on_error": bool(row["notify_on_error"]),
                    "notify_on_success": bool(row["notify_on_success"]),
                    "notify_on_bot_start": bool(row["notify_on_bot_start"]),
                    "notify_on_bot_stop": bool(row["notify_on_bot_stop"]),
                    "notify_on_cookies_expiry": bool(row["notify_on_cookies_expiry"]),
                }

        # Retourner les valeurs par défaut si aucune configuration n'existe
        return {
            "email_enabled": False,
            "email_address": "",
            "notify_on_error": True,
            "notify_on_success": False,
            "notify_on_bot_start": False,
            "notify_on_bot_stop": False,
            "notify_on_cookies_expiry": True,
        }

    def update_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Met à jour les paramètres de notification dans la base de données.

        Args:
            settings: Dictionnaire avec les nouveaux paramètres

        Returns:
            Dictionnaire avec les paramètres mis à jour
        """
        now = datetime.now().isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Vérifier si une configuration existe
            cursor.execute("SELECT id FROM notification_settings LIMIT 1")
            existing = cursor.fetchone()

            if existing:
                # Mettre à jour
                cursor.execute(
                    """
                    UPDATE notification_settings
                    SET email_enabled = ?,
                        email_address = ?,
                        notify_on_error = ?,
                        notify_on_success = ?,
                        notify_on_bot_start = ?,
                        notify_on_bot_stop = ?,
                        notify_on_cookies_expiry = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        settings.get("email_enabled", False),
                        settings.get("email_address", ""),
                        settings.get("notify_on_error", True),
                        settings.get("notify_on_success", False),
                        settings.get("notify_on_bot_start", False),
                        settings.get("notify_on_bot_stop", False),
                        settings.get("notify_on_cookies_expiry", True),
                        now,
                        existing["id"],
                    ),
                )
            else:
                # Créer
                cursor.execute(
                    """
                    INSERT INTO notification_settings (
                        email_enabled, email_address, notify_on_error, notify_on_success,
                        notify_on_bot_start, notify_on_bot_stop, notify_on_cookies_expiry,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        settings.get("email_enabled", False),
                        settings.get("email_address", ""),
                        settings.get("notify_on_error", True),
                        settings.get("notify_on_success", False),
                        settings.get("notify_on_bot_start", False),
                        settings.get("notify_on_bot_stop", False),
                        settings.get("notify_on_cookies_expiry", True),
                        now,
                        now,
                    ),
                )

        return self.get_settings()

    def _load_smtp_config(self) -> Dict[str, Any]:
        """
        Charge la configuration SMTP depuis les variables d'environnement.

        Returns:
            Dictionnaire avec la configuration SMTP
        """
        return {
            "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
            "port": int(os.getenv("SMTP_PORT", "587")),
            "username": os.getenv("SMTP_USER"),
            "password": os.getenv("SMTP_PASSWORD"),
            "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            "from_email": os.getenv("SMTP_FROM_EMAIL"),
        }

    def _validate_smtp_config(self, config: Dict[str, Any]) -> bool:
        """
        Valide la configuration SMTP.

        Args:
            config: Configuration SMTP à valider

        Returns:
            True si la configuration est valide, False sinon
        """
        required_fields = ["host", "port", "username", "password", "from_email"]
        return all(config.get(field) for field in required_fields)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        event_type: str = "test",
    ) -> Dict[str, Any]:
        """
        Envoie un email via SMTP.

        Args:
            to_email: Adresse email du destinataire
            subject: Sujet de l'email
            body: Corps de l'email (texte brut)
            event_type: Type d'événement (pour les logs)

        Returns:
            Dictionnaire avec le résultat de l'envoi
        """
        now = datetime.now().isoformat()

        # Charger la configuration SMTP
        smtp_config = self._load_smtp_config()

        # Valider la configuration
        if not self._validate_smtp_config(smtp_config):
            error_msg = "Configuration SMTP incomplète. Vérifiez les variables d'environnement."
            logger.error(error_msg)
            self._log_notification(event_type, to_email, subject, body, "failed", error_msg)
            return {
                "success": False,
                "error": error_msg,
            }

        # Valider l'email du destinataire
        try:
            validate_email(to_email, check_deliverability=False)
        except EmailNotValidError as e:
            error_msg = f"Adresse email invalide: {str(e)}"
            logger.error(error_msg)
            self._log_notification(event_type, to_email, subject, body, "failed", error_msg)
            return {
                "success": False,
                "error": error_msg,
            }

        # Créer le message
        message = MIMEMultipart()
        message["From"] = smtp_config["from_email"]
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain", "utf-8"))

        try:
            # Envoyer l'email
            if smtp_config["use_tls"]:
                await aiosmtplib.send(
                    message,
                    hostname=smtp_config["host"],
                    port=smtp_config["port"],
                    username=smtp_config["username"],
                    password=smtp_config["password"],
                    start_tls=True,
                )
            else:
                await aiosmtplib.send(
                    message,
                    hostname=smtp_config["host"],
                    port=smtp_config["port"],
                    username=smtp_config["username"],
                    password=smtp_config["password"],
                )

            logger.info(f"Email envoyé avec succès à {to_email}")
            self._log_notification(event_type, to_email, subject, body, "sent", None)

            return {
                "success": True,
                "message": "Email envoyé avec succès",
            }

        except Exception as e:
            error_msg = f"Erreur lors de l'envoi de l'email: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._log_notification(event_type, to_email, subject, body, "failed", error_msg)

            return {
                "success": False,
                "error": error_msg,
            }

    def _log_notification(
        self,
        event_type: str,
        recipient_email: str,
        subject: str,
        body: str,
        status: str,
        error_message: Optional[str] = None,
    ):
        """
        Enregistre l'envoi de notification dans la base de données.

        Args:
            event_type: Type d'événement
            recipient_email: Email du destinataire
            subject: Sujet de l'email
            body: Corps de l'email
            status: Statut (sent, failed, pending)
            error_message: Message d'erreur si échec
        """
        now = datetime.now().isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO notification_logs (
                    event_type, recipient_email, subject, body, status,
                    sent_at, error_message, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    recipient_email,
                    subject,
                    body,
                    status,
                    now if status == "sent" else None,
                    error_message,
                    now,
                ),
            )

    async def send_test_notification(self, to_email: str) -> Dict[str, Any]:
        """
        Envoie une notification de test.

        Args:
            to_email: Adresse email du destinataire

        Returns:
            Dictionnaire avec le résultat de l'envoi
        """
        subject = "🔔 Test de notification - LinkedIn Birthday Auto"
        body = """Bonjour,

Ceci est un email de test du système de notifications de LinkedIn Birthday Auto.

Si vous recevez ce message, votre configuration SMTP est correcte et les notifications fonctionnent.

Cordialement,
LinkedIn Birthday Auto
"""

        return await self.send_email(to_email, subject, body, event_type="test")

    async def notify_error(self, error_message: str, error_details: Optional[str] = None):
        """
        Envoie une notification d'erreur si activée.

        Args:
            error_message: Message d'erreur
            error_details: Détails supplémentaires de l'erreur
        """
        settings = self.get_settings()

        if not settings["email_enabled"] or not settings["notify_on_error"]:
            return

        if not settings["email_address"]:
            logger.warning("Notification d'erreur activée mais aucune adresse email configurée")
            return

        subject = "⚠️ Erreur LinkedIn Birthday Auto"
        body = f"""Une erreur s'est produite dans LinkedIn Birthday Auto:

Erreur: {error_message}

{f"Détails: {error_details}" if error_details else ""}

Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        await self.send_email(
            settings["email_address"],
            subject,
            body,
            event_type="error",
        )

    async def notify_success(self, message_count: int):
        """
        Envoie une notification de succès si activée.

        Args:
            message_count: Nombre de messages envoyés
        """
        settings = self.get_settings()

        if not settings["email_enabled"] or not settings["notify_on_success"]:
            return

        if not settings["email_address"]:
            return

        subject = "✅ Exécution réussie - LinkedIn Birthday Auto"
        body = f"""L'exécution de LinkedIn Birthday Auto s'est terminée avec succès.

Nombre de messages envoyés: {message_count}
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        await self.send_email(
            settings["email_address"],
            subject,
            body,
            event_type="success",
        )

    async def notify_bot_start(self):
        """Envoie une notification de démarrage du bot si activée."""
        settings = self.get_settings()

        if not settings["email_enabled"] or not settings["notify_on_bot_start"]:
            return

        if not settings["email_address"]:
            return

        subject = "🚀 Démarrage du bot - LinkedIn Birthday Auto"
        body = f"""Le bot LinkedIn Birthday Auto a démarré.

Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        await self.send_email(
            settings["email_address"],
            subject,
            body,
            event_type="bot_start",
        )

    async def notify_bot_stop(self):
        """Envoie une notification d'arrêt du bot si activée."""
        settings = self.get_settings()

        if not settings["email_enabled"] or not settings["notify_on_bot_stop"]:
            return

        if not settings["email_address"]:
            return

        subject = "🛑 Arrêt du bot - LinkedIn Birthday Auto"
        body = f"""Le bot LinkedIn Birthday Auto s'est arrêté.

Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        await self.send_email(
            settings["email_address"],
            subject,
            body,
            event_type="bot_stop",
        )

    async def notify_cookies_expiry(self):
        """Envoie une notification d'expiration des cookies si activée."""
        settings = self.get_settings()

        if not settings["email_enabled"] or not settings["notify_on_cookies_expiry"]:
            return

        if not settings["email_address"]:
            return

        subject = "🔑 Cookies LinkedIn expirés - LinkedIn Birthday Auto"
        body = f"""Les cookies de session LinkedIn ont expiré.

Vous devez vous reconnecter à LinkedIn pour continuer à utiliser le bot.

Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        await self.send_email(
            settings["email_address"],
            subject,
            body,
            event_type="cookies_expiry",
        )
