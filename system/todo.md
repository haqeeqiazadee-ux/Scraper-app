# TODO — Current Actionable Queue

## Completed — Original 69 Tasks (All Done)
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
- [x] **STORAGE-001:** SQLAlchemy metadata store (14 tests)
- [x] **STORAGE-002:** Filesystem object storage adapter (10 tests)
- [x] **STORAGE-003:** In-memory queue + cache backends (18 tests)
- [x] **STORAGE-004:** SQLite desktop adapter
- [x] **API-001:** Wire task CRUD to database (9 tests)
- [x] **API-002:** Wire policy CRUD to database (5 tests)
- [x] **API-003:** Execution router integration (6 tests)
- [x] **API-004:** Auth + tenant middleware
- [x] **API-005:** Result and export endpoints
- [x] **AI-001:** AI provider abstraction (14 tests)
- [x] **AI-002:** URL classifier (12 tests)
- [x] **AI-003:** Extraction prompt templates
- [x] **WORKER-001:** HTTP lane worker (5 tests)
- [x] **WORKER-002:** Browser lane worker (12 tests)
- [x] **WORKER-003:** AI normalization worker (20 tests)
- [x] **WORKER-004:** Lane escalation manager (11 tests)
- [x] **PROXY-001:** Enhanced proxy adapter (15 tests)
- [x] **PROXY-002:** Proxy provider integrations (56 tests)
- [x] **CAPTCHA-001:** Enhanced CAPTCHA adapter (15 tests)
- [x] **CAPTCHA-002:** CAPTCHA escalation strategy
- [x] **NORM-001:** Schema mapping / normalizer (25 tests)
- [x] **NORM-002:** Deduplication engine (12 tests)
- [x] **SESSION-001:** Session manager (14 tests)
- [x] **SESSION-002:** Cookie/browser profile persistence
- [x] **OBS-001:** Structured logging
- [x] **OBS-002:** Prometheus metrics
- [x] **OBS-003:** OpenTelemetry tracing
- [x] **SEC-001:** Secrets management (10 tests)
- [x] **SEC-002:** Security audit checklist
- [x] **WEB-001:** React web dashboard scaffold
- [x] **WEB-002:** Task management UI interactivity
- [x] **WEB-003:** Results and export UI
- [x] **EXT-001:** Chrome Manifest V3 extension scaffold
- [x] **EXT-002:** Cloud-connected extraction
- [x] **EXT-003:** Native messaging for local companion
- [x] **EXE-001:** Tauri v2 desktop project scaffold
- [x] **EXE-002:** Embed local control plane in desktop app
- [x] **EXE-003:** Build Windows installer
- [x] **COMPANION-001:** Native messaging host
- [x] **COMPANION-002:** Companion installer
- [x] **SELFHOST-001:** Docker Compose stack
- [x] **SELFHOST-002:** Kubernetes Helm chart
- [x] **CLOUD-001:** AWS Terraform modules
- [x] **CLOUD-002:** CI/CD deployment pipeline
- [x] **PKG-001:** Docker images for all services
- [x] **PKG-002:** Windows EXE packaging
- [x] **PKG-003:** Chrome extension packaging
- [x] **VERIFY-001:** Final documentation review
- [x] **VERIFY-002:** System audit
- [x] **TEST-002/003/004:** Integration + E2E test suites

## Completed — Phase 4+ Production Readiness Gap Closure
- [x] **GAP-001:** Redis distributed queue consumer + worker consumption loops
- [x] **GAP-002:** Hard-target execution lane (stealth browser + fingerprint randomization)
- [x] **GAP-003:** Rate limit enforcement + quota management (token bucket + tenant quotas)
- [x] **GAP-004:** Callback webhook executor (HMAC-SHA256) + task scheduler (cron/interval)
- [x] **GAP-005:** Web UI real API integration (full client, hooks, auth context, login)
- [x] **GAP-006:** System tracking files updated
- [x] **GAP-007:** Full test suite — 648 passed, 6 skipped, 0 failed
- [x] **GAP-008:** Final commit and push

## Completed — Production Readiness Improvements
- [x] **PROD-001:** Alembic migrations setup — async env.py, initial migration for all 6 tables

## Completed — QA Phase (Use-Case-Based Testing)

### Session 1 — Infrastructure through HTTP Lane (Phases 1-6, 11-12, 15-16)
- [x] **QA-001:** Phase 1 — Infrastructure Health (9 pass, 4 skip, 1 fix: /ready endpoint)
- [x] **QA-002:** Phase 2 — Authentication & Authorization (6 pass, 3 skip, 1 fix: auth validation)
- [x] **QA-003:** Phase 3 — Task CRUD (10 pass, 4 skip)
- [x] **QA-004:** Phase 4 — Policy CRUD (6 pass, 2 skip)
- [x] **QA-005:** Phase 5 — Execution Router (4 pass, 1 skip)
- [x] **QA-006:** Phase 6 — HTTP Lane Scraping (14 pass, 3 skip, 3 fix: CSS extraction, brotli, escalation)
- [x] **QA-007:** Phase 11 — Results & Export (7 pass, 4 skip, new: 3 export endpoints)
- [x] **QA-008:** Phase 12 — Scheduling (3 pass, 1 skip)
- [x] **QA-009:** Phase 15 — Rate Limiting (1 pass, 2 skip)
- [x] **QA-010:** Phase 16 — Observability/Metrics (3 pass)

### Session 2 — Extended Coverage (Phases 9-10, 13-15, 18)
- [x] **QA-011:** Phase 9 — API/Feed Lane — Shopify detection verified via router
- [x] **QA-012:** Phase 10 — AI Normalization (7 pass, 5 skip: Gemini 403)
- [x] **QA-013:** Phase 13 — Proxy rotation + geo-targeting (3 pass, 2 skip)
- [x] **QA-014:** Phase 14 — Session lifecycle + health scoring (3 pass, 1 skip)
- [x] **QA-015:** Phase 18 — Fallback chain routing verified (2 pass, 1 skip)

### Session 3 — Chunked Deep Testing (Phases 9, 12, 13, 14, 15, 16, 17, 18)
- [x] **QA-016:** Phase 18.1 — Extraction fallback chain (4 pass: JSON-LD → CSS → regex → AI)
- [x] **QA-017:** Phase 12.3 — Webhook callbacks (4 pass: delivery, HMAC, payload, retry)
- [x] **QA-018:** Phase 13.2-13.3 — Proxy health scoring + fallback (4 pass)
- [x] **QA-019:** Phase 14.2-14.3 — Session reuse + health formula (5 pass)
- [x] **QA-020:** Phase 15.2-15.3 — Quota management + billing plans (6 pass)
- [x] **QA-021:** Phase 16.1 — Structured JSON logging (3 pass)
- [x] **QA-022:** Phase 17.6 — Static catalog e-commerce (2 pass)
- [x] **QA-023:** Phase 9.2-9.3 — JSON endpoint + 429 handling (2 pass)

### Session 4 — Chromium Browser Testing (Phases 7, 8, 17)
- [x] **QA-024:** Phase 7 — Browser Lane (7 pass, 5 skip: SPA, Load More, lazy images, screenshots, timeout)
- [x] **QA-025:** Phase 8 — Hard-Target Lane (8 pass, 5 skip: stealth, fingerprint, CAPTCHA detect, escalation)
- [x] **QA-026:** Phase 17 — E-commerce scenarios (6 pass, 9 skip: PLP 25 items, PDP JSON-LD, Shopify)

### Session 5 — Skip Resolution (Group A: tests, Group B: features)
- [x] **QA-027:** Group A — Infinite scroll, multi-Load More, AJAX pagination, proxy sticky/random, session TTL, token bucket refill, per-domain limits, escalation logging, scheduler fires (11 pass)
- [x] **QA-028:** Group B — Policy lane override, custom CSS selectors, HTTP pagination, Retry-After, WooCommerce/RSS detection, artifact storage, variant+stock extraction (14 pass, 6 features implemented)

## Test Status: 936 passed, 0 failed

## Completed — QA Gap Closure (Session 6 — Playwright E2E + Backend)
- [x] **QA-029:** Playwright E2E infrastructure (conftest, test servers, Chromium)
- [x] **QA-030:** Frontend auth flow — 10 tests (UC-1.3.1-4, UC-2.1.3-4, UC-2.2.1)
- [x] **QA-031:** Task CRUD UI — 9 tests (UC-3.1.1, UC-3.2.1, UC-3.2.3, UC-3.4.2)
- [x] **QA-032:** Policy UI — 6 tests (UC-4.1.1, UC-4.3.2)
- [x] **QA-033:** AI normalization — 46 tests (UC-10.1.3, UC-10.2.1-3, UC-10.4.3, UC-10.5.3)
- [x] **QA-034:** Proxy/CAPTCHA integration — 17 tests (UC-8.2.1-2, UC-8.3.2, UC-8.3.4)
- [x] **QA-035:** Browser lane — 6 tests (UC-7.4.2, UC-7.7.2)
- [x] **QA-036:** API pagination — 19 tests (UC-9.2.2)
- [x] **QA-037:** E-commerce scenarios — 11 tests (UC-17.3.1/3, UC-17.4.2, UC-17.5.3)

## Completed — Production Gaps (Partial)
- [x] **PROD-004a:** Fix latency tracking TODO in HttpCollector (avg_latency_ms now calculated)
- [x] **PROD-004b:** Fix Square webhook signature verification TODO (HMAC-SHA256 wired in)
- [x] **QA-UC-6.3.1:** Custom CSS selectors from policy wired through to extraction pipeline
- [x] **QA-UC-6.4.1-2:** Multi-page pagination auto-detection in HTTP worker
- [x] **QA-UC-11.5.1-4:** Artifact storage/download API (full CRUD + file upload/download)

## Completed — Production Gaps (Remaining)
- [x] **PROD-003:** Load testing — Locust script with 2 user profiles, 15+ endpoints
- [x] **PROD-004c:** Health check DB probe — verified already implemented (SELECT 1 + table introspection)
- [x] **PROD-005:** Grafana dashboards — 10-panel overview + Prometheus + auto-provisioning

## Completed — Production Gaps (Final)
- [x] **PROD-002:** Live AI provider integration — OpenAI verified live (classify, extract, normalize), OpenAI provider created, fallback chain tested, Gemini network-blocked in sandbox but code verified correct

## Remaining — QA Gaps (0 blocking items)
All 31 previously-skipped QA items have been resolved:
- 13 frontend UI items → Playwright E2E tests (25 tests)
- 6 AI items → deterministic + OpenAI normalization with currency, title repair, HTML cleanup (46 tests)
- 4 proxy/CAPTCHA items → integration tests with mock solvers (17 tests)
- 4 e-commerce items → wholesale, Shopify fallback, reviews extraction (11 tests)
- 4 misc items → browser tab switching, crash recovery, API pagination (25 tests)

## In Progress — Phase 6: Stealth Upgrade (Anti-Bot Evasion Overhaul)

Research-driven upgrade based on analysis of top-tier scrapers (Crawlee, Camoufox, Bright Data, ScrapFly, ZenRows, curl_cffi) and modern anti-bot systems (AWS WAF, Cloudflare, DataDome, PerimeterX).

### P0 — Critical (fixes 3+ detection layers each)
- [x] **STEALTH-001:** Replace httpx with curl_cffi for TLS/JA3/HTTP2 browser impersonation in HTTP lane
- [x] **STEALTH-002:** Build coherent device profiles (UA + locale + timezone + screen + proxy geo — all must tell a consistent story)

### P1 — High Impact
- [x] **STEALTH-003:** Integrate Camoufox as hard-target browser engine (C++-level stealth, 0% detection on CreepJS)
- [x] **STEALTH-004:** Add warm-up navigation + referrer chains (visit homepage before deep pages)
- [x] **STEALTH-005:** Human-like behavioral simulation (Bezier mouse curves, scroll velocity, idle jitter, log-normal delays)

### P2 — Nice to Have (deferred)
- [ ] **STEALTH-006:** AWS WAF token lifecycle management (Amazon-specific)
- [ ] **STEALTH-007:** Auto-updating UA string database
- [ ] **STEALTH-008:** Mobile proxy tier support

## Blocked
(none)

## Summary
- **Total original tasks:** 69/69 complete
- **Gap closure tasks:** 8/8 complete
- **Production readiness tasks:** 5/5 complete
- **QA sessions completed:** 6
- **QA use cases:** 193 pass, 0 skip, 5 fixed
- **Total unit/integration/E2E tests:** 936 passed, 0 failed
- **Lessons learned:** 67
- **Stealth upgrade tasks:** 5/5 complete (76 tests passing)
- **Platform completeness:** Production-ready, undergoing stealth hardening
