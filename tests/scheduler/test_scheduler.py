"""Unit tests for scheduler.py

Note: These tests use mocked Redis/RQ to avoid dependencies.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.scheduler.scheduler import AutomationScheduler
from src.scheduler.models import (
    ScheduledJobConfig,
    BotType,
    ScheduleType,
    BirthdayBotConfig,
    VisitorBotConfig
)


@pytest.fixture
def temp_db():
    """Create temporary databases for testing."""
    config_fd, config_path = tempfile.mkstemp(suffix='_config.db')
    ap_fd, ap_path = tempfile.mkstemp(suffix='_apscheduler.db')
    os.close(config_fd)
    os.close(ap_fd)

    yield config_path, ap_path

    # Cleanup
    for path in [config_path, ap_path]:
        if os.path.exists(path):
            os.unlink(path)


@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    with patch('src.scheduler.scheduler.Redis') as mock_redis_class:
        mock_redis_instance = MagicMock()
        mock_redis_class.return_value = mock_redis_instance
        yield mock_redis_instance


@pytest.fixture
def mock_queue():
    """Mock RQ Queue."""
    with patch('src.scheduler.scheduler.Queue') as mock_queue_class:
        mock_queue_instance = MagicMock()
        mock_queue_class.return_value = mock_queue_instance

        # Mock enqueue method to return a fake job
        mock_job = MagicMock()
        mock_job.id = "test-rq-job-123"
        mock_queue_instance.enqueue.return_value = mock_job

        yield mock_queue_instance


@pytest.fixture
def scheduler(temp_db, mock_redis, mock_queue):
    """Create a scheduler instance with mocked dependencies."""
    config_path, ap_path = temp_db

    # Patch the database paths
    with patch('src.scheduler.job_store.JobConfigStore.__init__', lambda self: None), \
         patch('src.scheduler.job_store.JobExecutionStore.__init__', lambda self: None), \
         patch.object(AutomationScheduler, '_reload_jobs'):

        # Reset singleton
        AutomationScheduler._instance = None

        scheduler_instance = AutomationScheduler()

        # Manually set up stores with temp paths
        from src.scheduler.job_store import JobConfigStore, JobExecutionStore
        scheduler_instance.job_config_store = JobConfigStore(db_path=config_path)
        scheduler_instance.execution_store = JobExecutionStore(db_path=config_path)

        yield scheduler_instance

        # Shutdown
        if scheduler_instance.scheduler.running:
            scheduler_instance.shutdown(wait=False)


@pytest.fixture
def sample_birthday_job():
    """Create a sample Birthday Bot job."""
    return ScheduledJobConfig(
        name="Test Birthday Job",
        bot_type=BotType.BIRTHDAY,
        schedule_type=ScheduleType.DAILY,
        schedule_config={"hour": 8, "minute": 0},
        bot_config=BirthdayBotConfig(
            dry_run=False,
            process_late=True,
            max_days_late=7
        )
    )


@pytest.fixture
def sample_visitor_job():
    """Create a sample Visitor Bot job."""
    return ScheduledJobConfig(
        name="Test Visitor Job",
        bot_type=BotType.VISITOR,
        schedule_type=ScheduleType.WEEKLY,
        schedule_config={"hour": 14, "minute": 0, "day_of_week": "mon"},
        bot_config=VisitorBotConfig(
            dry_run=True,
            limit=50
        )
    )


class TestAutomationScheduler:
    """Tests for AutomationScheduler."""

    def test_singleton_pattern(self, scheduler):
        """Test that scheduler implements singleton pattern."""
        # Create another instance
        scheduler2 = AutomationScheduler()

        # Should be the same instance
        assert scheduler is scheduler2

    def test_add_job(self, scheduler, sample_birthday_job):
        """Test adding a new job."""
        created = scheduler.add_job(sample_birthday_job)

        assert created.id == sample_birthday_job.id
        assert created.name == sample_birthday_job.name

        # Verify it's in the database
        retrieved = scheduler.get_job(sample_birthday_job.id)
        assert retrieved is not None

    def test_add_disabled_job(self, scheduler, sample_birthday_job):
        """Test adding a disabled job (should not be scheduled)."""
        sample_birthday_job.enabled = False

        created = scheduler.add_job(sample_birthday_job)

        assert created.enabled is False

        # Verify it's in database but not in APScheduler
        retrieved = scheduler.get_job(sample_birthday_job.id)
        assert retrieved is not None

        ap_job = scheduler.scheduler.get_job(sample_birthday_job.id)
        assert ap_job is None  # Not scheduled

    def test_update_job(self, scheduler, sample_birthday_job):
        """Test updating a job."""
        # Create job
        scheduler.add_job(sample_birthday_job)

        # Update
        updates = {
            "name": "Updated Name",
            "enabled": False
        }
        updated = scheduler.update_job(sample_birthday_job.id, updates)

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.enabled is False

    def test_delete_job(self, scheduler, sample_birthday_job):
        """Test deleting a job."""
        # Create job
        scheduler.add_job(sample_birthday_job)

        # Delete
        success = scheduler.delete_job(sample_birthday_job.id)
        assert success is True

        # Verify it's gone
        retrieved = scheduler.get_job(sample_birthday_job.id)
        assert retrieved is None

    def test_toggle_job_disable(self, scheduler, sample_birthday_job):
        """Test disabling a job."""
        # Create enabled job
        scheduler.add_job(sample_birthday_job)

        # Disable
        updated = scheduler.toggle_job(sample_birthday_job.id, False)

        assert updated is not None
        assert updated.enabled is False

        # Should be removed from APScheduler
        ap_job = scheduler.scheduler.get_job(sample_birthday_job.id)
        assert ap_job is None

    def test_toggle_job_enable(self, scheduler, sample_birthday_job):
        """Test enabling a disabled job."""
        # Create disabled job
        sample_birthday_job.enabled = False
        scheduler.add_job(sample_birthday_job)

        # Enable
        updated = scheduler.toggle_job(sample_birthday_job.id, True)

        assert updated is not None
        assert updated.enabled is True

        # Should be scheduled in APScheduler
        ap_job = scheduler.scheduler.get_job(sample_birthday_job.id)
        assert ap_job is not None

    def test_list_jobs(self, scheduler, sample_birthday_job, sample_visitor_job):
        """Test listing jobs."""
        # Create two jobs
        scheduler.add_job(sample_birthday_job)
        scheduler.add_job(sample_visitor_job)

        # List all
        all_jobs = scheduler.list_jobs()
        assert len(all_jobs) == 2

    def test_list_enabled_only(self, scheduler, sample_birthday_job, sample_visitor_job):
        """Test listing only enabled jobs."""
        # Create one enabled, one disabled
        sample_visitor_job.enabled = False

        scheduler.add_job(sample_birthday_job)
        scheduler.add_job(sample_visitor_job)

        # List enabled only
        enabled = scheduler.list_jobs(enabled_only=True)
        assert len(enabled) == 1
        assert enabled[0].id == sample_birthday_job.id

    def test_run_job_now_birthday(self, scheduler, sample_birthday_job, mock_queue):
        """Test executing a birthday job immediately."""
        # Create job
        scheduler.add_job(sample_birthday_job)

        # Run now
        success = scheduler.run_job_now(sample_birthday_job.id)
        assert success is True

        # Verify RQ enqueue was called
        assert mock_queue.enqueue.called
        call_args = mock_queue.enqueue.call_args

        # Check that birthday task was enqueued
        assert call_args[0][0] == "src.queue.tasks.run_bot_task"
        assert call_args[1]['bot_mode'] == "unlimited"  # process_late=True
        assert call_args[1]['dry_run'] is False
        assert call_args[1]['max_days_late'] == 7

    def test_run_job_now_visitor(self, scheduler, sample_visitor_job, mock_queue):
        """Test executing a visitor job immediately."""
        # Create job
        scheduler.add_job(sample_visitor_job)

        # Run now
        success = scheduler.run_job_now(sample_visitor_job.id)
        assert success is True

        # Verify RQ enqueue was called
        assert mock_queue.enqueue.called
        call_args = mock_queue.enqueue.call_args

        # Check that visitor task was enqueued
        assert call_args[0][0] == "src.queue.tasks.run_profile_visit_task"
        assert call_args[1]['dry_run'] is True
        assert call_args[1]['limit'] == 50

    def test_run_job_now_nonexistent(self, scheduler):
        """Test running a nonexistent job."""
        success = scheduler.run_job_now("nonexistent-id")
        assert success is False

    def test_birthday_bot_mode_standard(self, scheduler, mock_queue):
        """Test that standard mode (no late processing) works correctly."""
        job = ScheduledJobConfig(
            name="Standard Birthday",
            bot_type=BotType.BIRTHDAY,
            schedule_type=ScheduleType.DAILY,
            schedule_config={"hour": 8, "minute": 0},
            bot_config=BirthdayBotConfig(
                dry_run=True,
                process_late=False  # Standard mode
            )
        )

        scheduler.add_job(job)
        scheduler.run_job_now(job.id)

        call_args = mock_queue.enqueue.call_args
        assert call_args[1]['bot_mode'] == "standard"
        assert call_args[1]['max_days_late'] == 0

    def test_birthday_bot_mode_with_late(self, scheduler, mock_queue):
        """Test that late processing mode works correctly."""
        job = ScheduledJobConfig(
            name="Late Birthday",
            bot_type=BotType.BIRTHDAY,
            schedule_type=ScheduleType.DAILY,
            schedule_config={"hour": 8, "minute": 0},
            bot_config=BirthdayBotConfig(
                dry_run=False,
                process_late=True,
                max_days_late=14
            )
        )

        scheduler.add_job(job)
        scheduler.run_job_now(job.id)

        call_args = mock_queue.enqueue.call_args
        assert call_args[1]['bot_mode'] == "unlimited"
        assert call_args[1]['max_days_late'] == 14

    def test_get_job_history(self, scheduler, sample_birthday_job):
        """Test retrieving job execution history."""
        # Create job
        scheduler.add_job(sample_birthday_job)

        # Execute it (creates execution log)
        scheduler.run_job_now(sample_birthday_job.id)

        # Get history
        history = scheduler.get_job_history(sample_birthday_job.id)

        assert len(history) >= 1
        assert history[0].job_id == sample_birthday_job.id

    def test_scheduler_start_stop(self, scheduler):
        """Test starting and stopping the scheduler."""
        # Start
        scheduler.start()
        assert scheduler.scheduler.running is True

        # Stop
        scheduler.shutdown(wait=False)
        assert scheduler.scheduler.running is False

    def test_trigger_creation_daily(self, scheduler, sample_birthday_job):
        """Test creating a daily trigger."""
        trigger = scheduler._create_trigger(sample_birthday_job)

        assert trigger is not None
        assert hasattr(trigger, 'hour')
        assert trigger.hour == 8

    def test_trigger_creation_weekly(self, scheduler, sample_visitor_job):
        """Test creating a weekly trigger."""
        trigger = scheduler._create_trigger(sample_visitor_job)

        assert trigger is not None
        assert hasattr(trigger, 'day_of_week')

    def test_trigger_creation_interval(self, scheduler):
        """Test creating an interval trigger."""
        job = ScheduledJobConfig(
            name="Interval Job",
            bot_type=BotType.BIRTHDAY,
            schedule_type=ScheduleType.INTERVAL,
            schedule_config={"hours": 2, "minutes": 0},
            bot_config=BirthdayBotConfig()
        )

        trigger = scheduler._create_trigger(job)

        assert trigger is not None
        assert hasattr(trigger, 'interval')

    def test_trigger_creation_cron(self, scheduler):
        """Test creating a cron trigger."""
        job = ScheduledJobConfig(
            name="Cron Job",
            bot_type=BotType.BIRTHDAY,
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 8-18 * * 1-5"},
            bot_config=BirthdayBotConfig()
        )

        trigger = scheduler._create_trigger(job)

        assert trigger is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
