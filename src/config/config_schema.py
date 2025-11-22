"""
Schémas Pydantic pour la validation de configuration.

Ce module définit les modèles de données pour toutes les configurations du bot LinkedIn.
Utilise Pydantic v2 pour une validation robuste avec type hints.
"""

from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import time


class BrowserConfig(BaseModel):
    """Configuration du navigateur Playwright."""

    model_config = ConfigDict(frozen=False)

    headless: bool = Field(
        default=True,
        description="Mode headless (sans interface graphique)"
    )
    slow_mo: tuple[int, int] = Field(
        default=(80, 150),
        description="Ralentissement aléatoire en ms (min, max)"
    )
    user_agents: List[str] = Field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ],
        description="Liste de User-Agents pour rotation anti-détection"
    )
    viewport_sizes: List[Dict[str, int]] = Field(
        default_factory=lambda: [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1440, 'height': 900},
        ],
        description="Tailles de viewport pour anti-détection"
    )
    locale: str = Field(default="fr-FR", description="Locale du navigateur")
    timezone: str = Field(default="Europe/Paris", description="Fuseau horaire")

    @field_validator('slow_mo')
    @classmethod
    def validate_slow_mo(cls, v: tuple[int, int]) -> tuple[int, int]:
        """Valide que slow_mo a des valeurs cohérentes."""
        if len(v) != 2:
            raise ValueError("slow_mo doit être un tuple de 2 entiers (min, max)")
        if v[0] > v[1]:
            raise ValueError("slow_mo[0] (min) doit être <= slow_mo[1] (max)")
        if v[0] < 0:
            raise ValueError("slow_mo valeurs doivent être positives")
        return v


class AuthConfig(BaseModel):
    """Configuration de l'authentification."""

    model_config = ConfigDict(frozen=False)

    auth_state_env_var: str = Field(
        default="LINKEDIN_AUTH_STATE",
        description="Variable d'environnement contenant l'auth state"
    )
    auth_file_path: str = Field(
        default="auth_state.json",
        description="Chemin du fichier auth state"
    )
    auth_fallback_path: Optional[str] = Field(
        default=None,
        description="Chemin de secours pour l'auth state"
    )


class MessagingLimitsConfig(BaseModel):
    """Configuration des limites d'envoi de messages."""

    model_config = ConfigDict(frozen=False)

    max_messages_per_run: Optional[int] = Field(
        default=None,
        description="Limite de messages par exécution (None = illimité)"
    )
    weekly_message_limit: int = Field(
        default=80,
        ge=1,
        le=500,
        description="Limite hebdomadaire de messages (1-500)"
    )
    daily_message_limit: Optional[int] = Field(
        default=None,
        description="Limite quotidienne de messages"
    )

    @field_validator('weekly_message_limit')
    @classmethod
    def validate_weekly_limit(cls, v: int) -> int:
        """Avertissement si limite trop élevée."""
        if v > 100:
            import logging
            logging.warning(
                f"⚠️ Limite hebdomadaire de {v} est élevée. "
                "LinkedIn recommande < 100 messages/semaine."
            )
        return v


class SchedulingConfig(BaseModel):
    """Configuration de la planification des messages."""

    model_config = ConfigDict(frozen=False)

    daily_start_hour: int = Field(
        default=7,
        ge=0,
        le=23,
        description="Heure de début d'envoi (0-23)"
    )
    daily_end_hour: int = Field(
        default=19,
        ge=0,
        le=23,
        description="Heure de fin d'envoi (0-23)"
    )
    timezone: str = Field(
        default="Europe/Paris",
        description="Fuseau horaire pour la planification"
    )

    @field_validator('daily_end_hour')
    @classmethod
    def validate_end_after_start(cls, v: int, info) -> int:
        """Valide que l'heure de fin est après l'heure de début."""
        if 'daily_start_hour' in info.data:
            if v <= info.data['daily_start_hour']:
                raise ValueError(
                    "daily_end_hour doit être > daily_start_hour"
                )
        return v


class DelaysConfig(BaseModel):
    """Configuration des délais entre actions."""

    model_config = ConfigDict(frozen=False)

    min_delay_seconds: int = Field(
        default=120,
        ge=30,
        description="Délai minimum entre messages (secondes)"
    )
    max_delay_seconds: int = Field(
        default=300,
        ge=60,
        description="Délai maximum entre messages (secondes)"
    )
    action_delay_min: float = Field(
        default=0.5,
        ge=0.1,
        description="Délai minimum entre micro-actions (secondes)"
    )
    action_delay_max: float = Field(
        default=1.5,
        ge=0.5,
        description="Délai maximum entre micro-actions (secondes)"
    )

    @field_validator('max_delay_seconds')
    @classmethod
    def validate_max_after_min(cls, v: int, info) -> int:
        """Valide que max > min."""
        if 'min_delay_seconds' in info.data:
            if v < info.data['min_delay_seconds']:
                raise ValueError(
                    "max_delay_seconds doit être >= min_delay_seconds"
                )
        return v


class MessagesConfig(BaseModel):
    """Configuration des messages d'anniversaire."""

    model_config = ConfigDict(frozen=False)

    messages_file: str = Field(
        default="messages.txt",
        description="Fichier contenant les messages standard"
    )
    late_messages_file: str = Field(
        default="late_messages.txt",
        description="Fichier contenant les messages en retard"
    )
    avoid_repetition_years: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Années d'historique pour éviter la répétition"
    )


class BirthdayFilterConfig(BaseModel):
    """Configuration du filtrage des anniversaires."""

    model_config = ConfigDict(frozen=False)

    process_today: bool = Field(
        default=True,
        description="Traiter les anniversaires du jour"
    )
    process_late: bool = Field(
        default=True,
        description="Traiter les anniversaires en retard"
    )
    max_days_late: int = Field(
        default=10,
        ge=1,
        le=365,
        description="Nombre maximum de jours de retard (1-365)"
    )


class ProxyConfig(BaseModel):
    """Configuration du proxy (optionnel)."""

    model_config = ConfigDict(frozen=False)

    enabled: bool = Field(default=False, description="Activer le proxy")
    rotation_enabled: bool = Field(
        default=False,
        description="Activer la rotation des proxies"
    )
    config_file: Optional[str] = Field(
        default="proxy_config.json",
        description="Fichier de configuration des proxies"
    )


class DebugConfig(BaseModel):
    """Configuration du débogage."""

    model_config = ConfigDict(frozen=False)

    advanced_debug: bool = Field(
        default=False,
        description="Activer le débogage avancé"
    )
    save_screenshots: bool = Field(
        default=True,
        description="Sauvegarder les screenshots d'erreurs"
    )
    save_html: bool = Field(
        default=False,
        description="Sauvegarder le HTML des pages"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Niveau de logging"
    )


class DatabaseConfig(BaseModel):
    """Configuration de la base de données."""

    model_config = ConfigDict(frozen=False)

    enabled: bool = Field(default=True, description="Activer la base de données")
    db_path: str = Field(
        default="linkedin_automation.db",
        description="Chemin du fichier SQLite"
    )
    timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Timeout des opérations DB (secondes)"
    )


class MonitoringConfig(BaseModel):
    """Configuration du monitoring."""

    model_config = ConfigDict(frozen=False)

    enabled: bool = Field(default=False, description="Activer le monitoring")
    prometheus_enabled: bool = Field(
        default=False,
        description="Activer les métriques Prometheus"
    )
    prometheus_port: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Port pour Prometheus"
    )


class LinkedInBotConfig(BaseModel):
    """Configuration complète du bot LinkedIn."""

    model_config = ConfigDict(frozen=False)

    # Métadonnées
    version: str = Field(default="2.0.0", description="Version de la config")

    # Mode de fonctionnement
    dry_run: bool = Field(
        default=False,
        description="Mode test (ne pas envoyer de vrais messages)"
    )
    bot_mode: Literal["standard", "unlimited", "custom"] = Field(
        default="standard",
        description="Mode du bot (standard avec limites, unlimited, ou custom)"
    )

    # Modules de configuration
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    messaging_limits: MessagingLimitsConfig = Field(
        default_factory=MessagingLimitsConfig
    )
    scheduling: SchedulingConfig = Field(default_factory=SchedulingConfig)
    delays: DelaysConfig = Field(default_factory=DelaysConfig)
    messages: MessagesConfig = Field(default_factory=MessagesConfig)
    birthday_filter: BirthdayFilterConfig = Field(
        default_factory=BirthdayFilterConfig
    )
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    debug: DebugConfig = Field(default_factory=DebugConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    def get_daily_window_seconds(self) -> int:
        """Calcule la fenêtre quotidienne en secondes."""
        return (
            self.scheduling.daily_end_hour - self.scheduling.daily_start_hour
        ) * 3600

    def is_unlimited_mode(self) -> bool:
        """Vérifie si le bot est en mode illimité."""
        return self.bot_mode == "unlimited"

    def get_effective_message_limit(self) -> Optional[int]:
        """Retourne la limite effective de messages par run."""
        if self.bot_mode == "unlimited":
            return None
        return self.messaging_limits.max_messages_per_run


# Configuration par défaut pour export
DEFAULT_CONFIG = LinkedInBotConfig()
