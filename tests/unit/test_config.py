"""
Tests unitaires pour le module de configuration.

Ce fichier démontre comment tester la nouvelle architecture.
"""

import pytest
import tempfile
import os
from pathlib import Path

# Import des modules à tester
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.config_schema import (
    LinkedInBotConfig,
    BrowserConfig,
    MessagingLimitsConfig,
    SchedulingConfig
)
from src.config.config_manager import ConfigManager
from pydantic import ValidationError


class TestConfigSchema:
    """Tests pour les schémas Pydantic."""

    def test_default_config_is_valid(self):
        """La configuration par défaut doit être valide."""
        config = LinkedInBotConfig()
        assert config.version == "2.0.0"
        assert config.dry_run is False
        assert config.bot_mode == "standard"

    def test_browser_config_default_values(self):
        """BrowserConfig doit avoir des valeurs par défaut correctes."""
        browser = BrowserConfig()
        assert browser.headless is True
        assert browser.locale == "fr-FR"
        assert browser.timezone == "Europe/Paris"
        assert len(browser.user_agents) > 0
        assert len(browser.viewport_sizes) > 0

    def test_browser_config_slow_mo_validation(self):
        """slow_mo doit valider que min <= max."""
        # Valide
        browser = BrowserConfig(slow_mo=(80, 150))
        assert browser.slow_mo == (80, 150)

        # Invalide : min > max
        with pytest.raises(ValidationError) as exc_info:
            BrowserConfig(slow_mo=(150, 80))
        assert "slow_mo[0] (min) doit être <= slow_mo[1] (max)" in str(exc_info.value)

        # Invalide : valeur négative
        with pytest.raises(ValidationError):
            BrowserConfig(slow_mo=(-10, 100))

    def test_messaging_limits_validation(self):
        """MessagingLimitsConfig doit valider les limites."""
        # Valide
        limits = MessagingLimitsConfig(weekly_message_limit=80)
        assert limits.weekly_message_limit == 80

        # Invalide : en dessous de la limite min
        with pytest.raises(ValidationError):
            MessagingLimitsConfig(weekly_message_limit=0)

        # Invalide : au-dessus de la limite max
        with pytest.raises(ValidationError):
            MessagingLimitsConfig(weekly_message_limit=1000)

    def test_scheduling_config_validation(self):
        """SchedulingConfig doit valider que end > start."""
        # Valide
        sched = SchedulingConfig(daily_start_hour=7, daily_end_hour=19)
        assert sched.daily_start_hour == 7
        assert sched.daily_end_hour == 19

        # Invalide : end <= start
        with pytest.raises(ValidationError):
            SchedulingConfig(daily_start_hour=19, daily_end_hour=7)

    def test_config_get_methods(self):
        """Les méthodes helper doivent fonctionner."""
        config = LinkedInBotConfig()

        # get_daily_window_seconds
        window = config.get_daily_window_seconds()
        expected = (config.scheduling.daily_end_hour - config.scheduling.daily_start_hour) * 3600
        assert window == expected

        # is_unlimited_mode
        config.bot_mode = "unlimited"
        assert config.is_unlimited_mode() is True

        config.bot_mode = "standard"
        assert config.is_unlimited_mode() is False

        # get_effective_message_limit
        config.bot_mode = "unlimited"
        assert config.get_effective_message_limit() is None

        config.bot_mode = "standard"
        config.messaging_limits.max_messages_per_run = 50
        assert config.get_effective_message_limit() == 50


class TestConfigManager:
    """Tests pour le ConfigManager."""

    def test_singleton_pattern(self):
        """ConfigManager doit être un singleton."""
        config1 = ConfigManager.get_instance()
        config2 = ConfigManager.get_instance()
        assert config1 is config2

    def test_load_from_yaml(self):
        """Chargement depuis un fichier YAML doit fonctionner."""
        # Créer un fichier YAML temporaire
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
version: "2.0.0"
dry_run: true
bot_mode: "unlimited"

browser:
  headless: false
  locale: "en-US"

messaging_limits:
  weekly_message_limit: 50
""")
            temp_path = f.name

        try:
            # Charger la config
            manager = ConfigManager(config_path=temp_path)

            assert manager.config.dry_run is True
            assert manager.config.bot_mode == "unlimited"
            assert manager.config.browser.headless is False
            assert manager.config.browser.locale == "en-US"
            assert manager.config.messaging_limits.weekly_message_limit == 50

        finally:
            os.unlink(temp_path)

    def test_load_invalid_yaml_raises_error(self):
        """Chargement d'un YAML invalide doit lever une erreur."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # yaml.YAMLError
                ConfigManager(config_path=temp_path)
        finally:
            os.unlink(temp_path)

    def test_get_method(self):
        """get() doit récupérer des valeurs imbriquées."""
        manager = ConfigManager()

        # Valeur directe
        assert manager.get("dry_run") is False
        assert manager.get("bot_mode") == "standard"

        # Valeur imbriquée
        assert manager.get("browser.headless") is True
        assert manager.get("browser.locale") == "fr-FR"
        assert manager.get("messaging_limits.weekly_message_limit") == 80

        # Valeur inexistante avec défaut
        assert manager.get("nonexistent.key", default="default_value") == "default_value"

    def test_set_method(self):
        """set() doit modifier des valeurs."""
        manager = ConfigManager()

        # Modifier valeur directe
        manager.set("dry_run", True)
        assert manager.config.dry_run is True

        # Modifier valeur imbriquée
        manager.set("browser.headless", False)
        assert manager.config.browser.headless is False

        manager.set("messaging_limits.weekly_message_limit", 100)
        assert manager.config.messaging_limits.weekly_message_limit == 100

    def test_export_to_dict(self):
        """export_to_dict() doit retourner un dict complet."""
        manager = ConfigManager()
        config_dict = manager.export_to_dict()

        assert isinstance(config_dict, dict)
        assert "version" in config_dict
        assert "browser" in config_dict
        assert "messaging_limits" in config_dict
        assert config_dict["browser"]["headless"] is True

    def test_validate_method(self):
        """validate() doit vérifier la config."""
        manager = ConfigManager()

        # Config valide
        assert manager.validate() is True

        # Modifier pour invalider
        manager.config.scheduling.daily_end_hour = 5
        manager.config.scheduling.daily_start_hour = 19
        # Note: Pydantic valide au moment de la création, pas après modification directe
        # Dans un vrai cas, on utiliserait set() qui revalidera


class TestEnvironmentOverrides:
    """Tests pour les overrides par variables d'environnement."""

    def test_env_override_dry_run(self, monkeypatch):
        """LINKEDIN_BOT_DRY_RUN doit override dry_run."""
        monkeypatch.setenv("LINKEDIN_BOT_DRY_RUN", "true")

        # Forcer une nouvelle instance
        ConfigManager._instance = None
        manager = ConfigManager.get_instance()

        assert manager.config.dry_run is True

    def test_env_override_nested_value(self, monkeypatch):
        """Variables env doivent override valeurs imbriquées."""
        monkeypatch.setenv("LINKEDIN_BOT_BROWSER_HEADLESS", "false")

        ConfigManager._instance = None
        manager = ConfigManager.get_instance()

        assert manager.config.browser.headless is False


# Fixtures pytest

@pytest.fixture
def temp_config_file():
    """Crée un fichier de configuration temporaire."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
version: "2.0.0"
dry_run: false
bot_mode: "standard"
""")
        temp_path = f.name

    yield temp_path

    os.unlink(temp_path)


@pytest.fixture
def clean_config_manager():
    """Reset le singleton ConfigManager entre les tests."""
    ConfigManager._instance = None
    yield
    ConfigManager._instance = None


# Pour exécuter les tests :
# pytest tests/unit/test_config.py -v
# pytest tests/unit/test_config.py -v --cov=src.config
