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

## Completed — Phase 6: Stealth Upgrade (Anti-Bot Evasion Overhaul)

Research-driven upgrade based on analysis of top-tier scrapers (Crawlee, Camoufox, Bright Data, ScrapFly, ZenRows, curl_cffi) and modern anti-bot systems (AWS WAF, Cloudflare, DataDome, PerimeterX).

- [x] **STEALTH-001:** Replace httpx with curl_cffi for TLS/JA3/HTTP2 browser impersonation in HTTP lane
- [x] **STEALTH-002:** Build coherent device profiles (UA + locale + timezone + screen + proxy geo — all consistent)
- [x] **STEALTH-003:** Integrate Camoufox as hard-target browser engine (C++-level stealth, 0% CreepJS)
- [x] **STEALTH-004:** Add warm-up navigation + referrer chains (visit homepage before deep pages)
- [x] **STEALTH-005:** Human-like behavioral simulation (Bezier mouse, scroll, idle jitter, log-normal delays)

## Completed — Phase 7: Universal Extraction Overhaul

- [x] **EXTRACT-001:** Fix .pk → PKR currency mapping + domain-priority disambiguation for ambiguous symbols
- [x] **EXTRACT-002:** Add noise filtering — reject nav labels, section headers, items without product signals
- [x] **EXTRACT-003:** Add microdata extraction tier (schema.org Product in HTML attributes)
- [x] **EXTRACT-004:** Add Open Graph extraction tier (og:type=product, og:price:amount)
- [x] **EXTRACT-005:** Expand CSS card selectors from 12 → 50+ (Shopify, WooCommerce, Magento, BigCommerce, etc.)
- [x] **EXTRACT-006:** Fix basic fallback to stop returning garbage — validate product signals before returning
- [x] **EXTRACT-007:** Quality-based confidence scoring (name=0.3, price=0.3, image=0.15, not field coverage)
- [x] **EXTRACT-008:** Lower DOM discovery threshold from 3 → 2 items

## Completed — Phase 8: Pro-Level Operational Upgrades

- [x] **OPS-001:** Resource blocking in browser worker (images/CSS/fonts/ads blocked = 60-80% faster)
- [x] **OPS-002:** API/XHR interception — capture JSON payloads from SPAs for cleaner data
- [x] **OPS-003:** URL-level deduplication — prevent scraping the same URL twice per session
- [x] **OPS-004:** Post-extraction data validation (reject zero prices, placeholder names, fake images)
- [x] **OPS-005:** Device profile integration in browser worker (consistent fingerprint per session)

## Completed — Deferred Items (All Done)

### Stealth
- [x] **STEALTH-006:** AWS WAF token lifecycle management (token storage, expiry, fingerprint consistency)
- [x] **STEALTH-007:** Auto-updating UA string database (version bumper for all 14 profiles)
- [x] **STEALTH-008:** Mobile proxy tier support (proxy_type field + type-based filtering)

### Infrastructure
- [x] **INFRA-001:** Sitemap.xml discovery for URL enumeration
- [x] **INFRA-002:** robots.txt compliance wiring (RobotsChecker with cache)
- [x] **INFRA-003:** Response caching with ETag/Last-Modified headers (memory LRU + disk)
- [x] **INFRA-004:** Circuit breaker for consistently-failing domains
- [x] **INFRA-005:** Load More button clicking in browser worker
- [x] **INFRA-006:** srcset image resolution (extract highest-res from srcset)

## Completed — Keepa API Integration

- [x] **KEEPA-001:** KeepaConnector with full API surface (query, search, deals, best sellers, sellers, categories)
- [x] **KEEPA-002:** Router smart routing — Amazon /dp/ → Keepa API, search/deals → browser
- [x] **KEEPA-003:** Data transformation (Keepa format → platform normalized format)
- [x] **KEEPA-004:** 30 tests (ASIN extraction, domain detection, routing, transformation, protocol)

## Completed — Google Sheets + Google Maps Integration

- [x] **SHEETS-001:** Google Sheets connector (read/write/search/batch/staleness)
- [x] **SHEETS-002:** KeepaSheetCache — check sheet before Keepa, write results back
- [x] **GMAPS-001:** Google Maps connector — 3-tier (Places API → SerpAPI → browser)
- [x] **GMAPS-002:** Business data extraction (name, address, phone, rating, hours, etc.)
- [x] **GMAPS-003:** Sheets integration for Maps results output

## Completed — Frontend Redesign

- [x] **FRONTEND-001:** Login page split layout (gradient branding + form)
- [x] **FRONTEND-002:** Amazon/Keepa page (ASIN search, product cards, domain selector)
- [x] **FRONTEND-003:** Google Maps page (business search, results grid, ratings)
- [x] **FRONTEND-004:** Sidebar nav updated (Amazon + Maps icons/routes)

## Completed — Live API Integration

- [x] **LIVE-001:** Keepa API key configured and verified (300 tokens, real product data)
- [x] **LIVE-002:** Google service account configured (scraper-sheets@yousell-489607)
- [x] **LIVE-003:** Google Sheets + Drive APIs enabled on project
- [x] **LIVE-004:** .env.example + .gitignore updated for all credentials

## Blocked
- **Google Sheets write from sandbox:** `sheets.googleapis.com` blocked by network firewall. Works on Railway/Render/local.

---

## NEW — Competitive Analysis Action Items (April 2026)

Based on comprehensive competitive analysis against 27 industry platforms (see `docs/COMPETITIVE_ANALYSIS.md`).
Superseded by HYDRA Revision Spec (`HYDRA_REVISION_SPEC_PROMPT.md`).

---

## Phase 9 — HYDRA: Universal Scraper Upgrade (7 Sprints)

Full spec: `HYDRA_REVISION_SPEC_PROMPT.md` (751 lines)

### Sprint 1: Foundation (**COMPLETE**)
- [x] **HYDRA-1.1:** Install new dependencies (trafilatura, html2text, rank-bm25, mcp)
- [x] **HYDRA-1.2:** Build `packages/core/markdown_converter.py` (trafilatura + html2text)
- [x] **HYDRA-1.3:** Build `packages/core/content_filter.py` (rank-bm25 integration)
- [x] **HYDRA-1.4:** Add `output_format` parameter to all workers (json/markdown/html/raw)
- [x] **HYDRA-1.5:** Tests for markdown output + BM25 filtering (34 tests)

### Sprint 2: Crawl Manager (**COMPLETE**)
- [x] **HYDRA-2.1:** Build `packages/core/crawl_manager.py` (BFS + queue + dedup + depth)
- [x] **HYDRA-2.2:** Link extraction from HTML (parse `<a href>`, scope filtering)
- [x] **HYDRA-2.3:** Crawl state persistence (in-memory + Redis-backed, resumable by crawl_id)
- [x] **HYDRA-2.4:** Add `/crawl`, `/crawl/{id}`, `/crawl/{id}/results`, `/crawl/{id}/stop` endpoints
- [x] **HYDRA-2.5:** Tests for recursive crawling (16 tests)

### Sprint 3: Adaptive Selectors + Change Detection (**COMPLETE**)
- [x] **HYDRA-3.1:** Upgrade `selector_cache.py` → `adaptive_selectors.py`
- [x] **HYDRA-3.2:** Fuzzy selector matching (SequenceMatcher on tag paths)
- [x] **HYDRA-3.3:** Selector auto-update on successful extraction
- [x] **HYDRA-3.4:** Build `packages/core/change_detector.py` (diff between crawl snapshots)
- [x] **HYDRA-3.5:** Tests for selector adaptation + change detection (25 tests)

### Sprint 4: Extraction Pipeline Upgrade (**COMPLETE**)
- [x] **HYDRA-4.1:** Add trafilatura tier to extraction cascade (tier 7 — article/blog content)
- [x] **HYDRA-4.2:** Add adaptive selector tier to cascade (tier 4)
- [x] **HYDRA-4.3:** Build `packages/core/ai_providers/social/twitter.py` (Twitter/X extractor)
- [x] **HYDRA-4.4:** Build `packages/core/ai_providers/social/linkedin.py` (LinkedIn extractor)
- [x] **HYDRA-4.5:** Upgrade `browser_worker.py` — smart wait, shadow DOM, lazy load trigger

### Sprint 5: Stealth + Router Upgrades (**COMPLETE**)
- [x] **HYDRA-5.1:** Add 10 new device profiles (24 total: Android, iOS, Edge, Brave, Firefox Linux)
- [x] **HYDRA-5.2:** Add canvas/WebGL/audio/battery fingerprint noise injection
- [x] **HYDRA-5.3:** Upgrade `router.py` — response-based reclassification (Cloudflare/DataDome/WAF)
- [x] **HYDRA-5.4:** Add cost-aware routing (`estimated_cost` + `LANE_COSTS` in RouteDecision)

### Sprint 6: MCP Server + Search (**COMPLETE**)
- [x] **HYDRA-6.1:** Build MCP server (5 tools: scrape, crawl, search, extract, route)
- [x] **HYDRA-6.2:** Build `/search` endpoint (Brave Search API → scrape top results)
- [x] **HYDRA-6.3:** Build `/extract` endpoint (structured extraction with JSON schema)
- [x] **HYDRA-6.4:** E2E tests for all new endpoints (101 tests passing)

### Sprint 7: Polish + Documentation (**COMPLETE**)
- [x] **HYDRA-7.1:** Build CLI tool (`scripts/cli.py` with Click — scrape, crawl, search, route)
- [x] **HYDRA-7.2:** UI update — 5 new pages (Crawl, Search, Extract, Changes, MCP), login disabled
- [x] **HYDRA-7.3:** Full E2E test suite — 83 Playwright + 18 API = 101 tests, GitHub Actions CI
- [x] **HYDRA-7.4:** Update `system/todo.md` with Phase 9 completion status
- [x] **HYDRA-7.5:** All commits pushed — HYDRA complete

---

## Summary
- **Total original tasks:** 69/69 complete
- **Gap closure tasks:** 8/8 complete
- **Production readiness tasks:** 5/5 complete
- **QA sessions completed:** 6
- **QA use cases:** 193 pass, 0 skip, 5 fixed
- **Stealth upgrade tasks:** 5/5 complete
- **Extraction overhaul tasks:** 8/8 complete
- **Operational upgrade tasks:** 5/5 complete
- **Infrastructure tasks:** 6/6 complete
- **Deferred stealth tasks:** 3/3 complete
- **Keepa integration tasks:** 4/4 complete
- **Google Sheets integration:** 2/2 complete
- **Google Maps scraper:** 3/3 complete
- **Frontend redesign:** 4/4 complete
- **Live API integration:** 4/4 complete
- **Competitive analysis:** Complete (27 platforms, 55+ features, 12 gaps identified)
- **HYDRA Phase 9 tasks:** 33/33 complete (7 sprints, all done)
- **HYDRA E2E tests:** 101 passing (83 Playwright + 18 API)
- **Facebook Group Extractor:** COMPLETE — 996 posts extracted live via CDP
- **UI pages:** 5 HYDRA pages + Facebook Groups page (24 total routes)
- **Lessons learned:** 117+
- **Unit tests passing:** 706+ (original) + 80 new HYDRA tests
- **Platform status:** ALL PHASES COMPLETE — HYDRA + Facebook Groups shipped
