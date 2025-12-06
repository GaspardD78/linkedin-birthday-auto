"""Data models for automation scheduler."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from uuid import uuid4


class ScheduleType(str, Enum):
    """Types of scheduling."""
    DAILY = "daily"
    WEEKLY = "weekly"
    INTERVAL = "interval"
    CRON = "cron"


class BotType(str, Enum):
    """Types of bots (2 only: birthday with optional late processing, visitor)."""
    BIRTHDAY = "birthday"
    VISITOR = "visitor"


class BirthdayBotConfig(BaseModel):
    """Configuration for Birthday Bot."""
    dry_run: bool = False  # Production mode by default
    process_late: bool = False  # Process late birthdays
    max_days_late: int = Field(default=7, ge=1, le=365)  # Max days late
    max_messages_per_run: Optional[int] = Field(default=10, ge=1)

    @field_validator('max_days_late')
    @classmethod
    def validate_max_days(cls, v, info):
        """Validate max_days_late only if process_late=True."""
        data = info.data
        if not data.get('process_late') and v != 7:
            # Reset to default if process_late=False
            return 7
        return v


class VisitorBotConfig(BaseModel):
    """Configuration for Visitor Bot."""
    dry_run: bool = False  # Production mode by default
    limit: int = Field(default=50, ge=1, le=500)  # Profiles per run


class ScheduledJobConfig(BaseModel):
    """Complete configuration for a scheduled job."""

    # Identity
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    bot_type: BotType

    # Activation
    enabled: bool = True

    # Scheduling
    schedule_type: ScheduleType
    schedule_config: Dict[str, Any] = Field(default_factory=dict)
    # Examples:
    # Daily: {"hour": 8, "minute": 0}
    # Weekly: {"day_of_week": "mon,wed,fri", "hour": 14, "minute": 30}
    # Interval: {"hours": 2, "minutes": 0}
    # Cron: {"cron_expression": "0 8-18 * * 1-5"}

    # Bot configuration (typed according to bot_type)
    bot_config: Union[BirthdayBotConfig, VisitorBotConfig]

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "system"

    # Execution state
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None  # success, failed, running
    last_run_error: Optional[str] = None
    next_run_at: Optional[datetime] = None

    # APScheduler options
    max_instances: int = 1  # No concurrent jobs
    misfire_grace_time: int = 3600  # 1h tolerance
    coalesce: bool = True  # Merge missed executions

    @field_validator('bot_config', mode='before')
    @classmethod
    def validate_bot_config(cls, v, info):
        """Convert dict to typed model according to bot_type."""
        if isinstance(v, dict):
            data = info.data
            bot_type = data.get('bot_type')
            if bot_type == BotType.BIRTHDAY:
                return BirthdayBotConfig(**v)
            elif bot_type == BotType.VISITOR:
                return VisitorBotConfig(**v)
        return v

    class Config:
        """Pydantic config."""
        use_enum_values = True


class JobExecutionLog(BaseModel):
    """Execution log for a job."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str  # running, success, failed, cancelled
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    messages_sent: int = 0
    profiles_visited: int = 0

    class Config:
        """Pydantic config."""
        use_enum_values = True
