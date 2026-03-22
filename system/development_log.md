# Development Log

## 2026-03-22 — Phase 0: Repository Initialization

### Repository Analysis

**Current state of existing code (scraper_pro/):**
- 45 files total, Python-first architecture
- Key modules: ai_scraper_v3.py (main scraper), engine_v2.py (scraping engine), web_dashboard.py (Flask dashboard)
- AI integration via Google Gemini for extraction
- Uses `scrapling` library for browser-based scraping
- Useful reusable components: proxy management, AI extraction logic, export functionality, vertical handling

### Actions taken:
- Created folder structure: system/, docs/, apps/, packages/, services/, infrastructure/, tests/, scripts/
- Extracted existing scraper_pro/ code from zip archive
- Initialized all mandatory system and docs files

### Architectural decisions:
- Preserved existing scraper_pro/ as-is for analysis; will refactor into target architecture during Phase 3+
- Target architecture per prompt: Python-first, FastAPI control plane, shared core engine, multiple runtime shells

---

## 2026-03-22 — Phase 1: Final Specs

### docs/final_specs.md created (1233 lines, 24 sections)

**Key architectural decisions documented:**
1. FastAPI control plane as central coordination layer
2. Pydantic models for all 7 shared data contracts
3. 5 execution lanes: API/feed, HTTP, browser, hard-target, AI normalization
4. Lane escalation: HTTP → Browser → Hard-target (automatic on failure)
5. AIProvider protocol supporting Gemini, OpenAI, Claude, and Ollama (local)
6. Storage abstraction: PostgreSQL/SQLite for metadata, S3/filesystem for artifacts, Redis/in-memory for queue
7. Tauri v2 for Windows EXE shell
8. Chrome Manifest V3 for browser extension
9. Native messaging for extension ↔ companion communication
10. Prometheus + OpenTelemetry for observability

---

## 2026-03-22 — Phase 2: Tasks Breakdown

### docs/tasks_breakdown.md created (69 tasks, 24 epics)

**Critical path:** REPO-001 → REPO-002 → ARCH-001 → SCHEMA-001 → STORAGE-001 → API-001 → API-003 → WORKER-001 → WORKER-002 → SELFHOST-001 → PKG-001 → VERIFY-002

---

## 2026-03-22 — Phase 3: Architecture Scaffolding

### CLAUDE.md created
- Project context file for AI coding sessions
- Documents architecture, tech stack, coding conventions, mandatory workflow
- Maps legacy scraper_pro/ files to new package destinations

### REPO-001: Monorepo folder structure
- Created 26 directories matching target architecture from spec section 6
- Added .gitkeep files to all empty directories
- Structure mirrors spec: apps/ (4 shells), packages/ (3 shared libs), services/ (4 backend services), infrastructure/ (3 deploy targets), tests/ (3 tiers)

### REPO-004: .gitignore and .env.example
- .gitignore covers Python, Node.js, Rust/Tauri, Docker, IDE files, OS files, secrets, database files, logs, artifacts
- .env.example documents all configuration variables grouped by category: database, Redis, storage, AI, proxy, CAPTCHA, auth, server, multi-tenant, observability

### REPO-002: Python monorepo tooling
- `pyproject.toml`: Project metadata, dependencies (core + 5 optional groups: ai, export, extraction, observability, dev), tool config for ruff, pytest, mypy, coverage
- `requirements-dev.txt`: Flat requirements file for development
- Python 3.11+ minimum version
- ruff for linting (select: E, F, W, I, N, UP, B, A, SIM, TCH)
- pytest with asyncio_mode="auto" and 3 markers (unit, integration, e2e)
- mypy with strict settings (disallow_untyped_defs)
- Coverage target: 80% on packages/ and services/

### ARCH-001: packages/contracts (7 Pydantic v2 models)
- **task.py**: Task lifecycle with TaskStatus enum (pending → queued → running → completed/failed/cancelled), priority 0-10, HttpUrl validation, TaskCreate/TaskUpdate for API input
- **policy.py**: Nested policy with RateLimit, ProxyPolicy, SessionPolicy, RetryPolicy sub-models, LanePreference enum, timeout validation (1000-300000ms), domain targeting
- **session.py**: Session with SessionType (http, browser, authenticated), SessionStatus lifecycle, computed health_score property using success rate
- **run.py**: Execution attempt tracking with RunStatus, lane/connector/proxy tracking, duration/bytes/AI tokens metrics
- **result.py**: Extraction result with confidence score (0-1), extraction_method tracking, normalization/dedup flags, artifact references
- **artifact.py**: ArtifactType enum (html_snapshot, screenshot, export_xlsx/json/csv), checksum validation, TTL support
- **billing.py**: PlanTier enum (free/starter/pro/enterprise), PLAN_DEFAULTS dict with quota limits per tier, UsageCounters for rolling counters, is_within_quota() method

**Design decisions:**
- Used `from __future__ import annotations` for forward references
- All models use `model_config = {"from_attributes": True}` for ORM compatibility
- Validation on all numeric fields (ge, le bounds)
- StrEnum for all enums (JSON-serializable)
- Field defaults match spec section 7

### ARCH-002: packages/core (interfaces + router)
- **interfaces.py**: 10 Protocol classes using structural subtyping (not ABC)
  - FetchRequest/FetchResponse dataclasses: URL, method, headers, cookies, proxy, timeout, body/text/html
  - Fetcher protocol: fetch(request) → response, close()
  - BrowserWorker protocol: extends Fetcher with scroll_to_bottom, click_element, wait_for_selector, get_page_html, screenshot
  - Connector protocol: fetch + health_check + get_metrics
  - ObjectStore protocol: put, get, delete, list_keys, get_presigned_url
  - MetadataStore protocol: connect, disconnect, execute, health_check
  - QueueBackend protocol: enqueue, dequeue, ack, nack, queue_size
  - CacheBackend protocol: get, set, delete, increment, exists
  - AIProvider protocol: extract, classify, normalize, get_token_usage
- **router.py**: ExecutionRouter with lane selection logic
  - Lane enum: API, HTTP, BROWSER, HARD_TARGET
  - RouteDecision dataclass with lane, reason, fallback_lanes, confidence
  - Built-in site profiles: BROWSER_REQUIRED_DOMAINS (Amazon, Instagram, TikTok, Twitter), API_AVAILABLE_DOMAINS (Shopify, WooCommerce)
  - record_outcome(): Exponential moving average for success rate tracking
  - get_next_lane(): Escalation support
  - Fallback escalation: API → [HTTP, BROWSER, HARD_TARGET], HTTP → [BROWSER, HARD_TARGET], BROWSER → [HARD_TARGET]

### ARCH-003: packages/connectors (5 adapter implementations)
- **http_collector.py**: HttpCollector using httpx
  - 4 realistic User-Agent strings for rotation
  - Stealth headers matching real browsers (Accept, Accept-Language, Sec-Fetch-*)
  - Async httpx client with lazy initialization
  - Proxy support, cookie handling, redirect following
  - ConnectorMetrics tracking (total, success, failed requests)
- **browser_worker.py**: PlaywrightBrowserWorker
  - Lazy browser initialization (Chromium)
  - Network idle wait for full page load
  - Cookie injection via context
  - scroll_to_bottom, click_element, wait_for_selector, get_page_html, screenshot
  - Proper cleanup: context close after each fetch, browser close on dispose
- **proxy_adapter.py**: ProxyAdapter (ported from scraper_pro/proxy_manager.py)
  - Proxy dataclass with URL builder, success_rate, avg_response_time, score (0.7 * success + 0.3 * speed), cooldown tracking
  - ProxyProvider protocol for pluggable sources
  - 4 rotation strategies: round_robin, random, weighted, sticky
  - Cooldown on consecutive failures (configurable max_failures, cooldown_seconds)
  - Thread-safe operations via time-based last_used tracking
- **captcha_adapter.py**: CaptchaAdapter (ported from scraper_pro/engine_v2.py CaptchaSolver)
  - CaptchaType enum: recaptcha_v2, recaptcha_v3, hcaptcha, image
  - CaptchaSolution dataclass with success, solution, cost, elapsed
  - CaptchaSolver protocol for pluggable services
  - Multi-service fallback chain with configurable max_attempts
  - Cost tracking: total_cost_usd, stats property
- **api_adapter.py**: ApiAdapter for known platform APIs
  - Generic REST client with Bearer token auth
  - JSON Accept header
  - Same ConnectorMetrics pattern as HttpCollector

### ARCH-004: services/control-plane (FastAPI skeleton)
- **app.py**: Application factory pattern
  - FastAPI with lifespan context manager (startup/shutdown)
  - CORS middleware (permissive for development)
  - Router registration: health, tasks (v1), policies (v1)
- **config.py**: Pydantic Settings class
  - Loads from .env file automatically
  - All settings with sensible defaults
  - SQLite default for development, PostgreSQL for production
- **routers/health.py**: /health (basic) and /ready (dependency checks)
- **routers/tasks.py**: Full CRUD for tasks
  - POST /api/v1/tasks — create task
  - GET /api/v1/tasks/{id} — get task by ID
  - GET /api/v1/tasks — list with status filter, pagination
  - PATCH /api/v1/tasks/{id} — update task fields
  - POST /api/v1/tasks/{id}/cancel — cancel task
  - In-memory dict store (will be replaced by database in STORAGE-001)
- **routers/policies.py**: Full CRUD for policies
  - POST, GET, GET list, PATCH, DELETE
  - Same in-memory pattern as tasks

**Issue encountered:** Python doesn't allow hyphens in package names (`services/control-plane` can't be imported as `services.control_plane`). Resolved with symlink: `services/control_plane` → `services/control-plane`. Will document this in CLAUDE.md and lessons.md.

---

## 2026-03-22 — Phase 4 (Partial): Tests + Storage Backends

### TEST-001: Test Infrastructure
- Created `tests/conftest.py` with shared fixtures (tenant_id, sample_url, sample_task_id)
- Created `__init__.py` files for test packages
- Installed pydantic, pydantic-settings, pytest, pytest-asyncio

### SCHEMA-001: Task Schema Tests (13 tests)
- TaskCreate: minimal valid, full valid, invalid URL rejection, priority bounds (0-10), task type enum
- Task: defaults, serialization roundtrip, JSON roundtrip, status enum values
- TaskUpdate: empty update, partial update, priority bounds

### SCHEMA-002: Policy Schema Tests (19 tests)
- RateLimit: defaults, custom values, minimum bounds
- ProxyPolicy: defaults, custom values
- SessionPolicy: defaults, bounds
- RetryPolicy: defaults, bounds
- PolicyCreate: minimal, full, name required, timeout bounds (1000-300000)
- Policy: defaults, serialization, JSON roundtrip, lane preference values
- PolicyUpdate: empty, partial

### SCHEMA-003: Remaining Schema Tests (32 tests)
- Session: create, defaults, health_score (computed: 0 requests=1.0, 80% success=0.88, 0% success=0.4), serialization, JSON, status/type enums
- Run: create, defaults, attempt minimum, serialization, status values
- Result: create, defaults, confidence bounds (0.0-1.0), serialization
- Artifact: create, defaults, size nonneg, type values, serialization
- Billing: usage counter defaults, plan defaults exist, tier ordering (free<starter<pro<enterprise), quota defaults, is_within_quota true/false/unknown, all resources, serialization

### Router Tests (12 tests) + Bug Fix
- **Bug found:** Router's domain matching was exact-only. `mystore.myshopify.com` didn't match `myshopify.com`.
- **Fix:** Added `_match_domain()` method that checks exact match first, then suffix match (domain.endswith("."+known_domain)).
- Tests: default HTTP, policy override, API domains (Shopify suffix), browser domains (Amazon), fallback chains, escalation, outcome recording, domain extraction (www stripping, port removal)

### STORAGE-002: Filesystem Object Store (10 tests)
- `FilesystemObjectStore`: put/get/delete/list_keys/presigned_url/checksum
- Path traversal protection (rejects `../../etc/passwd`)
- Nested directory auto-creation
- Overwrite support
- SHA-256 checksum generation

### STORAGE-003: In-Memory Queue + Cache (18 tests)
- `InMemoryQueue`: asyncio.Queue-based, FIFO ordering, ack/nack with re-queue, separate queue namespaces, dequeue with timeout
- `InMemoryCache`: dict-based with TTL support, increment for counters, automatic expiry cleanup, exists check

### Test Results
```
103 passed in 2.42s
```
