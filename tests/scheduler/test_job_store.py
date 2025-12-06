"""Unit tests for job_store.py"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from src.scheduler.job_store import JobConfigStore, JobExecutionStore
from src.scheduler.models import (
    ScheduledJobConfig,
    JobExecutionLog,
    BotType,
    ScheduleType,
    BirthdayBotConfig,
    VisitorBotConfig
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def job_store(temp_db):
    """Create a JobConfigStore instance."""
    return JobConfigStore(db_path=temp_db)


@pytest.fixture
def execution_store(temp_db):
    """Create a JobExecutionStore instance."""
    return JobExecutionStore(db_path=temp_db)


@pytest.fixture
def sample_birthday_job():
    """Create a sample Birthday Bot job."""
    return ScheduledJobConfig(
        name="Test Birthday Job",
        description="Test job for birthdays",
        bot_type=BotType.BIRTHDAY,
        schedule_type=ScheduleType.DAILY,
        schedule_config={"hour": 8, "minute": 0},
        bot_config=BirthdayBotConfig(
            dry_run=False,
            process_late=True,
            max_days_late=7,
            max_messages_per_run=10
        )
    )


@pytest.fixture
def sample_visitor_job():
    """Create a sample Visitor Bot job."""
    return ScheduledJobConfig(
        name="Test Visitor Job",
        bot_type=BotType.VISITOR,
        schedule_type=ScheduleType.WEEKLY,
        schedule_config={"hour": 14, "minute": 0, "day_of_week": "mon,wed"},
        bot_config=VisitorBotConfig(
            dry_run=True,
            limit=50
        )
    )


class TestJobConfigStore:
    """Tests for JobConfigStore."""

    def test_create_and_get_birthday_job(self, job_store, sample_birthday_job):
        """Test creating and retrieving a Birthday Bot job."""
        # Create
        created = job_store.create(sample_birthday_job)
        assert created.id == sample_birthday_job.id

        # Retrieve
        retrieved = job_store.get(sample_birthday_job.id)
        assert retrieved is not None
        assert retrieved.name == "Test Birthday Job"
        assert retrieved.bot_type == BotType.BIRTHDAY
        assert isinstance(retrieved.bot_config, BirthdayBotConfig)
        assert retrieved.bot_config.process_late is True
        assert retrieved.bot_config.max_days_late == 7

    def test_create_and_get_visitor_job(self, job_store, sample_visitor_job):
        """Test creating and retrieving a Visitor Bot job."""
        created = job_store.create(sample_visitor_job)

        retrieved = job_store.get(sample_visitor_job.id)
        assert retrieved is not None
        assert retrieved.name == "Test Visitor Job"
        assert retrieved.bot_type == BotType.VISITOR
        assert isinstance(retrieved.bot_config, VisitorBotConfig)
        assert retrieved.bot_config.dry_run is True
        assert retrieved.bot_config.limit == 50

    def test_get_nonexistent_job(self, job_store):
        """Test retrieving a job that doesn't exist."""
        result = job_store.get("nonexistent-id")
        assert result is None

    def test_list_all_jobs(self, job_store, sample_birthday_job, sample_visitor_job):
        """Test listing all jobs."""
        # Create two jobs
        job_store.create(sample_birthday_job)
        job_store.create(sample_visitor_job)

        # List all
        jobs = job_store.list_all()
        assert len(jobs) == 2

        # Verify both jobs are present
        names = {job.name for job in jobs}
        assert "Test Birthday Job" in names
        assert "Test Visitor Job" in names

    def test_list_enabled_only(self, job_store, sample_birthday_job, sample_visitor_job):
        """Test listing only enabled jobs."""
        # Create one enabled, one disabled
        sample_visitor_job.enabled = False

        job_store.create(sample_birthday_job)
        job_store.create(sample_visitor_job)

        # List enabled only
        enabled_jobs = job_store.list_all(enabled_only=True)
        assert len(enabled_jobs) == 1
        assert enabled_jobs[0].name == "Test Birthday Job"

    def test_update_job(self, job_store, sample_birthday_job):
        """Test updating a job."""
        # Create job
        job_store.create(sample_birthday_job)

        # Update
        updates = {
            "name": "Updated Name",
            "enabled": False,
            "schedule_config": {"hour": 10, "minute": 30}
        }
        updated = job_store.update(sample_birthday_job.id, updates)

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.enabled is False
        assert updated.schedule_config["hour"] == 10
        assert updated.schedule_config["minute"] == 30

        # Verify updated_at was changed
        assert updated.updated_at > sample_birthday_job.updated_at

    def test_update_nonexistent_job(self, job_store):
        """Test updating a job that doesn't exist."""
        result = job_store.update("nonexistent-id", {"name": "Test"})
        assert result is None

    def test_delete_job(self, job_store, sample_birthday_job):
        """Test deleting a job."""
        # Create job
        job_store.create(sample_birthday_job)

        # Verify it exists
        assert job_store.get(sample_birthday_job.id) is not None

        # Delete
        success = job_store.delete(sample_birthday_job.id)
        assert success is True

        # Verify it's gone
        assert job_store.get(sample_birthday_job.id) is None

    def test_delete_nonexistent_job(self, job_store):
        """Test deleting a job that doesn't exist."""
        success = job_store.delete("nonexistent-id")
        assert success is False

    def test_bot_config_serialization(self, job_store, sample_birthday_job):
        """Test that bot_config is correctly serialized and deserialized."""
        # Create job with complex bot_config
        job_store.create(sample_birthday_job)

        # Retrieve and verify
        retrieved = job_store.get(sample_birthday_job.id)
        assert isinstance(retrieved.bot_config, BirthdayBotConfig)
        assert retrieved.bot_config.dry_run == sample_birthday_job.bot_config.dry_run
        assert retrieved.bot_config.process_late == sample_birthday_job.bot_config.process_late
        assert retrieved.bot_config.max_days_late == sample_birthday_job.bot_config.max_days_late

    def test_schedule_config_serialization(self, job_store, sample_birthday_job):
        """Test that schedule_config is correctly serialized."""
        # Create job
        job_store.create(sample_birthday_job)

        # Retrieve and verify
        retrieved = job_store.get(sample_birthday_job.id)
        assert retrieved.schedule_config == {"hour": 8, "minute": 0}

    def test_datetime_fields(self, job_store, sample_birthday_job):
        """Test that datetime fields are correctly stored and retrieved."""
        # Set some datetime fields
        now = datetime.utcnow()
        sample_birthday_job.last_run_at = now
        sample_birthday_job.next_run_at = now + timedelta(hours=24)

        # Create job
        job_store.create(sample_birthday_job)

        # Retrieve and verify (with tolerance for microsecond differences)
        retrieved = job_store.get(sample_birthday_job.id)
        assert retrieved.last_run_at is not None
        assert abs((retrieved.last_run_at - now).total_seconds()) < 1

        assert retrieved.next_run_at is not None
        assert abs((retrieved.next_run_at - (now + timedelta(hours=24))).total_seconds()) < 1


class TestJobExecutionStore:
    """Tests for JobExecutionStore."""

    def test_create_and_get_execution(self, execution_store, sample_birthday_job):
        """Test creating and retrieving an execution log."""
        # Create execution log
        execution = JobExecutionLog(
            job_id=sample_birthday_job.id,
            started_at=datetime.utcnow(),
            status="running"
        )

        created = execution_store.create(execution)
        assert created.id == execution.id

        # Retrieve
        retrieved = execution_store.get(execution.id)
        assert retrieved is not None
        assert retrieved.job_id == sample_birthday_job.id
        assert retrieved.status == "running"

    def test_update_execution(self, execution_store, sample_birthday_job):
        """Test updating an execution log."""
        # Create execution
        execution = JobExecutionLog(
            job_id=sample_birthday_job.id,
            started_at=datetime.utcnow(),
            status="running"
        )
        execution_store.create(execution)

        # Update to success
        updates = {
            "status": "success",
            "finished_at": datetime.utcnow(),
            "messages_sent": 12,
            "result": {"messages": 12, "errors": 0}
        }
        updated = execution_store.update(execution.id, updates)

        assert updated is not None
        assert updated.status == "success"
        assert updated.finished_at is not None
        assert updated.messages_sent == 12
        assert updated.result["messages"] == 12

    def test_get_by_job(self, execution_store, sample_birthday_job, sample_visitor_job):
        """Test retrieving executions for a specific job."""
        # Create multiple executions for different jobs
        for i in range(3):
            execution_store.create(JobExecutionLog(
                job_id=sample_birthday_job.id,
                started_at=datetime.utcnow(),
                status="success"
            ))

        execution_store.create(JobExecutionLog(
            job_id=sample_visitor_job.id,
            started_at=datetime.utcnow(),
            status="success"
        ))

        # Get executions for birthday job
        executions = execution_store.get_by_job(sample_birthday_job.id)
        assert len(executions) == 3
        assert all(e.job_id == sample_birthday_job.id for e in executions)

    def test_get_by_job_with_limit(self, execution_store, sample_birthday_job):
        """Test limiting the number of executions returned."""
        # Create 10 executions
        for i in range(10):
            execution_store.create(JobExecutionLog(
                job_id=sample_birthday_job.id,
                started_at=datetime.utcnow(),
                status="success"
            ))

        # Get with limit
        executions = execution_store.get_by_job(sample_birthday_job.id, limit=5)
        assert len(executions) == 5

    def test_get_recent(self, execution_store, sample_birthday_job, sample_visitor_job):
        """Test retrieving recent executions across all jobs."""
        # Create executions for different jobs
        execution_store.create(JobExecutionLog(
            job_id=sample_birthday_job.id,
            started_at=datetime.utcnow(),
            status="success"
        ))

        execution_store.create(JobExecutionLog(
            job_id=sample_visitor_job.id,
            started_at=datetime.utcnow(),
            status="success"
        ))

        # Get recent
        recent = execution_store.get_recent(limit=10)
        assert len(recent) == 2

    def test_execution_ordering(self, execution_store, sample_birthday_job):
        """Test that executions are ordered by started_at DESC."""
        # Create executions with different timestamps
        now = datetime.utcnow()

        execution1 = JobExecutionLog(
            job_id=sample_birthday_job.id,
            started_at=now - timedelta(hours=2),
            status="success"
        )
        execution2 = JobExecutionLog(
            job_id=sample_birthday_job.id,
            started_at=now - timedelta(hours=1),
            status="success"
        )
        execution3 = JobExecutionLog(
            job_id=sample_birthday_job.id,
            started_at=now,
            status="running"
        )

        execution_store.create(execution1)
        execution_store.create(execution2)
        execution_store.create(execution3)

        # Get executions
        executions = execution_store.get_by_job(sample_birthday_job.id)

        # Verify ordering (most recent first)
        assert executions[0].id == execution3.id
        assert executions[1].id == execution2.id
        assert executions[2].id == execution1.id

    def test_result_serialization(self, execution_store, sample_birthday_job):
        """Test that result dict is correctly serialized."""
        execution = JobExecutionLog(
            job_id=sample_birthday_job.id,
            started_at=datetime.utcnow(),
            status="success",
            result={
                "messages_sent": 12,
                "profiles": ["user1", "user2"],
                "errors": []
            }
        )

        execution_store.create(execution)
        retrieved = execution_store.get(execution.id)

        assert retrieved.result is not None
        assert retrieved.result["messages_sent"] == 12
        assert retrieved.result["profiles"] == ["user1", "user2"]
        assert retrieved.result["errors"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
