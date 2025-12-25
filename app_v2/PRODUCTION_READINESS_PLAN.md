# Production Readiness Plan - APP_V2

**Date:** 2025-12-25
**Status:** AUDIT COMPLETE - Action Plan Ready
**Target Deployment:** Q1 2026

---

## 📊 Executive Summary

### Current State Assessment

| Aspect | Score | Status |
|--------|-------|--------|
| Architecture | ⭐⭐⭐⭐ | Excellent |
| Code Quality | ⭐⭐⭐ | Good with gaps |
| **Testing** | ⭐ | **CRITICAL - Zero tests** |
| Database Design | ⭐⭐ | Critical issues |
| Security | ⭐⭐ | Significant gaps |
| Deployment | ⭐⭐⭐⭐ | Well configured |
| Monitoring | ⭐⭐ | Partial |
| **Overall** | **2.4/5** | **NOT PRODUCTION READY** |

### Key Findings

✅ **Strengths**
- Modern async-first FastAPI architecture
- Clean layered separation of concerns (API, Service, Engine, DB)
- Comprehensive configuration management with Pydantic
- Docker multi-architecture support (x86 + ARM)
- GitHub Actions CI/CD pipeline in place
- Excellent deployment infrastructure (systemd, nginx, monitoring stack)

❌ **Critical Issues**
- **Zero tests** - No unit, integration, or E2E tests
- **Missing database indexes** - 5 critical indexes needed
- **Race conditions** in rate limiter - Quota enforcement broken
- **Duplicate database models** - birthday_messages + Interaction conflict
- **No health check endpoint** - Can't verify readiness
- **Incomplete error handling** - Generic exceptions mask real issues
- **No structured logging** - Debugging impossible in production
- **Zero Prometheus metrics** - No operational visibility

---

## 🚨 Critical Issues Breakdown

### CRITICAL #1: Zero Tests
- **Location:** `/app_v2/tests/` (empty)
- **Impact:** High - No regression protection, unpredictable production behavior
- **Scope:** All 2,313 lines of Python code (Birthday, Visitor, Engine)
- **Effort:** 40-60 hours
- **Must fix:** Yes (blocking production)

### CRITICAL #2: Missing Database Indexes
- **Location:** `app_v2/db/models.py`
- **Missing Indexes:**
  - `contact.birth_date` - Daily query bottleneck
  - `contact.status` - Frequent filtering
  - `contact.created_at` - Date-range queries
  - `interaction(contact_id, type)` - Composite for activity log
  - `linkedin_selector.last_success_at` - Selector performance
- **Impact:** Slow queries with dataset growth
- **Effort:** 2-3 hours
- **Must fix:** Yes (P0)

### CRITICAL #3: Race Conditions in Rate Limiter
- **Location:** `app_v2/core/rate_limiter.py`
- **Problem:**
  - Read-Modify-Write without atomic locks
  - Multiple processes can bypass quotas
  - No `SELECT FOR UPDATE` in quota checks
- **Impact:** Account ban from LinkedIn (quota violations)
- **Effort:** 4-6 hours (6-8 with Redis migration)
- **Must fix:** Yes (P0)
- **Decision needed:** SQLite locks vs Redis

### CRITICAL #4: Duplicate Database Models
- **Location:** `app_v2/db/models.py` lines 85-100
- **Problem:**
  - `birthday_messages` (legacy) + `interactions` (current)
  - rate_limiter.py queries `birthday_messages`
  - Code uses `Interaction` everywhere else
  - Inconsistent: `sent_at` (str) vs `created_at` (datetime)
- **Impact:** Data fragmentation, incorrect quota calculations
- **Effort:** 3-4 hours
- **Must fix:** Yes (P0)

### CRITICAL #5: Missing Health Check Endpoint
- **Location:** `app_v2/main.py`
- **Problem:**
  - No `/health` or `/ready` endpoints
  - Docker can't verify readiness
  - Deployments can't validate startup
- **Impact:** Blind deployments, unpredictable recovery
- **Effort:** 1 hour
- **Must fix:** Yes (P0)

---

## ⚠️ High Priority Issues (P1)

### P1.1: Insufficient Input Validation
- **Files:** `app_v2/api/schemas.py`, `app_v2/api/routers/`
- **Issues:**
  - `Interaction.payload` accepts any JSON (no schema)
  - `SourcingRequest.criteria` not validated
  - No size constraints (XSS/data exfiltration risk)
- **Effort:** 3-4 hours
- **Impact:** Security vulnerabilities

### P1.2: Generic Exception Handling
- **Files:** `app_v2/services/birthday_service.py`, `app_v2/engine/action_manager.py`
- **Issues:**
  - `except Exception: pass` masks real bugs
  - Insufficient logging context
  - tenacity library imported but underutilized
- **Effort:** 4-5 hours
- **Impact:** Production debugging impossible

### P1.3: No Structured Logging
- **Files:** `app_v2/` (everywhere)
- **Issues:**
  - Basic logging only, structlog library unused
  - No correlation IDs for request tracing
  - Logs not JSON (can't parse in ELK/Loki)
  - Lost context for debugging
- **Effort:** 5-6 hours
- **Impact:** No production observability

### P1.4: Zero Prometheus Metrics
- **Files:** `app_v2/main.py`
- **Issues:**
  - prometheus_client installed but unused
  - No metrics: latency, errors, quota usage, throughput
  - Grafana/Prometheus configured but no data
- **Effort:** 6-8 hours
- **Impact:** Can't monitor production health

### P1.5: Incomplete Circuit Breaker
- **Files:** `app_v2/core/rate_limiter.py`
- **Issues:**
  - Circuit breaker declared but logic incomplete
  - No automatic reset
  - No exponential backoff on LinkedIn errors
- **Effort:** 3-4 hours
- **Impact:** Poor recovery from LinkedIn API outages

---

## 📊 Medium Priority Issues (P2)

### P2.1: Settings Recreated Per Request
- **Files:** `app_v2/main.py:18`, `app_v2/services/birthday_service.py:28`
- **Issue:** `Settings()` instantiated every time (I/O overhead)
- **Solution:** Singleton or FastAPI dependency
- **Effort:** 1-2 hours
- **Impact:** Minor performance overhead

### P2.2: No Pagination Enforcement
- **Files:** `app_v2/api/routers/data.py`
- **Issue:** Endpoints can load unlimited results
- **Risk:** OOM with large datasets
- **Effort:** 2-3 hours
- **Impact:** Memory exhaustion risk

### P2.3: Incomplete Documentation
- **Files:** `app_v2/engine/selector_engine.py`, `app_v2/engine/auth_manager.py`
- **Issue:** Complex functions lack docstrings
- **Effort:** 4-6 hours
- **Impact:** High onboarding cost for new devs

### P2.4: Partial Type Hints
- **Files:** `app_v2/engine/action_manager.py` (226 lines)
- **Issue:** Some parameters missing type annotations
- **Effort:** 2-3 hours
- **Impact:** MyPy can't fully validate

### P2.5: Unbounded Dependency Versions
- **Files:** `pyproject.toml`
- **Issue:** `playwright>=1.40.0` allows breaking changes
- **Effort:** 1 hour
- **Impact:** Potential unexpected breakage

---

## 📅 Detailed Action Plan

### PHASE 1: Critical Stabilization (Week 1)

#### Task 1.1: Add Database Indexes
- **Effort:** 2-3 hours
- **Dependencies:** None
- **Deliverables:**
  - SQL migration script
  - Index verification script
  - Performance baseline (before/after)
- **Success Criteria:**
  - `SELECT * FROM contacts WHERE birth_date = ?` < 10ms
  - No duplicate indexes
  - All 5 indexes present
- **SQL to apply:**
  ```sql
  -- Contact indexes
  CREATE INDEX IF NOT EXISTS idx_contact_birth_date
    ON contacts(birth_date);

  CREATE INDEX IF NOT EXISTS idx_contact_status
    ON contacts(status);

  CREATE INDEX IF NOT EXISTS idx_contact_created_at
    ON contacts(created_at);

  -- Interaction indexes
  CREATE INDEX IF NOT EXISTS idx_interaction_contact_type
    ON interactions(contact_id, type);

  -- LinkedInSelector index
  CREATE INDEX IF NOT EXISTS idx_selector_success
    ON linkedin_selectors(last_success_at);
  ```

#### Task 1.2: Fix Rate Limiter Race Conditions
- **Effort:** 4-6 hours
- **Dependencies:** Task 1.1 (indexes)
- **Deliverables:**
  - Fixed rate_limiter.py with atomic operations
  - Unit tests for concurrency
  - Benchmark showing no quota violations
- **Architecture Decision:**
  - **Option A (SQLite + Locks):** 2 hours, single-process only
    ```python
    # Use SELECT FOR UPDATE
    result = await session.execute(
        select(Contact).with_for_update()
        .where(Contact.id == contact_id)
    )
    ```
  - **Option B (Redis):** 4-6 hours, multi-process/node support
    - Already in docker-compose
    - Atomic counters with INCR
    - TTL for daily/weekly buckets
  - **Recommendation:** Option B (better scalability)

#### Task 1.3: Add Health Check Endpoint
- **Effort:** 1 hour
- **Dependencies:** None
- **Deliverables:**
  ```python
  # GET /health - Liveness probe
  Response: {"status": "healthy", "timestamp": "..."}

  # GET /ready - Readiness probe
  Response: {
    "status": "ready",
    "database": "ok",
    "dependencies": ["redis"],
    "timestamp": "..."
  }
  ```
- **Docker compose:** Add healthcheck
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 10s
    timeout: 5s
    retries: 3
  ```

#### Task 1.4: Consolidate Database Models
- **Effort:** 3-4 hours
- **Dependencies:** Task 1.1 (indexes)
- **Deliverables:**
  - Migration: birthday_messages → interactions
  - Data integrity verification
  - Updated rate_limiter.py to use interactions table
  - Rollback procedure
- **Steps:**
  1. Create migration script
  2. Migrate data with integrity checks
  3. Update rate_limiter queries
  4. Delete birthday_messages table
  5. Verify rate limiter returns same results
  6. Add tests

**PHASE 1 TOTAL: 10-15 hours**

---

### PHASE 2: Testing & Quality (Week 2)

#### Task 2.1: Unit Tests Foundation
- **Effort:** 8-10 hours
- **Dependencies:** Phase 1 complete
- **Scope:** Core modules, min 60% coverage
- **Test Files:**
  ```
  tests/
  ├── test_core/
  │   ├── test_config.py (Settings validation)
  │   ├── test_rate_limiter.py (All quota logic)
  │   └── test_rate_limiter_concurrency.py (Race conditions)
  ├── test_db/
  │   ├── test_models.py (ORM mappings)
  │   └── test_engine.py (Async session management)
  └── conftest.py (Shared fixtures)
  ```
- **Coverage targets:**
  - config.py: 95%+
  - rate_limiter.py: 90%+
  - models.py: 100%
  - engine.py: 85%+

#### Task 2.2: Integration Tests - API Layer
- **Effort:** 12-15 hours
- **Dependencies:** Task 2.1
- **Scope:** All endpoints, error cases
- **Test Files:**
  ```
  tests/
  ├── test_api/
  │   ├── test_control_endpoints.py
  │   │   ├── POST /control/birthday (dry_run=true)
  │   │   ├── POST /control/birthday (dry_run=false)
  │   │   ├── POST /control/sourcing
  │   │   └── Error cases (401, 422, 500)
  │   └── test_data_endpoints.py
  │       ├── GET /data/contacts (with filters)
  │       ├── GET /data/interactions
  │       └── Pagination tests
  ```
- **Setup:**
  - Fixtures: test database (in-memory SQLite)
  - Test client: TestClient(app)
  - Database reset between tests

#### Task 2.3: End-to-End Tests
- **Effort:** 20-25 hours
- **Dependencies:** Task 2.2
- **Scope:** Full workflows, realistic scenarios
- **Scenarios:**
  ```
  tests/
  ├── test_e2e/
  │   ├── test_birthday_campaign_workflow.py
  │   │   ├── Select contacts with birthdays
  │   │   ├── Verify rate limits applied
  │   │   ├── Simulate message sending
  │   │   └── Verify interactions recorded
  │   ├── test_rate_limiting_enforcement.py
  │   │   ├── Multiple campaigns in same day
  │   │   ├── Weekly quota enforcement
  │   │   └── Per-execution limits
  │   ├── test_error_recovery.py
  │   │   ├── Database unavailable recovery
  │   │   ├── Browser timeout handling
  │   │   └── LinkedIn API errors
  │   └── test_circuit_breaker.py
  │       ├── Open state (reject requests)
  │       ├── Half-open state (test recovery)
  │       └── Auto-reset to closed
  ```
- **Setup:**
  - Docker Compose test environment
  - Test database + Redis
  - Mock LinkedIn browser when needed

#### Task 2.4: Coverage Reporting
- **Effort:** 2-3 hours
- **Dependencies:** Tasks 2.1-2.3
- **Deliverables:**
  - pytest.ini configured
  - pytest-cov integration
  - HTML coverage reports
  - Coverage badge in README
  - GitHub Actions CI job

**PHASE 2 TOTAL: 42-53 hours**

---

### PHASE 3: Security & Observability (Week 3)

#### Task 3.1: Structured Logging
- **Effort:** 5-6 hours
- **Scope:** All modules
- **Implementation:**
  ```python
  # Use structlog throughout
  import structlog

  logger = structlog.get_logger(__name__)

  # Example usage
  logger.info(
      "birthday_message_sent",
      contact_id=123,
      message_length=len(message),
      response_time=1.23,
      correlation_id=request.state.request_id
  )
  ```
- **Configuration:**
  - JSON output for production
  - Correlation IDs for request tracing
  - Context propagation through async calls
  - Log levels per module

#### Task 3.2: Prometheus Metrics
- **Effort:** 6-8 hours
- **Scope:** Instrument API, services, database
- **Key Metrics:**
  ```python
  # Counters
  MESSAGES_SENT = Counter(
      'linkedin_birthday_messages_sent_total',
      'Total messages sent',
      ['status']  # success, failed
  )

  # Histograms
  API_LATENCY = Histogram(
      'linkedin_api_request_duration_seconds',
      'API request latency',
      buckets=(0.1, 0.5, 1.0, 2.0, 5.0)
  )

  # Gauges
  RATE_LIMIT_REMAINING = Gauge(
      'linkedin_rate_limit_remaining',
      'Messages remaining in quota',
      ['period']  # daily, weekly
  )

  # Counters by type
  CONTACTS_PROCESSED = Counter(
      'linkedin_contacts_processed_total',
      'Contacts processed',
      ['source', 'outcome']  # birthday, sourcing | success, skip
  )

  ERRORS_TOTAL = Counter(
      'linkedin_errors_total',
      'Total errors',
      ['type', 'service']  # auth, timeout, network | birthday, visitor
  )
  ```
- **Grafana Dashboards:**
  - Birthday campaign health
  - Quota usage and trends
  - Error rates and types
  - API latency p50/p95/p99
  - Circuit breaker status

#### Task 3.3: Input Validation & Error Handling
- **Effort:** 4-5 hours
- **Scope:** Schemas, endpoints, exception handlers
- **Changes:**
  ```python
  # Improved schemas with validation
  class InteractionPayload(BaseModel):
      """Validated interaction payload"""
      message_id: int
      message_text: str = Field(..., max_length=5000)
      response_status: str = Field(..., pattern='^(success|failed)$')
      error_message: Optional[str] = Field(None, max_length=1000)

  class Interaction(Base):
      payload: Mapped[Optional[InteractionPayload]] = ...

  # Global exception handlers
  @app.exception_handler(ValueError)
  async def value_error_handler(request, exc):
      return JSONResponse(status_code=400, content={"error": str(exc)})

  @app.exception_handler(Exception)
  async def generic_exception_handler(request, exc):
      logger.error("unhandled_exception", error=str(exc), exc_info=exc)
      return JSONResponse(status_code=500, content={"error": "Internal error"})
  ```

#### Task 3.4: Complete Circuit Breaker
- **Effort:** 3-4 hours
- **Scope:** Enhance rate_limiter.py
- **Implementation:**
  ```python
  class CircuitBreaker:
      """Circuit breaker for LinkedIn API calls"""
      CLOSED = "closed"      # Normal operation
      OPEN = "open"          # Rejecting requests
      HALF_OPEN = "half_open"  # Testing recovery

      async def call(self, coro):
          """Execute coroutine with circuit breaker logic"""
          if self.state == OPEN:
              if self._should_attempt_reset():
                  self.state = HALF_OPEN
              else:
                  raise CircuitBreakerOpen()

          try:
              result = await coro
              self._on_success()
              return result
          except Exception as e:
              self._on_failure()
              raise

      def _on_failure(self):
          """Exponential backoff: 1s, 2s, 4s, 8s, ..."""
          self.failures += 1
          if self.failures >= self.failure_threshold:
              self.state = OPEN
              self.open_until = datetime.now() + timedelta(
                  seconds=2 ** min(self.failures - 1, 5)
              )
  ```

**PHASE 3 TOTAL: 18-23 hours**

---

### PHASE 4: Optimization & Documentation (Week 4)

#### Task 4.1: Caching & Performance
- **Effort:** 5-7 hours
- **Changes:**
  - Settings singleton (FastAPI dependency)
  - LinkedInSelector caching (Redis or memory)
  - Query optimization (SELECT only needed columns)
  - Pagination limits (max 1000 results)
  ```python
  # Singleton Settings
  @lru_cache(maxsize=1)
  def get_settings():
      return Settings()

  # Use as dependency
  async def endpoint(settings: Settings = Depends(get_settings)):
      ...

  # Pagination enforcement
  async def get_contacts(
      skip: int = 0,
      limit: int = Query(50, ge=1, le=1000)
  ):
      return contacts[skip : skip + limit]
  ```

#### Task 4.2: Comprehensive Documentation
- **Effort:** 6-8 hours
- **Deliverables:**
  - `docs/APP_V2_ARCHITECTURE.md` - Complete system design
  - `docs/APP_V2_API.md` - All endpoints with examples
  - `docs/APP_V2_DATABASE.md` - Schema, indexes, migrations
  - `docs/APP_V2_DEPLOYMENT.md` - Production checklist
  - `docs/APP_V2_TESTING.md` - How to write tests
  - `docs/APP_V2_MONITORING.md` - Metrics, dashboards, alerts
  - `README.md` update - Quick start for V2

#### Task 4.3: CI/CD Pipeline
- **Effort:** 4-5 hours
- **Deliverables:**
  - GitHub Actions workflow: `test.yml`
    - pytest + coverage
    - MyPy type checking
    - Ruff linting
    - Bandit security scan
    - Coverage badge
  - Docker image build workflow (already exists, enhance it)
  - Automated release process

#### Task 4.4: Production Checklist
- **Effort:** 2-3 hours
- **Deliverables:**
  - `docs/PRODUCTION_CHECKLIST.md`
  - Environment variables validation
  - Database backup strategy
  - Rollback procedures
  - Monitoring alerts setup
  - Performance baselines

**PHASE 4 TOTAL: 17-23 hours**

---

### PHASE 5: Validation & Polish (Optional)

#### Task 5.1: Load Testing
- **Effort:** 4-6 hours
- **Scope:** Stress test with production-like scenarios
- **Scenarios:**
  - 100 concurrent birthday campaigns
  - 1000 contact batch processing
  - High-frequency API calls
- **Metrics:**
  - Database connection pool saturation
  - Memory growth over time
  - CPU usage patterns
  - Identify bottlenecks

#### Task 5.2: Security Audit
- **Effort:** 4-5 hours
- **Scope:** OWASP Top 10 review
- **Coverage:**
  - SQL injection (SQLAlchemy protection)
  - XSS vectors (Playwright/Browser context)
  - CSRF protection
  - Authentication/authorization (API key scheme)
  - Secrets management (never in logs)
  - Dependency vulnerabilities (safety check)

**PHASE 5 TOTAL: 8-11 hours (optional)**

---

## 📊 Timeline Summary

### Estimated Hours by Phase

| Phase | Tasks | Hours | Weeks |
|-------|-------|-------|-------|
| **Phase 1** | Stabilization (P0) | 10-15 | 1 |
| **Phase 2** | Testing (P1) | 42-53 | 2 |
| **Phase 3** | Security (P1) | 18-23 | 1 |
| **Phase 4** | Documentation (P2) | 17-23 | 1 |
| **Phase 5** | Validation (P3) | 8-11 | Optional |
| **TOTAL** | Complete Roadmap | **93-121** | **3-4 weeks** |

### Recommended Sprint Schedule

```
Week 1 (Phase 1) - Critical Stabilization
├─ Day 1-2: Database indexes + consolidation
├─ Day 2-3: Rate limiter fixes
├─ Day 4-5: Health check endpoint
└─ Review & testing: Phase 1 completion

Week 2 (Phase 2) - Testing & Quality
├─ Days 1-3: Unit tests foundation
├─ Days 3-4: Integration tests
├─ Days 5+: E2E tests begin
└─ Parallel: Coverage reporting setup

Week 3 (Phase 2+3) - Continue Tests + Security
├─ Days 1-2: Complete E2E tests
├─ Days 2-3: Structured logging
├─ Days 4-5: Prometheus metrics
└─ Parallel: Input validation

Week 4 (Phase 3+4) - Security + Documentation
├─ Days 1-2: Circuit breaker + final security
├─ Days 2-5: Documentation (API, Architecture, Deployment)
├─ Parallel: CI/CD pipeline
└─ Final: Production checklist

Week 5 (Optional) - Validation
├─ Load testing
└─ Security audit
```

---

## ✅ Success Criteria for Production Readiness

### Must Have (Blocking)
- [ ] **70%+ code coverage** with all P0/P1 scenarios passing
- [ ] **No race conditions** - Rate limiting atomically enforced
- [ ] **Database indexes** - All 5 critical indexes present
- [ ] **Health endpoint** - `/health` and `/ready` working
- [ ] **Input validation** - All payloads validated
- [ ] **Structured logging** - Correlation IDs and JSON output
- [ ] **Error handling** - No generic `except Exception`
- [ ] **Circuit breaker** - Functional with auto-recovery

### Should Have (High Priority)
- [ ] **Monitoring dashboard** - Grafana with 15+ metrics
- [ ] **Performance baseline** - Queries < 100ms p95
- [ ] **Database backup** - Automated, tested recovery
- [ ] **API documentation** - All endpoints documented
- [ ] **Deployment guide** - Step-by-step production runbook
- [ ] **CI/CD pipeline** - Automated tests on every commit

### Nice to Have (Polish)
- [ ] Load testing results
- [ ] Security audit report
- [ ] Performance optimization report
- [ ] Migration guide from V1

---

## 🔄 Dependencies & Critical Path

```
PHASE 1
├─ 1.1 Database Indexes [2-3h]
│   └─ 1.4 DB Consolidation [3-4h]
│       └─ 2.1 Unit Tests [8-10h]
│           └─ 2.2 Integration Tests [12-15h]
│               └─ 2.3 E2E Tests [20-25h]
│
├─ 1.2 Rate Limiter [4-6h]
│   └─ 3.4 Circuit Breaker [3-4h]
│
├─ 1.3 Health Check [1h]
│
└─ PARALLEL: 3.1, 3.2, 3.3 Security [15-19h]
    └─ 4.1, 4.2, 4.3 Documentation [17-21h]
```

**Critical Path:** Phase 1 → Phase 2 → Phase 3/4 (parallel)

---

## 🎯 Next Steps

1. **Review this plan** with team/stakeholders
2. **Prioritize phases** based on deadline
3. **Allocate resources** (1 dev full-time = 3-4 weeks, 2 devs = 2-3 weeks)
4. **Create GitHub issues** for each task
5. **Start Phase 1** immediately (10-15h to unblock everything)

---

## 📝 Notes & Observations

### About the V2 Architecture
- V2 is NOT a complete rewrite of V1 - it's a well-planned architectural refactor
- Clean separation: API layer (FastAPI), Service layer (business logic), Engine layer (browser automation), DB layer
- Excellent foundation - just needs stabilization for production

### Legacy Compatibility
- `birthday_messages` table kept for backward compatibility during migration
- Should be fully removed after consolidation (Task 1.4)

### Infrastructure
- Docker Compose is excellent (optimized for Raspberry Pi 4)
- Monitoring stack ready (Prometheus + Grafana)
- Deployment automation ready (systemd services)
- Just need to populate the stack with metrics and health checks

### Confidence Level
- **Architecture:** 95% confidence it will work in production
- **Code quality:** 80% confidence (needs tests)
- **Operations:** 70% confidence (needs monitoring + observability)

With this plan executed completely, V2 will be **production-ready** with:
- Zero technical debt
- Full test coverage
- Complete observability
- Security hardening
- Rock-solid rate limiting

---

## 📞 Questions & Clarifications

### Architecture Decisions Needed

**1. Rate Limiting Backend:**
- **SQLite + Locks** (simple, 2h, single-process)
- **Redis** (scalable, 6h, multi-process/node) ← **RECOMMENDED**

**2. Logging Backend:**
- **Local JSON files** (simple, 3h)
- **ELK Stack** (production-grade, requires infrastructure)
- **Loki** (cloud-native, 6h) ← **RECOMMENDED for RPi**

**3. Monitoring Preference:**
- Use existing Prometheus + Grafana (already running in compose)
- Add custom dashboards and alerts

**4. Deployment Target:**
- Raspberry Pi 4 only
- Multi-node Kubernetes
- AWS/Cloud provider
- → Affects scaling decisions

---

**Created:** 2025-12-25
**Last Updated:** 2025-12-25
**Owner:** DevOps/Architecture
**Status:** Ready for Implementation
