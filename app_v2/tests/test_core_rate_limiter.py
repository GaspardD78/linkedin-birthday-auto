"""
Unit tests for rate limiter with atomic operations and circuit breaker.

Tests cover:
- Quota enforcement (daily, weekly, per-session)
- Atomic operations
- Circuit breaker logic
- Fallback to database
- Error handling
"""

import pytest
from datetime import datetime, timedelta, timezone

from app_v2.core.rate_limiter import RateLimiter
from app_v2.db.models import Interaction


@pytest.mark.unit
class TestRateLimiterQuotaEnforcement:
    """Test quota enforcement across different time periods."""

    async def test_can_send_message_all_checks_pass(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test that can_send_message returns True when all checks pass."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        result = await limiter.can_send_message()
        assert result is True

    async def test_session_limit_enforcement(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test that session limit is enforced."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        # Simulate sending messages up to limit
        for i in range(test_settings.max_messages_per_execution):
            assert await limiter.can_send_message() is True
            limiter._messages_sent_this_session = i + 1

        # Next message should be rejected
        assert await limiter.can_send_message() is False

    async def test_circuit_breaker_opens_on_errors(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test that circuit breaker opens after consecutive errors."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        # Simulate 3 failed messages
        for i in range(3):
            assert await limiter.can_send_message() is True
            await limiter.record_message(
                contact_id=1,
                success=False,
                message_text="Test message",
            )

        # Circuit should be open now
        assert await limiter.can_send_message() is False

    async def test_circuit_breaker_resets_on_success(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test that circuit breaker resets after successful message."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        # Open circuit
        limiter._error_count = 3
        limiter._circuit_open_until = datetime.now(timezone.utc) + timedelta(seconds=1)

        # Should be open
        assert await limiter.can_send_message() is False

        # Set circuit to closed
        limiter._circuit_open_until = None
        limiter._error_count = 0

        # Should be able to send
        assert await limiter.can_send_message() is True

    async def test_error_count_resets_on_success(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test that error counter resets after successful message."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        # Set error count
        limiter._error_count = 2

        # Record successful message
        from app_v2.db.models import Contact
        contact = Contact(
            name="Test User",
            profile_url="https://test.com",
            birth_date=None,
        )
        test_db_session.add(contact)
        await test_db_session.flush()

        await limiter.record_message(
            contact_id=contact.id,
            success=True,
            message_text="Test message",
        )

        # Error count should reset
        assert limiter._error_count == 0

    async def test_daily_limit_enforcement(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test that daily limit is enforced via Redis."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        # Simulate reaching daily limit
        key = limiter._get_daily_key()
        await test_redis_mock.set(key, test_settings.max_messages_per_day)

        # Should be rejected
        assert await limiter.can_send_message() is False

    async def test_weekly_limit_enforcement(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test that weekly limit is enforced via Redis."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        # Simulate reaching weekly limit
        key = limiter._get_weekly_key()
        await test_redis_mock.set(key, test_settings.max_messages_per_week)

        # Should be rejected
        assert await limiter.can_send_message() is False


@pytest.mark.unit
class TestRateLimiterQuotaTracking:
    """Test quota tracking and counter operations."""

    async def test_record_message_increments_session_counter(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test that recording a successful message increments session counter."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        from app_v2.db.models import Contact
        contact = Contact(
            name="Test User",
            profile_url="https://test.com",
        )
        test_db_session.add(contact)
        await test_db_session.flush()

        assert limiter._messages_sent_this_session == 0

        await limiter.record_message(
            contact_id=contact.id,
            success=True,
            message_text="Test message",
        )

        assert limiter._messages_sent_this_session == 1

    async def test_record_message_increments_daily_counter(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test that recording a message increments Redis daily counter."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        from app_v2.db.models import Contact
        contact = Contact(
            name="Test User",
            profile_url="https://test.com",
        )
        test_db_session.add(contact)
        await test_db_session.flush()

        await limiter.record_message(
            contact_id=contact.id,
            success=True,
            message_text="Test message",
        )

        # Check Redis counter was incremented
        key = limiter._get_daily_key()
        count = await test_redis_mock.get(key)
        assert count == "1"

    async def test_record_message_stores_interaction(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test that recording a message stores interaction in database."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        from app_v2.db.models import Contact
        contact = Contact(
            name="Test User",
            profile_url="https://test.com",
        )
        test_db_session.add(contact)
        await test_db_session.flush()

        await limiter.record_message(
            contact_id=contact.id,
            success=True,
            message_text="Test birthday message",
        )

        # Verify interaction was created
        from sqlalchemy import select
        stmt = select(Interaction).where(Interaction.contact_id == contact.id)
        result = await test_db_session.execute(stmt)
        interaction = result.scalar()

        assert interaction is not None
        assert interaction.type == "birthday_sent"
        assert interaction.status == "success"


@pytest.mark.unit
class TestRateLimiterFallback:
    """Test fallback behavior when Redis is unavailable."""

    async def test_can_send_message_without_redis(
        self, test_db_session, test_settings, populated_db
    ):
        """Test that rate limiter works without Redis (using database)."""
        # No Redis client provided
        limiter = RateLimiter(test_settings, test_db_session, redis_client=None)

        result = await limiter.can_send_message()
        # Should still work (falls back to DB)
        assert result is True

    async def test_get_daily_count_from_database(
        self, test_db_session, test_settings, populated_db
    ):
        """Test that daily count can be retrieved from database."""
        limiter = RateLimiter(test_settings, test_db_session, redis_client=None)

        count = await limiter._get_daily_count_db()
        # Should return count of today's successful messages
        assert isinstance(count, int)
        assert count >= 0


@pytest.mark.unit
class TestRateLimiterRemainingQuota:
    """Test remaining quota getters."""

    async def test_get_remaining_daily_quota(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test calculation of remaining daily quota."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        remaining = await limiter.get_remaining_daily_quota()
        assert remaining == test_settings.max_messages_per_day

    async def test_get_remaining_weekly_quota(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test calculation of remaining weekly quota."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        remaining = await limiter.get_remaining_weekly_quota()
        assert remaining == test_settings.max_messages_per_week

    async def test_get_remaining_session_quota(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test calculation of remaining session quota."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        # Initial quota should be full
        remaining = await limiter.get_remaining_session_quota()
        assert remaining == test_settings.max_messages_per_execution

        # After sending a message
        limiter._messages_sent_this_session = 2
        remaining = await limiter.get_remaining_session_quota()
        assert remaining == test_settings.max_messages_per_execution - 2


@pytest.mark.unit
class TestRateLimiterRandomDelay:
    """Test delay generation."""

    async def test_get_random_delay_is_in_range(
        self, test_db_session, test_settings, test_redis_mock
    ):
        """Test that random delay is within configured range."""
        limiter = RateLimiter(test_settings, test_db_session, test_redis_mock)

        for _ in range(10):
            delay = await limiter.get_random_delay()
            assert test_settings.min_delay_between_messages <= delay <= test_settings.max_delay_between_messages
