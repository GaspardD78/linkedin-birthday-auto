# 🏗️ ARCHITECTURE DETAILS - LinkedIn Auto RPi4

**Comprehensive Technical Reference**
**Version:** 1.0
**Date:** 2025-12-18

---

## TABLE OF CONTENTS

1. [Bots Detailed Specification](#1-bots-detailed-specification)
2. [API Routes Complete Reference](#2-api-routes-complete-reference)
3. [Database Schema](#3-database-schema)
4. [Data Flow Diagrams](#4-data-flow-diagrams)

---

# 1. BOTS DETAILED SPECIFICATION

All bots inherit from `BaseLinkedInBot` in `src/core/base_bot.py`.

## 1.1 Birthday Bot

**File:** `src/bots/birthday_bot.py`
**Purpose:** Send LinkedIn messages on connection anniversaries
**Trigger:** Scheduled daily (configurable)
**Timeout:** 120 seconds

### Functionality

```python
class BirthdayBot(BaseLinkedInBot):
    """
    Sends personalized messages on connection anniversaries.

    Modes:
    - STANDARD: Today's anniversaries only
    - UNLIMITED: Today + late messages (configurable max_days_late)
    """
```

### Execution Flow

1. **Initialization**
   - Load authentication (cookies)
   - Initialize database connection
   - Load messaging configuration (templates, limits)
   - Initialize notification service

2. **Check Limits** (`_check_limits()`)
   ```
   ├─ Daily limit check
   │  └─ If daily_limit (e.g., 20) reached → SKIP execution
   ├─ Weekly limit check
   │  └─ If weekly_limit (e.g., 50) reached → SKIP execution
   └─ Get current usage from database
   ```

3. **Fetch Birthdays** (`_get_birthdays()`)
   ```
   ├─ Query LinkedIn API for connection anniversaries
   ├─ Filter by date:
   │  ├─ TODAY anniversaries (if config.process_today=true)
   │  └─ LATE anniversaries (if config.process_late=true, max_days_late days)
   ├─ Exclude:
   │  ├─ Blacklisted contacts
   │  ├─ Already sent this month
   │  └─ Contacts with errors in last 7 days
   └─ Return list of ContactData objects
   ```

4. **Send Messages** (`_send_birthday_message()`)
   ```
   For each contact:
   ├─ Navigate to LinkedIn profile
   ├─ Click "Message" button (selectors from database)
   ├─ Fill message text:
   │  ├─ Use template (personalized with name)
   │  ├─ Add delay between characters (random 100-300ms)
   │  └─ Random typing speed simulation
   ├─ Submit message
   ├─ Log result to database (bot_executions)
   └─ Handle errors:
      ├─ If timeout → log and continue
      ├─ If rate-limited → break loop
      └─ If login expired → fail entire run
   ```

5. **Database Logging**
   ```sql
   INSERT INTO birthday_messages (
       contact_name,
       linkedin_url,
       sent_at,
       message_text,
       execution_id
   ) VALUES (?, ?, ?, ?, ?)

   UPDATE bot_executions SET
       messages_sent = count,
       status = 'completed',
       duration_seconds = elapsed
   ```

### Configuration

```yaml
# config/default_config.yaml
bots:
  birthday:
    enabled: true
    mode: "standard"              # or "unlimited"
    max_days_late: 10             # for unlimited mode

    process_today: true
    process_late: false

    messaging:
      template: "Happy anniversary of connecting! {{name}}"
      delay_between_messages: 5   # seconds
      typing_speed: "random"      # 100-300ms per char

    limits:
      daily_limit: 20             # max messages per day
      weekly_limit: 50            # max messages per week

    schedule: "0 8 * * *"         # 08:00 daily
```

### Output

```json
{
  "status": "completed",
  "total_contacts": 15,
  "messages_sent": 12,
  "ignored": 3,
  "errors": 0,
  "daily_remaining": 8,
  "weekly_remaining": 38,
  "duration_seconds": 42.5,
  "execution_id": "exec_1234567890"
}
```

### Exception Handling

```python
try:
    # Message sending
except DailyLimitReachedError:
    return {"status": "skipped", "reason": "daily_limit_reached"}
except WeeklyLimitReachedError:
    return {"status": "skipped", "reason": "weekly_limit_reached"}
except MessageSendError as e:
    return {"status": "error", "message": str(e), "contact": contact.name}
except PlaywrightTimeoutError:
    return {"status": "error", "reason": "browser_timeout"}
```

---

## 1.2 Visitor Bot

**File:** `src/bots/visitor_bot.py`
**Purpose:** Visit targeted LinkedIn profiles (increases "Who viewed your profile")
**Trigger:** Scheduled (configurable)
**Timeout:** 300+ seconds (depends on profile count)

### Functionality

```python
class VisitorBot(BaseLinkedInBot):
    """
    Visits LinkedIn profiles from saved searches or queries.

    Strategy:
    - Extract search URL from campaign
    - Scroll through search results
    - Visit profiles with configurable delay
    - Track visits in database
    """
```

### Execution Flow

1. **Load Campaign**
   ```
   ├─ Get campaign from database (name, search_url, filters)
   ├─ Parse filters:
   │  ├─ Connections only (1st degree)
   │  ├─ Keywords (job titles, industries)
   │  ├─ Location
   │  └─ Last activity (active in X days)
   └─ Initialize profile counter
   ```

2. **Navigate & Extract Profiles** (`_get_profiles_from_search()`)
   ```
   ├─ Navigate to search URL
   ├─ Wait for results to load
   ├─ Scroll through paginated results
   ├─ For each profile card:
   │  ├─ Extract profile URL
   │  ├─ Check if already visited (database)
   │  ├─ Check if blacklisted
   │  └─ Add to queue if new
   └─ Stop when max_profiles reached
   ```

3. **Visit Profiles** (`_visit_profile()`)
   ```
   For each profile URL:
   ├─ Navigate to profile
   ├─ Wait for page load (full_page=true for profile)
   ├─ Delay between visits:
   │  ├─ Random: 10-30 seconds (avoid detection)
   │  └─ Respects rate limiting
   ├─ Log visit to database
   ├─ Take screenshot (optional, for logging)
   └─ Move to next profile

   Profile visit = LinkedIn sees "Someone viewed your profile"
   ```

4. **Database Logging**
   ```sql
   INSERT INTO profile_visits (
       profile_url,
       campaign_id,
       visited_at,
       execution_id
   ) VALUES (?, ?, ?, ?)

   UPDATE campaigns SET
       last_visit_count = count,
       last_execution_id = ?
   ```

### Configuration

```yaml
bots:
  visitor:
    enabled: true
    schedule: "0 10 * * *"        # 10:00 daily

    profile_visit:
      max_profiles: 50            # profiles to visit per run
      delay_between_visits: 15    # seconds (random +/- 5s)
      visits_per_hour: 15         # rate limiting

    search_strategy:
      use_saved_searches: true
      keywords: []                 # override search keywords
      connections_only: true

    screenshot_enabled: false       # log visits with screenshots
```

### Output

```json
{
  "status": "completed",
  "profiles_found": 120,
  "profiles_visited": 50,
  "skipped_blacklist": 5,
  "skipped_already_visited": 65,
  "errors": 0,
  "average_delay_seconds": 18.5,
  "duration_seconds": 875,
  "execution_id": "exec_1234567890"
}
```

---

## 1.3 Invitation Manager Bot

**File:** `src/bots/invitation_manager_bot.py`
**Purpose:** Auto-accept/decline pending LinkedIn invitations
**Trigger:** Scheduled weekly (or manual)
**Timeout:** 180 seconds

### Functionality

```python
class InvitationManagerBot(BaseLinkedInBot):
    """
    Manages pending LinkedIn invitations.

    Actions:
    - Auto-accept connections (with optional message)
    - Auto-decline based on criteria
    - Log all actions for audit trail
    """
```

### Execution Flow

1. **Navigate to Invitations Page**
   ```
   ├─ Go to linkedin.com/mynetwork/invitations-in/
   ├─ Wait for invitations to load
   ├─ Count pending invitations
   └─ Initialize action counter
   ```

2. **Process Invitations** (`_process_invitations()`)
   ```
   For each pending invitation:
   ├─ Check profile preview:
   │  ├─ Read headline (job title)
   │  ├─ Read mutual connections count
   │  └─ Read location
   │
   ├─ Apply acceptance rules:
   │  ├─ If whitelist match → ACCEPT
   │  ├─ If blacklist match → DECLINE
   │  ├─ If keywords match → ACCEPT
   │  ├─ If mutual connections > threshold → ACCEPT
   │  └─ Otherwise → (depends on config)
   │
   ├─ Perform action:
   │  ├─ Click Accept/Decline button
   │  ├─ Optional: Send follow-up message
   │  └─ Log action
   │
   └─ Move to next invitation
   ```

3. **Database Logging**
   ```sql
   INSERT INTO invitations (
       sender_name,
       sender_url,
       decision,
       reason,
       executed_at,
       execution_id
   ) VALUES (?, ?, ?, ?, ?, ?)
   ```

### Configuration

```yaml
bots:
  invitation_manager:
    enabled: true
    schedule: "0 0 * * 0"         # Weekly Sunday midnight

    auto_accept:
      enabled: true
      criteria:
        require_mutual_connections: 2
        accept_keywords: ["engineer", "developer", "founder"]
        whitelist: ["alice@company.com", "bob@company.com"]

      follow_up_message: null      # or custom message

    auto_decline:
      enabled: false
      criteria:
        decline_keywords: ["recruiter", "spam"]
        blacklist: ["suspicious@email.com"]

      decline_message: "Not accepting now"

    rate_limit:
      actions_per_run: 20          # max invitations per execution
      delay_between_actions: 3     # seconds
```

### Output

```json
{
  "status": "completed",
  "total_pending": 15,
  "accepted": 10,
  "declined": 0,
  "skipped": 5,
  "errors": 0,
  "duration_seconds": 120,
  "execution_id": "exec_1234567890"
}
```

---

## 1.4 Unlimited Bot (Legacy)

**File:** `src/bots/unlimited_bot.py`
**Purpose:** Alternative birthday bot with extended capabilities
**Status:** Optional, less maintained than BirthdayBot

### Difference from BirthdayBot

```python
class UnlimitedBot(BirthdayBot):
    """
    Extended birthday bot with:
    - Longer timeout (180s vs 120s)
    - Better error recovery
    - Late message handling
    - More flexible configuration
    """
```

### Key Features

- Sends messages to birthdays from N days ago (configurable)
- Better error resilience (retry logic)
- Can handle more profiles per run
- More detailed logging

---

# 2. API ROUTES COMPLETE REFERENCE

## 2.1 Bot Control Routes

**File:** `src/api/routes/bot_control.py`
**Base Path:** `/bot`

### POST /bot/{bot_name}/trigger

Manually trigger a bot execution

```http
POST /bot/birthday/trigger HTTP/1.1
Authorization: Bearer <API_KEY>
Content-Type: application/json

{
  "dry_run": false,
  "force": false
}
```

**Response (200 OK):**
```json
{
  "status": "queued",
  "job_id": "job_12345",
  "bot_name": "birthday",
  "message": "Birthday bot queued for execution"
}
```

**Status Codes:**
- `200` - Bot queued successfully
- `401` - Invalid API key
- `400` - Invalid bot name
- `409` - Another instance already running

---

### GET /bot/{bot_name}/status

Get current bot execution status

```http
GET /bot/birthday/status HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "bot_name": "birthday",
  "status": "running",
  "job_id": "job_12345",
  "started_at": "2025-12-18T10:05:30Z",
  "progress": {
    "processed": 12,
    "total": 20,
    "percentage": 60
  },
  "last_execution": {
    "status": "completed",
    "messages_sent": 15,
    "duration_seconds": 42,
    "timestamp": "2025-12-18T08:15:00Z"
  }
}
```

---

### GET /bot/list

List all available bots

```http
GET /bot/list HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "bots": [
    {
      "name": "birthday",
      "display_name": "Birthday Bot",
      "description": "Send anniversary messages",
      "enabled": true,
      "last_execution": "2025-12-18T08:15:00Z",
      "status": "idle"
    },
    {
      "name": "visitor",
      "display_name": "Visitor Bot",
      "description": "Visit profiles from search",
      "enabled": true,
      "last_execution": "2025-12-17T10:20:00Z",
      "status": "idle"
    },
    {
      "name": "invitation_manager",
      "display_name": "Invitation Manager",
      "description": "Auto-accept/decline invitations",
      "enabled": true,
      "last_execution": "2025-12-17T00:05:00Z",
      "status": "idle"
    }
  ]
}
```

---

### POST /bot/{bot_name}/stop

Stop a running bot

```http
POST /bot/birthday/stop HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "status": "stopped",
  "job_id": "job_12345",
  "message": "Bot stopped gracefully"
}
```

---

### GET /bot/{bot_name}/history

Get execution history for a bot

```http
GET /bot/birthday/history?limit=10 HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "bot_name": "birthday",
  "executions": [
    {
      "execution_id": "exec_67890",
      "status": "completed",
      "started_at": "2025-12-18T08:00:00Z",
      "ended_at": "2025-12-18T08:00:42Z",
      "duration_seconds": 42,
      "result": {
        "messages_sent": 15,
        "errors": 0
      }
    },
    {
      "execution_id": "exec_67891",
      "status": "completed",
      "started_at": "2025-12-17T08:00:00Z",
      "ended_at": "2025-12-17T08:00:50Z",
      "duration_seconds": 50,
      "result": {
        "messages_sent": 12,
        "errors": 0
      }
    }
  ]
}
```

---

## 2.2 Authentication Routes

**File:** `src/api/auth_routes.py`
**Base Path:** `/auth`

### POST /auth/upload

Upload LinkedIn authentication cookies

```http
POST /auth/upload HTTP/1.1
Authorization: Bearer <API_KEY>
Content-Type: multipart/form-data

[Binary file: auth_state.json]
```

**Expected File Format:**
```json
[
  {
    "name": "li_at",
    "value": "AQEDARZx...",
    "domain": ".linkedin.com",
    "path": "/",
    "expires": 1735689600,
    "httpOnly": true,
    "secure": true,
    "sameSite": "None"
  },
  {
    "name": "JSESSIONID",
    "value": "\"AQZZZZZ...\"",
    "domain": "www.linkedin.com",
    "path": "/",
    "httpOnly": true,
    "secure": true
  }
]
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Cookies uploaded and validated",
  "profile": {
    "name": "John Doe",
    "email": "john@example.com",
    "headline": "Software Engineer"
  }
}
```

---

### GET /auth/status

Check authentication status

```http
GET /auth/status HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "authenticated": true,
  "expires_at": "2025-12-25T10:30:00Z",
  "profile": {
    "name": "John Doe",
    "headline": "Software Engineer",
    "profile_picture": "https://media.licdn.com/..."
  },
  "warnings": []
}
```

---

### POST /auth/refresh

Refresh authentication (if cookies about to expire)

```http
POST /auth/refresh HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "status": "refreshed",
  "new_expires_at": "2025-12-31T15:00:00Z"
}
```

---

## 2.3 Configuration Routes

**File:** `src/api/routes/config_routes.py`
**Base Path:** `/config`

### GET /config/yaml

Get current YAML configuration

```http
GET /config/yaml HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```
Content-Type: text/yaml

bots:
  birthday:
    enabled: true
    schedule: "0 8 * * *"
    ...
```

---

### POST /config/yaml

Update YAML configuration

```http
POST /config/yaml HTTP/1.1
Authorization: Bearer <API_KEY>
Content-Type: application/x-yaml

bots:
  birthday:
    enabled: true
    schedule: "0 9 * * *"  # Changed to 09:00
    ...
```

**Response (200 OK):**
```json
{
  "status": "updated",
  "message": "Configuration reloaded",
  "next_birthday_run": "2025-12-19T09:00:00Z"
}
```

---

### GET /config/schema

Get configuration schema (for validation)

```http
GET /config/schema HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "schema": {
    "type": "object",
    "properties": {
      "bots": {
        "type": "object",
        "properties": {
          "birthday": {
            "type": "object",
            "properties": {
              "enabled": {"type": "boolean"},
              "schedule": {"type": "string", "pattern": "cron"},
              ...
            }
          }
        }
      }
    }
  }
}
```

---

## 2.4 Scheduler Routes

**File:** `src/api/routes/scheduler_routes.py`
**Base Path:** `/scheduler`

### GET /scheduler/jobs

List all scheduled jobs

```http
GET /scheduler/jobs HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "jobs": [
    {
      "id": "birthday_daily",
      "bot_name": "birthday",
      "schedule": "0 8 * * *",
      "next_run": "2025-12-19T08:00:00Z",
      "last_run": {
        "timestamp": "2025-12-18T08:00:00Z",
        "status": "completed",
        "result": {"messages_sent": 15}
      }
    },
    {
      "id": "visitor_daily",
      "bot_name": "visitor",
      "schedule": "0 10 * * *",
      "next_run": "2025-12-19T10:00:00Z",
      "last_run": null
    }
  ]
}
```

---

### POST /scheduler/jobs/{job_id}/trigger

Manually trigger a scheduled job

```http
POST /scheduler/jobs/birthday_daily/trigger HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "job_id": "birthday_daily",
  "status": "triggered",
  "execution_id": "exec_12345"
}
```

---

## 2.5 Visitor Routes

**File:** `src/api/routes/visitor_routes.py`
**Base Path:** `/visitor`

### GET /visitor/campaigns

List all campaigns (visitor bot search configurations)

```http
GET /visitor/campaigns HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "campaigns": [
    {
      "id": "camp_001",
      "name": "Python Developers",
      "search_url": "https://www.linkedin.com/search/results/people/?keywords=python&...",
      "filters": {
        "keywords": ["python", "developer"],
        "location": ["San Francisco"],
        "industry": ["Tech"]
      },
      "status": "active",
      "profile_count": 50,
      "last_visited": "2025-12-18T10:15:00Z"
    }
  ]
}
```

---

### POST /visitor/campaigns

Create new campaign

```http
POST /visitor/campaigns HTTP/1.1
Authorization: Bearer <API_KEY>
Content-Type: application/json

{
  "name": "DevOps Engineers",
  "search_url": "https://www.linkedin.com/search/results/people/?keywords=devops&...",
  "filters": {
    "keywords": ["devops", "kubernetes"],
    "location": ["London"],
    "industry": ["Tech"]
  }
}
```

**Response (201 Created):**
```json
{
  "campaign_id": "camp_002",
  "status": "created",
  "message": "Campaign ready for visitor bot"
}
```

---

## 2.6 Deployment Routes

**File:** `src/api/routes/deployment.py`
**Base Path:** `/system`

### GET /system/health

System health check

```http
GET /system/health HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "services": {
    "api": "healthy",
    "database": "healthy",
    "redis": "healthy",
    "worker": "healthy"
  },
  "system": {
    "memory_usage_mb": 650,
    "memory_total_mb": 4096,
    "cpu_usage_percent": 15,
    "uptime_seconds": 86400,
    "temperature_celsius": 42
  }
}
```

---

### GET /system/logs

Get recent system logs

```http
GET /system/logs?bot=birthday&limit=50 HTTP/1.1
Authorization: Bearer <API_KEY>
```

**Response (200 OK):**
```json
{
  "logs": [
    {
      "timestamp": "2025-12-18T08:00:42Z",
      "level": "INFO",
      "bot": "birthday",
      "message": "Bot execution completed",
      "data": {
        "messages_sent": 15,
        "duration_seconds": 42
      }
    }
  ]
}
```

---

### POST /system/restart

Restart specific service

```http
POST /system/restart HTTP/1.1
Authorization: Bearer <API_KEY>
Content-Type: application/json

{
  "service": "bot-worker"
}
```

**Response (202 Accepted):**
```json
{
  "status": "restarting",
  "service": "bot-worker",
  "estimated_time": 30
}
```

---

# 3. DATABASE SCHEMA

**Type:** SQLite 3
**Mode:** WAL (Write-Ahead Logging)
**Location:** `./data/linkedin.db`

## 3.1 Core Tables

### schema_version
Tracks database schema version for migrations

```sql
CREATE TABLE schema_version (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### contacts
Stores LinkedIn contacts data

```sql
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    linkedin_url TEXT UNIQUE NOT NULL,
    email TEXT,
    headline TEXT,
    location TEXT,
    profile_picture_url TEXT,
    relationship_score REAL DEFAULT 0.0,  -- 0-1 (relevance)
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_visited TIMESTAMP
);

CREATE INDEX idx_contacts_url ON contacts(linkedin_url);
CREATE INDEX idx_contacts_name ON contacts(name);
```

---

### birthday_messages
Audit trail of sent birthday/anniversary messages

```sql
CREATE TABLE birthday_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    contact_id INTEGER,
    contact_name TEXT NOT NULL,
    linkedin_url TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_text TEXT,
    status TEXT DEFAULT 'sent',  -- sent, failed, skipped
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(contact_id) REFERENCES contacts(id)
);

CREATE INDEX idx_messages_execution ON birthday_messages(execution_id);
CREATE INDEX idx_messages_contact ON birthday_messages(contact_id);
```

---

### profile_visits
Tracks profile visits by visitor bot

```sql
CREATE TABLE profile_visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL,
    campaign_id INTEGER,
    profile_url TEXT NOT NULL,
    profile_name TEXT,
    visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    visit_duration_seconds INTEGER,
    screenshot_path TEXT,
    status TEXT DEFAULT 'visited',  -- visited, skipped, error
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);

CREATE INDEX idx_visits_execution ON profile_visits(execution_id);
CREATE INDEX idx_visits_campaign ON profile_visits(campaign_id);
```

---

### errors
Error tracking and debugging

```sql
CREATE TABLE errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT,
    bot_name TEXT NOT NULL,
    error_type TEXT NOT NULL,  -- TimeoutError, MessageSendError, etc
    error_message TEXT,
    traceback TEXT,
    context_data TEXT,  -- JSON with context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_errors_execution ON errors(execution_id);
CREATE INDEX idx_errors_bot ON errors(bot_name);
```

---

### linkedin_selectors
CSS selectors for LinkedIn page elements (dynamically updated)

```sql
CREATE TABLE linkedin_selectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_type TEXT NOT NULL,  -- profile, message_button, send_message, etc
    element_name TEXT NOT NULL,
    selector TEXT NOT NULL,
    selector_type TEXT DEFAULT 'css',  -- css, xpath
    confidence REAL DEFAULT 0.9,  -- How reliable this selector is
    last_tested TIMESTAMP,
    status TEXT DEFAULT 'active',  -- active, deprecated
    notes TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE UNIQUE INDEX idx_selectors_type_name ON linkedin_selectors(page_type, element_name);
```

---

### scraped_profiles
Cache of profile data from searches

```sql
CREATE TABLE scraped_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    profile_url TEXT UNIQUE NOT NULL,
    profile_data TEXT,  -- JSON with name, headline, etc
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_visited BOOLEAN DEFAULT 0,
    visit_date TIMESTAMP,
    status TEXT DEFAULT 'pending',  -- pending, visited, blacklisted
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);

CREATE INDEX idx_profiles_campaign ON scraped_profiles(campaign_id);
CREATE INDEX idx_profiles_visited ON scraped_profiles(is_visited);
```

---

### campaigns
Visitor bot campaign configurations

```sql
CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    search_url TEXT NOT NULL,
    filters TEXT,  -- JSON with keywords, location, industry, etc
    max_profiles INTEGER DEFAULT 50,
    status TEXT DEFAULT 'active',  -- active, paused, archived
    profile_count INTEGER DEFAULT 0,
    visited_count INTEGER DEFAULT 0,
    last_execution_id TEXT,
    last_visit_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_campaigns_status ON campaigns(status);
```

---

### bot_executions
Complete execution history for all bots

```sql
CREATE TABLE bot_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT UNIQUE NOT NULL,
    bot_name TEXT NOT NULL,  -- birthday, visitor, invitation_manager
    status TEXT NOT NULL,  -- completed, failed, timeout, skipped
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    duration_seconds REAL,
    result_data TEXT,  -- JSON with counts, messages_sent, errors, etc
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_executions_bot ON bot_executions(bot_name);
CREATE INDEX idx_executions_status ON bot_executions(status);
CREATE INDEX idx_executions_date ON bot_executions(created_at);
```

---

### notification_settings
Dashboard notification preferences

```sql
CREATE TABLE notification_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE,  -- user identifier
    email TEXT,
    notify_on_completion BOOLEAN DEFAULT 1,
    notify_on_error BOOLEAN DEFAULT 1,
    notify_on_limit_reached BOOLEAN DEFAULT 1,
    notify_daily_summary BOOLEAN DEFAULT 0,
    summary_time TEXT DEFAULT '18:00',  -- HH:MM format
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### notification_logs
History of sent notifications

```sql
CREATE TABLE notification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT,
    notification_type TEXT,  -- completion, error, summary
    recipient TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent',  -- sent, failed, pending
    error_message TEXT,
    FOREIGN KEY(execution_id) REFERENCES bot_executions(execution_id)
);

CREATE INDEX idx_notifications_execution ON notification_logs(execution_id);
```

---

### blacklist
Contacts to exclude from operations

```sql
CREATE TABLE blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_name TEXT NOT NULL,
    linkedin_url TEXT UNIQUE NOT NULL,
    reason TEXT,  -- spam, requested, error, etc
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    added_by TEXT,  -- admin, system, manual
    is_active BOOLEAN DEFAULT 1,
    notes TEXT
);

CREATE INDEX idx_blacklist_active ON blacklist(is_active);
```

---

## 3.2 Example Queries

### Get today's sent messages count
```sql
SELECT COUNT(*) as sent_today
FROM birthday_messages
WHERE DATE(sent_at) = DATE('now')
  AND status = 'sent';
```

### Get bot execution statistics
```sql
SELECT
    bot_name,
    status,
    COUNT(*) as count,
    AVG(duration_seconds) as avg_duration,
    MAX(created_at) as last_run
FROM bot_executions
WHERE created_at > datetime('now', '-30 days')
GROUP BY bot_name, status
ORDER BY bot_name, status;
```

### Get blacklisted contacts
```sql
SELECT * FROM blacklist
WHERE is_active = 1
ORDER BY added_at DESC;
```

### Get visitor bot campaign progress
```sql
SELECT
    c.name,
    c.profile_count as total_profiles,
    COUNT(sp.id) as extracted,
    SUM(CASE WHEN sp.is_visited = 1 THEN 1 ELSE 0 END) as visited,
    ROUND(100.0 * SUM(CASE WHEN sp.is_visited = 1 THEN 1 ELSE 0 END) / COUNT(sp.id), 1) as completion_percent
FROM campaigns c
LEFT JOIN scraped_profiles sp ON c.id = sp.campaign_id
WHERE c.status = 'active'
GROUP BY c.id
ORDER BY completion_percent DESC;
```

---

# 4. DATA FLOW DIAGRAMS

## 4.1 Birthday Bot Execution Flow

```
┌─────────────────┐
│  User Triggers  │
│  (API / Cron)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ 1. Load Config & Auth       │
│    - Load YAML config       │
│    - Decrypt cookies        │
│    - Initialize Playwright  │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 2. Check Limits             │
│    - Query DB (daily/weekly)│
│    - Compare with config    │
│    - Abort if limit reached │
└────────┬────────────────────┘
         │
         ├─ Limit OK ─┐
         │            │
         │            ▼
         │        ┌──────────────────────┐
         │        │ 3. Fetch Birthdays   │
         │        │    - Query LinkedIn  │
         │        │    - Filter by date  │
         │        │    - Exclude (BL, DB)│
         │        └────────┬─────────────┘
         │                 │
         │                 ▼
         │        ┌──────────────────────┐
         │        │ 4. Loop: Send Msgs   │
         │        │ For each contact:    │
         │        │  - Navigate profile  │
         │        │  - Send message      │
         │        │  - Log to DB         │
         │        │  - Handle errors     │
         │        └────────┬─────────────┘
         │                 │
         │                 ▼
         │        ┌──────────────────────┐
         │        │ 5. Cleanup           │
         │        │  - Close browser     │
         │        │  - GC collect        │
         │        │  - Close DB          │
         │        └────────┬─────────────┘
         │                 │
         └─ Limit Reached ─┤
         │                 │
         ▼                 ▼
    ┌─────────────────────────────┐
    │ 6. Return Result            │
    │    - Write to DB            │
    │    - Send notification      │
    │    - Return JSON response   │
    └─────────────────────────────┘
```

## 4.2 Request Processing Flow

```
┌──────────────────────┐
│ HTTP Request         │
│ POST /bot/*/trigger  │
└──────────┬───────────┘
           │
           ▼
    ┌─────────────────┐
    │ Security Check  │
    │ - API Key valid?│
    │ - Rate limit OK?│
    └────┬────────┬───┘
         │ ✓      │ ✗
         │        └──────┐
         │               ▼
         │          401 Unauthorized
         │
         ▼
    ┌─────────────────────┐
    │ Enqueue to Redis    │
    │ Create job in queue │
    └────┬────────────────┘
         │
         ▼
    ┌─────────────────────┐
    │ RQ Worker           │
    │ (picks up job)      │
    └────┬────────────────┘
         │
         ▼
    ┌─────────────────────┐
    │ Import Bot class    │
    └────┬────────────────┘
         │
         ▼
    ┌─────────────────────┐
    │ Execute bot.run()   │
    └────┬────────────────┘
         │
         ├─ Success ──┐
         │            │
         │            ▼
         │    ┌──────────────────┐
         │    │ Store result     │
         │    │ - DB             │
         │    │ - Redis result   │
         │    └──────────────────┘
         │
         ├─ Timeout ──┐
         │            │
         │            ▼
         │    ┌──────────────────┐
         │    │ Mark failed      │
         │    │ - Log error      │
         │    │ - Retry if <3    │
         │    └──────────────────┘
         │
         └─ Exception ┐
                      │
                      ▼
              ┌──────────────────┐
              │ Log to errors    │
              │ - Stacktrace     │
              │ - Context        │
              └──────────────────┘
                      │
                      ▼
              Dashboard & API
              can query results
```

---

## 4.3 Memory Lifecycle During Bot Execution

```
Start:
┌─────────────────────────────────────────┐
│ Free Memory: 1200 MB / 4GB              │
└─────────────────────────────────────────┘
         │
         ▼ (Setup phase)
┌─────────────────────────────────────────┐
│ After Playwright Init: 800 MB free      │
│ - Chromium process: ~300MB              │
│ - Browser instances: ~100MB             │
└─────────────────────────────────────────┘
         │
         ▼ (Run phase - Bot processing)
┌─────────────────────────────────────────┐
│ During message sending: 400 MB free     │
│ - Additional page data: ~100MB          │
│ - Message buffers: ~50MB                │
└─────────────────────────────────────────┘
         │
         ▼ (Teardown phase)
┌─────────────────────────────────────────┐
│ After context.close(): 600 MB free      │
│ - DOM cached freed: ~200MB              │
└─────────────────────────────────────────┘
         │
         ▼ (GC collection)
┌─────────────────────────────────────────┐
│ After gc.collect(): 1100 MB free ✅     │
│ - Python objects freed: ~300-500MB      │
│ - Ready for next bot                    │
└─────────────────────────────────────────┘
```

---

**END OF ARCHITECTURE DETAILS**

For daily operations, see [KNOWLEDGE_BASE_v1.1.md Part D](KNOWLEDGE_BASE_v1.1.md#partie-d--procédures-opérationnelles)
