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

    def get_settings(self, mask_password: bool = False) -> Dict[str, Any]:
        """
        Récupère les paramètres de notification depuis la base de données.

        Args:
            mask_password: Si True, masque le mot de passe SMTP avec '****'

        Returns:
            Dictionnaire avec les paramètres de notification
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notification_settings ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()

            if row:
                # Récupérer le mot de passe et le masquer si nécessaire
                smtp_password = row["smtp_password"] if "smtp_password" in row.keys() else None
                if mask_password and smtp_password:
                    smtp_password = "****"

                return {
                    "email_enabled": bool(row["email_enabled"]),
                    "email_address": row["email_address"],
                    "notify_on_error": bool(row["notify_on_error"]),
                    "notify_on_success": bool(row["notify_on_success"]),
                    "notify_on_bot_start": bool(row["notify_on_bot_start"]),
                    "notify_on_bot_stop": bool(row["notify_on_bot_stop"]),
                    "notify_on_cookies_expiry": bool(row["notify_on_cookies_expiry"]),
                    "smtp_host": row["smtp_host"] if "smtp_host" in row.keys() else None,
                    "smtp_port": row["smtp_port"] if "smtp_port" in row.keys() else None,
                    "smtp_user": row["smtp_user"] if "smtp_user" in row.keys() else None,
                    "smtp_password": smtp_password,
                    "smtp_use_tls": bool(row["smtp_use_tls"]) if "smtp_use_tls" in row.keys() and row["smtp_use_tls"] is not None else True,
                    "smtp_from_email": row["smtp_from_email"] if "smtp_from_email" in row.keys() else None,
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
            "smtp_host": None,
            "smtp_port": None,
            "smtp_user": None,
            "smtp_password": None,
            "smtp_use_tls": True,
            "smtp_from_email": None,
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

        # Si le mot de passe est masqué (****), ne pas le mettre à jour
        smtp_password = settings.get("smtp_password")
        if smtp_password == "****":
            # Récupérer le mot de passe actuel de la DB
            current_settings = self.get_settings(mask_password=False)
            smtp_password = current_settings.get("smtp_password")

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
                        smtp_host = ?,
                        smtp_port = ?,
                        smtp_user = ?,
                        smtp_password = ?,
                        smtp_use_tls = ?,
                        smtp_from_email = ?,
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
                        settings.get("smtp_host"),
                        settings.get("smtp_port"),
                        settings.get("smtp_user"),
                        smtp_password,
                        settings.get("smtp_use_tls", True),
                        settings.get("smtp_from_email"),
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
                        smtp_host, smtp_port, smtp_user, smtp_password, smtp_use_tls, smtp_from_email,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        settings.get("email_enabled", False),
                        settings.get("email_address", ""),
                        settings.get("notify_on_error", True),
                        settings.get("notify_on_success", False),
                        settings.get("notify_on_bot_start", False),
                        settings.get("notify_on_bot_stop", False),
                        settings.get("notify_on_cookies_expiry", True),
                        settings.get("smtp_host"),
                        settings.get("smtp_port"),
                        settings.get("smtp_user"),
                        smtp_password,
                        settings.get("smtp_use_tls", True),
                        settings.get("smtp_from_email"),
                        now,
                        now,
                    ),
                )

        # Invalidate cached SMTP config
        self._smtp_config = None

        return self.get_settings(mask_password=True)

    def _load_smtp_config(self) -> Dict[str, Any]:
        """
        Charge la configuration SMTP depuis la base de données, avec fallback sur les variables d'environnement.

        La priorité est donnée aux valeurs de la base de données. Si une valeur est nulle/vide
        dans la DB, on utilise la valeur de la variable d'environnement correspondante.

        Returns:
            Dictionnaire avec la configuration SMTP
        """
        # Récupérer les paramètres de la base de données
        db_settings = self.get_settings(mask_password=False)

        # Récupérer les valeurs depuis la DB, avec fallback sur les variables d'environnement
        host = db_settings.get("smtp_host") or os.getenv("SMTP_HOST", "smtp.gmail.com")

        # Pour le port, gérer le cas où la valeur DB est None ou 0
        db_port = db_settings.get("smtp_port")
        if db_port:
            port = int(db_port)
        else:
            port = int(os.getenv("SMTP_PORT", "587"))

        username = db_settings.get("smtp_user") or os.getenv("SMTP_USER")
        password = db_settings.get("smtp_password") or os.getenv("SMTP_PASSWORD")

        # Pour use_tls, la valeur DB a priorité si elle est explicitement définie
        db_use_tls = db_settings.get("smtp_use_tls")
        if db_use_tls is not None:
            use_tls = bool(db_use_tls)
        else:
            use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

        from_email = db_settings.get("smtp_from_email") or os.getenv("SMTP_FROM_EMAIL")

        config = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "use_tls": use_tls,
            "from_email": from_email,
        }

        # Log configuration (sans le mot de passe)
        logger.debug(
            f"SMTP config loaded: host={config['host']}, port={config['port']}, "
            f"user={config['username']}, use_tls={config['use_tls']}, from={config['from_email']}"
        )

        return config

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
