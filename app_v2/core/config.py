from typing import Optional
from datetime import datetime
import pytz
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Configuration de l'application v2 utilisant Pydantic Settings v2.
    Gère les paramètres d'authentification, de base de données, de limites et du navigateur.
    """

    # Auth (chiffrées)
    api_key: SecretStr = Field(..., description="Clé API pour l'authentification sécurisée des services internes")
    auth_encryption_key: SecretStr = Field(..., description="Clé de chiffrement Fernet pour sécuriser les données sensibles comme les tokens")
    jwt_secret: SecretStr = Field(..., description="Secret utilisé pour signer et valider les JSON Web Tokens (JWT)")

    # Database
    database_url: str = Field("sqlite+aiosqlite:///./data/linkedin.db", description="URL de connexion à la base de données SQLite")

    # Logging
    log_level: str = Field("INFO", description="Niveau de log (DEBUG, INFO, WARNING, ERROR)")

    # Rate Limiting (valeurs EXACTES de l'ancien config)
    max_messages_per_week: int = Field(100, description="Nombre maximum de messages autorisés par semaine")
    max_messages_per_day: int = Field(15, description="Nombre maximum de messages autorisés par jour")
    max_messages_per_execution: int = Field(15, description="Nombre maximum de messages envoyés par exécution du script")
    min_delay_between_messages: int = Field(90, description="Délai minimum en secondes entre l'envoi de deux messages")
    max_delay_between_messages: int = Field(180, description="Délai maximum en secondes entre l'envoi de deux messages")

    # Working Hours (timezone Paris)
    working_hours_start: int = Field(7, description="Heure de début de la plage de travail (0-23, timezone Paris)")
    working_hours_end: int = Field(19, description="Heure de fin de la plage de travail (0-23, timezone Paris)")

    # Birthday Processing
    process_today: bool = Field(True, description="Indique si les anniversaires du jour doivent être traités")
    process_late: bool = Field(True, description="Indique si les anniversaires en retard doivent être traités")
    max_days_late: int = Field(10, description="Nombre maximum de jours de retard acceptés pour souhaiter un anniversaire")
    avoid_repetition_years: int = Field(2, description="Nombre d'années pendant lesquelles on évite de renvoyer un message au même contact")

    # Browser (pour RPi 4)
    headless: bool = Field(True, description="Indique si le navigateur doit être lancé en mode sans interface graphique")
    browser_timeout: int = Field(30000, description="Délai d'attente maximum pour les opérations du navigateur en millisecondes")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def is_working_hours(self) -> bool:
        """
        Vérifie si l'heure actuelle est dans la plage horaire définie (Fuseau horaire Paris).
        Retourne True si l'heure courante à Paris est entre working_hours_start (inclus) et working_hours_end (exclus).
        """
        paris_tz = pytz.timezone('Europe/Paris')
        current_time_paris = datetime.now(paris_tz)
        return self.working_hours_start <= current_time_paris.hour < self.working_hours_end
