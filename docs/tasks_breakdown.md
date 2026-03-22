# Tasks Breakdown

> **Status:** IN PROGRESS
> **Last Updated:** 2026-03-22
> **Derived from:** docs/final_specs.md

---

## Epic 1: Repository Setup

### REPO-001: Initialize monorepo folder structure
- **Parent Epic:** Repository Setup
- **Description:** Create the target folder structure for the platform monorepo.
- **Objective:** All top-level directories exist with placeholder files.
- **Prerequisites:** None
- **Files/Modules:** `/apps`, `/packages`, `/services`, `/infrastructure`, `/tests`, `/scripts`, `/docs`, `/system`
- **Implementation Steps:**
  1. Create directories: `apps/web`, `apps/desktop`, `apps/extension`, `packages/contracts`, `packages/core`, `packages/connectors`, `services/control-plane`, `services/worker-http`, `services/worker-browser`, `services/worker-ai`, `infrastructure/docker`, `infrastructure/terraform`, `tests/unit`, `tests/integration`, `tests/e2e`
  2. Add `.gitkeep` files to empty directories
  3. Create root `pyproject.toml` for monorepo tooling
- **Validation:** All directories exist, `ls -R` confirms structure
- **Tests Required:** None (structural)
- **Expected Output:** Complete folder tree
- **Done Criteria:** All directories exist with .gitkeep or initial files
- **Status:** COMPLETE

### REPO-002: Configure Python monorepo tooling
- **Parent Epic:** Repository Setup
- **Description:** Set up Python packaging, linting, formatting, and dependency management.
- **Objective:** `pyproject.toml` with workspace config, ruff for linting, pytest for testing.
- **Prerequisites:** REPO-001
- **Files/Modules:** `pyproject.toml`, `ruff.toml`, `.python-version`
- **Implementation Steps:**
  1. Create root `pyproject.toml` with project metadata and tool config
  2. Configure ruff for linting and formatting
  3. Set Python 3.11+ as minimum version
  4. Configure pytest with asyncio support
  5. Create `requirements-dev.txt` for development dependencies
- **Validation:** `ruff check .` passes, `pytest --collect-only` works
- **Tests Required:** None (tooling)
- **Expected Output:** Configured tooling files
- **Done Criteria:** Linter, formatter, and test runner configured and working
- **Status:** COMPLETE

### REPO-003: Set up CI/CD pipeline
- **Parent Epic:** Repository Setup
- **Description:** GitHub Actions workflow for lint, test, build on every push.
- **Objective:** CI runs automatically on PR and push to main.
- **Prerequisites:** REPO-002
- **Files/Modules:** `.github/workflows/ci.yml`
- **Implementation Steps:**
  1. Create `.github/workflows/ci.yml`
  2. Steps: checkout → setup Python → install deps → lint → test → build
  3. Matrix: Python 3.11, 3.12
  4. Cache pip dependencies
- **Validation:** Push a commit, verify CI runs and passes
- **Tests Required:** CI pipeline itself validates tests
- **Expected Output:** Green CI checks on GitHub
- **Done Criteria:** CI passes on push
- **Status:** COMPLETE

### REPO-004: Create .gitignore and .env.example
- **Parent Epic:** Repository Setup
- **Description:** Proper gitignore for Python, Node, Rust, and env template.
- **Objective:** Sensitive files never committed; developers know which env vars to set.
- **Prerequisites:** REPO-001
- **Files/Modules:** `.gitignore`, `.env.example`
- **Implementation Steps:**
  1. Create comprehensive `.gitignore` (Python, Node, Rust, IDE, OS files)
  2. Create `.env.example` with all configuration variables and descriptions
- **Validation:** `git status` doesn't show ignored file types
- **Tests Required:** None
- **Expected Output:** `.gitignore`, `.env.example`
- **Done Criteria:** Files exist and are correct
- **Status:** COMPLETE

---

## Epic 2: Documentation

### DOC-001: Finalize docs/final_specs.md
- **Parent Epic:** Documentation
- **Description:** Review and finalize the specification document.
- **Objective:** Specs reviewed for contradictions, gaps filled, marked as FINAL.
- **Prerequisites:** None (draft exists)
- **Files/Modules:** `docs/final_specs.md`
- **Implementation Steps:**
  1. Review all 24 sections for internal consistency
  2. Fill any remaining gaps
  3. Mark status as FINAL
- **Validation:** Peer review or self-review checklist
- **Tests Required:** None
- **Expected Output:** Finalized spec document
- **Done Criteria:** No TODOs remain, status = FINAL
- **Status:** COMPLETE

### DOC-002: Create API reference skeleton
- **Parent Epic:** Documentation
- **Description:** Create OpenAPI/Swagger skeleton for the control plane API.
- **Objective:** API endpoints documented with request/response schemas.
- **Prerequisites:** SCHEMA-001, API-001
- **Files/Modules:** `docs/api-reference.md`, auto-generated from FastAPI
- **Implementation Steps:**
  1. FastAPI auto-generates OpenAPI spec
  2. Create `docs/api-reference.md` with endpoint summaries
  3. Add example requests/responses
- **Validation:** OpenAPI spec validates, docs render correctly
- **Tests Required:** None
- **Expected Output:** API documentation
- **Done Criteria:** All endpoints documented with examples
- **Status:** NOT_STARTED

### DOC-003: Create developer setup guide
- **Parent Epic:** Documentation
- **Description:** Step-by-step guide for setting up the development environment.
- **Objective:** New developer can go from clone to running tests in 15 minutes.
- **Prerequisites:** REPO-002
- **Files/Modules:** `docs/dev-setup.md`
- **Implementation Steps:**
  1. Document prerequisites (Python, Docker, Node.js, Rust)
  2. Document install steps
  3. Document running services locally
  4. Document running tests
- **Validation:** Follow the guide on a clean machine
- **Tests Required:** None
- **Expected Output:** Setup guide document
- **Done Criteria:** Guide is complete and tested
- **Status:** NOT_STARTED

---

## Epic 3: Architecture Scaffolding

### ARCH-001: Create packages/contracts module
- **Parent Epic:** Architecture Scaffolding
- **Description:** Create the shared contracts package with Pydantic models.
- **Objective:** All shared data contracts defined in one importable package.
- **Prerequisites:** REPO-001, REPO-002
- **Files/Modules:** `packages/contracts/__init__.py`, `packages/contracts/task.py`, `packages/contracts/policy.py`, `packages/contracts/session.py`, `packages/contracts/run.py`, `packages/contracts/result.py`, `packages/contracts/artifact.py`, `packages/contracts/billing.py`
- **Implementation Steps:**
  1. Create `packages/contracts/` with `pyproject.toml`
  2. Implement each schema as Pydantic model per Section 7 of specs
  3. Create `__init__.py` with public exports
  4. Add JSON schema generation utility
- **Validation:** Models instantiate, validate, serialize/deserialize correctly
- **Tests Required:** `tests/unit/test_contracts.py`
- **Expected Output:** Importable contracts package
- **Done Criteria:** All 7 schemas implemented with validation, tests passing
- **Status:** COMPLETE

### ARCH-002: Create packages/core engine skeleton
- **Parent Epic:** Architecture Scaffolding
- **Description:** Scaffold the shared core engine package with interfaces.
- **Objective:** Define the Fetcher, Browser, Connector, and Storage protocol interfaces.
- **Prerequisites:** ARCH-001
- **Files/Modules:** `packages/core/__init__.py`, `packages/core/interfaces.py`, `packages/core/router.py`
- **Implementation Steps:**
  1. Create `packages/core/` with `pyproject.toml`
  2. Define Protocol classes: `Fetcher`, `BrowserWorker`, `Connector`, `ObjectStore`, `MetadataStore`, `QueueBackend`
  3. Create `router.py` skeleton for execution routing
  4. Create `__init__.py` with exports
- **Validation:** Interfaces importable, type checking passes
- **Tests Required:** `tests/unit/test_core_interfaces.py`
- **Expected Output:** Core package with protocol interfaces
- **Done Criteria:** All interfaces defined, mypy passes
- **Status:** COMPLETE

### ARCH-003: Create packages/connectors skeleton
- **Parent Epic:** Architecture Scaffolding
- **Description:** Scaffold the connectors package with adapter stubs.
- **Objective:** Connector adapter stubs for HTTP, browser, proxy, CAPTCHA.
- **Prerequisites:** ARCH-002
- **Files/Modules:** `packages/connectors/http_collector.py`, `packages/connectors/browser_worker.py`, `packages/connectors/proxy_adapter.py`, `packages/connectors/captcha_adapter.py`, `packages/connectors/api_adapter.py`
- **Implementation Steps:**
  1. Create `packages/connectors/` with `pyproject.toml`
  2. Create stub implementations of each Connector protocol
  3. Each stub raises NotImplementedError
- **Validation:** Stubs importable, conform to Connector protocol
- **Tests Required:** `tests/unit/test_connector_stubs.py`
- **Expected Output:** Connector package skeleton
- **Done Criteria:** All adapter stubs exist and conform to protocols
- **Status:** COMPLETE

### ARCH-004: Create services/control-plane skeleton
- **Parent Epic:** Architecture Scaffolding
- **Description:** Scaffold the FastAPI control plane service.
- **Objective:** FastAPI app with health endpoint and project structure.
- **Prerequisites:** ARCH-001, ARCH-002
- **Files/Modules:** `services/control-plane/app.py`, `services/control-plane/routers/`, `services/control-plane/dependencies.py`
- **Implementation Steps:**
  1. Create `services/control-plane/` with `pyproject.toml`
  2. Create FastAPI app with CORS, error handling, health endpoint
  3. Create router stubs for tasks, policies, sessions, admin
  4. Create dependency injection setup
- **Validation:** `uvicorn app:app` starts, `/health` returns 200
- **Tests Required:** `tests/integration/test_control_plane_health.py`
- **Expected Output:** Running FastAPI app skeleton
- **Done Criteria:** Server starts, health endpoint works
- **Status:** COMPLETE

---

## Epic 4: Shared Contracts / Schemas

### SCHEMA-001: Implement Task schema
- **Parent Epic:** Shared Contracts
- **Description:** Pydantic model for the Task contract with full validation.
- **Objective:** Task model validates all fields, serializes to JSON and DB-ready dict.
- **Prerequisites:** ARCH-001
- **Files/Modules:** `packages/contracts/task.py`
- **Implementation Steps:**
  1. Define `Task` Pydantic model per spec section 7.1
  2. Add validators (URL format, status transitions, priority range)
  3. Add `TaskCreate`, `TaskUpdate` schemas for API input
  4. Add JSON schema export
- **Validation:** Create valid/invalid tasks, check validation works
- **Tests Required:** `tests/unit/test_task_schema.py`
- **Expected Output:** Task model with validation
- **Done Criteria:** All fields validated, serialization works, tests pass
- **Status:** COMPLETE

### SCHEMA-002: Implement Policy schema
- **Parent Epic:** Shared Contracts
- **Description:** Pydantic model for extraction policies.
- **Objective:** Policy model with nested rate limit, proxy, session, and retry policies.
- **Prerequisites:** ARCH-001
- **Files/Modules:** `packages/contracts/policy.py`
- **Implementation Steps:**
  1. Define `Policy`, `RateLimit`, `ProxyPolicy`, `SessionPolicy`, `RetryPolicy` models
  2. Add validators
  3. Add `PolicyCreate`, `PolicyUpdate` schemas
- **Validation:** Create valid/invalid policies, check nested validation
- **Tests Required:** `tests/unit/test_policy_schema.py`
- **Expected Output:** Policy model with nested schemas
- **Done Criteria:** All nested models validated, tests pass
- **Status:** COMPLETE

### SCHEMA-003: Implement Session, Run, Result, Artifact, Billing schemas
- **Parent Epic:** Shared Contracts
- **Description:** Implement remaining shared contract models.
- **Objective:** All 7 contract schemas from spec section 7 implemented.
- **Prerequisites:** ARCH-001
- **Files/Modules:** `packages/contracts/session.py`, `packages/contracts/run.py`, `packages/contracts/result.py`, `packages/contracts/artifact.py`, `packages/contracts/billing.py`
- **Implementation Steps:**
  1. Implement each schema per spec sections 7.3-7.7
  2. Add validators for each
  3. Add create/update variants for API use
- **Validation:** All models validate, serialize, and cross-reference correctly
- **Tests Required:** `tests/unit/test_schemas.py`
- **Expected Output:** Complete contracts package
- **Done Criteria:** All 7 schemas implemented, all tests pass
- **Status:** COMPLETE

---

## Epic 5: Backend / Control Plane

### API-001: Implement task CRUD endpoints
- **Parent Epic:** Backend / Control Plane
- **Description:** REST API for creating, reading, updating, and cancelling tasks.
- **Objective:** `POST /tasks`, `GET /tasks/{id}`, `POST /tasks/{id}/cancel`, `GET /tasks` (list).
- **Prerequisites:** ARCH-004, SCHEMA-001, STORAGE-001
- **Files/Modules:** `services/control-plane/routers/tasks.py`
- **Implementation Steps:**
  1. Create `tasks.py` router
  2. Implement POST /api/v1/tasks (create task, enqueue)
  3. Implement GET /api/v1/tasks/{id} (get status + result)
  4. Implement POST /api/v1/tasks/{id}/cancel
  5. Implement GET /api/v1/tasks (list with pagination + filters)
  6. Wire to database and queue dependencies
- **Validation:** All endpoints return correct responses, handle errors
- **Tests Required:** `tests/integration/test_task_api.py`
- **Expected Output:** Working task CRUD API
- **Done Criteria:** All 4 endpoints work, integration tests pass
- **Status:** NOT_STARTED

### API-002: Implement policy CRUD endpoints
- **Parent Epic:** Backend / Control Plane
- **Description:** REST API for managing extraction policies.
- **Objective:** Full CRUD for policies.
- **Prerequisites:** ARCH-004, SCHEMA-002, STORAGE-001
- **Files/Modules:** `services/control-plane/routers/policies.py`
- **Implementation Steps:**
  1. Create `policies.py` router
  2. Implement CRUD: create, get, list, update, delete
  3. Validate policy references (domain patterns, lane preferences)
- **Validation:** All endpoints work, handle edge cases
- **Tests Required:** `tests/integration/test_policy_api.py`
- **Expected Output:** Working policy CRUD API
- **Done Criteria:** Full CRUD works, tests pass
- **Status:** NOT_STARTED

### API-003: Implement execution router
- **Parent Epic:** Backend / Control Plane
- **Description:** Route submitted tasks to the correct execution lane.
- **Objective:** Router selects lane based on policy, site profile, and historical data.
- **Prerequisites:** API-001, ARCH-002
- **Files/Modules:** `packages/core/router.py`, `services/control-plane/routers/tasks.py`
- **Implementation Steps:**
  1. Implement lane selection logic per spec section 8.6
  2. Check policy preferred_lane → site profile → default HTTP
  3. Add escalation logic (HTTP → Browser → Hard-target)
  4. Dispatch to correct worker queue
- **Validation:** Router selects correct lane for known test cases
- **Tests Required:** `tests/unit/test_router.py`
- **Expected Output:** Working execution router
- **Done Criteria:** Lane selection correct for all test scenarios, tests pass
- **Status:** NOT_STARTED

### API-004: Implement authentication and tenant middleware
- **Parent Epic:** Backend / Control Plane
- **Description:** API key authentication and tenant isolation middleware.
- **Objective:** All API requests authenticated; tenant_id injected into request context.
- **Prerequisites:** ARCH-004, STORAGE-001
- **Files/Modules:** `services/control-plane/middleware/auth.py`, `services/control-plane/dependencies.py`
- **Implementation Steps:**
  1. Create auth middleware that extracts API key from Bearer token
  2. Look up tenant from API key
  3. Inject tenant_id into request state
  4. Reject unauthorized requests with 401
  5. Add quota checking middleware
- **Validation:** Requests without valid API key rejected; tenant isolation works
- **Tests Required:** `tests/integration/test_auth.py`
- **Expected Output:** Working auth middleware
- **Done Criteria:** Auth enforced, tenant isolation verified, tests pass
- **Status:** NOT_STARTED

### API-005: Implement result and export endpoints
- **Parent Epic:** Backend / Control Plane
- **Description:** Endpoints for retrieving results and exporting data.
- **Objective:** `GET /results/{id}`, `GET /tasks/{id}/results`, `POST /export`.
- **Prerequisites:** API-001, SCHEMA-003, STORAGE-002
- **Files/Modules:** `services/control-plane/routers/results.py`, `services/control-plane/routers/export.py`
- **Implementation Steps:**
  1. Implement GET result by ID
  2. Implement GET results by task ID
  3. Implement POST export (generate XLSX/JSON/CSV, store as artifact)
  4. Implement GET artifact download (presigned URL or direct)
- **Validation:** Results retrieved correctly, exports generate valid files
- **Tests Required:** `tests/integration/test_results_api.py`
- **Expected Output:** Working result/export API
- **Done Criteria:** Results and exports work end-to-end, tests pass
- **Status:** NOT_STARTED

---

## Epic 6: Worker / Execution Lanes

### WORKER-001: Implement HTTP lane worker
- **Parent Epic:** Workers
- **Description:** Worker service that processes HTTP lane tasks from the queue.
- **Objective:** Dequeue task → HTTP fetch → extract → normalize → store result.
- **Prerequisites:** API-003, ARCH-003, STORAGE-001
- **Files/Modules:** `services/worker-http/worker.py`, `packages/connectors/http_collector.py`
- **Implementation Steps:**
  1. Create worker service that polls Redis queue
  2. Implement HTTP collector using httpx with stealth headers
  3. Implement extraction using fallback chain (extruct → CSS → regex)
  4. Store result in database and artifacts in object store
  5. Update task status
- **Validation:** Submit HTTP task → result appears in DB
- **Tests Required:** `tests/integration/test_http_worker.py`
- **Expected Output:** Working HTTP lane worker
- **Done Criteria:** End-to-end HTTP extraction works, tests pass
- **Status:** NOT_STARTED

### WORKER-002: Implement browser lane worker
- **Parent Epic:** Workers
- **Description:** Worker that uses Playwright for JavaScript-rendered pages.
- **Objective:** Dequeue task → launch browser → navigate → interact → extract → store.
- **Prerequisites:** WORKER-001, ARCH-003
- **Files/Modules:** `services/worker-browser/worker.py`, `packages/connectors/browser_worker.py`
- **Implementation Steps:**
  1. Create browser worker service
  2. Implement Playwright-based browser pool
  3. Port existing ajax_handler.py patterns (scroll, click, wait)
  4. Implement extraction from rendered DOM
  5. Store result + optional screenshot artifact
- **Validation:** Submit browser task for JS-rendered page → result appears
- **Tests Required:** `tests/integration/test_browser_worker.py`
- **Expected Output:** Working browser lane worker
- **Done Criteria:** JS-rendered pages extracted correctly, tests pass
- **Status:** NOT_STARTED

### WORKER-003: Implement AI normalization worker
- **Parent Epic:** Workers
- **Description:** Worker that normalizes raw extraction results using AI.
- **Objective:** Consume raw results → AI repair/normalize → store cleaned results.
- **Prerequisites:** WORKER-001, AI-001
- **Files/Modules:** `services/worker-ai/worker.py`, `packages/core/ai_provider.py`
- **Implementation Steps:**
  1. Create AI worker service
  2. Implement AI provider interface with Gemini and OpenAI adapters
  3. Port existing ai_scraper_v3.py extraction prompt patterns
  4. Normalize raw results to canonical schema
  5. Store normalized results
- **Validation:** Raw results cleaned by AI match expected schema
- **Tests Required:** `tests/integration/test_ai_worker.py`
- **Expected Output:** Working AI normalization worker
- **Done Criteria:** AI normalization produces valid canonical results, tests pass
- **Status:** NOT_STARTED

### WORKER-004: Implement lane escalation logic
- **Parent Epic:** Workers
- **Description:** Automatic escalation from HTTP → Browser → Hard-target on failure.
- **Objective:** If HTTP lane fails, task auto-escalates to browser; if browser fails, to hard-target.
- **Prerequisites:** WORKER-001, WORKER-002, API-003
- **Files/Modules:** `packages/core/router.py`, `services/control-plane/routers/tasks.py`
- **Implementation Steps:**
  1. On worker failure, publish escalation event
  2. Router receives event, selects next lane
  3. Re-enqueue task with new lane designation
  4. Track escalation in run history
  5. Max escalation depth configurable (default: 3)
- **Validation:** Failed HTTP task auto-escalates to browser lane
- **Tests Required:** `tests/integration/test_escalation.py`
- **Expected Output:** Working auto-escalation
- **Done Criteria:** Escalation works across lanes, max depth respected, tests pass
- **Status:** NOT_STARTED

---

## Epic 7: Proxy Gateway

### PROXY-001: Port and refactor proxy_manager.py
- **Parent Epic:** Proxy Gateway
- **Description:** Refactor existing proxy_manager.py into packages/connectors.
- **Objective:** AdvancedProxyManager available as shared package with clean interface.
- **Prerequisites:** ARCH-003
- **Files/Modules:** `packages/connectors/proxy_adapter.py`
- **Implementation Steps:**
  1. Copy proxy_manager.py logic to `packages/connectors/proxy_adapter.py`
  2. Implement ProxyProvider protocol from spec section 11.1
  3. Refactor: remove print statements, add structured logging
  4. Add async support (currently sync only)
  5. Add cost tracking per proxy request
- **Validation:** All rotation strategies work, health scoring accurate
- **Tests Required:** `tests/unit/test_proxy_adapter.py`
- **Expected Output:** Refactored proxy adapter
- **Done Criteria:** All strategies work, async-compatible, tests pass
- **Status:** NOT_STARTED

### PROXY-002: Implement proxy provider integrations
- **Parent Epic:** Proxy Gateway
- **Description:** Adapters for proxy providers (file-based, API-based, inline).
- **Objective:** Multiple proxy sources can feed into the proxy manager.
- **Prerequisites:** PROXY-001
- **Files/Modules:** `packages/connectors/proxy_providers/`
- **Implementation Steps:**
  1. Port FileProxyProvider (load from file)
  2. Port APIProxyProvider (fetch from API endpoint)
  3. Add InlineProxyProvider (configured directly in policy)
  4. Add provider health checking
- **Validation:** Each provider type loads proxies correctly
- **Tests Required:** `tests/unit/test_proxy_providers.py`
- **Expected Output:** Working proxy providers
- **Done Criteria:** All 3 provider types work, tests pass
- **Status:** NOT_STARTED

---

## Epic 8: CAPTCHA Gateway

### CAPTCHA-001: Port and refactor CAPTCHA solver
- **Parent Epic:** CAPTCHA Gateway
- **Description:** Refactor engine_v2.py CaptchaSolver into packages/connectors.
- **Objective:** CAPTCHA adapter with multi-service support and cost tracking.
- **Prerequisites:** ARCH-003
- **Files/Modules:** `packages/connectors/captcha_adapter.py`
- **Implementation Steps:**
  1. Extract CaptchaSolver from engine_v2.py
  2. Create CaptchaAdapter with unified interface
  3. Support: 2Captcha, Anti-Captcha, CapMonster
  4. Add cost tracking per solve
  5. Add fallback between services
  6. Add async support
- **Validation:** Mock CAPTCHA challenges solved correctly
- **Tests Required:** `tests/unit/test_captcha_adapter.py`
- **Expected Output:** Working CAPTCHA adapter
- **Done Criteria:** Multi-service support works, cost tracking, async, tests pass
- **Status:** NOT_STARTED

### CAPTCHA-002: Implement CAPTCHA escalation strategy
- **Parent Epic:** CAPTCHA Gateway
- **Description:** Auto-escalation when CAPTCHA detected during scraping.
- **Objective:** Detection → attempt solve → retry → escalate if fails.
- **Prerequisites:** CAPTCHA-001, WORKER-001
- **Files/Modules:** `packages/connectors/captcha_adapter.py`, `packages/core/router.py`
- **Implementation Steps:**
  1. Implement CAPTCHA detection in HTTP and browser responses
  2. On detection: pause → solve → retry request with solution
  3. If solve fails: try next solver → try different proxy → abandon
  4. Log CAPTCHA events with cost
  5. Track per-domain CAPTCHA frequency
- **Validation:** CAPTCHA detection and resolution works in test scenarios
- **Tests Required:** `tests/integration/test_captcha_escalation.py`
- **Expected Output:** Working CAPTCHA escalation
- **Done Criteria:** Detection, solving, and escalation work end-to-end, tests pass
- **Status:** NOT_STARTED

---

## Epic 9: Session Service

### SESSION-001: Implement session manager
- **Parent Epic:** Session Service
- **Description:** Session lifecycle management with health scoring.
- **Objective:** Create, track, score, and invalidate sessions per spec section 10.
- **Prerequisites:** ARCH-002, SCHEMA-003, STORAGE-001
- **Files/Modules:** `packages/core/session_manager.py`
- **Implementation Steps:**
  1. Implement session creation (HTTP, browser, authenticated types)
  2. Implement health scoring algorithm per spec section 10.5
  3. Implement invalidation rules per spec section 10.6
  4. Implement proxy affinity (sticky sessions)
  5. Store sessions in Redis (cache) + PostgreSQL (persistence)
- **Validation:** Sessions created, scored, and invalidated correctly
- **Tests Required:** `tests/unit/test_session_manager.py`
- **Expected Output:** Working session manager
- **Done Criteria:** Full lifecycle works, health scoring accurate, tests pass
- **Status:** NOT_STARTED

### SESSION-002: Implement cookie and browser profile persistence
- **Parent Epic:** Session Service
- **Description:** Persist cookies and browser profiles for session reuse.
- **Objective:** Sessions survive restarts; browser profiles reusable.
- **Prerequisites:** SESSION-001, STORAGE-002
- **Files/Modules:** `packages/core/session_manager.py`, `packages/core/browser_profiles.py`
- **Implementation Steps:**
  1. Port auth_scraper.py cookie persistence logic
  2. Encrypt cookies at rest
  3. Implement browser profile storage (cookies, localStorage, fingerprint)
  4. Profile rotation on schedule or detection signal
- **Validation:** Session persists across restarts, profiles load correctly
- **Tests Required:** `tests/unit/test_session_persistence.py`
- **Expected Output:** Working session persistence
- **Done Criteria:** Cookies + profiles persist and reload, encryption works, tests pass
- **Status:** NOT_STARTED

---

## Epic 10: Storage

### STORAGE-001: Implement PostgreSQL metadata store
- **Parent Epic:** Storage
- **Description:** Database schema and repository layer for PostgreSQL.
- **Objective:** All metadata tables created, CRUD operations via repository pattern.
- **Prerequisites:** ARCH-001, SCHEMA-001, SCHEMA-002, SCHEMA-003
- **Files/Modules:** `packages/core/storage/metadata.py`, `packages/core/storage/migrations/`
- **Implementation Steps:**
  1. Create SQLAlchemy models matching contract schemas
  2. Create Alembic migration for initial schema
  3. Implement repository classes (TaskRepo, PolicyRepo, SessionRepo, etc.)
  4. Add row-level tenant isolation (tenant_id on all queries)
  5. Add connection pooling configuration
- **Validation:** Migrations run, CRUD operations work, tenant isolation verified
- **Tests Required:** `tests/integration/test_metadata_store.py`
- **Expected Output:** Working PostgreSQL store with migrations
- **Done Criteria:** All tables created, repos work, tenant isolation verified, tests pass
- **Status:** NOT_STARTED

### STORAGE-002: Implement object storage adapter
- **Parent Epic:** Storage
- **Description:** S3-compatible object storage for artifacts.
- **Objective:** ObjectStore interface with S3 and filesystem implementations.
- **Prerequisites:** ARCH-002
- **Files/Modules:** `packages/core/storage/object_store.py`
- **Implementation Steps:**
  1. Implement ObjectStore protocol (put, get, delete, list, presigned_url)
  2. S3 implementation using boto3/aioboto3
  3. Filesystem implementation for local/desktop mode
  4. Add content-type detection and checksum verification
- **Validation:** Store and retrieve artifacts with both backends
- **Tests Required:** `tests/integration/test_object_store.py`
- **Expected Output:** Working object storage with 2 backends
- **Done Criteria:** Both S3 and filesystem backends work, tests pass
- **Status:** NOT_STARTED

### STORAGE-003: Implement Redis queue/cache backend
- **Parent Epic:** Storage
- **Description:** Redis integration for task queue, session cache, rate limiting.
- **Objective:** QueueBackend and CacheBackend implementations using Redis.
- **Prerequisites:** ARCH-002
- **Files/Modules:** `packages/core/storage/queue.py`, `packages/core/storage/cache.py`
- **Implementation Steps:**
  1. Implement QueueBackend protocol with Redis (enqueue, dequeue, ack, nack)
  2. Implement session cache (get, set, expire)
  3. Implement rate limit counters (increment, check, reset)
  4. Add pub/sub for real-time progress notifications
  5. Add in-memory fallback for desktop mode
- **Validation:** Queue operations work, cache operations work, rate limiting works
- **Tests Required:** `tests/integration/test_redis_backend.py`
- **Expected Output:** Working Redis backend
- **Done Criteria:** Queue, cache, and rate limiting work, in-memory fallback works, tests pass
- **Status:** NOT_STARTED

### STORAGE-004: Implement SQLite adapter for desktop mode
- **Parent Epic:** Storage
- **Description:** SQLite implementation of MetadataStore for desktop EXE.
- **Objective:** Same repository interface, backed by SQLite instead of PostgreSQL.
- **Prerequisites:** STORAGE-001
- **Files/Modules:** `packages/core/storage/sqlite_metadata.py`
- **Implementation Steps:**
  1. Create SQLite-compatible schema (adapt from PostgreSQL migrations)
  2. Implement same repository interface using aiosqlite
  3. Handle SQLite-specific limitations (no row-level security, limited concurrent writes)
  4. Auto-create database file on first run
- **Validation:** Same test suite passes with SQLite backend
- **Tests Required:** `tests/integration/test_sqlite_store.py`
- **Expected Output:** Working SQLite metadata store
- **Done Criteria:** Repository interface works with SQLite, tests pass
- **Status:** NOT_STARTED

---

## Epic 11: AI Layer

### AI-001: Implement AI provider abstraction
- **Parent Epic:** AI Layer
- **Description:** AIProvider interface with Gemini and OpenAI implementations.
- **Objective:** Pluggable AI providers per spec section 12.6.
- **Prerequisites:** ARCH-002
- **Files/Modules:** `packages/core/ai_provider.py`, `packages/core/ai_providers/gemini.py`, `packages/core/ai_providers/openai.py`
- **Implementation Steps:**
  1. Define AIProvider protocol (extract, classify, normalize)
  2. Port GeminiAI from ai_scraper_v3.py as GeminiProvider
  3. Implement OpenAIProvider
  4. Add provider factory with fallback chain
  5. Add token usage tracking
- **Validation:** Both providers produce valid extraction results
- **Tests Required:** `tests/unit/test_ai_providers.py`
- **Expected Output:** Working AI provider abstraction with 2 implementations
- **Done Criteria:** Both providers work, fallback between them works, tests pass
- **Status:** NOT_STARTED

### AI-002: Implement AI routing classifier
- **Parent Epic:** AI Layer
- **Description:** Lightweight classifier to predict best execution lane for a URL.
- **Objective:** Given a URL, predict whether API/HTTP/browser lane is best.
- **Prerequisites:** AI-001
- **Files/Modules:** `packages/core/ai_classifier.py`
- **Implementation Steps:**
  1. Implement URL-pattern-based heuristic classifier
  2. Add historical success rate lookup
  3. Optional: AI-powered classification for unknown URLs
  4. Cache classification results
- **Validation:** Classifier returns correct lane for known test URLs
- **Tests Required:** `tests/unit/test_ai_classifier.py`
- **Expected Output:** Working lane classifier
- **Done Criteria:** Correct lane prediction for test cases, tests pass
- **Status:** NOT_STARTED

### AI-003: Port extraction prompt engineering
- **Parent Epic:** AI Layer
- **Description:** Port and refine AI extraction prompts from ai_scraper_v3.py.
- **Objective:** Reusable prompt templates for product extraction, normalization, repair.
- **Prerequisites:** AI-001
- **Files/Modules:** `packages/core/ai_prompts.py`
- **Implementation Steps:**
  1. Extract prompt templates from ai_scraper_v3.py
  2. Create parameterizable prompt builder
  3. Add prompts for: product extraction, schema normalization, data repair, deduplication
  4. Add response parsing with validation
- **Validation:** Prompts produce correct results on test HTML samples
- **Tests Required:** `tests/unit/test_ai_prompts.py`
- **Expected Output:** Reusable prompt templates
- **Done Criteria:** All prompt types produce valid output, tests pass
- **Status:** NOT_STARTED

---

## Epic 12: Result Normalization

### NORM-001: Implement schema mapping layer
- **Parent Epic:** Normalization
- **Description:** Map heterogeneous extraction results to canonical Result schema.
- **Objective:** Any extraction output maps to standardized field names and types.
- **Prerequisites:** SCHEMA-003, ARCH-002
- **Files/Modules:** `packages/core/normalizer.py`
- **Implementation Steps:**
  1. Define field mapping rules (e.g., "cost" → "price", "product_name" → "name")
  2. Implement type coercion (string prices to floats, date parsing)
  3. Port smart_extractors.py ProductData mapping logic
  4. Handle missing fields gracefully (null vs default)
- **Validation:** Various raw extraction formats normalize to canonical schema
- **Tests Required:** `tests/unit/test_normalizer.py`
- **Expected Output:** Working normalization layer
- **Done Criteria:** 10+ test cases normalize correctly, tests pass
- **Status:** NOT_STARTED

### NORM-002: Implement deduplication engine
- **Parent Epic:** Normalization
- **Description:** Detect and merge duplicate records in extraction results.
- **Objective:** Same product from different pages/runs identified as duplicate.
- **Prerequisites:** NORM-001
- **Files/Modules:** `packages/core/dedup.py`
- **Implementation Steps:**
  1. Implement fuzzy matching on product name + URL
  2. Implement exact matching on SKU/GTIN
  3. Merge strategy: keep most complete record
  4. Configurable similarity threshold
- **Validation:** Known duplicates detected, non-duplicates preserved
- **Tests Required:** `tests/unit/test_dedup.py`
- **Expected Output:** Working dedup engine
- **Done Criteria:** Duplicates detected accurately, merge logic correct, tests pass
- **Status:** NOT_STARTED

---

## Epic 13: Web Dashboard

### WEB-001: Create React dashboard project
- **Parent Epic:** Web Dashboard
- **Description:** Initialize React + Vite project for the web dashboard.
- **Objective:** Running React app with routing, basic layout, and API client.
- **Prerequisites:** API-001
- **Files/Modules:** `apps/web/`
- **Implementation Steps:**
  1. `npm create vite@latest` with React + TypeScript template
  2. Add Tailwind CSS
  3. Add React Router for navigation
  4. Create API client module (fetch wrapper for control plane)
  5. Create layout: sidebar, header, main content area
- **Validation:** `npm run dev` starts, basic layout renders
- **Tests Required:** None (scaffold)
- **Expected Output:** Running React app shell
- **Done Criteria:** App starts, navigation works, API client configured
- **Status:** NOT_STARTED

### WEB-002: Implement task management UI
- **Parent Epic:** Web Dashboard
- **Description:** Pages for creating, viewing, and managing scraping tasks.
- **Objective:** User can submit a task, see its progress, and view results.
- **Prerequisites:** WEB-001, API-001
- **Files/Modules:** `apps/web/src/pages/tasks/`
- **Implementation Steps:**
  1. Create task list page with filters and pagination
  2. Create task detail page with run history and status
  3. Create task creation form (URL, policy, options)
  4. Add real-time progress updates (polling or WebSocket)
  5. Add task cancellation button
- **Validation:** End-to-end: create task in UI → see progress → view results
- **Tests Required:** `apps/web/src/__tests__/tasks.test.tsx`
- **Expected Output:** Working task management UI
- **Done Criteria:** Full task lifecycle visible in UI, tests pass
- **Status:** NOT_STARTED

### WEB-003: Implement results and export UI
- **Parent Epic:** Web Dashboard
- **Description:** Pages for viewing extraction results and exporting data.
- **Objective:** User can browse results, view details, and export to XLSX/JSON/CSV.
- **Prerequisites:** WEB-002, API-005
- **Files/Modules:** `apps/web/src/pages/results/`
- **Implementation Steps:**
  1. Create results list page
  2. Create result detail page (data table view)
  3. Add export buttons (XLSX, JSON, CSV)
  4. Port smart_exporter.py formatting logic for Excel
  5. Add download handling
- **Validation:** Results viewable, exports download correctly
- **Tests Required:** `apps/web/src/__tests__/results.test.tsx`
- **Expected Output:** Working results/export UI
- **Done Criteria:** Results browsable, exports work, tests pass
- **Status:** NOT_STARTED

---

## Epic 14: Windows EXE

### EXE-001: Initialize Tauri desktop project
- **Parent Epic:** Windows EXE
- **Description:** Create Tauri v2 project wrapping the web dashboard.
- **Objective:** Desktop window renders the React UI with system tray support.
- **Prerequisites:** WEB-001
- **Files/Modules:** `apps/desktop/`
- **Implementation Steps:**
  1. Initialize Tauri v2 project in `apps/desktop/`
  2. Configure to load web dashboard UI
  3. Add system tray icon and menu
  4. Configure window settings (title, size, icon)
  5. Add auto-start option
- **Validation:** `cargo tauri dev` launches desktop window with UI
- **Tests Required:** None (scaffold)
- **Expected Output:** Running Tauri desktop app
- **Done Criteria:** Desktop window launches, UI renders, system tray works
- **Status:** NOT_STARTED

### EXE-002: Embed local control plane in desktop app
- **Parent Epic:** Windows EXE
- **Description:** Run FastAPI control plane as embedded localhost server in Tauri.
- **Objective:** Desktop app starts control plane on localhost, UI connects to it.
- **Prerequisites:** EXE-001, ARCH-004, STORAGE-004
- **Files/Modules:** `apps/desktop/src-tauri/`, `services/control-plane/`
- **Implementation Steps:**
  1. Bundle Python runtime with Tauri (PyInstaller or embedded)
  2. Start uvicorn server on localhost:PORT on app launch
  3. Configure UI to connect to localhost control plane
  4. Use SQLite for metadata, filesystem for artifacts, in-memory for queue
  5. Graceful shutdown on app close
- **Validation:** App starts → control plane starts → UI works → submit task → get result
- **Tests Required:** `tests/e2e/test_desktop_app.py`
- **Expected Output:** Working desktop app with embedded backend
- **Done Criteria:** Full task lifecycle works locally, tests pass
- **Status:** NOT_STARTED

### EXE-003: Build Windows installer
- **Parent Epic:** Windows EXE
- **Description:** Create .msi or .exe installer with code signing.
- **Objective:** Downloadable installer for Windows 10/11.
- **Prerequisites:** EXE-002
- **Files/Modules:** `apps/desktop/`, CI config
- **Implementation Steps:**
  1. Configure Tauri bundler for Windows
  2. Add application icon and metadata
  3. Configure code signing (if certificate available)
  4. Build installer in CI
  5. Test install/uninstall on clean Windows
- **Validation:** Installer works on Windows 10/11, no admin rights required
- **Tests Required:** Manual install test
- **Expected Output:** Windows installer (.msi)
- **Done Criteria:** Installer works, app runs post-install, uninstall clean
- **Status:** NOT_STARTED

---

## Epic 15: Browser Extension

### EXT-001: Create Chrome extension scaffold
- **Parent Epic:** Browser Extension
- **Description:** Manifest V3 Chrome extension with popup, content script, background worker.
- **Objective:** Extension loads in Chrome, popup renders, content script injects.
- **Prerequisites:** None
- **Files/Modules:** `apps/extension/`
- **Implementation Steps:**
  1. Create `manifest.json` (Manifest V3)
  2. Create popup HTML/JS (React or vanilla)
  3. Create background service worker
  4. Create content script for page interaction
  5. Add extension icon
- **Validation:** Load unpacked in Chrome, popup opens, content script runs
- **Tests Required:** None (scaffold)
- **Expected Output:** Working extension scaffold
- **Done Criteria:** Extension loads, popup renders, content script active
- **Status:** NOT_STARTED

### EXT-002: Implement cloud-connected extraction
- **Parent Epic:** Browser Extension
- **Description:** Extension sends current page to cloud backend for extraction.
- **Objective:** User clicks extract → page sent to API → results displayed in popup.
- **Prerequisites:** EXT-001, API-001
- **Files/Modules:** `apps/extension/src/`
- **Implementation Steps:**
  1. Content script captures page HTML and URL
  2. Background worker sends to control plane API
  3. Poll for result
  4. Display results in popup
  5. Handle API key configuration
- **Validation:** Click extract on product page → results appear in popup
- **Tests Required:** `apps/extension/tests/test_extraction.js`
- **Expected Output:** Working cloud extraction from extension
- **Done Criteria:** End-to-end extraction works, tests pass
- **Status:** NOT_STARTED

### EXT-003: Implement native messaging for local companion
- **Parent Epic:** Browser Extension
- **Description:** Extension communicates with local EXE via Chrome native messaging.
- **Objective:** Extension can send tasks to local desktop app instead of cloud.
- **Prerequisites:** EXT-001, EXE-002, COMPANION-001
- **Files/Modules:** `apps/extension/src/`, `apps/companion/`
- **Implementation Steps:**
  1. Create native messaging manifest
  2. Implement message protocol (JSON-based)
  3. Extension detects if companion is available
  4. Route requests to companion instead of cloud
  5. Receive results back via native messaging
- **Validation:** Extension connects to local companion, extraction works
- **Tests Required:** `apps/extension/tests/test_native_messaging.js`
- **Expected Output:** Working native messaging bridge
- **Done Criteria:** Extension ↔ companion communication works, tests pass
- **Status:** NOT_STARTED

---

## Epic 16: Local Companion / Native Messaging

### COMPANION-001: Create native messaging host
- **Parent Epic:** Companion
- **Description:** Lightweight native service that bridges extension and desktop EXE.
- **Objective:** Registers as Chrome native messaging host, forwards requests to local control plane.
- **Prerequisites:** EXE-002
- **Files/Modules:** `apps/companion/`
- **Implementation Steps:**
  1. Create Python-based native messaging host
  2. Register with Chrome (native messaging manifest in system location)
  3. Implement message protocol: receive JSON from extension → forward to localhost API
  4. Return results back to extension
  5. Validate extension ID before accepting connections
- **Validation:** Companion registers, extension connects, messages flow
- **Tests Required:** `tests/integration/test_companion.py`
- **Expected Output:** Working native messaging host
- **Done Criteria:** Extension → companion → local API → results → extension works, tests pass
- **Status:** NOT_STARTED

### COMPANION-002: Implement companion installer
- **Parent Epic:** Companion
- **Description:** Install companion as part of desktop EXE install or separately.
- **Objective:** Companion auto-registers with Chrome on install.
- **Prerequisites:** COMPANION-001, EXE-003
- **Files/Modules:** `apps/companion/installer/`
- **Implementation Steps:**
  1. Bundle companion with desktop EXE installer
  2. Register native messaging manifest in correct Chrome location
  3. Option for standalone companion install (without full desktop app)
  4. Uninstall cleanup (remove registry entries)
- **Validation:** Install desktop → companion registered → extension detects it
- **Tests Required:** Manual install test
- **Expected Output:** Working companion installer
- **Done Criteria:** Companion auto-registers on install, tests pass
- **Status:** NOT_STARTED

---

## Epic 17: Self-Hosted Deployment

### SELFHOST-001: Create Docker Compose stack
- **Parent Epic:** Self-Hosted Deployment
- **Description:** Docker Compose file with all services for self-hosted deployment.
- **Objective:** `docker compose up` starts the full platform.
- **Prerequisites:** API-001, WORKER-001, WORKER-002, STORAGE-001, STORAGE-002, STORAGE-003
- **Files/Modules:** `infrastructure/docker/docker-compose.yml`, `infrastructure/docker/Dockerfile.*`
- **Implementation Steps:**
  1. Create Dockerfiles for: control-plane, worker-http, worker-browser, worker-ai
  2. Create docker-compose.yml with all services + PostgreSQL + Redis + MinIO + nginx
  3. Add health checks for all services
  4. Create `.env.example` with all configuration
  5. Add `install.sh` for guided setup
- **Validation:** `docker compose up` → all services healthy within 60 seconds
- **Tests Required:** `tests/e2e/test_docker_compose.sh`
- **Expected Output:** Working Docker Compose stack
- **Done Criteria:** Stack starts, health checks pass, task lifecycle works, tests pass
- **Status:** NOT_STARTED

### SELFHOST-002: Create Kubernetes Helm chart
- **Parent Epic:** Self-Hosted Deployment
- **Description:** Helm chart for Kubernetes deployment.
- **Objective:** `helm install` deploys the platform on any Kubernetes cluster.
- **Prerequisites:** SELFHOST-001
- **Files/Modules:** `infrastructure/helm/`
- **Implementation Steps:**
  1. Create Helm chart structure
  2. Define deployments, services, ingress, configmaps, secrets
  3. Add HPA for worker scaling
  4. Add PersistentVolumeClaims for data
  5. Add values.yaml with all configuration options
- **Validation:** `helm install` on local k8s (minikube/kind) succeeds
- **Tests Required:** `tests/e2e/test_helm_deploy.sh`
- **Expected Output:** Working Helm chart
- **Done Criteria:** Helm install works, all pods healthy, task lifecycle works
- **Status:** NOT_STARTED

---

## Epic 18: Cloud Deployment

### CLOUD-001: Create Terraform modules for AWS
- **Parent Epic:** Cloud Deployment
- **Description:** Terraform modules for deploying on AWS.
- **Objective:** `terraform apply` creates complete AWS infrastructure.
- **Prerequisites:** SELFHOST-001
- **Files/Modules:** `infrastructure/terraform/aws/`
- **Implementation Steps:**
  1. Module: ECS/Fargate for services
  2. Module: RDS PostgreSQL
  3. Module: ElastiCache Redis
  4. Module: S3 for artifacts
  5. Module: ALB for load balancing
  6. Module: Secrets Manager
  7. Create `variables.tf` and `outputs.tf`
- **Validation:** `terraform plan` succeeds, `terraform apply` on test account works
- **Tests Required:** `tests/e2e/test_aws_deploy.sh`
- **Expected Output:** Working AWS Terraform modules
- **Done Criteria:** Infrastructure creates successfully, services deploy, tests pass
- **Status:** NOT_STARTED

### CLOUD-002: Create CI/CD deployment pipeline
- **Parent Epic:** Cloud Deployment
- **Description:** GitHub Actions workflow for automated deployment.
- **Objective:** Push to main → build → test → deploy to staging → promote to production.
- **Prerequisites:** REPO-003, CLOUD-001
- **Files/Modules:** `.github/workflows/deploy.yml`
- **Implementation Steps:**
  1. Build and push Docker images to ECR/GHCR
  2. Run integration tests
  3. Deploy to staging environment
  4. Run smoke tests on staging
  5. Manual approval gate for production
  6. Deploy to production
- **Validation:** Full pipeline runs on push
- **Tests Required:** Pipeline itself validates
- **Expected Output:** Working CI/CD pipeline
- **Done Criteria:** Automated deployment works end-to-end
- **Status:** NOT_STARTED

---

## Epic 19: Testing

### TEST-001: Set up test infrastructure
- **Parent Epic:** Testing
- **Description:** Configure pytest, testcontainers, fixtures, and test utilities.
- **Objective:** Test infrastructure ready for unit, integration, and e2e tests.
- **Prerequisites:** REPO-002
- **Files/Modules:** `tests/conftest.py`, `tests/fixtures/`, `tests/utils/`
- **Implementation Steps:**
  1. Create `tests/conftest.py` with shared fixtures
  2. Configure testcontainers for PostgreSQL, Redis, MinIO
  3. Create test data factories
  4. Create mock HTTP server for connector tests
  5. Create test HTML pages for extraction tests
- **Validation:** `pytest --collect-only` discovers all tests
- **Tests Required:** Meta-test: fixtures work correctly
- **Expected Output:** Working test infrastructure
- **Done Criteria:** All fixtures work, testcontainers start, tests discoverable
- **Status:** NOT_STARTED

### TEST-002: Write unit tests for all contracts
- **Parent Epic:** Testing
- **Description:** Unit tests for all Pydantic contract models.
- **Objective:** 100% coverage on validation logic for all 7 contract schemas.
- **Prerequisites:** TEST-001, SCHEMA-001, SCHEMA-002, SCHEMA-003
- **Files/Modules:** `tests/unit/test_contracts/`
- **Implementation Steps:**
  1. Test valid object creation for each schema
  2. Test validation rejection for invalid data
  3. Test serialization/deserialization roundtrip
  4. Test edge cases (empty strings, null fields, boundary values)
- **Validation:** All tests pass, coverage >95% on contracts package
- **Tests Required:** This IS the tests
- **Expected Output:** Comprehensive contract tests
- **Done Criteria:** All tests pass, coverage target met
- **Status:** NOT_STARTED

### TEST-003: Write integration tests for control plane
- **Parent Epic:** Testing
- **Description:** Integration tests for all API endpoints using TestClient.
- **Objective:** Every endpoint tested with valid and invalid inputs.
- **Prerequisites:** TEST-001, API-001, API-002, API-004, API-005
- **Files/Modules:** `tests/integration/test_api/`
- **Implementation Steps:**
  1. Test task CRUD endpoints
  2. Test policy CRUD endpoints
  3. Test result/export endpoints
  4. Test auth middleware (valid key, invalid key, missing key)
  5. Test quota enforcement
  6. Test error handling (404, 422, 500)
- **Validation:** All tests pass with testcontainers
- **Tests Required:** This IS the tests
- **Expected Output:** Comprehensive API tests
- **Done Criteria:** All endpoints covered, tests pass
- **Status:** NOT_STARTED

### TEST-004: Write end-to-end extraction tests
- **Parent Epic:** Testing
- **Description:** Full pipeline tests: submit task → execute → get result.
- **Objective:** Verify the complete extraction pipeline works for real URLs.
- **Prerequisites:** TEST-001, WORKER-001, WORKER-002
- **Files/Modules:** `tests/e2e/test_extraction.py`
- **Implementation Steps:**
  1. Test HTTP lane extraction against httpbin.org / test server
  2. Test browser lane extraction against JS-rendered test page
  3. Test fallback/escalation (HTTP fail → browser succeed)
  4. Test result normalization
  5. Test export generation
- **Validation:** All e2e tests pass
- **Tests Required:** This IS the tests
- **Expected Output:** E2E test suite
- **Done Criteria:** Full pipeline tested, tests pass
- **Status:** NOT_STARTED

---

## Epic 20: Observability

### OBS-001: Add structured logging
- **Parent Epic:** Observability
- **Description:** JSON structured logging across all services.
- **Objective:** All services emit JSON logs with correlation IDs.
- **Prerequisites:** ARCH-004
- **Files/Modules:** `packages/core/logging.py`
- **Implementation Steps:**
  1. Create logging configuration module
  2. Configure structlog or python-json-logger
  3. Add correlation_id middleware to FastAPI
  4. Add tenant_id to all log records
  5. Configure per-service log levels via env vars
- **Validation:** Logs output as JSON with all required fields
- **Tests Required:** `tests/unit/test_logging.py`
- **Expected Output:** Structured logging across all services
- **Done Criteria:** JSON logs emitted with correlation IDs, tests pass
- **Status:** NOT_STARTED

### OBS-002: Add Prometheus metrics
- **Parent Epic:** Observability
- **Description:** Prometheus metrics for all key operations.
- **Objective:** Counters, histograms, gauges per spec section 17.2.
- **Prerequisites:** ARCH-004
- **Files/Modules:** `packages/core/metrics.py`, `services/control-plane/metrics.py`
- **Implementation Steps:**
  1. Add prometheus-client dependency
  2. Define metrics: task counters, latency histograms, pool gauges
  3. Add `/metrics` endpoint to control plane
  4. Instrument workers with timing decorators
  5. Create Grafana dashboard JSON
- **Validation:** `/metrics` returns valid Prometheus format
- **Tests Required:** `tests/unit/test_metrics.py`
- **Expected Output:** Working Prometheus metrics
- **Done Criteria:** All key metrics emitted, Grafana dashboard works, tests pass
- **Status:** NOT_STARTED

### OBS-003: Add OpenTelemetry tracing
- **Parent Epic:** Observability
- **Description:** Distributed tracing across services using OpenTelemetry.
- **Objective:** Full trace from task submission to result storage.
- **Prerequisites:** OBS-001
- **Files/Modules:** `packages/core/tracing.py`
- **Implementation Steps:**
  1. Add opentelemetry-api and opentelemetry-sdk
  2. Instrument FastAPI with OTEL middleware
  3. Instrument workers with span creation
  4. Propagate trace context across queue messages
  5. Configure export to Jaeger/Tempo
- **Validation:** Traces visible in Jaeger, spans cover full lifecycle
- **Tests Required:** `tests/integration/test_tracing.py`
- **Expected Output:** Working distributed tracing
- **Done Criteria:** Full task lifecycle traced, visible in Jaeger, tests pass
- **Status:** NOT_STARTED

---

## Epic 21: Packaging

### PKG-001: Create Docker images for all services
- **Parent Epic:** Packaging
- **Description:** Optimized Docker images for each service.
- **Objective:** Multi-stage Dockerfiles producing small, secure images.
- **Prerequisites:** API-001, WORKER-001, WORKER-002, WORKER-003
- **Files/Modules:** `infrastructure/docker/Dockerfile.*`
- **Implementation Steps:**
  1. Control plane: Python slim base, FastAPI + uvicorn
  2. Worker-HTTP: Python slim base, httpx
  3. Worker-Browser: Python + Playwright + Chromium
  4. Worker-AI: Python slim base, AI provider clients
  5. Multi-stage builds to minimize image size
  6. Non-root user in all images
- **Validation:** All images build, containers start, health checks pass
- **Tests Required:** `tests/e2e/test_docker_images.sh`
- **Expected Output:** Docker images for all services
- **Done Criteria:** Images build, run, and pass health checks
- **Status:** NOT_STARTED

### PKG-002: Build Windows EXE installer
- **Parent Epic:** Packaging
- **Description:** Tauri-based Windows installer with bundled runtime.
- **Objective:** Single .msi installer for Windows 10/11.
- **Prerequisites:** EXE-003
- **Files/Modules:** `apps/desktop/`, CI config
- **Implementation Steps:**
  1. Configure Tauri build for Windows target
  2. Bundle Python runtime (embedded distribution)
  3. Bundle Chromium for browser lane
  4. Add code signing to CI pipeline
  5. Test on Windows 10 and 11
- **Validation:** Installer works, app runs, no admin rights needed
- **Tests Required:** Manual test on clean Windows VMs
- **Expected Output:** Windows .msi installer
- **Done Criteria:** Installs and runs on Windows 10/11
- **Status:** NOT_STARTED

### PKG-003: Package browser extension
- **Parent Epic:** Packaging
- **Description:** Chrome Web Store-ready extension package.
- **Objective:** .zip package ready for Chrome Web Store submission.
- **Prerequisites:** EXT-002
- **Files/Modules:** `apps/extension/`
- **Implementation Steps:**
  1. Build extension for production (minify, bundle)
  2. Verify Manifest V3 compliance
  3. Create Chrome Web Store listing assets (screenshots, description)
  4. Generate .zip package
  5. Verify package with Chrome Extension lint tool
- **Validation:** Package loads in Chrome, passes CWS review checklist
- **Tests Required:** Extension lint pass
- **Expected Output:** Chrome Web Store .zip package
- **Done Criteria:** Package loads, CWS review criteria met
- **Status:** NOT_STARTED

---

## Epic 22: Security

### SEC-001: Implement secrets management
- **Parent Epic:** Security
- **Description:** Secure storage and access for all secrets (API keys, passwords).
- **Objective:** Secrets never in code, logs, or API responses.
- **Prerequisites:** ARCH-004
- **Files/Modules:** `packages/core/secrets.py`
- **Implementation Steps:**
  1. Create secrets interface (get_secret, set_secret)
  2. Implementation for env vars (default)
  3. Implementation for AWS Secrets Manager
  4. Implementation for OS keychain (desktop)
  5. Audit: ensure no secrets in logs or responses
- **Validation:** Secrets retrieved from all backends, not leaked
- **Tests Required:** `tests/unit/test_secrets.py`
- **Expected Output:** Working secrets management
- **Done Criteria:** Secrets secure across all deployment modes, tests pass
- **Status:** NOT_STARTED

### SEC-002: Security audit and hardening
- **Parent Epic:** Security
- **Description:** Review all code for security vulnerabilities.
- **Objective:** No OWASP top 10 vulnerabilities, all inputs validated.
- **Prerequisites:** API-001, API-004, WEB-001
- **Files/Modules:** All service and package code
- **Implementation Steps:**
  1. Run bandit (Python security linter)
  2. Check for SQL injection (parameterized queries only)
  3. Check for XSS in web dashboard (React auto-escapes, verify custom HTML)
  4. Check for command injection (no shell=True)
  5. Verify CORS configuration
  6. Verify CSP headers
  7. Check dependency vulnerabilities (pip-audit)
- **Validation:** All security tools pass, no high/critical findings
- **Tests Required:** Security tool results as artifacts
- **Expected Output:** Clean security audit
- **Done Criteria:** No high/critical vulnerabilities, all findings addressed
- **Status:** NOT_STARTED

---

## Epic 23: Migration / Refactor

### MIGRATE-001: Extract reusable code from scraper_pro/
- **Parent Epic:** Migration
- **Description:** Move reusable code from existing scraper_pro/ into new packages.
- **Objective:** Reusable logic available in packages/, scraper_pro/ deprecated.
- **Prerequisites:** ARCH-001, ARCH-002, ARCH-003
- **Files/Modules:** `scraper_pro/` → `packages/`
- **Implementation Steps:**
  1. Move fallback_chain.py → packages/core/fallback.py
  2. Move smart_extractors.py data structures → packages/contracts/
  3. Move proxy_manager.py → packages/connectors/proxy_adapter.py
  4. Move AI extraction logic → packages/core/ai_providers/
  5. Move exporter logic → packages/core/exporter.py
  6. Move scheduler logic → packages/core/scheduler.py
  7. Update all imports
  8. Mark scraper_pro/ as legacy reference
- **Validation:** New packages work, old code no longer imported
- **Tests Required:** Existing tests still pass after migration
- **Expected Output:** Code migrated to target architecture
- **Done Criteria:** All reusable code in packages/, imports updated, tests pass
- **Status:** NOT_STARTED

### MIGRATE-002: Create fetcher abstraction over Scrapling
- **Parent Epic:** Migration
- **Description:** Abstract Scrapling dependency behind Fetcher interface.
- **Objective:** Scrapling is one implementation of the Fetcher protocol, not a hard dependency.
- **Prerequisites:** ARCH-002, MIGRATE-001
- **Files/Modules:** `packages/core/interfaces.py`, `packages/connectors/scrapling_fetcher.py`
- **Implementation Steps:**
  1. Define Fetcher protocol in packages/core/interfaces.py
  2. Create ScraplingFetcher adapter implementing the protocol
  3. Update all code to use Fetcher protocol instead of Scrapling directly
  4. Add httpx-based fetcher as alternative implementation
- **Validation:** Both fetcher implementations work, existing functionality preserved
- **Tests Required:** `tests/unit/test_fetchers.py`
- **Expected Output:** Fetcher abstraction with 2 implementations
- **Done Criteria:** Scrapling abstracted, alternative fetcher works, tests pass
- **Status:** NOT_STARTED

---

## Epic 24: Documentation & Verification

### VERIFY-001: Final documentation review
- **Parent Epic:** Verification
- **Description:** Review all docs for accuracy, completeness, and consistency.
- **Objective:** All documentation matches implemented code.
- **Prerequisites:** All other epics
- **Files/Modules:** `docs/`, `system/`
- **Implementation Steps:**
  1. Review final_specs.md against implementation
  2. Update tasks_breakdown.md with final statuses
  3. Verify API documentation matches endpoints
  4. Verify dev setup guide works on clean machine
  5. Update README.md with current project state
- **Validation:** All docs accurate, no stale information
- **Tests Required:** None (review)
- **Expected Output:** Updated documentation
- **Done Criteria:** All docs current and accurate
- **Status:** NOT_STARTED

### VERIFY-002: Final system audit
- **Parent Epic:** Verification
- **Description:** Complete project audit against acceptance criteria.
- **Objective:** Every acceptance criterion from spec section 23 verified.
- **Prerequisites:** All other epics
- **Files/Modules:** `system/final_step_logs.md`
- **Implementation Steps:**
  1. Walk through every acceptance criterion (technical, product, packaging, deployment)
  2. Record evidence for each
  3. Log in final_step_logs.md
  4. Create final completion report
- **Validation:** All acceptance criteria pass
- **Tests Required:** Acceptance test suite
- **Expected Output:** Completion report with evidence
- **Done Criteria:** All acceptance criteria verified with evidence
- **Status:** NOT_STARTED

---

## Dependency Graph

```
REPO-001 ──┬── REPO-002 ── REPO-003
            │            └── TEST-001
            ├── REPO-004
            └── ARCH-001 ──┬── ARCH-002 ──┬── ARCH-003 ── PROXY-001
                           │              │             └── CAPTCHA-001
                           │              ├── STORAGE-002
                           │              ├── STORAGE-003
                           │              ├── AI-001 ──┬── AI-002
                           │              │            └── AI-003
                           │              └── NORM-001 ── NORM-002
                           │
                           ├── SCHEMA-001 ──┐
                           ├── SCHEMA-002 ──┼── STORAGE-001 ──┬── API-001 ──┬── API-003
                           └── SCHEMA-003 ──┘                 │            ├── API-005
                                                              │            └── WORKER-001 ──┬── WORKER-002
                                                              │                             ├── WORKER-003
                                                              │                             └── WORKER-004
                                                              ├── API-002
                                                              ├── API-004
                                                              ├── SESSION-001 ── SESSION-002
                                                              └── STORAGE-004

ARCH-004 ── API-001 (also depends on SCHEMA-001 + STORAGE-001)
          └── OBS-001 ── OBS-002
                       └── OBS-003

WEB-001 ──┬── WEB-002 ── WEB-003
           └── EXE-001 ── EXE-002 ── EXE-003
                                   └── COMPANION-001 ── COMPANION-002

EXT-001 ──┬── EXT-002
           └── EXT-003

SELFHOST-001 ──┬── SELFHOST-002
                └── CLOUD-001 ── CLOUD-002

PKG-001 (depends on all workers)
PKG-002 (depends on EXE-003)
PKG-003 (depends on EXT-002)

SEC-001 (depends on ARCH-004)
SEC-002 (depends on most implementation tasks)

MIGRATE-001 (depends on ARCH-001, ARCH-002, ARCH-003)
MIGRATE-002 (depends on MIGRATE-001)

VERIFY-001, VERIFY-002 (depend on all other epics)
```

---

## Execution Order

### Phase A — Foundation (Parallel)
1. REPO-001, REPO-004 (parallel)
2. REPO-002 (after REPO-001)
3. REPO-003 (after REPO-002)
4. ARCH-001 (after REPO-002)
5. DOC-001 (parallel with everything)

### Phase B — Contracts & Storage (Parallel)
6. SCHEMA-001, SCHEMA-002, SCHEMA-003 (parallel, after ARCH-001)
7. ARCH-002 (after ARCH-001)
8. ARCH-003 (after ARCH-002)
9. ARCH-004 (after ARCH-001 + ARCH-002)
10. STORAGE-001 (after SCHEMA-001 + SCHEMA-002 + SCHEMA-003)
11. STORAGE-002, STORAGE-003 (parallel, after ARCH-002)

### Phase C — Core Services (Sequential with parallel branches)
12. API-001 (after ARCH-004 + SCHEMA-001 + STORAGE-001)
13. API-002, API-004 (parallel, after ARCH-004 + STORAGE-001)
14. API-003 (after API-001 + ARCH-002)
15. API-005 (after API-001 + SCHEMA-003 + STORAGE-002)
16. PROXY-001, CAPTCHA-001 (parallel, after ARCH-003)
17. SESSION-001 (after ARCH-002 + SCHEMA-003 + STORAGE-001)

### Phase D — Workers (Sequential)
18. WORKER-001 (after API-003 + ARCH-003 + STORAGE-001)
19. WORKER-002 (after WORKER-001)
20. AI-001 (after ARCH-002) — can parallel with workers
21. WORKER-003 (after WORKER-001 + AI-001)
22. WORKER-004 (after WORKER-001 + WORKER-002 + API-003)

### Phase E — Front Ends (Parallel branches)
23. WEB-001 (after API-001) → WEB-002 → WEB-003
24. EXT-001 (independent) → EXT-002 (after API-001) → EXT-003
25. EXE-001 (after WEB-001) → EXE-002 → EXE-003
26. COMPANION-001 (after EXE-002) → COMPANION-002

### Phase F — Migration & AI (Parallel with Phase E)
27. MIGRATE-001 (after ARCH-001 + ARCH-002 + ARCH-003)
28. MIGRATE-002 (after MIGRATE-001)
29. AI-002, AI-003 (parallel, after AI-001)
30. NORM-001, NORM-002 (sequential, after SCHEMA-003 + ARCH-002)

### Phase G — Infrastructure & Quality
31. TEST-001 (after REPO-002) → TEST-002 → TEST-003 → TEST-004
32. OBS-001 (after ARCH-004) → OBS-002 → OBS-003
33. SEC-001 (after ARCH-004)
34. SELFHOST-001 → SELFHOST-002
35. CLOUD-001 → CLOUD-002

### Phase H — Packaging & Verification
36. PKG-001, PKG-002, PKG-003 (parallel)
37. SEC-002 (after most implementation)
38. VERIFY-001, VERIFY-002 (last)

---

## Parallelizable Tasks

These groups can run simultaneously:

| Group | Tasks |
|-------|-------|
| Foundation | REPO-001, REPO-004, DOC-001 |
| Contracts | SCHEMA-001, SCHEMA-002, SCHEMA-003 |
| Storage backends | STORAGE-002, STORAGE-003 |
| Connectors | PROXY-001, CAPTCHA-001 |
| API endpoints | API-002, API-004 |
| AI sub-tasks | AI-002, AI-003 |
| Front ends | WEB-001, EXT-001, EXE-001 |
| Observability | OBS-001 + OBS-002 (while workers being built) |
| Testing | TEST-001 (while storage being built) |
| Packaging | PKG-001, PKG-002, PKG-003 |

---

## Critical Path

The longest dependency chain that determines minimum project duration:

```
REPO-001 → REPO-002 → ARCH-001 → SCHEMA-001 → STORAGE-001 → API-001 → API-003 → WORKER-001 → WORKER-002 → SELFHOST-001 → PKG-001 → VERIFY-002
```

**12 sequential tasks on critical path.** Delays to any of these delay the whole project.

---

## Risk Hotspots

| Task | Risk | Impact |
|------|------|--------|
| WORKER-002 (Browser worker) | Playwright complexity, flaky browser automation | Blocks hard-target lane and extension |
| EXE-002 (Embedded control plane) | Python bundling with Tauri, cross-platform issues | Blocks desktop app entirely |
| EXT-003 (Native messaging) | Chrome API restrictions, platform-specific registry | Blocks local companion mode |
| MIGRATE-002 (Fetcher abstraction) | Scrapling internal API changes | Blocks clean architecture |
| STORAGE-001 (PostgreSQL) | Schema design errors, migration issues | Blocks all API work |
| CLOUD-001 (Terraform) | Cloud provider API changes, cost management | Blocks cloud deployment |

---

## Milestone Mapping

| Milestone | Tasks Required | Target |
|-----------|---------------|--------|
| **M0 — Foundation** | REPO-*, DOC-001, All SCHEMA-*, ARCH-* | Week 1-2 |
| **M1 — Core Platform** | STORAGE-*, API-*, WORKER-001 | Week 3-5 |
| **M2 — Browser & AI** | WORKER-002, WORKER-003, WORKER-004, AI-*, SESSION-*, PROXY-*, CAPTCHA-* | Week 6-8 |
| **M3 — Web Dashboard** | WEB-*, NORM-* | Week 9-10 |
| **M4 — Desktop App** | EXE-*, MIGRATE-* | Week 11-13 |
| **M5 — Browser Extension** | EXT-*, COMPANION-* | Week 14-15 |
| **M6 — Hardening** | SEC-*, OBS-*, TEST-* | Week 16-17 |
| **M7 — Deployment** | SELFHOST-*, CLOUD-*, PKG-*, VERIFY-* | Week 18-20 |

---

## Task Summary

| Epic | Task Count | Status |
|------|-----------|--------|
| 1. Repository Setup | 4 | NOT_STARTED |
| 2. Documentation | 3 | NOT_STARTED |
| 3. Architecture Scaffolding | 4 | NOT_STARTED |
| 4. Shared Contracts | 3 | NOT_STARTED |
| 5. Backend / Control Plane | 5 | NOT_STARTED |
| 6. Workers / Execution Lanes | 4 | NOT_STARTED |
| 7. Proxy Gateway | 2 | NOT_STARTED |
| 8. CAPTCHA Gateway | 2 | NOT_STARTED |
| 9. Session Service | 2 | NOT_STARTED |
| 10. Storage | 4 | NOT_STARTED |
| 11. AI Layer | 3 | NOT_STARTED |
| 12. Result Normalization | 2 | NOT_STARTED |
| 13. Web Dashboard | 3 | NOT_STARTED |
| 14. Windows EXE | 3 | NOT_STARTED |
| 15. Browser Extension | 3 | NOT_STARTED |
| 16. Local Companion | 2 | NOT_STARTED |
| 17. Self-Hosted Deployment | 2 | NOT_STARTED |
| 18. Cloud Deployment | 2 | NOT_STARTED |
| 19. Testing | 4 | NOT_STARTED |
| 20. Observability | 3 | NOT_STARTED |
| 21. Packaging | 3 | NOT_STARTED |
| 22. Security | 2 | NOT_STARTED |
| 23. Migration / Refactor | 2 | NOT_STARTED |
| 24. Documentation & Verify | 2 | NOT_STARTED |
| **TOTAL** | **69** | |

---

*This document is the execution plan for the project. All tasks must be completed, logged, and verified before the project is considered done.*