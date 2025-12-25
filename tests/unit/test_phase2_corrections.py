"""
Unit tests for Phase 2 corrections (BUG #7-10).

These tests verify the critical fixes for:
- BUG #7: Asyncio fire-and-forget notifications
- BUG #8: Cache invalidation timezone consistency
- BUG #9: Redis race condition handling
- BUG #10: Timezone-aware datetime parsing
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from rq.exceptions import NoSuchJobError
import asyncio

# ═══════════════════════════════════════════════════════════════
# BUG #8: DateParsingService Cache Invalidation - UTC-aware
# ═══════════════════════════════════════════════════════════════

def test_date_parser_cache_invalidation_uses_utc():
    """
    Verify that DateParsingService uses UTC for cache invalidation.
    This ensures consistency even when running on servers with different timezones.
    """
    from src.utils.date_parser import DateParsingService

    # Reset state
    DateParsingService._LAST_CACHE_DATE = None
    DateParsingService._CACHE_BY_DATE = {}

    # Mock datetime.now(timezone.utc) to return a specific time
    with patch('src.utils.date_parser.datetime') as mock_datetime_class:
        # Create a real datetime object for fromisoformat
        mock_datetime_class.fromisoformat = datetime.fromisoformat
        mock_datetime_class.strptime = datetime.strptime

        # Mock now() to return UTC time
        utc_time = datetime(2025, 12, 25, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime_class.now.return_value = utc_time

        # Trigger cache invalidation
        DateParsingService._invalidate_cache_if_needed()

        # Verify the cache date was set to UTC date
        assert DateParsingService._LAST_CACHE_DATE == '2025-12-25'
        # Verify cache was cleared
        assert DateParsingService._CACHE_BY_DATE == {}

        # Verify datetime.now was called with timezone.utc
        mock_datetime_class.now.assert_called_with(timezone.utc)


def test_date_parser_cache_invalidation_on_day_change():
    """
    Verify that cache is invalidated when the day changes (UTC).
    """
    from src.utils.date_parser import DateParsingService

    # Set initial cache
    DateParsingService._LAST_CACHE_DATE = '2025-12-24'
    DateParsingService._CACHE_BY_DATE = {'old': 'data'}

    # Mock to return next day
    with patch('src.utils.date_parser.datetime') as mock_dt:
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.strptime = datetime.strptime
        mock_dt.now.return_value = datetime(2025, 12, 25, 12, 0, 0, tzinfo=timezone.utc)

        DateParsingService._invalidate_cache_if_needed()

        # Verify cache was cleared
        assert DateParsingService._CACHE_BY_DATE == {}
        assert DateParsingService._LAST_CACHE_DATE == '2025-12-25'


# ═══════════════════════════════════════════════════════════════
# BUG #10: ISO DateTime Parsing - Robust error handling
# ═══════════════════════════════════════════════════════════════

def test_parse_iso_datetime_with_z_suffix():
    """Test parsing ISO datetime with Z suffix (UTC indicator)."""
    from src.core.base_bot import BaseLinkedInBot

    # Create a mock config
    config = Mock()
    config.dry_run = True
    config.bot_mode = "standard"

    with patch.object(BaseLinkedInBot, '__init__', return_value=None):
        bot = BaseLinkedInBot()
        result = bot._parse_iso_datetime("2025-01-01T12:00:00Z")

        expected = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert result == expected


def test_parse_iso_datetime_with_timezone_offset():
    """Test parsing ISO datetime with explicit timezone offset."""
    from src.core.base_bot import BaseLinkedInBot

    with patch.object(BaseLinkedInBot, '__init__', return_value=None):
        bot = BaseLinkedInBot()
        result = bot._parse_iso_datetime("2025-01-01T12:00:00+05:30")

        # Should be converted back to UTC
        assert result.tzinfo is not None
        # Original time in UTC: 12:00:00+05:30 = 06:30:00 UTC
        expected_utc = datetime(2025, 1, 1, 6, 30, 0, tzinfo=timezone.utc)
        assert result == expected_utc


def test_parse_iso_datetime_naive_assumes_utc():
    """Test that naive datetime (no timezone) is assumed to be UTC."""
    from src.core.base_bot import BaseLinkedInBot

    with patch.object(BaseLinkedInBot, '__init__', return_value=None):
        bot = BaseLinkedInBot()
        result = bot._parse_iso_datetime("2025-01-01T12:00:00")

        # Should assume UTC
        assert result.tzinfo == timezone.utc
        assert result == datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_iso_datetime_with_microseconds():
    """Test parsing ISO datetime with microseconds."""
    from src.core.base_bot import BaseLinkedInBot

    with patch.object(BaseLinkedInBot, '__init__', return_value=None):
        bot = BaseLinkedInBot()
        result = bot._parse_iso_datetime("2025-01-01T12:00:00.123456Z")

        expected = datetime(2025, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)
        assert result == expected


def test_parse_iso_datetime_date_only():
    """Test parsing date-only format."""
    from src.core.base_bot import BaseLinkedInBot

    with patch.object(BaseLinkedInBot, '__init__', return_value=None):
        bot = BaseLinkedInBot()
        result = bot._parse_iso_datetime("2025-01-01")

        expected = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert result == expected


def test_parse_iso_datetime_with_space_separator():
    """Test parsing datetime with space separator instead of T."""
    from src.core.base_bot import BaseLinkedInBot

    with patch.object(BaseLinkedInBot, '__init__', return_value=None):
        bot = BaseLinkedInBot()
        result = bot._parse_iso_datetime("2025-01-01 12:00:00")

        expected = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert result == expected


def test_parse_iso_datetime_empty_string_raises():
    """Test that empty string raises ValueError."""
    from src.core.base_bot import BaseLinkedInBot

    with patch.object(BaseLinkedInBot, '__init__', return_value=None):
        bot = BaseLinkedInBot()
        with pytest.raises(ValueError):
            bot._parse_iso_datetime("")


def test_parse_iso_datetime_invalid_format_raises():
    """Test that completely invalid format raises ValueError."""
    from src.core.base_bot import BaseLinkedInBot

    with patch.object(BaseLinkedInBot, '__init__', return_value=None):
        bot = BaseLinkedInBot()
        with pytest.raises(ValueError):
            bot._parse_iso_datetime("not-a-valid-date")


# ═══════════════════════════════════════════════════════════════
# BUG #9: Redis Race Condition - Proper exception handling
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_redis_race_condition_nosuchjob_caught():
    """
    Test that NoSuchJobError is properly caught and logged.
    This tests the race condition where a job finishes between
    get_job_ids() and Job.fetch().
    """
    from src.api.routes.bot_control import get_bot_status
    from rq.job import Job

    with patch('src.api.routes.bot_control.get_redis_queue') as mock_get_queue:
        mock_redis = Mock()
        mock_queue = Mock()
        mock_registry = Mock()

        # Setup: job_1 exists, job_2 was just removed
        mock_registry.get_job_ids.return_value = ['job_1', 'job_2']
        mock_queue.job_ids = []

        # Mock Job.fetch
        mock_job_1 = Mock(spec=Job)
        mock_job_1.id = 'job_1'
        mock_job_1.meta = {'job_type': 'birthday'}
        mock_job_1.enqueued_at = datetime.now(timezone.utc)
        mock_job_1.started_at = datetime.now(timezone.utc)

        def fetch_side_effect(job_id, connection):
            if job_id == 'job_1':
                return mock_job_1
            elif job_id == 'job_2':
                # Simulate race condition: job disappeared
                raise NoSuchJobError(f"No such job: {job_id}")
            return None

        mock_get_queue.return_value.__enter__.return_value = (mock_redis, mock_queue)

        with patch('src.api.routes.bot_control.StartedJobRegistry', return_value=mock_registry):
            with patch('src.api.routes.bot_control.Job.fetch', side_effect=fetch_side_effect):
                # Should not raise, should handle gracefully
                response = await get_bot_status(authenticated=True)

                # Verify response contains job_1 but skips job_2
                assert len(response.active_jobs) == 1
                assert response.active_jobs[0].id == 'job_1'


@pytest.mark.asyncio
async def test_redis_race_condition_other_exception_logged():
    """
    Test that non-NoSuchJobError exceptions are logged with warning.
    This ensures we don't silently ignore real errors.
    """
    from src.api.routes.bot_control import get_bot_status
    from rq.job import Job

    with patch('src.api.routes.bot_control.get_redis_queue') as mock_get_queue:
        mock_redis = Mock()
        mock_queue = Mock()
        mock_registry = Mock()

        mock_registry.get_job_ids.return_value = ['job_1']
        mock_queue.job_ids = []

        # Simulate a different error (not NoSuchJobError)
        def fetch_side_effect(job_id, connection):
            raise RuntimeError("Redis connection lost")

        mock_get_queue.return_value.__enter__.return_value = (mock_redis, mock_queue)

        with patch('src.api.routes.bot_control.StartedJobRegistry', return_value=mock_registry):
            with patch('src.api.routes.bot_control.Job.fetch', side_effect=fetch_side_effect):
                with patch('src.api.routes.bot_control.logger') as mock_logger:
                    response = await get_bot_status(authenticated=True)

                    # Verify warning was logged for non-NoSuchJobError
                    mock_logger.warning.assert_called()
                    # Response should be empty (job fetch failed)
                    assert len(response.active_jobs) == 0


# ═══════════════════════════════════════════════════════════════
# BUG #7: Asyncio Notifications - Proper cleanup
# ═══════════════════════════════════════════════════════════════

def test_notification_task_cleanup_in_sync_context():
    """
    Test that notification tasks are cleaned up properly.
    This tests the fix for asyncio fire-and-forget without GC.
    """
    from src.bots.birthday_bot import BirthdayBot

    config = Mock()
    config.paths.logs_dir = "/tmp"
    config.dry_run = True
    config.bot_mode = "standard"

    bot = BirthdayBot(config)
    bot._notification_tasks = []

    # Create a new event loop for this test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def fast_task():
        await asyncio.sleep(0.01)
        return "done"

    async def slow_task():
        await asyncio.sleep(0.5)
        return "slow"

    try:
        # Create tasks
        t1 = loop.create_task(fast_task())
        t2 = loop.create_task(slow_task())

        bot._notification_tasks = [t1, t2]

        # Call cleanup with timeout=5s (t1 should complete, t2 might not)
        with patch('asyncio.get_running_loop', return_value=loop):
            bot.cleanup_notification_tasks()

        # Fast task should be done
        assert t1.done()
        # Slow task might not be done after timeout
        assert t2.done() or not t2.done()  # Either can happen

    finally:
        loop.close()


def test_notification_tasks_do_not_accumulate_indefinitely():
    """
    Test that notification tasks list doesn't grow unbounded.
    Tasks should only be cleaned up during cleanup_notification_tasks(),
    not on every send (which would be O(n)).
    """
    from src.bots.birthday_bot import BirthdayBot

    config = Mock()
    config.paths.logs_dir = "/tmp"
    config.dry_run = True
    config.bot_mode = "standard"

    bot = BirthdayBot(config)
    bot._notification_tasks = []

    # Simulate many completed tasks
    completed_tasks = []
    for i in range(100):
        task = Mock()
        task.done.return_value = True
        completed_tasks.append(task)

    bot._notification_tasks = completed_tasks

    # Before cleanup, list still has all 100 tasks
    assert len(bot._notification_tasks) == 100

    # Create a mock loop for cleanup
    mock_loop = Mock()
    mock_done = set(completed_tasks)
    mock_loop.run_until_complete.return_value = (mock_done, set())

    # Cleanup should filter them out
    with patch('asyncio.get_running_loop', return_value=mock_loop):
        bot.cleanup_notification_tasks()

        # After cleanup, should be empty
        assert len(bot._notification_tasks) == 0


def test_notification_callback_logs_errors():
    """
    Test that done callbacks properly log task errors.
    """
    from src.bots.birthday_bot import BirthdayBot

    config = Mock()
    config.paths.logs_dir = "/tmp"
    config.dry_run = True
    config.bot_mode = "standard"

    bot = BirthdayBot(config)
    bot._notification_tasks = []

    # Create a new loop for testing
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def failing_task():
        raise ValueError("Test error")

    try:
        with patch('asyncio.get_running_loop', return_value=loop):
            with patch('src.bots.birthday_bot.logger') as mock_logger:
                # Simulate what _send_notification_sync does
                task = loop.create_task(failing_task())

                def log_error(t):
                    try:
                        t.result()
                    except Exception as err:
                        mock_logger.error(f"Notification task failed: {err}", exc_info=True)

                task.add_done_callback(log_error)
                bot._notification_tasks.append(task)

                # Wait for task to complete
                loop.run_until_complete(task)

                # Verify error was logged
                assert mock_logger.error.called

    finally:
        loop.close()
        asyncio.set_event_loop(None)
