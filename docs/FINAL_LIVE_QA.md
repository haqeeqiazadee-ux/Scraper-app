# FINAL LIVE QA — AI Scraping Platform

## Overview

This document provides a comprehensive step-by-step Live QA process for the AI Scraping Platform. Each use case is tested against a live running instance using automated HTTP requests (httpx + ASGI transport for in-process testing, or Playwright for browser-based UI testing).

**Test Runner:** `tests/qa/test_live_qa.py`
**Execution:** `python -m pytest tests/qa/test_live_qa.py -v --tb=short`

---

## Test Environment Setup

### Prerequisites
- Python 3.11+
- All project dependencies installed (`pip install -e ".[all]"`)
- No external services required (uses in-memory SQLite + in-memory queue)

### How the Live Environment Works
1. FastAPI app is created with `create_app()`
2. In-memory SQLite database is initialized
3. Rate limiter is configured with generous limits for testing
4. All middleware (CORS, rate limiting, quota) is active
5. Tests use `httpx.AsyncClient` with `ASGITransport` to make real HTTP requests against the live app

---

## QA Test Cases (28 Use Cases)

### Section 1: Health & Infrastructure (3 tests)

| # | Use Case | Method | Endpoint | Expected |
|---|----------|--------|----------|----------|
| 1.1 | Health check returns OK | GET | `/health` | 200, `{"status": "ok"}` |
| 1.2 | Readiness check returns ready | GET | `/ready` | 200, `{"status": "ready"}` |
| 1.3 | Prometheus metrics endpoint | GET | `/metrics` | 200, text/plain with `scraper_` prefixed metrics |

**Steps:**
1. Send GET to `/health` — verify status 200 and JSON contains `status: ok`
2. Send GET to `/ready` — verify status 200 and JSON contains `status: ready`
3. Send GET to `/metrics` — verify status 200, content type is `text/plain`, body contains Prometheus metric lines

---

### Section 2: Task CRUD (5 tests)

| # | Use Case | Method | Endpoint | Expected |
|---|----------|--------|----------|----------|
| 2.1 | Create a scraping task | POST | `/api/v1/tasks` | 201, task with ID |
| 2.2 | Get task by ID | GET | `/api/v1/tasks/{id}` | 200, full task object |
| 2.3 | List all tasks | GET | `/api/v1/tasks` | 200, array of tasks |
| 2.4 | Update task priority | PATCH | `/api/v1/tasks/{id}` | 200, updated task |
| 2.5 | Task not found returns 404 | GET | `/api/v1/tasks/{random_uuid}` | 404 |

**Steps:**
1. POST `/api/v1/tasks` with `{"url": "https://example.com/products", "task_type": "scrape", "priority": 5}` — verify 201, response has `id`, `status` is `pending`
2. GET `/api/v1/tasks/{id}` using the ID from step 1 — verify 200, URL matches
3. GET `/api/v1/tasks` — verify 200, response is a list, contains the task from step 1
4. PATCH `/api/v1/tasks/{id}` with `{"priority": 10}` — verify 200, priority is now 10
5. GET `/api/v1/tasks/{nonexistent_uuid}` — verify 404

---

### Section 3: Policy CRUD (5 tests)

| # | Use Case | Method | Endpoint | Expected |
|---|----------|--------|----------|----------|
| 3.1 | Create a scraping policy | POST | `/api/v1/policies` | 201, policy with ID |
| 3.2 | Get policy by ID | GET | `/api/v1/policies/{id}` | 200, full policy |
| 3.3 | List all policies | GET | `/api/v1/policies` | 200, array |
| 3.4 | Update policy | PATCH | `/api/v1/policies/{id}` | 200, updated |
| 3.5 | Delete policy | DELETE | `/api/v1/policies/{id}` | 204 |

**Steps:**
1. POST `/api/v1/policies` with `{"name": "E-commerce", "target_domains": ["example.com"], "preferred_lane": "auto", "timeout_ms": 30000}` — verify 201
2. GET `/api/v1/policies/{id}` — verify 200, name is "E-commerce"
3. GET `/api/v1/policies` — verify 200, list contains the policy
4. PATCH `/api/v1/policies/{id}` with `{"name": "E-commerce Updated"}` — verify 200, name changed
5. DELETE `/api/v1/policies/{id}` — verify 204, then GET returns 404

---

### Section 4: Task Execution & Routing (4 tests)

| # | Use Case | Method | Endpoint | Expected |
|---|----------|--------|----------|----------|
| 4.1 | Execute a task | POST | `/api/v1/tasks/{id}/execute` | 200, run with lane |
| 4.2 | Dry-run routing | POST | `/api/v1/route` | 200, route decision |
| 4.3 | Execute non-pending task fails | POST | `/api/v1/tasks/{id}/execute` | 409 conflict |
| 4.4 | Execute with policy routes correctly | POST | `/api/v1/tasks/{id}/execute` | 200, lane matches policy |

**Steps:**
1. Create a task, then POST `/api/v1/tasks/{id}/execute` — verify 200, response has `run_id`, `lane`, `status`
2. POST `/api/v1/route` with `{"url": "https://example.com/api/products.json"}` — verify 200, returns `lane` (should be `api` or `http`)
3. Execute the same task again — verify 409 (already running/completed)
4. Create policy with `preferred_lane: "browser"`, create task with that policy, execute — verify lane is `browser`

---

### Section 5: Task Complete & Webhook (3 tests)

| # | Use Case | Method | Endpoint | Expected |
|---|----------|--------|----------|----------|
| 5.1 | Complete a task | POST | `/api/v1/tasks/{id}/complete` | 200, status completed |
| 5.2 | Get task results after completion | GET | `/api/v1/tasks/{id}/results` | 200, results array |
| 5.3 | Task with callback_url triggers webhook | POST | `/api/v1/tasks/{id}/complete` | 200 + webhook fired |

**Steps:**
1. Create task, execute, then POST `/api/v1/tasks/{id}/complete` — verify 200, task status is `completed`
2. GET `/api/v1/tasks/{id}/results` — verify 200, returns results list
3. Create task with `callback_url`, execute, complete — verify webhook executor was invoked

---

### Section 6: Schedule Management (3 tests)

| # | Use Case | Method | Endpoint | Expected |
|---|----------|--------|----------|----------|
| 6.1 | Create a schedule | POST | `/api/v1/schedules` | 201, schedule ID |
| 6.2 | List schedules | GET | `/api/v1/schedules` | 200, array |
| 6.3 | Delete a schedule | DELETE | `/api/v1/schedules/{id}` | 200 |

**Steps:**
1. POST `/api/v1/schedules` with `{"task_id": "{id}", "schedule": "*/5 * * * *", "enabled": true}` — verify 201
2. GET `/api/v1/schedules` — verify 200, contains the schedule
3. DELETE `/api/v1/schedules/{id}` — verify 200, then list is empty

---

### Section 7: Rate Limiting (2 tests)

| # | Use Case | Method | Endpoint | Expected |
|---|----------|--------|----------|----------|
| 7.1 | Rate limit headers present | GET | `/api/v1/tasks` | 200 + X-RateLimit-* headers |
| 7.2 | Rate limit exceeded returns 429 | GET | `/api/v1/tasks` (burst) | 429 + Retry-After header |

**Steps:**
1. Send a normal request — verify `X-RateLimit-Limit` and `X-RateLimit-Remaining` headers are present
2. Configure a very low burst rate limiter (burst=2), send 5 rapid requests — verify at least one gets 429 with `Retry-After` header

---

### Section 8: Multi-Tenant Isolation (2 tests)

| # | Use Case | Method | Endpoint | Expected |
|---|----------|--------|----------|----------|
| 8.1 | Tenant A cannot see Tenant B tasks | GET | `/api/v1/tasks` | 200, empty for Tenant B |
| 8.2 | Default tenant works without header | GET | `/api/v1/tasks` | 200 |

**Steps:**
1. Create task as Tenant A (`X-Tenant-ID: tenant-a`), list tasks as Tenant B (`X-Tenant-ID: tenant-b`) — verify empty
2. Create task without `X-Tenant-ID` header — verify 200, uses default tenant

---

### Section 9: Core Engine — Execution Router (3 tests)

| # | Use Case | Method | N/A (unit) | Expected |
|---|----------|--------|------------|----------|
| 9.1 | API URL routes to API lane | — | — | lane = api |
| 9.2 | HTML URL routes to HTTP lane | — | — | lane = http |
| 9.3 | Hard-target domain routes to hard_target lane | — | — | lane = hard_target |

**Steps:**
1. Create ExecutionRouter, route `https://api.example.com/v1/products.json` — verify lane is `api`
2. Route `https://example.com/products` — verify lane is `http`
3. Route `https://www.linkedin.com/jobs` — verify lane is `hard_target`

---

### Section 10: Core Engine — Workers (3 tests)

| # | Use Case | Method | N/A (unit) | Expected |
|---|----------|--------|------------|----------|
| 10.1 | HTTP worker processes task | — | — | result with extracted_data |
| 10.2 | AI normalizer normalizes data | — | — | normalized items |
| 10.3 | Dedup engine removes duplicates | — | — | unique items only |

**Steps:**
1. Create HttpWorker with mock HTTP response, call `process_task()` — verify result has `extracted_data`, `confidence`, `status`
2. Create AINormalizationWorker, call `normalize()` with raw data — verify items are normalized (prices cleaned, fields mapped)
3. Create DedupEngine, pass duplicate items — verify duplicates removed

---

### Section 11: Core Engine — Rate Limiter & Quota (2 tests)

| # | Use Case | Method | N/A (unit) | Expected |
|---|----------|--------|------------|----------|
| 11.1 | Token bucket allows burst then limits | — | — | True then False |
| 11.2 | Quota tracks usage and enforces limits | — | — | QuotaExceededError |

**Steps:**
1. Create InMemoryRateLimiter with burst=3, acquire 3 times (all True), acquire 4th (False)
2. Create QuotaManager with max_tasks=5, record 5 usages, verify 6th raises QuotaExceededError

---

### Section 12: Scheduler & Webhooks (2 tests)

| # | Use Case | Method | N/A (unit) | Expected |
|---|----------|--------|------------|----------|
| 12.1 | Cron schedule parses and matches | — | — | correct next fire |
| 12.2 | Webhook sends POST with HMAC signature | — | — | X-Webhook-Signature header |

**Steps:**
1. Parse cron expression `*/5 * * * *`, verify it matches minute 0, 5, 10, ...
2. Create WebhookExecutor, mock httpx, send webhook — verify POST sent with `X-Webhook-Signature` header containing HMAC-SHA256

---

### Section 13: Session Manager (1 test)

| # | Use Case | Method | N/A (unit) | Expected |
|---|----------|--------|------------|----------|
| 13.1 | Session lifecycle: create → use → degrade → invalidate | — | — | correct status transitions |

**Steps:**
1. Create SessionManager, create session — verify status is `active`
2. Record 5 failures — verify status transitions to `degraded`, then `invalid` after threshold

---

## Execution Instructions

```bash
# Run all QA tests
python -m pytest tests/qa/test_live_qa.py -v --tb=short

# Run specific section
python -m pytest tests/qa/test_live_qa.py -v -k "Section01"
python -m pytest tests/qa/test_live_qa.py -v -k "Section04"

# Run with detailed output
python -m pytest tests/qa/test_live_qa.py -v --tb=long -s
```

## Pass Criteria

- All 28+ test cases must PASS
- No test should be SKIPPED (except JWT-dependent tests if PyJWT unavailable)
- Response times should be under 1 second for all API endpoints
- Rate limit headers must be present on all API responses
- Multi-tenant isolation must be verified
- All core engine components must produce correct outputs
