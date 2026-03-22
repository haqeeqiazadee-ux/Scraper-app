# TODO — Current Actionable Queue

## Completed (59/69 tasks)
- [x] **PHASE-0:** Repository and memory initialization
- [x] **PHASE-1:** Create docs/final_specs.md (1233 lines, all 24 sections)
- [x] **PHASE-2:** Create docs/tasks_breakdown.md (69 tasks across 24 epics)
- [x] **CLAUDE.md:** Created project context file
- [x] **REPO-001:** Initialize monorepo folder structure (26 directories)
- [x] **REPO-002:** Configure Python monorepo tooling
- [x] **REPO-003:** GitHub Actions CI pipeline (lint + test + typecheck)
- [x] **REPO-004:** Create .gitignore and .env.example
- [x] **DOC-001:** Finalize docs/final_specs.md
- [x] **DOC-002:** API reference skeleton
- [x] **DOC-003:** Developer setup guide
- [x] **ARCH-001:** Create packages/contracts module (7 Pydantic v2 schemas)
- [x] **ARCH-002:** Create packages/core engine skeleton (interfaces, router)
- [x] **ARCH-003:** Create packages/connectors skeleton (5 adapters)
- [x] **ARCH-004:** Create services/control-plane skeleton (FastAPI)
- [x] **TEST-001:** Set up test infrastructure (conftest, fixtures)
- [x] **SCHEMA-001:** Task schema validation tests (13 tests)
- [x] **SCHEMA-002:** Policy schema validation tests (19 tests)
- [x] **SCHEMA-003:** Remaining schema tests (32 tests)
- [x] **STORAGE-001:** SQLAlchemy metadata store — models, database, repositories (14 tests)
- [x] **STORAGE-002:** Filesystem object storage adapter (10 tests)
- [x] **STORAGE-003:** In-memory queue + cache backends (18 tests)
- [x] **STORAGE-004:** SQLite desktop adapter
- [x] **API-001:** Wire task CRUD to database (9 API tests)
- [x] **API-002:** Wire policy CRUD to database (5 API tests)
- [x] **API-003:** Execution router integration — /execute + /route endpoints (6 tests)
- [x] **API-004:** Auth + tenant middleware — JWT creation/verification, role-based access
- [x] **API-005:** Result and export endpoints
- [x] **AI-001:** AI provider abstraction — deterministic + Gemini + chain (14 tests)
- [x] **AI-002:** URL classifier — pattern-based lane prediction (12 tests)
- [x] **AI-003:** Extraction prompt templates (5 templates + builders)
- [x] **WORKER-001:** HTTP lane worker — fetch → extract → confidence → result (5 tests)
- [x] **WORKER-002:** Browser lane worker — Playwright-based extraction (12 tests)
- [x] **WORKER-003:** AI normalization worker — normalize + dedup pipeline (20 tests)
- [x] **WORKER-004:** Lane escalation manager (11 tests)
- [x] **PROXY-001:** Enhanced proxy adapter — file/list/rotating providers, sticky sessions, geo-targeting (15 tests)
- [x] **CAPTCHA-001:** Enhanced CAPTCHA adapter — 2Captcha, Anti-Captcha, CapMonster solvers (15 tests)
- [x] **CAPTCHA-002:** CAPTCHA escalation strategy — budget tracking, retry-before-solve
- [x] **NORM-001:** Schema mapping / normalizer (25 tests)
- [x] **NORM-002:** Deduplication engine — SKU/URL/fuzzy match + merge (12 tests)
- [x] **SESSION-001:** Session manager — lifecycle, health scoring, auto-invalidation (14 tests)
- [x] **SESSION-002:** Cookie and browser profile persistence — SessionPersistence + PersistentSessionManager
- [x] **OBS-001:** Structured logging — JSON formatter, configure_logging()
- [x] **OBS-002:** Prometheus metrics — MetricsCollector, middleware, /metrics endpoint
- [x] **OBS-003:** OpenTelemetry tracing — Tracer, SpanRecorder, configure_tracing()
- [x] **SEC-001:** Secrets management — SecretsManager with provider chain (10 tests)
- [x] **SEC-002:** Security audit checklist
- [x] **WEB-001:** React web dashboard scaffold (17 files)
- [x] **EXT-001:** Chrome Manifest V3 extension scaffold (11 files + icons)
- [x] **EXE-001:** Tauri v2 desktop project scaffold (12 files)
- [x] **COMPANION-001:** Native messaging host
- [x] **COMPANION-002:** Companion installer (Chrome/Chromium/Edge)
- [x] **SELFHOST-001:** Docker Compose stack (control-plane + PostgreSQL + Redis)
- [x] **SELFHOST-002:** Kubernetes Helm chart (13 templates)
- [x] **CLOUD-001:** AWS Terraform modules (VPC, ECS, RDS, Redis, S3, ECR)
- [x] **CLOUD-002:** CI/CD deployment pipeline — GitHub Actions (staging + production)
- [x] **PKG-001:** Docker images for all services (4 Dockerfiles)

## Test Status: 422 passed, 0 failed, 1 skipped (14.5s)

## Pending (10 remaining)
- [ ] **PROXY-002:** Proxy provider integrations (live API integration)
- [ ] **WEB-002:** Task management UI interactivity
- [ ] **WEB-003:** Results and export UI
- [ ] **EXE-002:** Embed local control plane in desktop app
- [ ] **EXE-003:** Build Windows installer
- [ ] **EXT-002:** Cloud-connected extraction
- [ ] **EXT-003:** Native messaging for local companion
- [ ] **TEST-002/003/004:** Integration + E2E test suites
- [ ] **PKG-002/003:** Windows EXE + extension packaging
- [ ] **VERIFY-001/002:** Final documentation review + system audit

## Blocked
(none)
