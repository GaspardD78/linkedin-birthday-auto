# Backend Features TODO

This document tracks features that require backend (Python FastAPI) modifications.

## 🔴 Priority: messages_ignored Feature

**Status**: Requires Backend Implementation

**Issue**: The dashboard displays a `messages_ignored` field in the history/statistics view, but the backend API does not provide this data.

**Current Behavior**:
- Frontend expects `messages_ignored` in `/api/stats/latest` response
- Backend does not track or return this metric
- Dashboard shows `undefined` or `0` for ignored messages count

**Required Backend Changes**:

### 1. Database Schema Update
Add `messages_ignored` field to the execution logs/statistics table:
```python
# In your SQLAlchemy model or database schema
class BotExecution(Base):
    # ... existing fields
    messages_sent: int
    messages_ignored: int  # NEW FIELD - count of profiles skipped/ignored
    errors: int
```

### 2. Bot Logic Update
Track ignored messages during bot execution:
```python
# In birthday bot / visitor bot logic
messages_ignored = 0

for profile in profiles_to_contact:
    if should_skip_profile(profile):
        messages_ignored += 1
        continue

    # ... send message logic
    messages_sent += 1

# Save to database
execution.messages_ignored = messages_ignored
```

**Reasons for Skipping/Ignoring**:
- Profile already contacted recently
- Profile in blacklist
- Daily limit reached
- Profile validation failed
- Connection level restrictions

### 3. API Response Update
Include `messages_ignored` in statistics endpoints:

**Endpoint**: `GET /api/stats/latest`
```json
{
  "birthday_bot": {
    "last_run": "2025-12-03T10:30:00Z",
    "messages_sent": 12,
    "messages_ignored": 3,  // ✅ Add this field
    "errors": 0,
    "status": "success"
  },
  "visitor_bot": {
    "last_run": "2025-12-03T11:00:00Z",
    "messages_sent": 8,
    "messages_ignored": 2,  // ✅ Add this field
    "errors": 0,
    "status": "success"
  }
}
```

**Endpoint**: `GET /api/history`
```json
{
  "executions": [
    {
      "id": 123,
      "bot_type": "birthday",
      "timestamp": "2025-12-03T10:30:00Z",
      "messages_sent": 12,
      "messages_ignored": 3,  // ✅ Add this field
      "errors": 0,
      "duration_seconds": 45,
      "status": "success"
    }
  ]
}
```

### 4. Dashboard Frontend (Already Compatible)
The dashboard is already coded to display this metric - no frontend changes needed once backend provides the data:

```typescript
// dashboard/app/(dashboard)/history/page.tsx (line ~87)
<td className="px-4 py-2 text-slate-400">{execution.messages_ignored || 0}</td>

// dashboard/app/(dashboard)/overview/page.tsx (line ~450)
<div className="text-3xl font-bold">{stats.messages_ignored || 0}</div>
```

### Implementation Priority
**HIGH** - This is a user-visible feature that appears incomplete without backend support.

### Testing Checklist
- [ ] Database migration adds `messages_ignored` column
- [ ] Bot logic correctly increments counter for skipped profiles
- [ ] `/api/stats/latest` returns `messages_ignored` for both bots
- [ ] `/api/history` returns `messages_ignored` for all executions
- [ ] Dashboard displays correct counts (not 0 or undefined)
- [ ] Historical data handling (old records without this field)

---

## 📝 Future Backend Enhancements

### Rate Limiting per Bot Type
- Implement per-bot-type rate limiting in backend
- Separate daily limits for birthday vs visitor bots
- Expose configuration via API

### Advanced Scheduling
- Support multiple daily execution windows
- Weekend/holiday scheduling rules
- Timezone-aware cron expressions

### Webhook Notifications
- Success/failure webhooks
- Integration with Slack/Discord/Email
- Configurable notification rules
