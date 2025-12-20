# Automation Scheduler Module

## Overview

This module provides automated scheduling for LinkedIn Birthday Bot automations using APScheduler.

## Architecture

```
src/scheduler/
├── __init__.py
├── models.py          # Pydantic models for jobs and execution logs
├── job_store.py       # SQLite persistence layer
├── scheduler.py       # APScheduler core logic
└── README.md         # This file
```

## Models

### BotType

Two bot types supported:
- **BIRTHDAY**: Birthday bot with optional late processing
- **VISITOR**: Profile visitor bot

**Note**: There is no separate "unlimited" bot. The Birthday bot has a `process_late` flag that enables late birthday processing.

### ScheduleType

Four scheduling modes:
- **DAILY**: Execute at a specific time every day
- **WEEKLY**: Execute on specific days of the week
- **INTERVAL**: Execute at regular intervals (e.g., every 2 hours)
- **CRON**: Advanced cron expression support

### BirthdayBotConfig

Configuration for Birthday Bot jobs:

```python
BirthdayBotConfig(
    dry_run: bool = False,           # Production mode by default
    process_late: bool = False,      # Process late birthdays
    max_days_late: int = 7,          # Max days to go back (if process_late=True)
    max_messages_per_run: int = 10   # Limit per execution
)
```

**Important**: `dry_run` defaults to `False` (production mode). Always verify configuration before enabling a schedule.

### VisitorBotConfig

Configuration for Visitor Bot jobs:

```python
VisitorBotConfig(
    dry_run: bool = False,  # Production mode by default
    limit: int = 50         # Profiles to visit per execution
)
```

### ScheduledJobConfig

Complete job configuration:

```python
ScheduledJobConfig(
    name: str,                    # Job name
    description: str,             # Optional description
    bot_type: BotType,            # BIRTHDAY or VISITOR
    enabled: bool = True,         # Active/inactive
    schedule_type: ScheduleType,  # DAILY, WEEKLY, INTERVAL, CRON
    schedule_config: dict,        # Schedule parameters (see examples)
    bot_config: dict,             # Bot-specific config
    max_instances: int = 1,       # No concurrent executions
    misfire_grace_time: int = 3600,  # 1h tolerance for missed executions
    coalesce: bool = True         # Merge missed runs
)
```

#### Schedule Config Examples

**Daily**:
```python
schedule_config = {
    "hour": 8,
    "minute": 0
}
```

**Weekly**:
```python
schedule_config = {
    "day_of_week": "mon,wed,fri",  # Monday, Wednesday, Friday
    "hour": 14,
    "minute": 30
}
```

**Interval**:
```python
schedule_config = {
    "hours": 2,      # Every 2 hours
    "minutes": 0
}
```

**Cron**:
```python
schedule_config = {
    "cron_expression": "0 8-18 * * 1-5"  # Mon-Fri, 8am-6pm
}
```

### JobExecutionLog

Execution history record:

```python
JobExecutionLog(
    job_id: str,
    started_at: datetime,
    finished_at: datetime | None,
    status: str,  # "running", "success", "failed"
    result: dict | None,
    error: str | None,
    messages_sent: int = 0,
    profiles_visited: int = 0
)
```

## Usage Examples

### Create a Daily Birthday Job

```python
from src.scheduler.models import (
    ScheduledJobConfig,
    BotType,
    ScheduleType,
    BirthdayBotConfig
)

job = ScheduledJobConfig(
    name="Daily Birthday Messages",
    description="Send birthday messages every day at 8am",
    bot_type=BotType.BIRTHDAY,
    schedule_type=ScheduleType.DAILY,
    schedule_config={"hour": 8, "minute": 0},
    bot_config=BirthdayBotConfig(
        dry_run=False,          # Production mode
        process_late=True,      # Include late birthdays
        max_days_late=7,        # Up to 7 days late
        max_messages_per_run=10
    )
)
```

### Create a Weekly Visitor Job

```python
from src.scheduler.models import (
    ScheduledJobConfig,
    BotType,
    ScheduleType,
    VisitorBotConfig
)

job = ScheduledJobConfig(
    name="Weekly Profile Visits",
    description="Visit profiles Mon/Wed/Fri at 2pm",
    bot_type=BotType.VISITOR,
    schedule_type=ScheduleType.WEEKLY,
    schedule_config={
        "day_of_week": "mon,wed,fri",
        "hour": 14,
        "minute": 0
    },
    bot_config=VisitorBotConfig(
        dry_run=True,   # Test mode
        limit=50
    )
)
```

### Create an Interval Job

```python
job = ScheduledJobConfig(
    name="Hourly Birthday Check",
    bot_type=BotType.BIRTHDAY,
    schedule_type=ScheduleType.INTERVAL,
    schedule_config={"hours": 1, "minutes": 0},
    bot_config=BirthdayBotConfig(
        dry_run=False,
        process_late=False  # Today only
    )
)
```

## Validation Rules

### BirthdayBotConfig

- `max_days_late`: Must be between 1 and 365
- If `process_late=False`, `max_days_late` is reset to default (7)

### VisitorBotConfig

- `limit`: Must be between 1 and 500

### ScheduledJobConfig

- `max_instances`: Defaults to 1 (no concurrent executions of same job)
- `misfire_grace_time`: Defaults to 3600 seconds (1 hour)
- `coalesce`: Defaults to True (merge missed runs into one execution)

## Dry-Run vs Production Mode

**IMPORTANT**: By default, all jobs run in **production mode** (`dry_run=False`).

### Production Mode (dry_run=False)

- ✅ Real messages sent
- ✅ Real profile visits
- ⚠️ Ensure configuration is correct
- ⚠️ Verify message templates
- ⚠️ Check daily/weekly limits

### Test Mode (dry_run=True)

- 🧪 Simulation only
- 🧪 No real actions
- 📋 Logs what would happen
- ✅ Safe for testing

**Best Practice**: Create jobs with `dry_run=True` first, test the schedule, then switch to `dry_run=False`.

## Testing

Run the unit tests:

```bash
pytest tests/scheduler/test_models.py -v
```

Expected output:
```
tests/scheduler/test_models.py::TestBirthdayBotConfig::test_defaults PASSED
tests/scheduler/test_models.py::TestBirthdayBotConfig::test_process_late_enabled PASSED
tests/scheduler/test_models.py::TestVisitorBotConfig::test_defaults PASSED
tests/scheduler/test_models.py::TestScheduledJobConfig::test_birthday_bot_job PASSED
tests/scheduler/test_models.py::TestScheduledJobConfig::test_visitor_bot_job PASSED
...
```

## Security Considerations

1. **Job Configuration Validation**: All configurations are validated via Pydantic
2. **No Code Injection**: Schedule configs use structured data, not eval()
3. **Dry-Run Default**: Consider changing default to `dry_run=True` for safety
4. **API Authentication**: Scheduler API endpoints require API key validation

## Performance

- **Job Store**: SQLite with indexed queries
- **APScheduler**: Background thread pool (max 3 workers)
- **Polling**: Jobs checked every second by APScheduler
- **Database**: Minimal overhead, ~100 jobs = <1MB

## Troubleshooting

### Job Not Executing

1. Check `enabled=True`
2. Verify `next_run_at` is in the future
3. Check scheduler is running (`scheduler.scheduler.running`)
4. Inspect logs for errors

### Missed Executions

- Increase `misfire_grace_time` if system was offline
- Check `coalesce=True` to prevent duplicate runs

### Wrong Schedule

- Validate `schedule_config` matches `schedule_type`
- For cron: use online cron validator
- Check timezone (default: Europe/Paris)

## API Documentation

This module exposes HTTP API endpoints for managing scheduled jobs.

**📖 Full API Documentation:** [docs/SCHEDULER_API.md](../../docs/SCHEDULER_API.md)

The API documentation includes:
- Complete endpoint reference (list, get, create, update, delete jobs)
- Request/response examples in JSON
- Authentication requirements
- Error handling and status codes
- Rate limiting and quotas

### Quick API Examples

```bash
# List all jobs
curl -H "X-API-Key: your-api-key" http://localhost:8000/scheduler/jobs

# Get specific job
curl -H "X-API-Key: your-api-key" http://localhost:8000/scheduler/jobs/{job_id}

# Create new job
curl -X POST -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d @job.json \
  http://localhost:8000/scheduler/jobs
```

## Future Enhancements

- [ ] Webhook notifications on job completion
- [ ] Job execution statistics dashboard
- [ ] Dynamic schedule adjustment based on quota
- [ ] Multi-timezone support
- [ ] Job dependencies (run job B after job A)

## License

Part of LinkedIn Birthday Auto project.
