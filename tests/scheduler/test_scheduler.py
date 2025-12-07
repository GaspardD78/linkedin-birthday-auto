"""Unit tests for scheduler.py

Note: These tests use mocked Redis/RQ to avoid dependencies.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

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

    # Patch the classes in the scheduler module to prevent real DB init during singleton creation
    # Also patch SQLAlchemyJobStore to avoid connecting to real DB in AutomationScheduler init
    # Also patch BackgroundScheduler to avoid real scheduling logic errors with mocked store
    # Patching at the CONSUMER module (src.scheduler.scheduler) because direct imports are already bound
    with patch('src.scheduler.scheduler.JobConfigStore'), \
         patch('src.scheduler.scheduler.JobExecutionStore'), \
         patch('src.scheduler.scheduler.SQLAlchemyJobStore'), \
         patch('src.scheduler.scheduler.BackgroundScheduler') as MockScheduler, \
         patch.object(AutomationScheduler, '_reload_jobs'):

        # Setup mock scheduler behavior to return a valid-looking job
        mock_scheduler_instance = MockScheduler.return_value

        # Ensure running is False initially so start() is called
        # Using PropertyMock to ensure it behaves like a property if checked that way
        type(mock_scheduler_instance).running = PropertyMock(return_value=False)

        mock_job = MagicMock()
        mock_job.next_run_time = datetime.utcnow()
        mock_scheduler_instance.get_job.return_value = mock_job
        mock_scheduler_instance.add_job.return_value = mock_job

        # Reset singleton
        AutomationScheduler._instance = None

        scheduler_instance = AutomationScheduler()

        # Manually set up stores with temp paths (using REAL classes for testing logic)
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

        # Since we mocked BackgroundScheduler, we can check if add_job was called
        # But wait, logic says: if saved_config.enabled: self._schedule_job(...)
        # So for disabled job, it should NOT be called.
        scheduler.scheduler.add_job.assert_not_called()

    def test_update_job(self, scheduler, sample_birthday_job):
        """Test updating a job."""
        # Create job
        scheduler.add_job(sample_birthday_job)
        scheduler.scheduler.add_job.reset_mock()

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

        # Should be removed from APScheduler (mock check)
        scheduler.scheduler.remove_job.assert_called()

    def test_toggle_job_enable(self, scheduler, sample_birthday_job):
        """Test enabling a disabled job."""
        # Create disabled job
        sample_birthday_job.enabled = False
        scheduler.add_job(sample_birthday_job)
        scheduler.scheduler.add_job.reset_mock()

        # Enable
        updated = scheduler.toggle_job(sample_birthday_job.id, True)

        assert updated is not None
        assert updated.enabled is True

        # Should be scheduled in APScheduler
        scheduler.scheduler.add_job.assert_called()

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
        # Since we use execute_scheduled_job from scheduler.py which creates NEW connections
        # we can't easily check mock_queue calls unless we patch Queue in scheduler.py too.
        # But wait, fixture 'mock_queue' patches 'src.scheduler.scheduler.Queue'.
        # execute_scheduled_job imports Queue from rq.
        # But execute_scheduled_job is defined in src/scheduler/scheduler.py.
        # So 'from rq import Queue' there means Queue is in scheduler namespace.
        # So patching 'src.scheduler.scheduler.Queue' should work!
        # HOWEVER, execute_scheduled_job re-instantiates it.

        # NOTE: execute_scheduled_job re-instantiates Redis and Queue inside the function.
        # So the mock_queue passed to fixture might NOT be the one used inside execute_scheduled_job.
        # Actually, patch mocks the CLASS. So Queue(...) returns the mock instance.
        # mock_queue_instance in fixture is the return value of Queue().
        # So yes, it should work!

        # Check args
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
        # assert scheduler.scheduler.running is True # This is a mock now, attribute access is fuzzy
        scheduler.scheduler.start.assert_called()

        # Toggle running state to True for shutdown check
        type(scheduler.scheduler).running = PropertyMock(return_value=True)

        # Stop
        scheduler.shutdown(wait=False)
        scheduler.scheduler.shutdown.assert_called()

    def test_trigger_creation_daily(self, scheduler, sample_birthday_job):
        """Test creating a daily trigger."""
        trigger = scheduler._create_trigger(sample_birthday_job)

        assert trigger is not None
        # CronTrigger stores fields in .fields list of Field objects, checking string repr is easier for simple verify
        assert "hour='8'" in str(trigger)
        assert "minute='0'" in str(trigger)

    def test_trigger_creation_weekly(self, scheduler, sample_visitor_job):
        """Test creating a weekly trigger."""
        trigger = scheduler._create_trigger(sample_visitor_job)

        assert trigger is not None
        assert "day_of_week='mon'" in str(trigger)

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
        # IntervalTrigger has .interval attribute which is a timedelta
        assert hasattr(trigger, 'interval')
        assert trigger.interval == timedelta(hours=2)

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
