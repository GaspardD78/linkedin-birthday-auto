"""
Gestionnaire de configuration centralisé (Singleton thread-safe).

Ce module gère le chargement, la validation et l'accès à la configuration
depuis différentes sources (YAML, variables d'environnement, valeurs par défaut).
"""

import os
import yaml
import logging
from typing import Optional, Any, Dict
from pathlib import Path
import threading
from .config_schema import LinkedInBotConfig, DEFAULT_CONFIG
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Gestionnaire de configuration singleton thread-safe.

    Priorité de chargement :
    1. Variables d'environnement (LINKEDIN_BOT_*)
    2. Fichier config.yaml
    3. Valeurs par défaut (config_schema.py)

    Exemples d'utilisation :
        >>> config = ConfigManager.get_instance()
        >>> config.browser.headless
        True
        >>> config.get("browser.headless")
        True
        >>> config.set("dry_run", True)
    """

    _instance: Optional['ConfigManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        config_path: Optional[str] = None,
        auto_reload: bool = False
    ):
        """
        Initialise le gestionnaire de configuration.

        Args:
            config_path: Chemin vers le fichier config.yaml
            auto_reload: Recharger automatiquement si le fichier change
        """
        self._config: LinkedInBotConfig = DEFAULT_CONFIG.model_copy()
        self._config_path: Optional[Path] = None
        self._auto_reload: bool = auto_reload
        self._file_mtime: Optional[float] = None

        if config_path:
            self.load_from_file(config_path)

        # Charger les overrides des variables d'environnement
        self._load_env_overrides()

        logger.info(
            f"Configuration loaded (mode: {self._config.bot_mode}, "
            f"dry_run: {self._config.dry_run})"
        )

    @classmethod
    def get_instance(
        cls,
        config_path: Optional[str] = None,
        force_reload: bool = False
    ) -> 'ConfigManager':
        """
        Retourne l'instance singleton du gestionnaire (thread-safe).

        Args:
            config_path: Chemin vers config.yaml (optionnel)
            force_reload: Forcer le rechargement

        Returns:
            Instance singleton de ConfigManager
        """
        if cls._instance is None or force_reload:
            with cls._lock:
                if cls._instance is None or force_reload:
                    # Chercher config.yaml dans plusieurs emplacements
                    if config_path is None:
                        config_path = cls._find_config_file()

                    cls._instance = cls(config_path)
                    logger.info("ConfigManager singleton initialized")

        return cls._instance

    @staticmethod
    def _find_config_file() -> Optional[str]:
        """
        Cherche config.yaml dans plusieurs emplacements.

        Ordre de recherche :
        1. LINKEDIN_BOT_CONFIG_PATH (env var)
        2. ./config/config.yaml
        3. ./config.yaml
        4. ~/.linkedin-bot/config.yaml

        Returns:
            Chemin vers config.yaml ou None
        """
        # 1. Variable d'environnement
        env_path = os.getenv('LINKEDIN_BOT_CONFIG_PATH')
        if env_path and Path(env_path).exists():
            logger.info(f"Using config from env var: {env_path}")
            return env_path

        # 2. ./config/config.yaml
        local_config = Path("config/config.yaml")
        if local_config.exists():
            logger.info(f"Using local config: {local_config}")
            return str(local_config)

        # 3. ./config.yaml
        root_config = Path("config.yaml")
        if root_config.exists():
            logger.info(f"Using root config: {root_config}")
            return str(root_config)

        # 4. ~/.linkedin-bot/config.yaml
        home_config = Path.home() / ".linkedin-bot" / "config.yaml"
        if home_config.exists():
            logger.info(f"Using home config: {home_config}")
            return str(home_config)

        logger.warning("No config.yaml found, using defaults")
        return None

    def load_from_file(self, config_path: str) -> None:
        """
        Charge la configuration depuis un fichier YAML.

        Args:
            config_path: Chemin vers le fichier YAML

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            ValidationError: Si la validation Pydantic échoue
            yaml.YAMLError: Si le YAML est invalide
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        self._config_path = path
        self._file_mtime = path.stat().st_mtime

        with open(path, 'r', encoding='utf-8') as f:
            try:
                yaml_data = yaml.safe_load(f)

                if yaml_data is None:
                    logger.warning(f"Empty config file: {config_path}")
                    return

                # Valider et créer la config avec Pydantic
                self._config = LinkedInBotConfig(**yaml_data)
                logger.info(f"Configuration loaded from {config_path}")

            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML in {config_path}: {e}")
                raise
            except ValidationError as e:
                logger.error(f"Configuration validation failed: {e}")
                raise

    def _load_env_overrides(self) -> None:
        """
        Charge les overrides depuis les variables d'environnement.

        Format : LINKEDIN_BOT_<SECTION>_<KEY>
        Exemples :
            LINKEDIN_BOT_DRY_RUN=true
            LINKEDIN_BOT_BROWSER_HEADLESS=false
            LINKEDIN_BOT_DEBUG_LOG_LEVEL=DEBUG
        """
        env_prefix = "LINKEDIN_BOT_"
        overrides_count = 0

        for key, value in os.environ.items():
            if not key.startswith(env_prefix):
                continue

            # Extraire la clé de config (ex: DRY_RUN, BROWSER_HEADLESS)
            config_key = key[len(env_prefix):].lower()

            # Parser la valeur
            parsed_value = self._parse_env_value(value)

            # Appliquer l'override
            try:
                self._set_nested_value(config_key, parsed_value)
                overrides_count += 1
                logger.debug(f"Applied env override: {config_key} = {parsed_value}")
            except Exception as e:
                logger.warning(
                    f"Failed to apply env override {key}: {e}"
                )

        if overrides_count > 0:
            logger.info(f"Applied {overrides_count} environment overrides")

    def _parse_env_value(self, value: str) -> Any:
        """
        Parse une valeur de variable d'environnement.

        Convertit les strings en types appropriés :
        - "true"/"false" -> bool
        - Nombres -> int/float
        - JSON -> dict/list
        - Reste -> str
        """
        # Booléens
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        if value.lower() in ('false', 'no', '0', 'off'):
            return False

        # Nombres
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # JSON
        if value.startswith('{') or value.startswith('['):
            try:
                import json
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        # String par défaut
        return value

    def _set_nested_value(self, key: str, value: Any) -> None:
        """
        Définit une valeur dans la config imbriquée.

        Supporte les clés avec underscores pour accéder aux sous-objets.
        Exemples :
            "dry_run" -> config.dry_run
            "browser_headless" -> config.browser.headless
            "debug_log_level" -> config.debug.log_level
        """
        # Séparer la clé en parties
        parts = key.split('_')

        # Essayer différentes combinaisons pour trouver le bon chemin
        # Ex: browser_headless peut être browser.headless
        for i in range(len(parts), 0, -1):
            section = '_'.join(parts[:i])
            field = '_'.join(parts[i:]) if i < len(parts) else None

            # Vérifier si c'est un champ direct de _config
            if hasattr(self._config, section) and field is None:
                setattr(self._config, section, value)
                return

            # Vérifier si c'est un sous-champ
            if hasattr(self._config, section) and field:
                sub_obj = getattr(self._config, section)
                if hasattr(sub_obj, field):
                    setattr(sub_obj, field, value)
                    return

        # Fallback : essayer de définir directement
        if hasattr(self._config, key):
            setattr(self._config, key, value)
            return

        raise ValueError(f"Unknown config key: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur de configuration.

        Args:
            key: Clé de configuration (supporte la notation pointée)
            default: Valeur par défaut si non trouvée

        Returns:
            Valeur de configuration

        Exemples:
            >>> config.get("dry_run")
            False
            >>> config.get("browser.headless")
            True
            >>> config.get("messaging_limits.weekly_message_limit")
            80
        """
        parts = key.split('.')
        value = self._config

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Définit une valeur de configuration.

        Args:
            key: Clé de configuration (notation pointée)
            value: Nouvelle valeur

        Exemples:
            >>> config.set("dry_run", True)
            >>> config.set("browser.headless", False)
        """
        parts = key.split('.')

        if len(parts) == 1:
            # Clé directe
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                raise ValueError(f"Unknown config key: {key}")
        else:
            # Clé imbriquée
            obj = self._config
            for part in parts[:-1]:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    raise ValueError(f"Unknown config path: {'.'.join(parts[:-1])}")

            final_key = parts[-1]
            if hasattr(obj, final_key):
                setattr(obj, final_key, value)
            else:
                raise ValueError(f"Unknown config key: {key}")

    def reload_if_changed(self) -> bool:
        """
        Recharge la config si le fichier a changé.

        Returns:
            True si rechargé, False sinon
        """
        if not self._config_path or not self._auto_reload:
            return False

        current_mtime = self._config_path.stat().st_mtime

        if current_mtime != self._file_mtime:
            logger.info(f"Config file changed, reloading: {self._config_path}")
            try:
                self.load_from_file(str(self._config_path))
                self._load_env_overrides()
                return True
            except Exception as e:
                logger.error(f"Failed to reload config: {e}")
                return False

        return False

    def export_to_yaml(self, output_path: str) -> None:
        """
        Exporte la configuration actuelle en YAML.

        Args:
            output_path: Chemin du fichier de sortie
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            # Convertir Pydantic model en dict
            config_dict = self._config.model_dump(mode='json')
            yaml.dump(
                config_dict,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
        logger.info(f"Configuration exported to {output_path}")

    def export_to_dict(self) -> Dict[str, Any]:
        """
        Exporte la configuration en dictionnaire.

        Returns:
            Dict avec toute la configuration
        """
        return self._config.model_dump(mode='json')

    def validate(self) -> bool:
        """
        Valide la configuration actuelle.

        Returns:
            True si valide, False sinon
        """
        try:
            # Pydantic valide automatiquement, mais on peut forcer une revalidation
            LinkedInBotConfig(**self._config.model_dump())
            logger.info("✅ Configuration is valid")
            return True
        except ValidationError as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return False

    @property
    def config(self) -> LinkedInBotConfig:
        """Accès direct à l'objet de configuration."""
        return self._config

    def __repr__(self) -> str:
        """Représentation string du gestionnaire."""
        return (
            f"<ConfigManager(mode={self._config.bot_mode}, "
            f"dry_run={self._config.dry_run}, "
            f"config_file={self._config_path})>"
        )


# Fonction utilitaire pour accès rapide
def get_config() -> LinkedInBotConfig:
    """
    Raccourci pour obtenir la configuration.

    Returns:
        Instance de LinkedInBotConfig

    Exemple:
        >>> from src.config import get_config
        >>> config = get_config()
        >>> if config.dry_run:
        >>>     print("Mode test activé")
    """
    return ConfigManager.get_instance().config
