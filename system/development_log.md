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

---

## 2026-03-22 — API-004: JWT Authentication & Tenant Middleware

### Implementation
- **middleware/auth.py**: JWT token creation (`create_access_token`) and verification (`verify_token`) using PyJWT. FastAPI dependency `get_current_user` extracts Bearer token, verifies JWT, returns user dict (sub, tenant_id, roles). `require_role(*roles)` dependency factory for RBAC.
- **routers/auth.py**: POST `/api/v1/auth/token` issues JWT (scaffolding — accepts any credentials). GET `/api/v1/auth/me` returns current user claims from token.
- **app.py**: Registered auth router with `/api/v1` prefix.
- Settings already in config.py: `secret_key`, `jwt_algorithm`, `jwt_access_token_expire_minutes`.

### Tests (12 tests in test_api_auth.py)
- Token creation (string format, embedded claims, custom expiry)
- Token verification (valid, expired, invalid, tampered)
- POST /auth/token endpoint (success, validation error)
- GET /auth/me endpoint (success, no token, invalid token, expired token)
- Role-based access (allowed, denied → 403)

---

## 2026-03-22 — WORKER-003: AI Normalization Worker

### Implementation

**services/worker-ai/worker.py** — `AINormalizationWorker` class implementing a three-stage normalisation pipeline:

1. **Deterministic normalisation** — delegates to `packages/core/normalizer.normalize_items()` for field alias resolution, price/rating cleaning, URL fixing
2. **Deduplication** — delegates to `packages/core/dedup.DedupEngine.deduplicate()` for SKU/URL exact match and fuzzy name match
3. **AI-assisted schema mapping** — when result confidence < threshold and an `AIProvider` is configured, calls `provider.normalize(item, target_schema)` per item. Failures are caught and the original item is kept.
4. **Confidence recalculation** — blends original confidence (60%) with field coverage ratio (40%)

Helper functions: `_field_coverage(item)` computes fraction of canonical fields filled; `_compute_confidence(items, base)` blends.

Symlink `services/worker_ai → worker-ai` created following existing convention (control_plane, worker_http, worker_browser).

### Tests (8 classes in tests/unit/test_worker_ai.py)

- **TestDeterministicNormalization** — field aliases, price/rating/URL cleaning, empty items
- **TestDeduplication** — exact URL dedup, fuzzy name dedup, distinct items preserved
- **TestAIFallback** — AI called when low confidence, skipped when high, graceful failure
- **TestBatchProcessing** — batch returns all, preserves extra keys
- **TestHighConfidencePassthrough** — no AI call, confidence recalculated
- **TestHelpers** — field_coverage and compute_confidence unit tests
- **TestClose** — idempotent close

---

## 2026-03-22 — SESSION-002: Cookie and Browser Profile Persistence

### Implementation
- **packages/core/session_persistence.py**: `SessionPersistence` class storing session data as JSON files on the filesystem. Uses `asyncio.get_running_loop().run_in_executor()` for non-blocking file I/O (no aiofiles dependency needed). Storage layout: `{storage_path}/{session_id}/cookies.json`, `profile.json`, `headers.json`. Includes `delete_session_data` (rmtree) and `list_sessions` (directory listing).
- **packages/core/session_store.py**: `PersistentSessionManager` wrapping the existing `SessionManager` with automatic persistence. `create_session` persists initial cookies/headers. `get_or_create_session` loads persisted data for new sessions. `update_cookies`/`update_headers`/`update_browser_profile` persist changes immediately. `cleanup` removes persisted data for expired/invalidated sessions before calling `cleanup_expired()`. All read operations delegated to inner SessionManager.

### Design Decisions
- Used `run_in_executor` with synchronous `pathlib.Path` operations rather than requiring aiofiles as a dependency. Keeps the dependency footprint minimal while still being non-blocking.
- Storage path is configurable (default `./session_data`), supporting both cloud and desktop deployment modes.
- `PersistentSessionManager` composes `SessionManager` rather than inheriting, following the project's composition-over-inheritance pattern.

### Tests (30+ tests in test_session_persistence.py)
- 10 test classes: CookiePersistence, BrowserProfilePersistence, HeadersPersistence, DeleteSessionData, ListSessions, StorageFormat, PersistentSessionManagerCreate, GetOrCreateSession, UpdateOperations, Cleanup, DelegatedOperations
- All tests use `tmp_path` fixture for isolated storage directories

## 2026-03-22 — OBS-002: Prometheus Metrics

### Design Decisions

- **No prometheus_client dependency** — Implemented a lightweight `MetricsCollector` class in `packages/core/metrics.py` that can export in Prometheus text exposition format without requiring the `prometheus_client` library. Keeps the platform cloud-agnostic.
- **Thread-safe** — All metric mutations protected by `threading.Lock` since metrics may be updated from middleware on different async contexts.
- **Global singleton** — `metrics = MetricsCollector()` at module level. Any component can `from packages.core.metrics import metrics` and start recording.
- **Label support** — All metric types (counter, gauge, histogram) support arbitrary label dicts, stored via composite keys `name{k1="v1",k2="v2"}`.
- **Dual export** — Prometheus text format (`/metrics`) for standard scraping, JSON (`/api/v1/metrics`) for the web dashboard.

### Standard Platform Metrics Wired

- `scraper_http_requests_total` (counter, by method/path/status) — via middleware
- `scraper_tasks_active` (gauge) — in-flight request tracking via middleware
- `scraper_request_duration_ms` (histogram, by method/path) — via middleware
- `scraper_errors_total` (counter, by type) — via middleware on unhandled exceptions
- Additional metrics (`scraper_tasks_total`, `scraper_proxy_pool_size`, `scraper_session_count`, `scraper_extraction_confidence`) available for workers/services to record via the global `metrics` singleton.

### Files Created/Modified

- `packages/core/metrics.py` (new) — MetricsCollector with counter/gauge/histogram + Prometheus/JSON export
- `services/control-plane/routers/metrics.py` (new) — /metrics and /api/v1/metrics endpoints
- `services/control-plane/middleware/metrics.py` (new) — MetricsMiddleware for automatic request tracking
- `services/control-plane/app.py` (modified) — wired metrics router and middleware
- `tests/unit/test_metrics.py` (new) — 30+ tests across 9 test classes

---

## 2026-03-22 — WEB-001: React Web Dashboard Scaffold

### Implementation

Created 17 files in `apps/web/` establishing the React + Vite + TypeScript web dashboard.

**Project configuration:**
- `package.json`: React 18.3, react-router-dom 6.23, @tanstack/react-query 5.40, Vite 5.2, TypeScript 5.4
- `tsconfig.json`: Strict mode, ESNext module, react-jsx, `@/*` path alias
- `vite.config.ts`: React plugin, `/api` proxy to `http://localhost:8000`, source maps

**TypeScript types (`src/api/types.ts`):**
- Mirrors all 7 Pydantic contracts: Task, Policy, Result, Run, Session, Artifact, Billing
- All enums as string union types (TaskStatus, RunStatus, LanePreference, etc.)
- PaginatedResponse<T> generic for list endpoints
- Separate ListItem interfaces matching actual API response shapes

**API client (`src/api/client.ts`):**
- Matches FastAPI endpoint signatures exactly: `/api/v1/tasks`, `/api/v1/policies`, `/api/v1/results`
- Typed request/response for all CRUD operations
- ApiError class with status code and detail message
- Query string builder for filters and pagination

**UI architecture:**
- Layout component with sidebar navigation (NavLink with active state)
- 5 pages: Dashboard, Tasks, TaskDetail, Policies, Results
- Reusable components: TaskTable, StatusBadge
- CSS custom properties for theming, responsive at 768px breakpoint
- Status badges color-coded per status (pending=amber, running=indigo, completed=green, failed=red, etc.)

### Design Decisions
- Plain CSS with custom properties instead of Tailwind — keeps the scaffold dependency-free and readable
- React Query with 30s staleTime for dashboard data — balances freshness with request volume
- Vite proxy for /api avoids CORS issues during development
- No form components yet — scaffold focuses on read operations, forms come in WEB-002

---

## 2026-03-22 — EXT-001: Chrome Manifest V3 Extension Scaffold

### Implementation

Created a complete Chrome Manifest V3 extension in `apps/extension/` with 11 source files plus placeholder icons.

### Architecture

- **Popup** communicates with **background service worker** via `chrome.runtime.sendMessage`
- **Service worker** coordinates with **content script** via `chrome.tabs.sendMessage`
- Content script performs client-side extraction (JSON-LD, meta tags, microdata, DOM heuristics)
- Service worker optionally forwards to cloud control plane for AI normalization
- Settings persisted via `chrome.storage.local`

### Extraction Modes

Four modes available: auto-detect, product, listing, article. Auto-detect uses JSON-LD `@type` hints and DOM heuristics (price elements trigger product mode). Each mode has tailored extraction logic in the content script.

### Files Created

- `manifest.json` — MV3 manifest (activeTab, storage, identity permissions; host_permissions for localhost:8000 and api.aiscraper.io)
- `popup/popup.html` + `popup.css` + `popup.js` — Dark-themed popup UI
- `background/service-worker.js` — ES module service worker with message routing
- `content/content.js` — IIFE content script with extraction + highlighting
- `options/options.html` + `options.js` — Settings page (API endpoint, key, mode, cloud toggle)
- `lib/api.js` — Control plane API client (extract, health, policies)
- `lib/extractor.js` — Shared extraction utilities (JSON-LD, meta, microdata, page type detection)
- `icons/icon{16,48,128}.png` — Valid PNG placeholders
- `icons/icon{16,48,128}.svg` — SVG placeholders

### Design Decisions

- Used ES module for service worker (`"type": "module"`) to enable `import` of lib/api.js
- Content script uses IIFE with double-injection guard (`window.__aiScraperInjected`)
- Element highlighting via CSS class injection (outline + translucent background)
- Cloud mode is opt-in — local extraction works without any API key
- Settings page uses inline styles (single file, no build step needed)

---

## 2026-03-22 — SELFHOST-002: Kubernetes Helm Chart

### Implementation

Created a production-ready Helm chart at `infrastructure/helm/scraper-platform/` with 13 files.

**Chart structure:**
- `Chart.yaml`: apiVersion v2, type application, Bitnami PostgreSQL 15.x.x and Redis 19.x.x as conditional subchart dependencies
- `values.yaml`: Comprehensive defaults for all 4 services (control-plane, worker-http, worker-browser, worker-ai), both embedded and external PostgreSQL/Redis, ingress, HPA, PVC, platform config, and secrets

**Template helpers (_helpers.tpl):**
- `scraper.name`, `scraper.fullname`, `scraper.chart` — standard Helm naming
- `scraper.labels`, `scraper.selectorLabels` — common label sets
- `scraper.componentLabels`, `scraper.componentSelectorLabels` — component-scoped variants
- `scraper.image` — resolves image ref from global registry + component image + appVersion fallback
- `scraper.postgresql.host/port/database/username` — resolves to subchart service or external config
- `scraper.redis.host/port` — resolves to subchart service or external config
- `scraper.secretName` — resolves to existing secret or chart-managed secret

**Deployments (4):**
- All share: configmap envFrom, secret env refs, artifact volume mount, liveness/readiness probes, resource limits
- Control plane: HPA-aware replica count
- Workers: pod anti-affinity (preferredDuringSchedulingIgnoredDuringExecution on hostname topology)
- AI worker: optional AI API key secret refs
- Browser worker: higher defaults (500m/1Gi request, 2cpu/2Gi limit) for Playwright

**Supporting resources:**
- Service: ClusterIP for control-plane (port 80 -> http)
- Ingress: conditional, supports className, annotations, multi-host paths, TLS
- ConfigMap: non-sensitive platform config
- Secret: conditional, base64-encoded credentials + AI API keys
- HPA: conditional, CPU + memory utilization targets
- PVC: conditional, ReadWriteMany for shared artifact storage

### Design Decisions
- Bitnami subchart dependencies for PostgreSQL and Redis
- Dual-mode: embedded subcharts for dev, external connections for production
- Secrets support both inline values and pre-existing Kubernetes Secrets
- Soft pod anti-affinity to avoid scheduling failures on small clusters
- Checksum annotations on deployments for automatic rollout on config changes

---

## 2026-03-22 — CLOUD-001: AWS Terraform Modules

### Implementation

Created production-grade Terraform configuration at `infrastructure/terraform/aws/` with 5 modules and a root module (20 files total).

**Root module (main.tf):**
- AWS provider with default tags, Terraform >= 1.5.0, hashicorp/aws ~> 5.0
- S3 backend block (commented out) for remote state
- ECR repositories per service with immutable tags, scan-on-push, lifecycle policies (keep 20 tagged, expire untagged after 7 days)
- Module composition: VPC -> S3 -> RDS -> Redis -> ECR -> ECS (with dependency wiring)

**modules/vpc:**
- VPC with DNS support/hostnames enabled
- Public subnets (map_public_ip_on_launch) + private subnets across available AZs
- Internet gateway for public subnets
- NAT gateway per AZ with EIP for private subnet egress (HA)
- Separate route tables: public (IGW) and private per AZ (NAT)
- S3 VPC gateway endpoint (free, attached to all route tables)
- VPC flow logs to CloudWatch (60s aggregation, 30d retention)

**modules/ecs:**
- Fargate cluster with Container Insights enabled
- FARGATE (base 1, weight 1) + FARGATE_SPOT (weight 3) capacity providers for cost optimization
- ALB in public subnets with TLS 1.3 security policy
- HTTP listener redirects to HTTPS (301)
- Target group with /health health check
- Task definitions with awslogs driver, environment variables for DB/Redis/S3
- ECS services in private subnets with deployment circuit breaker + rollback
- Only control-plane registered with ALB target group
- Auto-scaling: target tracking on CPU utilization (70%) with 60s scale-out / 300s scale-in cooldown
- IAM: task execution role (ECR pull, CloudWatch logs) + task role (S3 access)
- Deletion protection on ALB in prod

**modules/rds:**
- PostgreSQL 15.7 on gp3 storage with autoscaling
- Multi-AZ configurable (default: true)
- Encrypted at rest (default KMS)
- Performance Insights enabled (7d retention)
- Parameter group: pg_stat_statements, connection/disconnection/duration logging
- Automated backups (7d retention, 03:00-04:00 window)
- Deletion protection + final snapshot in prod; skip in dev
- PostgreSQL + upgrade CloudWatch logs exported
- Security group: port 5432 from ECS tasks only

**modules/redis:**
- Redis 7.1 replication group (cluster mode disabled)
- Transit encryption + at-rest encryption + auth token
- Automatic failover + multi-AZ when num_cache_clusters > 1
- maxmemory-policy: allkeys-lru
- Snapshot retention: 7d prod, 1d non-prod
- Security group: port 6379 from ECS tasks only

**modules/s3:**
- Unique bucket name: {project}-{env}-artifacts-{account_id}
- Versioning enabled
- KMS encryption with bucket key
- All public access blocked
- Bucket policy enforcing TLS
- Lifecycle rules: results/ -> STANDARD_IA at 30d -> GLACIER at 90d; temp/ expires at 7d; noncurrent versions expire at 30d; incomplete uploads abort at 3d
- CORS for web dashboard uploads

### Design Decisions
- NAT gateway per AZ (not shared) for production-grade HA — each AZ is independent
- FARGATE_SPOT with 3x weight over FARGATE for cost savings on workers (non-critical, restartable)
- S3 VPC endpoint is a gateway type (free) not interface type (paid) — cost-conscious
- ECR lifecycle policies to prevent unbounded image storage growth
- gp3 storage for RDS (better price-performance than gp2)
- Auth token for Redis transit encryption (required when transit_encryption_enabled=true)
- Terraform .gitignore excludes state files and tfvars to prevent secret leakage

---

## 2026-03-22 — EXE-001: Tauri v2 Desktop Project Scaffold

### Implementation

Created 12 files in `apps/desktop/` establishing the Tauri v2 desktop application shell.

**Rust backend (src-tauri/):**
- `Cargo.toml`: scraper-desktop crate with tauri 2.0, tauri-build 2.0, serde, serde_json, tokio, tauri-plugin-shell 2.0, tray-icon feature
- `tauri.conf.json`: Window 1200x800, CSP for localhost API, shell plugin scoped to Python uvicorn, tray icon config, bundle identifiers
- `src/main.rs`: Tauri Builder with shell plugin, 4 invoke handlers, devtools in debug, system tray placeholder
- `src/lib.rs`: ServerState with Mutex PID tracking. start_local_server spawns uvicorn on 127.0.0.1:8321 with desktop env vars (SQLite, filesystem, memory). stop_local_server uses platform-aware kill (taskkill on Windows, kill -TERM on Unix). get_status and get_version.
- `build.rs`: Standard tauri_build::build()

**Frontend (src/):**
- `main.tsx`: React root with QueryClient (30s staleTime), BrowserRouter
- `App.tsx`: Desktop UI with server management controls, status indicator, API link
- `hooks/useTauri.ts`: Typed invoke wrapper with __TAURI_INTERNALS__ detection, graceful browser fallback

**Configuration:**
- `package.json`: React 18 + @tauri-apps/api 2.0 + @tauri-apps/plugin-shell 2.0 + @tauri-apps/cli 2.0
- `vite.config.ts`: Fixed port 5173, TAURI_ env prefix, platform-specific build targets
- `tsconfig.json` + `tsconfig.node.json`: Strict TypeScript, path aliases
- `index.html`: Entry point with drag region styles

### Design Decisions
- Local server port 8321 (different from cloud 8000) to avoid conflicts
- Desktop env: SCRAPER_MODE=desktop, SQLite DB, filesystem storage, memory queue/cache
- std::sync::Mutex (not tokio) since critical sections are short without await points
- Shell plugin scope restricts sidecar to only the Python uvicorn command
- Platform-aware process kill: taskkill /T /F on Windows, kill -TERM on Unix
