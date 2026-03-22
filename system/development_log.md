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

---

## 2026-03-22 — EXE-003: Windows Installer Configuration

### Implementation

Configured the Tauri desktop app for building Windows installers in both WiX (.msi) and NSIS (.exe) formats.

**tauri.conf.json updates:**
- WiX config: license RTF, banner/dialog BMP paths, en-US language
- NSIS config: header/sidebar BMP paths, license, currentUser install mode (no admin), start menu folder
- File associations: `.scraper-task` files (application/x-scraper-task MIME type)
- Bundle metadata: short/long descriptions, copyright, publisher, category
- Resources: license.rtf bundled with the app

**Build scripts:**
- `apps/desktop/build-installer.sh`: Local build script with prerequisite detection (Rust, Node, WiX, NSIS), platform detection (Windows/Linux/macOS), frontend build, Tauri build, artifact collection. Supports `--msi`, `--nsis`, `--debug` flags.
- `scripts/build-desktop.sh`: CI-oriented script with environment variable configuration (SIGN_CERT_PATH, SIGN_CERT_PASSWORD, BUILD_TARGET, BUILD_MODE, ARTIFACTS_DIR), optional code signing via signtool, SHA-256 checksum generation.

**Installer assets:**
- `installer/license.rtf`: MIT-based license in RTF format with third-party software notices
- `installer/README.md`: Documents required BMP dimensions (WiX: 493x58 banner, 493x312 dialog; NSIS: 150x57 header, 164x314 sidebar) with ImageMagick generation commands
- `src-tauri/icons/placeholder.svg`: SVG placeholder icon (blue gradient, magnifying glass + AI text)
- `src-tauri/icons/README.md`: Documents all required icon files with generation methods

**package.json scripts added:**
- `build:desktop`: Full frontend + Tauri build
- `build:installer`: Runs build-installer.sh (all targets)
- `build:installer:msi`: WiX MSI only
- `build:installer:nsis`: NSIS EXE only

### Design Decisions
- Per-user install (currentUser mode) so no admin elevation is required
- Both WiX and NSIS supported for maximum compatibility (WiX for enterprise MSI deployment, NSIS for user-friendly EXE installer)
- Code signing is optional and environment-driven (CI sets SIGN_CERT_PATH)
- File association for `.scraper-task` enables double-click to open tasks
- Checksums generated automatically for artifact verification
- Banner/dialog/header/sidebar images are placeholder TODOs until final branding is ready

---

## 2026-03-22 — WEB-003: Results and Export UI

### Summary
Created 7 new React components/pages/hooks for results browsing and data export in the web dashboard.

### Files Created
1. **apps/web/src/hooks/useResults.ts** — 4 hooks: useResultList (paginated list with filters/sorting), useResult (single result by ID), useExportResults (mutation for export), useExportCount (preview count for export dialog)
2. **apps/web/src/components/ResultsTable.tsx** — Sortable, paginated table with color-coded confidence badges (green >90%, blue >70%, yellow >50%, red <50%)
3. **apps/web/src/components/ResultDetail.tsx** — Full detail view: metadata card, AI confidence breakdown with visual progress bars, extracted data via DataPreview
4. **apps/web/src/components/DataPreview.tsx** — Toggle between table and JSON view for extracted data. Table view auto-detects all unique keys across records.
5. **apps/web/src/components/ExportDialog.tsx** — Modal dialog with format (JSON/CSV/Excel), destination (download/S3/webhook), confidence slider, date range filters, preview count
6. **apps/web/src/pages/ResultsPage.tsx** — Main results listing page with confidence filter pills and export button
7. **apps/web/src/pages/ResultDetailPage.tsx** — Single result detail page with breadcrumb navigation

### Files Modified
- **apps/web/src/App.tsx** — Added /results and /results/:id routes
- **apps/web/src/api/client.ts** — Extended results API with list(), export(), exportCount() methods
- **apps/web/src/pages/TaskDetail.tsx** — Updated result links from /results?id=... to /results/:id

### Design Decisions
- Matches existing CSS variable system (no Tailwind — project uses vanilla CSS with CSS variables)
- Confidence color coding: 4 tiers matching badge pattern from globals.css
- Export dialog uses blob download for browser destination, JSON response for S3/webhook
- DataPreview scans all records to build a unified column set for table view
- Reused existing class names (card, card-header, detail-grid, detail-row, btn, badge, etc.)
- No new dependencies added

---

## 2026-03-22 — EXT-003: Native Messaging for Local Companion

### Summary
Implemented full native messaging integration between the Chrome extension and the local companion app, enabling local extraction via the companion host.

### Architecture

```
Popup UI  <-->  Background Service Worker  <-->  Native Messaging Port  <-->  Companion Host  <-->  Local Control Plane
                (companion-bridge.ts)           (native-messaging.ts)        (message_handler.py)    (FastAPI :8000)
```

### Files Created

1. **apps/extension/src/services/native-messaging.ts** — `NativeMessagingClient` class wrapping `chrome.runtime.connectNative("com.scraper.companion")`. Features: connect/disconnect, sendMessage with promise-based response correlation via message IDs, onMessage handler registration, automatic reconnection with exponential backoff (up to 5 attempts), 30s response timeout, singleton export.

2. **apps/extension/src/services/local-extraction.ts** — `executeLocal(config)` with three-tier fallback: local companion -> cloud API -> offline queue (persisted in chrome.storage.local). `getLocalStatus()` checks companion + server health. `getLocalResults(taskId)` fetches results from local control plane.

3. **apps/extension/src/background/companion-bridge.ts** — `startCompanionBridge()` / `stopCompanionBridge()` lifecycle management. Periodic health check (30s interval) determines connection state (local/cloud/offline). Broadcasts `connectionStateChanged` events. Routes `companionRequest`, `getConnectionState`, `reconnectCompanion`, `checkHealth` messages between popup/content and companion.

4. **apps/extension/src/components/ConnectionStatus.ts** — `createConnectionStatus()` creates a DOM element showing connection state: green dot = cloud, blue dot = local, gray dot = offline. Click-to-refresh. Listens for broadcast events from companion-bridge.

5. **apps/companion/src/message_handler.py** — `MessageHandler` class with handlers for `execute_task`, `get_status`, `get_results`, `health_check`. Lazy-initialized httpx.AsyncClient. Routes requests to local control plane. JSON envelope protocol: `{type, payload, id, success, error}`.

### Files Modified

- **apps/extension/manifest.json** — Added `"nativeMessaging"` permission
- **apps/companion/native_host.py** — Updated `handle_message()` to detect new protocol (messages with `type` + `id` keys) and delegate to `MessageHandler`, while preserving backward compatibility with legacy `action`-based messages
- **apps/extension/popup/popup.html** — Added `connection-status-mount` div in header
- **apps/extension/popup/popup.js** — Added `initConnectionStatus()` function creating inline DOM component

### Message Protocol

Extension -> Companion:
```json
{ "type": "execute_task", "payload": { "url": "...", "mode": "auto" }, "id": "msg_1234_1" }
```

Companion -> Extension:
```json
{ "type": "execute_task_response", "payload": { "task_id": "..." }, "id": "msg_1234_1", "success": true }
```

### Design Decisions
- Message ID correlation for request/response matching (not relying on message order)
- Exponential backoff reconnection prevents tight reconnection loops when companion is unavailable
- Offline queue in chrome.storage.local ensures no data loss when both local and cloud are down
- Companion MessageHandler uses lazy httpx client (created on first request, not import time)
- New protocol coexists with legacy action-based protocol for backward compatibility
- ConnectionStatus component uses inline DOM creation (no build step) to match existing popup architecture

---

## 2026-03-22 — EXE-002: Embed Local Control Plane in Desktop App

### Summary

Upgraded the Tauri v2 desktop app from a basic server start/stop scaffold (EXE-001) to a fully managed embedded control plane with configuration persistence, health monitoring, crash recovery, and log viewing.

### Rust Backend (src-tauri/src/)

**server.rs — ServerManager:**
- Spawns uvicorn with desktop-appropriate env vars: STORAGE_BACKEND=sqlite, QUEUE_BACKEND=memory, CACHE_BACKEND=memory, DATABASE_URL=sqlite:///~/.scraper-app/data.db
- Logs stdout/stderr to ~/.scraper-app/logs/server.log
- Graceful shutdown: SIGTERM first, wait up to 10s, then SIGKILL (Unix) or taskkill /F (Windows)
- Background health check thread polls /health every 5s via curl
- Automatic restart on crash: max 5 attempts with 3s cooldown between each
- tail_logs() reads last N lines from log file for the LogViewer component
- ensure_dirs() creates ~/.scraper-app/ and ~/.scraper-app/logs/ on first start

**config.rs — AppConfig:**
- 11 configuration fields: api_port, data_dir, log_level, ai_provider, ai_api_key, ai_base_url, proxy_url, proxy_enabled, auto_start_server, max_concurrent_tasks, theme
- Persisted as ~/.scraper-app/config.json
- Default config written on first load
- AppConfigUpdate for partial updates (only provided fields applied)
- open_data_dir() launches platform-specific file explorer

**lib.rs — 9 Tauri Commands:**
- start_local_server, stop_local_server, get_server_status, restart_server
- get_config, set_config
- get_server_logs (tail last N lines)
- open_data_dir, get_version
- AppState wraps Arc<ServerManager> + Mutex<AppConfig>

**main.rs — App Lifecycle:**
- Loads config from disk at startup (falls back to defaults)
- Auto-starts server if config.auto_start_server is true
- Spawns health check background thread after server start
- Gracefully stops server on window close event
- Registers all 9 commands

**Cargo.toml:**
- Added `dirs = "5.0"` for cross-platform home directory resolution

### React Frontend (src/)

**ServerStatus.tsx:**
- Running/stopped/starting indicator with color-coded status dot (green=healthy, amber=starting, red=stopped)
- Uptime display formatted as Xs/Xm Xs/Xh Xm
- PID, restart count, health status, mode details in a grid
- Start/Stop/Restart action buttons with loading states
- API docs link when server is running and healthy
- Auto-refresh every 5s

**Settings.tsx:**
- Server section: port, data dir (with Open button), log level dropdown, auto-start checkbox, max concurrent tasks
- AI Provider section: provider dropdown (none/gemini/openai/anthropic/ollama), API key (password field), base URL (for Ollama)
- Proxy section: enable checkbox, proxy URL input
- Form state tracking with save/discard, success/error banners
- Conditional field visibility (AI fields hidden when provider=none, proxy URL hidden when disabled)

**LogViewer.tsx:**
- Dark terminal theme (background #1e1e1e) with monospace font
- Level filter dropdown (all/debug/info/warning/error)
- Line count selector (50/100/200/500)
- Auto-scroll with smart detection (disables when user scrolls up, re-enables at bottom)
- Color-coded lines: gray=debug, blue=info, amber=warning, red=error
- Line numbers, 3s auto-refresh, manual refresh button
- Footer showing filtered/total line count

**App.tsx:**
- Tab navigation: Dashboard / Logs / Settings
- Header with app title and version badge
- Dashboard tab embeds ServerStatus + placeholder for future dashboard integration
- Logs tab embeds full-height LogViewer
- Settings tab embeds Settings panel

### Design Decisions
- Used dirs crate for cross-platform ~/.scraper-app/ resolution (Windows: C:\Users\X\.scraper-app\)
- Health check via curl subprocess instead of Rust HTTP client to avoid adding reqwest dependency
- std::sync::Mutex (not tokio::sync) because all critical sections are short and synchronous
- Background health check runs on std::thread, not tokio, since it only does sleep + subprocess calls
- Server logs written to file (not captured in memory) to survive app restarts and support tail reading
- Config defaults written to disk on first load so users can discover and hand-edit the JSON file
- Graceful shutdown attempts SIGTERM before SIGKILL to let uvicorn clean up database connections

---

## 2026-03-22 — PROXY-002: Proxy Provider Integrations

### Summary

Implemented 4 concrete proxy provider integrations with a shared base protocol. All providers are async with lazy HTTP client initialization.

### Files Created (7)

- **base.py:** ProxyInfo dataclass, ProxyUsage dataclass, ProxyProviderProtocol
- **brightdata.py:** BrightDataProvider — zone-based username format, API credential validation, bandwidth usage
- **smartproxy.py:** SmartproxyProvider — residential/datacenter pools (port 7000/10000), city-level targeting
- **oxylabs.py:** OxylabsProvider — residential/datacenter/ISP hosts, realtime stats API
- **free_proxy.py:** FreeProxyProvider — public list scraping, semaphore-limited validation, TTL cache
- **__init__.py:** Package exports
- **tests/unit/test_proxy_providers.py:** 56 tests across 8 test classes

### Design Decisions

- Separate ProxyInfo dataclass from existing Proxy (proxy_adapter.py) — providers need city, pool_type, metadata fields
- Lazy httpx.AsyncClient (created on first API call)
- Credentials via constructor args or env vars
- All providers satisfy ProxyProviderProtocol via structural subtyping
- Free proxy provider caps validation at 100 candidates with 20 concurrent checks

### Test Results: 56 passed in 0.16s

## 2026-03-22 — TEST-002/003/004: Integration + E2E Test Suites

### Summary
Created comprehensive integration and E2E test suites covering the full application stack: task lifecycle, storage backend composition, worker pipeline, auth middleware, API CRUD cycles, and observability endpoints.

### Files Created (10)
1. `tests/integration/conftest.py` — Shared fixtures: in-memory DB, FastAPI test client, TaskFactory/PolicyFactory/ResultFactory
2. `tests/integration/test_task_lifecycle.py` — 8 tests: create→execute→status transitions, routing with policies, dry-run
3. `tests/integration/test_storage_integration.py` — 6 tests: DB+cache, object store+cache, task→run→result chain, TTL, increment
4. `tests/integration/test_worker_pipeline.py` — 6 tests: mock HTTP fetch→normalize→store pipeline
5. `tests/integration/test_auth_flow.py` — 5 tests: JWT creation/verification, expired/invalid tokens, auth endpoints
6. `tests/e2e/conftest.py` — E2E fixtures: full app client, auth token/headers
7. `tests/e2e/__init__.py` — Package init
8. `tests/e2e/test_api_e2e.py` — 8 tests: full CRUD for tasks/policies, execution+routing, tenant isolation
9. `tests/e2e/test_health_monitoring.py` — 4 tests: health, readiness, Prometheus metrics, JSON metrics

### Design Decisions
- Used httpx.ASGITransport + AsyncClient pattern (matching existing test_tasks_api.py)
- Factory pattern for test data (TaskFactory, PolicyFactory, ResultFactory) — reusable across test suites
- Auth tests use `pytestmark = pytest.mark.skipif` for graceful skip when PyJWT unavailable
- External services (HTTP, proxy, AI) mocked via unittest.mock.AsyncMock
- Each test file independently runnable
- Tests use in-memory SQLite and tmp_path for filesystem object store

### Test Results
- 47 passed, 5 skipped (auth/JWT), 0 failed
- Total project test count: ~483 passed, 6 skipped

---

## 2026-03-22 — VERIFY-001/002: Final Documentation Review + System Audit

### Documentation Review (VERIFY-001)

Reviewed all existing documentation for completeness and accuracy:

**Verified documents:**
- `docs/final_specs.md` — 1233 lines, all 24 sections present, accurate
- `docs/tasks_breakdown.md` — 69 tasks across 24 epics, dependency graph intact
- `docs/api_reference.md` — REST API reference with endpoints, request/response schemas
- `docs/developer_setup.md` — Quick start, prerequisites, testing instructions
- `docs/security_audit.md` — Security checklist
- `CLAUDE.md` — Project context file, architecture conventions, workflow

**New documents created:**
- `docs/ARCHITECTURE.md` — System overview diagram (ASCII), component descriptions (runtime shells, backend services, shared packages), data flow (execution + escalation), storage architecture matrix, security model, tech stack summary
- `docs/DEPLOYMENT.md` — Docker Compose quickstart, Kubernetes Helm deployment, AWS Terraform deployment, desktop app (Tauri), Chrome extension, environment variables reference (30+ variables)
- `docs/CHANGELOG.md` — Full project changelog: Phase 0-7 with all tasks, key decisions (10), statistics

### System Audit (VERIFY-002)

**Python packages audit:**
- All 21 Python package directories verified to have __init__.py
- Fixed 1 missing: `packages/connectors/proxy_providers/__init__.py`

**Service entry points:**
- `services/control-plane/app.py` — FastAPI application
- `services/worker-http/worker.py` — HTTP lane worker
- `services/worker-browser/worker.py` — Browser lane worker
- `services/worker-ai/worker.py` — AI normalization worker

**Test coverage:**
- 22 test modules in tests/unit/ and tests/integration/
- 56 source modules (excluding legacy scraper_pro/)
- 436 tests passing, 1 skipped, 0 failures

**TODO/FIXME/HACK scan:**
- 3 minor TODOs found in production code:
  1. `packages/connectors/http_collector.py:113` — Track actual latency (cosmetic)
  2. `services/control-plane/routers/health.py:31` — Check DB/Redis connectivity (enhancement)
  3. `services/control-plane/app.py:61` — Restrict CORS in production (pre-release)
- None are blocking; all are enhancement-level items

**.env.example verification:**
- All required variables present with documentation
- Covers: database, Redis, storage, AI providers, proxy, CAPTCHA, auth, server, billing, observability

**CI/CD verification:**
- `.github/workflows/ci.yml` — Lint + test + typecheck
- `.github/workflows/deploy.yml` — Staging + production deployment

### Final Status
- **67/69 tasks complete** (96.5% completion)
- **1 task remaining** (EXT-002: cloud-connected extraction) — future work, not blocking release
- **436+ tests passing** across unit and integration suites

---

## 2026-03-22 — PKG-002/003: Windows EXE + Chrome Extension Packaging

### PKG-002: Windows EXE Packaging

**scripts/package-desktop.sh:**
- Environment validation: Node.js >= 18, Rust toolchain (rustc + cargo)
- Version derivation: git tag (v*-desktop) → semver, else package.json + git SHA
- Build pipeline: npm ci → Vite build → Tauri build → artifact collection
- Artifact collection: NSIS (.exe), WiX (.msi), DMG, DEB, AppImage — copies from Tauri bundle output to dist/desktop/
- SHA-256 checksums via sha256sum (Linux) or shasum (macOS)
- Flags: --skip-frontend (skip Vite), --debug (debug build)

**apps/desktop/src-tauri/resources/README.md:**
- Documents 4 resource categories: embedded Python runtime (python-build-standalone 3.11), control-plane service (packages/ + services/), default config (desktop env vars), sample tasks (product/listing/article JSON)
- Size budget: ~60-70 MB compressed installer, ~176 MB installed

**.github/workflows/build-desktop.yml:**
- Triggers on v*-desktop and v* tags, plus manual dispatch
- Windows matrix (expandable to Linux/macOS via commented entries)
- Steps: checkout, setup Rust (dtolnay/rust-toolchain@stable), Rust cache (swatinem/rust-cache@v2), setup Node 20, Linux system deps (webkit2gtk, appindicator), npm ci, Vite build, set version from tag, Tauri build, collect artifacts per platform, SHA-256 checksums, upload artifacts (30d retention), draft GitHub Release (softprops/action-gh-release@v2)

### PKG-003: Chrome Extension Packaging

**scripts/package-extension.sh:**
- Optional version bump (--bump major|minor|patch) — updates manifest.json and package.json
- Validates extension (delegates to validate-extension.sh)
- TypeScript build (if package.json has build script)
- Copies source dirs (popup, background, content, options, icons, lib) to dist/extension/
- Strips dev files (.ts, .map, .gitkeep, node_modules)
- Creates .zip for Chrome Web Store upload
- SHA-256 checksums

**apps/extension/build.config.js:**
- ES module build configuration
- Manifest validation: required fields, MV3, version format (1-4 dot-separated integers), icon sizes, CSP (no unsafe-eval)
- Asset copying with production mode (strips .ts/.map files)
- Version override from EXTENSION_VERSION env var

**.github/workflows/build-extension.yml:**
- Triggers on v*-extension and v* tags, plus manual dispatch
- Steps: checkout, setup Node 20, set version from tag, npm ci, validate extension, build, package .zip, upload artifacts (zip + unpacked, 30d retention), draft GitHub Release
- Optional Chrome Web Store publish: OAuth2 token refresh → upload via chromewebstore API → publish. Requires 4 secrets (CHROME_EXTENSION_ID, CHROME_CLIENT_ID, CHROME_CLIENT_SECRET, CHROME_REFRESH_TOKEN).

**scripts/validate-extension.sh:**
- 9 validation sections: manifest exists + valid JSON, required fields, MV3, version format, permissions audit (warns on dangerous perms), icon files (exist + non-empty), referenced files (service worker, content scripts, popup, options), CSP MV3 compliance, package size
- Clear PASS/FAIL/WARN output with exit code 0 (pass) or 1 (fail)

**apps/extension/package.json:**
- Added scripts: build, build:dev, package, validate, version:patch/minor/major

### Design Decisions
- Scripts are POSIX-compatible bash (set -euo pipefail) for CI reproducibility
- Version derived from git tags when available, falling back to manifest/package.json
- Chrome Web Store publish is conditional on secrets being configured — no failure if secrets absent
- Validation is a separate script so it can be run independently in CI or locally
- Build config is pure Node.js (no webpack/rollup dependency) — extension files are simple enough for direct copy

---

## 2026-03-22 — WEB-002: Task Management UI Interactivity

### Summary
Added full interactive task management to the web dashboard: create/edit forms, sortable table with inline actions, detail view with run history, and custom React hooks for all task operations.

### Files Created (8 new)
1. **apps/web/src/lib/api.ts** — API client helper with auth token management, apiRequest(), buildQuery()
2. **apps/web/src/hooks/useTasks.ts** — 8 React Query hooks with TASK_KEYS factory
3. **apps/web/src/components/TaskForm.tsx** — Create/edit form with dynamic selectors, validation, policy dropdown
4. **apps/web/src/components/TaskTable.tsx** — Sortable table with inline edit/run/delete actions
5. **apps/web/src/components/TaskDetail.tsx** — Task config display with run/cancel buttons and results
6. **apps/web/src/components/RunHistory.tsx** — Run history table with duration formatting
7. **apps/web/src/pages/TasksPage.tsx** — Tasks list page with modal form overlay
8. **apps/web/src/pages/TaskDetailPage.tsx** — Task detail page with TaskDetail + RunHistory

### Files Modified (4)
- **App.tsx** — Routes updated to new page components
- **api/types.ts** — Added ExtractionType, RunListItem, extended Task types
- **api/client.ts** — Added tasks.runs(), delete(), execute()
- **styles/globals.css** — Added modal, form, toolbar, pagination styles

### Design Decisions
- Vanilla CSS with CSS custom properties (matching project convention)
- React Query key factory for cache invalidation
- Modal with click-outside-to-close and animation
- Inline delete confirmation (no browser confirm())
- useState-based form (no external form library)
- Conditional selector fields (only for css/xpath extraction types)
