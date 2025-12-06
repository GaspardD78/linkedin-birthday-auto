# Scheduler API Routes Documentation

## Base URL

```
/scheduler
```

All routes require API key authentication via `X-API-Key` header.

## Endpoints

### 1. List Jobs

**GET** `/scheduler/jobs`

List all scheduled jobs.

**Query Parameters:**
- `enabled_only` (boolean, optional): If true, only return enabled jobs. Default: false

**Response:** Array of JobResponse

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Daily Birthday Messages",
    "description": "Send birthday messages every day at 8am",
    "bot_type": "birthday",
    "enabled": true,
    "schedule_type": "daily",
    "schedule_config": {"hour": 8, "minute": 0},
    "bot_config": {
      "dry_run": false,
      "process_late": true,
      "max_days_late": 7,
      "max_messages_per_run": 10
    },
    "created_at": "2025-01-15T10:00:00",
    "updated_at": "2025-01-15T10:00:00",
    "last_run_at": "2025-01-15T08:00:00",
    "last_run_status": "success",
    "last_run_error": null,
    "next_run_at": "2025-01-16T08:00:00"
  }
]
```

---

### 2. Get Job

**GET** `/scheduler/jobs/{job_id}`

Get a specific job by ID.

**Path Parameters:**
- `job_id` (string): Job identifier (UUID)

**Response:** JobResponse

**Errors:**
- `404 Not Found`: Job doesn't exist

---

### 3. Create Job

**POST** `/scheduler/jobs`

Create a new scheduled job.

**Request Body:** CreateJobRequest

```json
{
  "name": "Daily Birthday Messages",
  "description": "Send birthday messages every day at 8am",
  "bot_type": "birthday",
  "enabled": true,
  "schedule_type": "daily",
  "schedule_config": {"hour": 8, "minute": 0},
  "bot_config": {
    "dry_run": false,
    "process_late": true,
    "max_days_late": 7,
    "max_messages_per_run": 10
  }
}
```

**Response:** JobResponse (201 Created)

**Errors:**
- `400 Bad Request`: Invalid bot_type or validation error
- `500 Internal Server Error`: Job creation failed

---

### 4. Update Job

**PUT** `/scheduler/jobs/{job_id}`

Update an existing job (partial updates supported).

**Path Parameters:**
- `job_id` (string): Job identifier

**Request Body:** UpdateJobRequest (all fields optional)

```json
{
  "enabled": false,
  "schedule_config": {"hour": 9, "minute": 30}
}
```

**Response:** JobResponse

**Errors:**
- `400 Bad Request`: Validation error
- `404 Not Found`: Job doesn't exist

---

### 5. Delete Job

**DELETE** `/scheduler/jobs/{job_id}`

Delete a scheduled job.

**Path Parameters:**
- `job_id` (string): Job identifier

**Response:** 204 No Content

**Errors:**
- `404 Not Found`: Job doesn't exist

---

### 6. Toggle Job

**POST** `/scheduler/jobs/{job_id}/toggle`

Enable or disable a job.

**Path Parameters:**
- `job_id` (string): Job identifier

**Request Body:**

```json
{
  "enabled": false
}
```

**Response:** JobResponse

**Errors:**
- `404 Not Found`: Job doesn't exist

---

### 7. Run Job Now

**POST** `/scheduler/jobs/{job_id}/run`

Execute a job immediately (outside of schedule).

**Path Parameters:**
- `job_id` (string): Job identifier

**Response:** 202 Accepted

```json
{
  "message": "Job 550e8400-e29b-41d4-a716-446655440000 queued for immediate execution",
  "status": "queued"
}
```

**Errors:**
- `404 Not Found`: Job doesn't exist

---

### 8. Get Job History

**GET** `/scheduler/jobs/{job_id}/history`

Get execution history for a job.

**Path Parameters:**
- `job_id` (string): Job identifier

**Query Parameters:**
- `limit` (integer, optional): Max logs to return (1-200). Default: 50

**Response:** Array of JobExecutionLog

```json
[
  {
    "id": "log-123",
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "started_at": "2025-01-15T08:00:00",
    "finished_at": "2025-01-15T08:05:00",
    "status": "success",
    "result": {"messages_sent": 12},
    "error": null,
    "messages_sent": 12,
    "profiles_visited": 0
  }
]
```

**Errors:**
- `400 Bad Request`: Invalid limit
- `404 Not Found`: Job doesn't exist

---

### 9. Scheduler Health

**GET** `/scheduler/health`

Check scheduler health.

**Response:**

```json
{
  "status": "healthy",
  "scheduler_running": true,
  "redis_connected": true,
  "total_jobs": 5,
  "enabled_jobs": 3
}
```

**No authentication required**

---

## Data Models

### ScheduleType

- `daily`: Execute at specific time every day
- `weekly`: Execute on specific days of week
- `interval`: Execute at regular intervals
- `cron`: Advanced cron expression

### BotType

- `birthday`: Birthday bot
- `visitor`: Profile visitor bot

### Schedule Config Examples

**Daily:**
```json
{
  "hour": 8,
  "minute": 0
}
```

**Weekly:**
```json
{
  "hour": 14,
  "minute": 30,
  "day_of_week": "mon,wed,fri"
}
```

**Interval:**
```json
{
  "hours": 2,
  "minutes": 0
}
```

**Cron:**
```json
{
  "cron_expression": "0 8-18 * * 1-5"
}
```

### Bot Config Examples

**Birthday Bot:**
```json
{
  "dry_run": false,
  "process_late": true,
  "max_days_late": 7,
  "max_messages_per_run": 10
}
```

**Visitor Bot:**
```json
{
  "dry_run": false,
  "limit": 50
}
```

---

## Example Usage

### Create a Daily Birthday Job

```bash
curl -X POST http://localhost:8000/scheduler/jobs \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Birthday Messages",
    "bot_type": "birthday",
    "schedule_type": "daily",
    "schedule_config": {"hour": 8, "minute": 0},
    "bot_config": {
      "dry_run": false,
      "process_late": true,
      "max_days_late": 7
    }
  }'
```

### List All Jobs

```bash
curl http://localhost:8000/scheduler/jobs \
  -H "X-API-Key: your-api-key"
```

### Disable a Job

```bash
curl -X POST http://localhost:8000/scheduler/jobs/{job_id}/toggle \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Run Job Immediately

```bash
curl -X POST http://localhost:8000/scheduler/jobs/{job_id}/run \
  -H "X-API-Key: your-api-key"
```

### Get Execution History

```bash
curl http://localhost:8000/scheduler/jobs/{job_id}/history?limit=20 \
  -H "X-API-Key: your-api-key"
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message description"
}
```

**Common Status Codes:**
- `200 OK`: Success
- `201 Created`: Resource created
- `202 Accepted`: Request accepted (async)
- `204 No Content`: Success, no response body
- `400 Bad Request`: Validation error
- `401 Unauthorized`: Missing/invalid API key
- `404 Not Found`: Resource doesn't exist
- `500 Internal Server Error`: Server error

---

## Notes

1. **API Key**: All routes except `/scheduler/health` require `X-API-Key` header
2. **Timezones**: All timestamps are in ISO 8601 format (UTC)
3. **Dry Run**: Recommended to test with `dry_run: true` first
4. **Limits**: Execution history limited to 200 logs per request
5. **Concurrency**: Jobs are limited to 1 concurrent execution by default
