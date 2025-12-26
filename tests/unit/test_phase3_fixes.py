"""
Tests pour Phase 3: Incohérences Métier (INC #1, INC #2)

Ces tests valident les corrections des incohérences métier identifiées durant l'audit.
- INC #1: max_days_late hardcode vs config
- INC #2: messaging_limits source of truth
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from src.bots.unlimited_bot import run_unlimited_bot, UnlimitedBirthdayBot
from src.bots.birthday_bot import BirthdayBot
from src.config.config_schema import LinkedInBotConfig as Config, BirthdayFilterConfig as BirthdayFilter, MessagingLimitsConfig as MessagingLimits


class TestPhase3INC1MaxDaysLate:
    """Tests for INC #1: max_days_late config vs unlimited_bot hardcode"""

    def test_run_unlimited_bot_uses_config_max_days_late_when_none(self):
        """
        Test that run_unlimited_bot uses config value when max_days_late is None.

        Phase 3 Fix (INC #1):
        - Default parameter changed from hardcoded 10 to None
        - When None, loads from config.birthday_filter.max_days_late
        """
        mock_config = MagicMock(spec=Config)
        mock_config.birthday_filter = MagicMock(spec=BirthdayFilter)
        mock_config.birthday_filter.max_days_late = 25  # Config value
        mock_config.dry_run = False
        mock_config.messaging_limits = MagicMock(spec=MessagingLimits)
        mock_config.messaging_limits.weekly_message_limit = 999999
        mock_config.messaging_limits.daily_message_limit = 999999
        mock_config.model_copy = MagicMock(return_value=mock_config)

        # Mock the bot run method
        with patch('src.bots.unlimited_bot.UnlimitedBirthdayBot') as mock_bot_class:
            mock_bot_instance = MagicMock()
            mock_bot_instance.__enter__ = MagicMock(return_value=mock_bot_instance)
            mock_bot_instance.__exit__ = MagicMock(return_value=False)
            mock_bot_instance.run = MagicMock(return_value={'success': True})
            mock_bot_class.return_value = mock_bot_instance

            # Call with max_days_late=None (should use config value)
            result = run_unlimited_bot(config=mock_config, dry_run=False, max_days_late=None)

            # Verify the config was updated with the value from config
            assert mock_config.birthday_filter.max_days_late == 25

    def test_run_unlimited_bot_respects_explicit_max_days_late(self):
        """
        Test that explicit max_days_late parameter is respected over config.
        """
        mock_config = MagicMock(spec=Config)
        mock_config.birthday_filter = MagicMock(spec=BirthdayFilter)
        mock_config.birthday_filter.max_days_late = 25  # Config value
        mock_config.dry_run = False
        mock_config.messaging_limits = MagicMock(spec=MessagingLimits)
        mock_config.messaging_limits.weekly_message_limit = 999999
        mock_config.messaging_limits.daily_message_limit = 999999
        mock_config.model_copy = MagicMock(return_value=mock_config)

        with patch('src.bots.unlimited_bot.UnlimitedBirthdayBot') as mock_bot_class:
            mock_bot_instance = MagicMock()
            mock_bot_instance.__enter__ = MagicMock(return_value=mock_bot_instance)
            mock_bot_instance.__exit__ = MagicMock(return_value=False)
            mock_bot_instance.run = MagicMock(return_value={'success': True})
            mock_bot_class.return_value = mock_bot_instance

            # Call with explicit max_days_late=30 (should override config)
            result = run_unlimited_bot(config=mock_config, dry_run=False, max_days_late=30)

            # Verify the config was updated with the explicit value
            assert mock_config.birthday_filter.max_days_late == 30


class TestPhase3INC2MessagingLimits:
    """Tests for INC #2: messaging_limits source of truth"""

    def test_birthday_bot_check_limits_uses_config_limits(self):
        """
        Test that BirthdayBot._check_limits uses limits from config, not DB.

        Phase 3 Fix (INC #2):
        - Limits come from config.yaml (policy)
        - Counters come from database (current state)
        - This separates concerns properly
        """
        mock_config = MagicMock(spec=Config)
        mock_config.bot_mode = "standard"
        mock_config.messaging_limits = MagicMock(spec=MessagingLimits)
        mock_config.messaging_limits.weekly_message_limit = 100
        mock_config.messaging_limits.daily_message_limit = 15
        mock_config.paths = MagicMock()
        mock_config.paths.logs_dir = "/tmp/logs"

        mock_db = MagicMock()
        mock_db.get_weekly_message_count = MagicMock(return_value=50)
        mock_db.get_daily_message_count = MagicMock(return_value=10)

        with patch('src.bots.birthday_bot.BirthdayBot.__init__', return_value=None):
            bot = BirthdayBot(config=mock_config)
            bot.db = mock_db
            bot.config = mock_config

            # This should not raise any error (50 < 100, 10 < 15)
            try:
                bot._check_limits()
                success = True
            except Exception as e:
                success = False

            assert success, "Should not raise error when under limits"

            # Verify DB was queried for counters
            mock_db.get_weekly_message_count.assert_called_once()
            mock_db.get_daily_message_count.assert_called_once()

    def test_birthday_bot_respects_weekly_limit_from_config(self):
        """
        Test that weekly limit from config is enforced.
        """
        from src.utils.exceptions import WeeklyLimitReachedError

        mock_config = MagicMock(spec=Config)
        mock_config.bot_mode = "standard"
        mock_config.messaging_limits = MagicMock(spec=MessagingLimits)
        mock_config.messaging_limits.weekly_message_limit = 100  # Config limit
        mock_config.messaging_limits.daily_message_limit = None
        mock_config.paths = MagicMock()
        mock_config.paths.logs_dir = "/tmp/logs"

        mock_db = MagicMock()
        mock_db.get_weekly_message_count = MagicMock(return_value=105)  # Over limit

        with patch('src.bots.birthday_bot.BirthdayBot.__init__', return_value=None):
            bot = BirthdayBot(config=mock_config)
            bot.db = mock_db
            bot.config = mock_config

            # Should raise WeeklyLimitReachedError
            with pytest.raises(WeeklyLimitReachedError):
                bot._check_limits()

    def test_birthday_bot_calculates_max_allowed_respects_config_limits(self):
        """
        Test that _calculate_max_allowed_messages respects config limits.
        """
        mock_config = MagicMock(spec=Config)
        mock_config.bot_mode = "standard"
        mock_config.messaging_limits = MagicMock(spec=MessagingLimits)
        mock_config.messaging_limits.max_messages_per_run = 15
        mock_config.messaging_limits.weekly_message_limit = 100
        mock_config.messaging_limits.daily_message_limit = 20
        mock_config.paths = MagicMock()
        mock_config.paths.logs_dir = "/tmp/logs"

        mock_db = MagicMock()
        mock_db.get_weekly_message_count = MagicMock(return_value=85)  # 15 left in weekly budget
        mock_db.get_daily_message_count = MagicMock(return_value=10)  # 10 left in daily budget

        with patch('src.bots.birthday_bot.BirthdayBot.__init__', return_value=None):
            bot = BirthdayBot(config=mock_config)
            bot.db = mock_db
            bot.config = mock_config

            max_allowed = bot._calculate_max_allowed_messages()

            # Should be min(15, 15, 10) = 10
            assert max_allowed == 10

    def test_unlimited_bot_overrides_limits_intentionally(self):
        """
        Test that UnlimitedBirthdayBot intentionally overrides messaging limits.

        This validates that INC #2 is properly handled: the "dual source" is
        intentional for unlimited mode, and it's documented.
        """
        mock_config = MagicMock(spec=Config)
        mock_config.birthday_filter = MagicMock(spec=BirthdayFilter)
        mock_config.birthday_filter.max_days_late = 10
        mock_config.birthday_filter.process_today = False
        mock_config.birthday_filter.process_late = False
        mock_config.dry_run = False
        mock_config.messaging_limits = MagicMock(spec=MessagingLimits)
        mock_config.messaging_limits.weekly_message_limit = 100
        mock_config.messaging_limits.daily_message_limit = 15
        mock_config.model_copy = MagicMock(return_value=mock_config)

        with patch('src.bots.unlimited_bot.UnlimitedBirthdayBot') as mock_bot_class:
            mock_bot_instance = MagicMock()
            mock_bot_instance.__enter__ = MagicMock(return_value=mock_bot_instance)
            mock_bot_instance.__exit__ = MagicMock(return_value=False)
            mock_bot_instance.run = MagicMock(return_value={'success': True})
            mock_bot_class.return_value = mock_bot_instance

            result = run_unlimited_bot(config=mock_config)

            # Verify limits were overridden to 999999 (as intended for unlimited mode)
            assert mock_config.messaging_limits.weekly_message_limit == 999999
            assert mock_config.messaging_limits.daily_message_limit == 999999


class TestPhase3ConfigConsistency:
    """Additional tests to ensure config consistency across modes"""

    def test_config_values_are_loaded_consistently(self):
        """
        Test that config values are consistently loaded from source.
        """
        # This test verifies that whether we use max_days_late parameter or not,
        # the config gets the right value
        mock_config = MagicMock(spec=Config)
        mock_config.birthday_filter = MagicMock(spec=BirthdayFilter)
        mock_config.birthday_filter.max_days_late = 10
        mock_config.dry_run = False
        mock_config.messaging_limits = MagicMock(spec=MessagingLimits)
        mock_config.messaging_limits.weekly_message_limit = 100
        mock_config.messaging_limits.daily_message_limit = 15
        mock_config.model_copy = MagicMock(return_value=mock_config)

        with patch('src.bots.unlimited_bot.UnlimitedBirthdayBot') as mock_bot_class:
            mock_bot_instance = MagicMock()
            mock_bot_instance.__enter__ = MagicMock(return_value=mock_bot_instance)
            mock_bot_instance.__exit__ = MagicMock(return_value=False)
            mock_bot_instance.run = MagicMock(return_value={'success': True})
            mock_bot_class.return_value = mock_bot_instance

            # Test 1: When max_days_late is None, should use config
            run_unlimited_bot(config=mock_config, max_days_late=None)
            assert mock_config.birthday_filter.max_days_late == 10

            # Reset for second test
            mock_config.birthday_filter.max_days_late = 10

            # Test 2: When max_days_late is provided, should use that
            run_unlimited_bot(config=mock_config, max_days_late=20)
            assert mock_config.birthday_filter.max_days_late == 20
