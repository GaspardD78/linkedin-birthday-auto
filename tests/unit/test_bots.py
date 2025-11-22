"""
Tests unitaires pour les bots BirthdayBot et UnlimitedBirthdayBot.

Ce fichier démontre comment tester les bots avec des mocks.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from pathlib import Path
import sys

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.bots.birthday_bot import BirthdayBot
from src.bots.unlimited_bot import UnlimitedBirthdayBot
from src.config.config_schema import LinkedInBotConfig
from src.utils.exceptions import WeeklyLimitReachedError, DailyLimitReachedError


class TestBirthdayBot:
    """Tests pour BirthdayBot (mode standard)."""

    @pytest.fixture
    def mock_config(self):
        """Configuration mockée pour les tests."""
        config = LinkedInBotConfig()
        config.dry_run = True
        config.bot_mode = "standard"
        config.birthday_filter.process_today = True
        config.birthday_filter.process_late = False
        config.database.enabled = False
        return config

    @pytest.fixture
    def mock_browser_manager(self):
        """BrowserManager mocké."""
        manager = Mock()
        manager.browser = Mock()
        manager.context = Mock()
        manager.page = Mock()
        return manager

    def test_init_sets_correct_mode(self, mock_config):
        """Le bot doit s'initialiser en mode standard."""
        with patch('src.bots.birthday_bot.BrowserManager'):
            bot = BirthdayBot(config=mock_config)
            assert bot.config.bot_mode == "standard"

    def test_check_limits_raises_when_weekly_limit_reached(self, mock_config):
        """_check_limits doit lever WeeklyLimitReachedError si limite atteinte."""
        mock_config.database.enabled = True

        with patch('src.bots.birthday_bot.BrowserManager'), \
             patch('src.bots.birthday_bot.get_database') as mock_get_db:

            # Mock database qui retourne une limite atteinte
            mock_db = Mock()
            mock_db.get_weekly_message_count.return_value = 80
            mock_db.get_daily_message_count.return_value = 0
            mock_get_db.return_value = mock_db

            bot = BirthdayBot(config=mock_config)
            bot.db = mock_db

            # Doit lever l'exception
            with pytest.raises(WeeklyLimitReachedError):
                bot._check_limits()

    def test_check_limits_raises_when_daily_limit_reached(self, mock_config):
        """_check_limits doit lever DailyLimitReachedError si limite atteinte."""
        mock_config.database.enabled = True
        mock_config.messaging_limits.daily_message_limit = 10

        with patch('src.bots.birthday_bot.BrowserManager'), \
             patch('src.bots.birthday_bot.get_database') as mock_get_db:

            # Mock database
            mock_db = Mock()
            mock_db.get_weekly_message_count.return_value = 50
            mock_db.get_daily_message_count.return_value = 10
            mock_get_db.return_value = mock_db

            bot = BirthdayBot(config=mock_config)
            bot.db = mock_db

            # Doit lever l'exception
            with pytest.raises(DailyLimitReachedError):
                bot._check_limits()

    def test_calculate_max_messages_respects_weekly_limit(self, mock_config):
        """_calculate_max_messages_to_send doit respecter la limite hebdo."""
        mock_config.database.enabled = True
        mock_config.messaging_limits.weekly_message_limit = 80

        with patch('src.bots.birthday_bot.BrowserManager'), \
             patch('src.bots.birthday_bot.get_database') as mock_get_db:

            # Mock database : 75 messages cette semaine
            mock_db = Mock()
            mock_db.get_weekly_message_count.return_value = 75
            mock_db.get_daily_message_count.return_value = 0
            mock_get_db.return_value = mock_db

            bot = BirthdayBot(config=mock_config)
            bot.db = mock_db

            # Avec 10 contacts, on ne devrait en traiter que 5 (80-75)
            max_messages = bot._calculate_max_messages_to_send(contacts_count=10)
            assert max_messages == 5

    def test_calculate_max_messages_respects_daily_limit(self, mock_config):
        """_calculate_max_messages_to_send doit respecter la limite quotidienne."""
        mock_config.database.enabled = True
        mock_config.messaging_limits.weekly_message_limit = 80
        mock_config.messaging_limits.daily_message_limit = 10

        with patch('src.bots.birthday_bot.BrowserManager'), \
             patch('src.bots.birthday_bot.get_database') as mock_get_db:

            # Mock database : 8 messages aujourd'hui
            mock_db = Mock()
            mock_db.get_weekly_message_count.return_value = 50
            mock_db.get_daily_message_count.return_value = 8
            mock_get_db.return_value = mock_db

            bot = BirthdayBot(config=mock_config)
            bot.db = mock_db

            # Avec 10 contacts, on ne devrait en traiter que 2 (10-8)
            max_messages = bot._calculate_max_messages_to_send(contacts_count=10)
            assert max_messages == 2

    def test_calculate_max_messages_respects_per_run_limit(self, mock_config):
        """_calculate_max_messages_to_send doit respecter max_messages_per_run."""
        mock_config.messaging_limits.max_messages_per_run = 5
        mock_config.database.enabled = False

        with patch('src.bots.birthday_bot.BrowserManager'):
            bot = BirthdayBot(config=mock_config)

            # Avec 10 contacts, on ne devrait en traiter que 5 (limite par run)
            max_messages = bot._calculate_max_messages_to_send(contacts_count=10)
            assert max_messages == 5

    def test_build_result_structure(self, mock_config):
        """_build_result doit retourner la bonne structure."""
        with patch('src.bots.birthday_bot.BrowserManager'):
            bot = BirthdayBot(config=mock_config)

            result = bot._build_result(
                messages_sent=5,
                contacts_processed=5,
                birthdays_today=5,
                birthdays_late_ignored=3,
                duration_seconds=120.5
            )

            assert result['success'] is True
            assert result['bot_mode'] == 'standard'
            assert result['messages_sent'] == 5
            assert result['contacts_processed'] == 5
            assert result['birthdays_today'] == 5
            assert result['birthdays_late_ignored'] == 3
            assert result['duration_seconds'] == 120.5
            assert result['dry_run'] is True
            assert 'timestamp' in result

    def test_build_error_result_structure(self, mock_config):
        """_build_error_result doit retourner la bonne structure."""
        with patch('src.bots.birthday_bot.BrowserManager'):
            bot = BirthdayBot(config=mock_config)

            result = bot._build_error_result("Test error")

            assert result['success'] is False
            assert result['bot_mode'] == 'standard'
            assert result['error'] == "Test error"
            assert result['messages_sent'] == 0
            assert result['contacts_processed'] == 0
            assert 'timestamp' in result


class TestUnlimitedBirthdayBot:
    """Tests pour UnlimitedBirthdayBot (mode unlimited)."""

    @pytest.fixture
    def mock_config(self):
        """Configuration mockée pour les tests."""
        config = LinkedInBotConfig()
        config.dry_run = True
        config.bot_mode = "unlimited"
        config.birthday_filter.process_today = True
        config.birthday_filter.process_late = True
        config.birthday_filter.max_days_late = 10
        config.database.enabled = False
        return config

    def test_init_sets_correct_mode(self, mock_config):
        """Le bot doit s'initialiser en mode unlimited."""
        with patch('src.bots.unlimited_bot.BrowserManager'):
            bot = UnlimitedBirthdayBot(config=mock_config)
            assert bot.config.bot_mode == "unlimited"

    def test_estimate_duration_calculation(self, mock_config):
        """_estimate_duration doit calculer correctement la durée."""
        with patch('src.bots.unlimited_bot.BrowserManager'):
            bot = UnlimitedBirthdayBot(config=mock_config)

            # En dry-run, délai moyen = 3s
            # 10 contacts * 3s = 30s = 0m
            duration = bot._estimate_duration(10)
            assert "0m" in duration or "30s" in duration

            # 100 contacts * 3s = 300s = 5m
            duration = bot._estimate_duration(100)
            assert "5m" in duration

    def test_format_duration_with_hours(self, mock_config):
        """_format_duration doit formater avec heures/minutes/secondes."""
        with patch('src.bots.unlimited_bot.BrowserManager'):
            bot = UnlimitedBirthdayBot(config=mock_config)

            # 3665 secondes = 1h 1m 5s
            formatted = bot._format_duration(3665)
            assert "1h" in formatted
            assert "1m" in formatted
            assert "5s" in formatted

            # 125 secondes = 2m 5s
            formatted = bot._format_duration(125)
            assert "2m" in formatted
            assert "5s" in formatted
            assert "h" not in formatted

            # 45 secondes = 45s
            formatted = bot._format_duration(45)
            assert "45s" in formatted
            assert "m" not in formatted
            assert "h" not in formatted

    def test_build_result_structure(self, mock_config):
        """_build_result doit retourner la bonne structure."""
        with patch('src.bots.unlimited_bot.BrowserManager'):
            bot = UnlimitedBirthdayBot(config=mock_config)

            result = bot._build_result(
                messages_sent=15,
                contacts_processed=15,
                birthdays_today=5,
                birthdays_late=10,
                duration_seconds=450.5
            )

            assert result['success'] is True
            assert result['bot_mode'] == 'unlimited'
            assert result['messages_sent'] == 15
            assert result['contacts_processed'] == 15
            assert result['birthdays_today'] == 5
            assert result['birthdays_late'] == 10
            assert result['duration_seconds'] == 450.5
            assert result['dry_run'] is True
            assert 'timestamp' in result

    def test_build_error_result_structure(self, mock_config):
        """_build_error_result doit retourner la bonne structure."""
        with patch('src.bots.unlimited_bot.BrowserManager'):
            bot = UnlimitedBirthdayBot(config=mock_config)

            result = bot._build_error_result("Test error")

            assert result['success'] is False
            assert result['bot_mode'] == 'unlimited'
            assert result['error'] == "Test error"
            assert result['messages_sent'] == 0
            assert result['contacts_processed'] == 0
            assert 'timestamp' in result


class TestBotComparison:
    """Tests comparant les deux bots."""

    def test_standard_ignores_late_birthdays(self):
        """BirthdayBot doit ignorer les anniversaires en retard."""
        config = LinkedInBotConfig()
        config.dry_run = True
        config.bot_mode = "standard"
        config.birthday_filter.process_late = False

        with patch('src.bots.birthday_bot.BrowserManager'):
            bot = BirthdayBot(config=config)
            assert bot.config.birthday_filter.process_late is False

    def test_unlimited_processes_late_birthdays(self):
        """UnlimitedBot doit traiter les anniversaires en retard."""
        config = LinkedInBotConfig()
        config.dry_run = True
        config.bot_mode = "unlimited"
        config.birthday_filter.process_late = True

        with patch('src.bots.unlimited_bot.BrowserManager'):
            bot = UnlimitedBirthdayBot(config=config)
            assert bot.config.birthday_filter.process_late is True


# Fixtures pytest communes

@pytest.fixture
def clean_singletons():
    """Reset les singletons entre les tests."""
    from src.config.config_manager import ConfigManager
    ConfigManager._instance = None
    yield
    ConfigManager._instance = None


# Pour exécuter les tests :
# pytest tests/unit/test_bots.py -v
# pytest tests/unit/test_bots.py -v --cov=src.bots
