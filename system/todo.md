# TODO — Current Actionable Queue

## Completed
- [x] **PHASE-0:** Repository and memory initialization
- [x] **PHASE-1:** Create docs/final_specs.md (1233 lines, all 24 sections)
- [x] **PHASE-2:** Create docs/tasks_breakdown.md (69 tasks across 24 epics)
- [x] **CLAUDE.md:** Created project context file
- [x] **REPO-001:** Initialize monorepo folder structure (26 directories)
- [x] **REPO-004:** Create .gitignore and .env.example
- [x] **REPO-002:** Configure Python monorepo tooling (pyproject.toml, ruff, pytest, mypy)
- [x] **ARCH-001:** Create packages/contracts module (7 Pydantic v2 schemas)
- [x] **ARCH-002:** Create packages/core engine skeleton (interfaces, router)
- [x] **ARCH-003:** Create packages/connectors skeleton (HTTP, browser, proxy, CAPTCHA, API)
- [x] **ARCH-004:** Create services/control-plane skeleton (FastAPI app, health, tasks, policies)

## In Progress
- [ ] **PHASE-3 WRAP-UP:** Commit and push all Phase 3 work

## Pending (Next Up — Phase 4: Incremental Implementation)
- [ ] SCHEMA-001: Implement Task schema validation tests
- [ ] SCHEMA-002: Implement Policy schema validation tests
- [ ] SCHEMA-003: Implement remaining schema validation tests
- [ ] STORAGE-001: Implement PostgreSQL metadata store
- [ ] STORAGE-002: Implement object storage adapter
- [ ] STORAGE-003: Implement Redis queue/cache backend
- [ ] STORAGE-004: Implement SQLite adapter for desktop mode
- [ ] API-001: Wire task CRUD to database (replace in-memory store)
- [ ] API-002: Wire policy CRUD to database
- [ ] API-003: Implement execution router integration
- [ ] API-004: Implement authentication and tenant middleware
- [ ] API-005: Implement result and export endpoints

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
- [ ] TEST-001 through TEST-004: Testing infrastructure
- [ ] OBS-001 through OBS-003: Observability
- [ ] PKG-001 through PKG-003: Packaging
- [ ] SEC-001, SEC-002: Security
- [ ] MIGRATE-001, MIGRATE-002: Migration/refactor
- [ ] VERIFY-001, VERIFY-002: Final verification

## Blocked
(none)
