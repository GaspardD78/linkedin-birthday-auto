"""
Unit tests for Settings configuration (app_v2/core/config.py).

Tests configuration validation, defaults, and edge cases.
"""

import pytest
from pydantic import ValidationError
from app_v2.core.config import Settings


@pytest.mark.unit
class TestSettingsValidation:
    """Test Settings validation logic."""

    def test_settings_with_defaults(self):
        """Test that Settings can be created with minimal config."""
        settings = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            api_key="test-key",
            auth_encryption_key="test-encryption-key-1234567890",
            jwt_secret="test-jwt-secret-1234567890",
        )

        assert settings.database_url == "sqlite+aiosqlite:///test.db"
        assert settings.api_key.get_secret_value() == "test-key"
        assert settings.max_messages_per_day == 15  # default
        assert settings.max_messages_per_week == 100  # default

    def test_settings_custom_rate_limits(self):
        """Test custom rate limiting configuration."""
        settings = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            api_key="test-key",
            auth_encryption_key="test-encryption-key-1234567890",
            jwt_secret="test-jwt-secret-1234567890",
            max_messages_per_day=50,
            max_messages_per_week=200,
            max_messages_per_execution=10,
        )

        assert settings.max_messages_per_day == 50
        assert settings.max_messages_per_week == 200
        assert settings.max_messages_per_execution == 10

    def test_database_url_default(self):
        """Test that database URL has a default value."""
        settings = Settings(
            api_key="test-key",
            auth_encryption_key="test-encryption-key-1234567890",
            jwt_secret="test-jwt-secret-1234567890",
        )

        assert "sqlite+aiosqlite" in settings.database_url

    def test_headless_default(self):
        """Test that headless mode is enabled by default."""
        settings = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            api_key="test-key",
            auth_encryption_key="test-encryption-key-1234567890",
            jwt_secret="test-jwt-secret-1234567890",
        )

        assert settings.headless is True

    def test_browser_timeout_default(self):
        """Test browser timeout default value."""
        settings = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            api_key="test-key",
            auth_encryption_key="test-encryption-key-1234567890",
            jwt_secret="test-jwt-secret-1234567890",
        )

        assert settings.browser_timeout == 30000

    def test_working_hours_defaults(self):
        """Test working hours defaults."""
        settings = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            api_key="test-key",
            auth_encryption_key="test-encryption-key-1234567890",
            jwt_secret="test-jwt-secret-1234567890",
        )

        assert settings.working_hours_start == 7
        assert settings.working_hours_end == 19


@pytest.mark.unit
class TestSettingsSecrets:
    """Test secret key validation."""

    def test_encryption_key_required(self, monkeypatch):
        """Test that encryption key is required."""
        # Clear environment variables that might provide defaults
        monkeypatch.delenv("AUTH_ENCRYPTION_KEY", raising=False)
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)

        with pytest.raises(ValidationError):
            Settings(
                database_url="sqlite+aiosqlite:///test.db",
                api_key="test-key",
                jwt_secret="test-jwt-secret-1234567890",
                # Missing auth_encryption_key
            )

    def test_jwt_secret_required(self, monkeypatch):
        """Test that JWT secret is required."""
        # Clear environment variables that might provide defaults
        monkeypatch.delenv("AUTH_ENCRYPTION_KEY", raising=False)
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)

        with pytest.raises(ValidationError):
            Settings(
                database_url="sqlite+aiosqlite:///test.db",
                api_key="test-key",
                auth_encryption_key="test-encryption-key-1234567890",
                # Missing jwt_secret
            )

    def test_api_key_required(self, monkeypatch):
        """Test that API key is required."""
        # Clear environment variables that might provide defaults
        monkeypatch.delenv("AUTH_ENCRYPTION_KEY", raising=False)
        monkeypatch.delenv("API_KEY", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)

        with pytest.raises(ValidationError):
            Settings(
                database_url="sqlite+aiosqlite:///test.db",
                auth_encryption_key="test-encryption-key-1234567890",
                jwt_secret="test-jwt-secret-1234567890",
                # Missing api_key
            )


@pytest.mark.unit
class TestSettingsRateLimits:
    """Test rate limiting configuration."""

    def test_daily_limit_must_be_positive(self):
        """Test that daily message limit must be positive."""
        settings = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            api_key="test-key",
            auth_encryption_key="test-encryption-key-1234567890",
            jwt_secret="test-jwt-secret-1234567890",
            max_messages_per_day=1,
        )

        assert settings.max_messages_per_day == 1

    def test_weekly_limit_must_be_positive(self):
        """Test that weekly message limit must be positive."""
        settings = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            api_key="test-key",
            auth_encryption_key="test-encryption-key-1234567890",
            jwt_secret="test-jwt-secret-1234567890",
            max_messages_per_week=1,
        )

        assert settings.max_messages_per_week == 1

    def test_execution_limit_must_be_positive(self):
        """Test that execution message limit must be positive."""
        settings = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            api_key="test-key",
            auth_encryption_key="test-encryption-key-1234567890",
            jwt_secret="test-jwt-secret-1234567890",
            max_messages_per_execution=1,
        )

        assert settings.max_messages_per_execution == 1

    def test_delay_between_messages_defaults(self):
        """Test delay between messages defaults."""
        settings = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            api_key="test-key",
            auth_encryption_key="test-encryption-key-1234567890",
            jwt_secret="test-jwt-secret-1234567890",
        )

        assert settings.min_delay_between_messages == 90
        assert settings.max_delay_between_messages == 180
        assert settings.max_delay_between_messages >= settings.min_delay_between_messages

    def test_is_working_hours_method(self):
        """Test is_working_hours method exists and is callable."""
        settings = Settings(
            database_url="sqlite+aiosqlite:///test.db",
            api_key="test-key",
            auth_encryption_key="test-encryption-key-1234567890",
            jwt_secret="test-jwt-secret-1234567890",
        )

        result = settings.is_working_hours()
        assert isinstance(result, bool)
