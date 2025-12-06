"""Unit tests for scheduler models."""

import pytest
from datetime import datetime
from src.scheduler.models import (
    ScheduleType,
    BotType,
    BirthdayBotConfig,
    VisitorBotConfig,
    ScheduledJobConfig,
    JobExecutionLog
)


class TestBirthdayBotConfig:
    """Tests for BirthdayBotConfig model."""

    def test_defaults(self):
        """Test default values."""
        config = BirthdayBotConfig()

        assert config.dry_run is False, "dry_run should default to False (production mode)"
        assert config.process_late is False, "process_late should default to False"
        assert config.max_days_late == 7, "max_days_late should default to 7"
        assert config.max_messages_per_run == 10, "max_messages_per_run should default to 10"

    def test_process_late_enabled(self):
        """Test with process_late enabled."""
        config = BirthdayBotConfig(
            process_late=True,
            max_days_late=14
        )

        assert config.process_late is True
        assert config.max_days_late == 14

    def test_dry_run_mode(self):
        """Test dry-run mode."""
        config = BirthdayBotConfig(dry_run=True)

        assert config.dry_run is True
        assert config.process_late is False  # Other fields keep defaults

    def test_max_days_late_validation(self):
        """Test max_days_late is within bounds."""
        # Valid range: 1-365
        config = BirthdayBotConfig(process_late=True, max_days_late=1)
        assert config.max_days_late == 1

        config = BirthdayBotConfig(process_late=True, max_days_late=365)
        assert config.max_days_late == 365

    def test_full_config(self):
        """Test complete configuration."""
        config = BirthdayBotConfig(
            dry_run=False,
            process_late=True,
            max_days_late=10,
            max_messages_per_run=20
        )

        assert config.dry_run is False
        assert config.process_late is True
        assert config.max_days_late == 10
        assert config.max_messages_per_run == 20


class TestVisitorBotConfig:
    """Tests for VisitorBotConfig model."""

    def test_defaults(self):
        """Test default values."""
        config = VisitorBotConfig()

        assert config.dry_run is False, "dry_run should default to False"
        assert config.limit == 50, "limit should default to 50"

    def test_custom_limit(self):
        """Test custom limit."""
        config = VisitorBotConfig(limit=100)

        assert config.limit == 100

    def test_dry_run_enabled(self):
        """Test dry-run mode."""
        config = VisitorBotConfig(dry_run=True, limit=25)

        assert config.dry_run is True
        assert config.limit == 25


class TestScheduledJobConfig:
    """Tests for ScheduledJobConfig model."""

    def test_birthday_bot_job(self):
        """Test creating a Birthday Bot job."""
        job = ScheduledJobConfig(
            name="Daily Birthday Bot",
            description="Send birthday messages daily",
            bot_type=BotType.BIRTHDAY,
            schedule_type=ScheduleType.DAILY,
            schedule_config={"hour": 8, "minute": 0},
            bot_config={
                "dry_run": False,
                "process_late": True,
                "max_days_late": 7,
                "max_messages_per_run": 10
            }
        )

        assert job.name == "Daily Birthday Bot"
        assert job.bot_type == BotType.BIRTHDAY
        assert job.schedule_type == ScheduleType.DAILY
        assert job.enabled is True  # Default
        assert isinstance(job.bot_config, BirthdayBotConfig)
        assert job.bot_config.process_late is True
        assert job.bot_config.max_days_late == 7
        assert job.id is not None  # Auto-generated UUID
        assert job.created_at is not None

    def test_visitor_bot_job(self):
        """Test creating a Visitor Bot job."""
        job = ScheduledJobConfig(
            name="Weekly Visitor Bot",
            bot_type=BotType.VISITOR,
            schedule_type=ScheduleType.WEEKLY,
            schedule_config={"hour": 14, "minute": 0, "day_of_week": "mon,wed,fri"},
            bot_config={
                "dry_run": True,
                "limit": 50
            }
        )

        assert job.name == "Weekly Visitor Bot"
        assert job.bot_type == BotType.VISITOR
        assert isinstance(job.bot_config, VisitorBotConfig)
        assert job.bot_config.dry_run is True
        assert job.bot_config.limit == 50

    def test_interval_schedule(self):
        """Test interval schedule configuration."""
        job = ScheduledJobConfig(
            name="Interval Job",
            bot_type=BotType.BIRTHDAY,
            schedule_type=ScheduleType.INTERVAL,
            schedule_config={"hours": 2, "minutes": 0},
            bot_config={"dry_run": False}
        )

        assert job.schedule_type == ScheduleType.INTERVAL
        assert job.schedule_config["hours"] == 2

    def test_cron_schedule(self):
        """Test cron schedule configuration."""
        job = ScheduledJobConfig(
            name="Cron Job",
            bot_type=BotType.BIRTHDAY,
            schedule_type=ScheduleType.CRON,
            schedule_config={"cron_expression": "0 8-18 * * 1-5"},
            bot_config={"dry_run": False}
        )

        assert job.schedule_type == ScheduleType.CRON
        assert job.schedule_config["cron_expression"] == "0 8-18 * * 1-5"

    def test_disabled_job(self):
        """Test creating a disabled job."""
        job = ScheduledJobConfig(
            name="Disabled Job",
            bot_type=BotType.BIRTHDAY,
            enabled=False,
            schedule_type=ScheduleType.DAILY,
            schedule_config={"hour": 8, "minute": 0},
            bot_config={"dry_run": True}
        )

        assert job.enabled is False

    def test_apscheduler_options(self):
        """Test APScheduler-specific options."""
        job = ScheduledJobConfig(
            name="Test Job",
            bot_type=BotType.BIRTHDAY,
            schedule_type=ScheduleType.DAILY,
            schedule_config={"hour": 8, "minute": 0},
            bot_config={"dry_run": True},
            max_instances=2,
            misfire_grace_time=7200,
            coalesce=False
        )

        assert job.max_instances == 2
        assert job.misfire_grace_time == 7200
        assert job.coalesce is False


class TestJobExecutionLog:
    """Tests for JobExecutionLog model."""

    def test_execution_log_creation(self):
        """Test creating an execution log."""
        job_id = "test-job-123"
        started = datetime.utcnow()

        log = JobExecutionLog(
            job_id=job_id,
            started_at=started,
            status="running"
        )

        assert log.job_id == job_id
        assert log.started_at == started
        assert log.status == "running"
        assert log.finished_at is None
        assert log.messages_sent == 0
        assert log.profiles_visited == 0
        assert log.id is not None  # Auto-generated

    def test_successful_execution(self):
        """Test successful execution log."""
        log = JobExecutionLog(
            job_id="job-1",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            status="success",
            result={"messages_sent": 12},
            messages_sent=12
        )

        assert log.status == "success"
        assert log.finished_at is not None
        assert log.messages_sent == 12
        assert log.result["messages_sent"] == 12

    def test_failed_execution(self):
        """Test failed execution log."""
        log = JobExecutionLog(
            job_id="job-2",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            status="failed",
            error="Connection timeout"
        )

        assert log.status == "failed"
        assert log.error == "Connection timeout"
        assert log.finished_at is not None


class TestEnums:
    """Tests for enum types."""

    def test_schedule_types(self):
        """Test ScheduleType enum."""
        assert ScheduleType.DAILY == "daily"
        assert ScheduleType.WEEKLY == "weekly"
        assert ScheduleType.INTERVAL == "interval"
        assert ScheduleType.CRON == "cron"

    def test_bot_types(self):
        """Test BotType enum."""
        assert BotType.BIRTHDAY == "birthday"
        assert BotType.VISITOR == "visitor"
        # Ensure no "unlimited" type exists
        assert not hasattr(BotType, 'UNLIMITED')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
