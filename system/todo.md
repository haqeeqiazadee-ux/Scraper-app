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
- [x] **SCHEMA-003:** Remaining schema tests — Session, Run, Result, Artifact, Billing (32 tests)
- [x] **Router tests:** ExecutionRouter lane selection tests (12 tests) + domain suffix fix
- [x] **STORAGE-002:** Filesystem object storage adapter (10 tests)
- [x] **STORAGE-003:** In-memory queue + cache backends (18 tests)
- [x] **STORAGE-001:** SQLAlchemy metadata store — ORM models, database engine, repositories (14 tests)

## Test Status: 117 passed, 0 failed

## Pending (Next Up)
- [ ] STORAGE-001: Implement SQLAlchemy metadata store (PostgreSQL/SQLite)
- [ ] STORAGE-004: SQLite adapter for desktop mode
- [ ] API-001: Wire task CRUD to database (replace in-memory store)
- [ ] API-002: Wire policy CRUD to database
- [ ] API-003: Implement execution router integration
- [ ] API-004: Implement authentication and tenant middleware
- [ ] API-005: Implement result and export endpoints
- [ ] OBS-001: Add structured logging

## Pending (Later Phases)
- [ ] WORKER-001 through WORKER-004: Execution lane workers
- [ ] PROXY-001, PROXY-002: Proxy gateway
- [ ] CAPTCHA-001, CAPTCHA-002: CAPTCHA gateway
- [ ] SESSION-001, SESSION-002: Session service
- [ ] AI-001 through AI-003: AI layer
- [ ] NORM-001, NORM-002: Result normalization
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
- [ ] MIGRATE-001, MIGRATE-002: Migration/refactor
- [ ] VERIFY-001, VERIFY-002: Final verification

## Blocked
(none)

## Test Status
- **Total tests:** 103
- **Passing:** 103
- **Failing:** 0
