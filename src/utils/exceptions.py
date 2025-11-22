"""
Hiérarchie d'exceptions personnalisées pour LinkedIn Bot.

Ce module définit toutes les exceptions spécifiques au bot avec des
recovery strategies et des codes d'erreur pour faciliter le debugging.
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(Enum):
    """Codes d'erreur pour classification."""

    # Authentification (1xxx)
    AUTH_FAILED = 1001
    AUTH_EXPIRED = 1002
    AUTH_INVALID = 1003
    SESSION_EXPIRED = 1004

    # Navigation/Browser (2xxx)
    BROWSER_LAUNCH_FAILED = 2001
    PAGE_LOAD_TIMEOUT = 2002
    ELEMENT_NOT_FOUND = 2003
    ELEMENT_DETACHED = 2004
    NETWORK_ERROR = 2005

    # LinkedIn Limits (3xxx)
    RATE_LIMIT_EXCEEDED = 3001
    WEEKLY_LIMIT_REACHED = 3002
    DAILY_LIMIT_REACHED = 3003
    ACCOUNT_RESTRICTED = 3004
    CAPTCHA_REQUIRED = 3005

    # Messages (4xxx)
    MESSAGE_SEND_FAILED = 4001
    MODAL_NOT_FOUND = 4002
    MESSAGE_BOX_NOT_FOUND = 4003
    SEND_BUTTON_DISABLED = 4004

    # Database (5xxx)
    DATABASE_CONNECTION_FAILED = 5001
    DATABASE_LOCKED = 5002
    DATABASE_QUERY_FAILED = 5003

    # Configuration (6xxx)
    CONFIG_INVALID = 6001
    CONFIG_FILE_NOT_FOUND = 6002
    CONFIG_VALIDATION_FAILED = 6003

    # Generic (9xxx)
    UNKNOWN_ERROR = 9000
    NOT_IMPLEMENTED = 9001


class LinkedInBotError(Exception):
    """
    Exception de base pour toutes les erreurs du bot LinkedIn.

    Tous les autres exceptions doivent hériter de celle-ci.

    Args:
        message: Message d'erreur descriptif
        error_code: Code d'erreur (ErrorCode enum)
        details: Détails supplémentaires (dict)
        recoverable: Si True, l'erreur peut être récupérée
        retry_after: Secondes à attendre avant retry (si recoverable)
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False,
        retry_after: Optional[int] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.recoverable = recoverable
        self.retry_after = retry_after
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Formate le message d'erreur complet."""
        msg = f"[{self.error_code.name}] {self.message}"
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            msg += f" ({details_str})"
        if self.recoverable and self.retry_after:
            msg += f" [Retry after {self.retry_after}s]"
        return msg

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'exception en dictionnaire pour logging/API."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code.name,
            "error_code_value": self.error_code.value,
            "details": self.details,
            "recoverable": self.recoverable,
            "retry_after": self.retry_after
        }


# ═══════════════════════════════════════════════════════════════════
# AUTHENTIFICATION
# ═══════════════════════════════════════════════════════════════════

class AuthenticationError(LinkedInBotError):
    """Erreur d'authentification générique."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTH_FAILED,
            recoverable=False,
            **kwargs
        )


class SessionExpiredError(AuthenticationError):
    """Session LinkedIn expirée."""

    def __init__(self, message: str = "LinkedIn session has expired", **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.SESSION_EXPIRED,
            recoverable=False,
            **kwargs
        )


class InvalidAuthStateError(AuthenticationError):
    """État d'authentification invalide."""

    def __init__(self, message: str = "Invalid auth state", **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTH_INVALID,
            recoverable=False,
            **kwargs
        )


# ═══════════════════════════════════════════════════════════════════
# NAVIGATION / BROWSER
# ═══════════════════════════════════════════════════════════════════

class BrowserError(LinkedInBotError):
    """Erreur du navigateur."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.BROWSER_LAUNCH_FAILED,
            recoverable=True,
            retry_after=30,
            **kwargs
        )


class PageLoadTimeoutError(BrowserError):
    """Timeout lors du chargement d'une page."""

    def __init__(self, url: str, timeout: int, **kwargs):
        super().__init__(
            message=f"Page load timeout after {timeout}s",
            error_code=ErrorCode.PAGE_LOAD_TIMEOUT,
            details={"url": url, "timeout": timeout},
            recoverable=True,
            retry_after=10,
            **kwargs
        )


class ElementNotFoundError(BrowserError):
    """Élément DOM introuvable."""

    def __init__(self, selector: str, **kwargs):
        super().__init__(
            message=f"Element not found: {selector}",
            error_code=ErrorCode.ELEMENT_NOT_FOUND,
            details={"selector": selector},
            recoverable=True,
            retry_after=5,
            **kwargs
        )


class ElementDetachedError(BrowserError):
    """Élément détaché du DOM."""

    def __init__(self, selector: str, **kwargs):
        super().__init__(
            message=f"Element detached from DOM: {selector}",
            error_code=ErrorCode.ELEMENT_DETACHED,
            details={"selector": selector},
            recoverable=True,
            retry_after=2,
            **kwargs
        )


class NetworkError(BrowserError):
    """Erreur réseau."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.NETWORK_ERROR,
            recoverable=True,
            retry_after=60,
            **kwargs
        )


# ═══════════════════════════════════════════════════════════════════
# LIMITES LINKEDIN
# ═══════════════════════════════════════════════════════════════════

class RateLimitError(LinkedInBotError):
    """Limite de taux dépassée (rate limiting)."""

    def __init__(
        self,
        message: str = "LinkedIn rate limit exceeded",
        retry_after: int = 3600,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            recoverable=True,
            retry_after=retry_after,
            **kwargs
        )


class WeeklyLimitReachedError(LinkedInBotError):
    """Limite hebdomadaire atteinte."""

    def __init__(
        self,
        current: int,
        limit: int,
        **kwargs
    ):
        super().__init__(
            message=f"Weekly message limit reached ({current}/{limit})",
            error_code=ErrorCode.WEEKLY_LIMIT_REACHED,
            details={"current": current, "limit": limit},
            recoverable=False,
            **kwargs
        )


class DailyLimitReachedError(LinkedInBotError):
    """Limite quotidienne atteinte."""

    def __init__(
        self,
        current: int,
        limit: int,
        **kwargs
    ):
        super().__init__(
            message=f"Daily message limit reached ({current}/{limit})",
            error_code=ErrorCode.DAILY_LIMIT_REACHED,
            details={"current": current, "limit": limit},
            recoverable=False,
            **kwargs
        )


class AccountRestrictedError(LinkedInBotError):
    """Compte LinkedIn restreint."""

    def __init__(self, reason: Optional[str] = None, **kwargs):
        message = "LinkedIn account is restricted"
        if reason:
            message += f": {reason}"
        super().__init__(
            message=message,
            error_code=ErrorCode.ACCOUNT_RESTRICTED,
            details={"reason": reason} if reason else {},
            recoverable=False,
            **kwargs
        )


class CaptchaRequiredError(LinkedInBotError):
    """Captcha requis par LinkedIn."""

    def __init__(self, **kwargs):
        super().__init__(
            message="LinkedIn requires captcha verification",
            error_code=ErrorCode.CAPTCHA_REQUIRED,
            recoverable=False,
            **kwargs
        )


# ═══════════════════════════════════════════════════════════════════
# MESSAGES
# ═══════════════════════════════════════════════════════════════════

class MessageSendError(LinkedInBotError):
    """Erreur lors de l'envoi d'un message."""

    def __init__(self, contact_name: str, reason: str, **kwargs):
        super().__init__(
            message=f"Failed to send message to {contact_name}: {reason}",
            error_code=ErrorCode.MESSAGE_SEND_FAILED,
            details={"contact": contact_name, "reason": reason},
            recoverable=True,
            retry_after=10,
            **kwargs
        )


class ModalNotFoundError(MessageSendError):
    """Modale de message introuvable."""

    def __init__(self, contact_name: str, **kwargs):
        super().__init__(
            contact_name=contact_name,
            reason="Message modal not found",
            error_code=ErrorCode.MODAL_NOT_FOUND,
            **kwargs
        )


class MessageBoxNotFoundError(MessageSendError):
    """Zone de texte du message introuvable."""

    def __init__(self, contact_name: str, **kwargs):
        super().__init__(
            contact_name=contact_name,
            reason="Message text box not found",
            error_code=ErrorCode.MESSAGE_BOX_NOT_FOUND,
            **kwargs
        )


class SendButtonDisabledError(MessageSendError):
    """Bouton d'envoi désactivé."""

    def __init__(self, contact_name: str, **kwargs):
        super().__init__(
            contact_name=contact_name,
            reason="Send button is disabled",
            error_code=ErrorCode.SEND_BUTTON_DISABLED,
            **kwargs
        )


# ═══════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════

class DatabaseError(LinkedInBotError):
    """Erreur de base de données."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.DATABASE_CONNECTION_FAILED,
            recoverable=True,
            retry_after=5,
            **kwargs
        )


class DatabaseLockedError(DatabaseError):
    """Base de données verrouillée."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Database is locked",
            error_code=ErrorCode.DATABASE_LOCKED,
            recoverable=True,
            retry_after=2,
            **kwargs
        )


class DatabaseQueryError(DatabaseError):
    """Erreur lors d'une requête."""

    def __init__(self, query: str, error: str, **kwargs):
        super().__init__(
            message=f"Database query failed: {error}",
            error_code=ErrorCode.DATABASE_QUERY_FAILED,
            details={"query": query, "error": error},
            **kwargs
        )


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

class ConfigurationError(LinkedInBotError):
    """Erreur de configuration."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIG_INVALID,
            recoverable=False,
            **kwargs
        )


class ConfigFileNotFoundError(ConfigurationError):
    """Fichier de configuration introuvable."""

    def __init__(self, config_path: str, **kwargs):
        super().__init__(
            message=f"Config file not found: {config_path}",
            error_code=ErrorCode.CONFIG_FILE_NOT_FOUND,
            details={"config_path": config_path},
            **kwargs
        )


class ConfigValidationError(ConfigurationError):
    """Erreur de validation de configuration."""

    def __init__(self, errors: str, **kwargs):
        super().__init__(
            message=f"Configuration validation failed: {errors}",
            error_code=ErrorCode.CONFIG_VALIDATION_FAILED,
            details={"validation_errors": errors},
            **kwargs
        )


# ═══════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════

def get_recovery_strategy(error: LinkedInBotError) -> Optional[str]:
    """
    Retourne une stratégie de récupération pour une erreur.

    Args:
        error: L'exception levée

    Returns:
        Stratégie de récupération recommandée (str) ou None
    """
    if not error.recoverable:
        return None

    strategies = {
        ErrorCode.PAGE_LOAD_TIMEOUT: "Retry loading the page with increased timeout",
        ErrorCode.ELEMENT_NOT_FOUND: "Wait and retry, or check if LinkedIn UI changed",
        ErrorCode.ELEMENT_DETACHED: "Refresh element reference and retry",
        ErrorCode.RATE_LIMIT_EXCEEDED: f"Wait {error.retry_after}s before retrying",
        ErrorCode.DATABASE_LOCKED: "Retry with exponential backoff",
        ErrorCode.NETWORK_ERROR: "Check network connection and retry",
        ErrorCode.MESSAGE_SEND_FAILED: "Close modals and retry message sending",
    }

    return strategies.get(error.error_code, "Retry operation after delay")


def is_critical_error(error: LinkedInBotError) -> bool:
    """
    Détermine si une erreur est critique (nécessite arrêt du bot).

    Args:
        error: L'exception levée

    Returns:
        True si critique, False sinon
    """
    critical_codes = {
        ErrorCode.AUTH_FAILED,
        ErrorCode.SESSION_EXPIRED,
        ErrorCode.ACCOUNT_RESTRICTED,
        ErrorCode.CAPTCHA_REQUIRED,
        ErrorCode.CONFIG_INVALID,
    }

    return error.error_code in critical_codes
