"""
Routes API pour la gestion des notifications par email.

Fournit des endpoints pour configurer et tester les notifications.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from typing import Dict, Any, Optional
import logging

from ...services.notification_service import NotificationService
from ..security import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationSettings(BaseModel):
    """Modèle pour les paramètres de notification."""

    email_enabled: bool = Field(default=False, description="Activer les notifications par email")
    email_address: str = Field(default="", description="Adresse email de destination")
    notify_on_error: bool = Field(default=True, description="Notifier en cas d'erreur")
    notify_on_success: bool = Field(default=False, description="Notifier après succès")
    notify_on_bot_start: bool = Field(default=False, description="Notifier au démarrage")
    notify_on_bot_stop: bool = Field(default=False, description="Notifier à l'arrêt")
    notify_on_cookies_expiry: bool = Field(
        default=True, description="Notifier quand cookies expirent"
    )
    # SMTP Configuration fields
    smtp_host: Optional[str] = Field(default=None, description="Serveur SMTP (ex: smtp.gmail.com)")
    smtp_port: Optional[int] = Field(default=None, description="Port SMTP (ex: 587)")
    smtp_user: Optional[str] = Field(default=None, description="Nom d'utilisateur SMTP")
    smtp_password: Optional[str] = Field(default=None, description="Mot de passe SMTP")
    smtp_use_tls: bool = Field(default=True, description="Utiliser TLS pour la connexion SMTP")
    smtp_from_email: Optional[str] = Field(default=None, description="Adresse email d'expédition")


class TestNotificationRequest(BaseModel):
    """Modèle pour la requête d'envoi de notification de test."""

    email: EmailStr = Field(..., description="Adresse email pour le test")


def get_notification_service() -> NotificationService:
    """Dependency pour obtenir le service de notifications."""
    from ...core.database import Database

    db = Database("/app/data/linkedin.db")
    return NotificationService(db)


@router.get("/settings", dependencies=[Depends(verify_api_key)])
async def get_notification_settings(
    notification_service: NotificationService = Depends(get_notification_service),
) -> Dict[str, Any]:
    """
    Récupère les paramètres de notification.

    Le mot de passe SMTP est masqué pour des raisons de sécurité.

    Returns:
        Paramètres de notification actuels
    """
    try:
        # Mask password for security when returning settings
        settings = notification_service.get_settings(mask_password=True)
        return {
            "success": True,
            "settings": settings,
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des paramètres: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings", dependencies=[Depends(verify_api_key)])
async def update_notification_settings(
    settings: NotificationSettings,
    notification_service: NotificationService = Depends(get_notification_service),
) -> Dict[str, Any]:
    """
    Met à jour les paramètres de notification.

    Args:
        settings: Nouveaux paramètres de notification

    Returns:
        Paramètres de notification mis à jour
    """
    try:
        updated_settings = notification_service.update_settings(settings.dict())
        return {
            "success": True,
            "settings": updated_settings,
            "message": "Paramètres mis à jour avec succès",
        }
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des paramètres: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", dependencies=[Depends(verify_api_key)])
async def send_test_notification(
    request: TestNotificationRequest,
    notification_service: NotificationService = Depends(get_notification_service),
) -> Dict[str, Any]:
    """
    Envoie une notification de test.

    Args:
        request: Requête contenant l'email de destination

    Returns:
        Résultat de l'envoi
    """
    try:
        result = await notification_service.send_test_notification(request.email)

        if result["success"]:
            return {
                "success": True,
                "message": "Email de test envoyé avec succès",
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Erreur inconnue"),
            }

    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
