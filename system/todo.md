# TODO — Current Actionable Queue

## Completed
- [x] **PHASE-0:** Repository and memory initialization
- [x] **PHASE-1:** Create docs/final_specs.md (1233 lines, all 24 sections)
- [x] **PHASE-2:** Create docs/tasks_breakdown.md (69 tasks across 24 epics)
- [x] **CLAUDE.md:** Created project context file
- [x] **REPO-001:** Initialize monorepo folder structure (26 directories)
- [x] **REPO-004:** Create .gitignore and .env.example
- [x] **REPO-002:** Configure Python monorepo tooling
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
- [x] **API-001:** Wire task CRUD to database (9 API tests)
- [x] **API-002:** Wire policy CRUD to database (5 API tests)
- [x] **AI-001:** AI provider abstraction — deterministic + Gemini + chain (14 tests)
- [x] **WORKER-001:** HTTP lane worker — fetch → extract → confidence → result (5 tests)

## Test Status: 150 passed, 0 failed (4.34s)

## Pending (Next Up)
- [ ] WORKER-002: Browser lane worker
- [ ] WORKER-003: AI normalization worker
- [ ] WORKER-004: Lane escalation logic
- [ ] API-003: Execution router integration
- [ ] API-004: Auth + tenant middleware (JWT)
- [ ] API-005: Result and export endpoints
- [ ] NORM-001: Schema mapping / normalizer
- [ ] SESSION-001: Session manager
- [ ] OBS-001: Structured logging

## Pending (Later Phases)
- [ ] PROXY-001, PROXY-002: Proxy gateway
- [ ] CAPTCHA-001, CAPTCHA-002: CAPTCHA gateway
- [ ] AI-002, AI-003: AI classifier + prompts
- [ ] MIGRATE-001, MIGRATE-002: Migration/refactor
- [ ] WEB-001 through WEB-003: Web dashboard
- [ ] EXE-001 through EXE-003: Windows EXE
- [ ] EXT-001 through EXT-003: Browser extension
- [ ] COMPANION-001, COMPANION-002: Local companion
- [ ] SELFHOST-001, SELFHOST-002: Self-hosted deployment
- [ ] CLOUD-001, CLOUD-002: Cloud deployment
- [ ] TEST-002 through TEST-004: Additional test suites
- [ ] OBS-002, OBS-003: Metrics + tracing
- [ ] PKG-001 through PKG-003: Packaging
- [ ] SEC-001, SEC-002: Security
- [ ] VERIFY-001, VERIFY-002: Final verification

## Blocked
(none)
