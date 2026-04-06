# CLAUDE.md — Project Context for AI Scraping Platform

> **INHERITS FROM:** `~/.claude/CLAUDE.md` (Global Master Directives)
> All global rules (autonomy mode, agent hierarchy, MCP servers, skills library, session memory, auto-update protocol) apply to this project. This file adds **project-specific** context only.

> This file is the authoritative context document for Claude Code sessions working on this project.

## Project Summary

**Name:** AI Scraping Platform
**Live Site:** https://myscraper.netlify.app
**Backend API:** https://scraper-platform-production-17cb.up.railway.app
**Public API:** https://scraper-platform-production-17cb.up.railway.app/v1
**Repo:** https://github.com/fahad-scraper/Scraper-app
**Owner:** Muhammad Usman
**Status:** PRODUCTION — All 10 phases complete, 12 workflows live, 37 E2E tests passing

## Architecture

**Monorepo** with frontend (React/Vite on Netlify), backend (FastAPI on Railway), and scraping engine.

```
/
+-- apps/web/                  # React + Vite SPA (Netlify)
+-- packages/
|   +-- contracts/             # Pydantic v2 schemas (Task, Result, Policy, PublicAPI)
|   +-- core/                  # Engine: router, extractors, crawl_manager, mcp_server
|   +-- connectors/            # HTTP (curl_cffi), browser, proxy, Keepa, Maps
+-- services/control-plane/    # FastAPI backend (Railway)
|   +-- routers/               # 22 routers including public_api.py
|   +-- middleware/             # auth, rate_limit, quota, api_key_auth, idempotency, audit
|   +-- utils/                 # response envelopes, error codes
+-- tests/e2e/                 # 37 Playwright + httpx live E2E tests
+-- infrastructure/            # Docker, Terraform, Helm, Supabase
+-- docs/                      # Specs, QA logs, WORKFLOW_FIX_LOG.xlsx
+-- system/                    # todo.md, execution_trace.md, lessons.md
```

## Deployment

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend (SPA) | Netlify | https://myscraper.netlify.app |
| Backend (API) | Railway | https://scraper-platform-production-17cb.up.railway.app |
| Database | Supabase | PostgreSQL 15 |
| API Proxy | Netlify | `/api/*` -> Railway |

**Environment Variables (Railway):**
- `DATABASE_URL` — Supabase PostgreSQL
- `SECRET_KEY` — JWT signing
- `SERPER_API_KEY` — Web search + Google Maps (Serper Places)
- `KEEPA_API_KEY` — Amazon product data
- `GEMINI_API_KEY` — AI extraction
- `CORS_ORIGINS` — Allowed origins

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async)
- **Frontend:** React 18, TypeScript, Vite, TanStack Query, React Router v6
- **Database:** PostgreSQL 15 (Supabase), SQLite (desktop/dev)
- **HTTP Client:** curl_cffi (TLS/JA3 impersonation), httpx (fallback)
- **Browser:** Camoufox (stealth), Playwright (fallback)
- **AI:** Google Gemini (default), OpenAI (fallback)
- **Testing:** pytest, Playwright, httpx (37 live E2E tests)
- **CI/CD:** GitHub -> Railway (auto-deploy), Netlify (manual trigger)

## 12 Live Workflows (All Verified)

| # | Workflow | Status | Key Feature |
|---|---------|--------|-------------|
| 1 | Quick Scrape | PASS | 4 extraction modes (Everything/Products/Content/Custom), 120+ items from any URL |
| 2 | Web Crawl | PASS | BFS recursive crawling, depth/page limits, status polling |
| 3 | Web Search | PASS | Serper API -> scrape top results, 3+ results with extracted data |
| 4 | Structured Extract | PASS | JSON schema -> 4/4 fields extracted, confidence=1.0 |
| 5 | Amazon/Keepa | PASS | ASIN lookup, product data, price history, 298 API tokens |
| 6 | Google Maps | PASS | Serper Places, 10+ businesses with ratings/addresses |
| 7 | Facebook Groups | DOCUMENTED | Needs self-hosted backend (Chrome/Playwright), UI shows requirements |
| 8 | Templates | PASS | 55 templates, full pipeline: apply -> task -> execute -> 51 items |
| 9 | Results & Export | PASS | Auto-save, CSV/JSON export (real files, not stubs) |
| 10 | Change Detection | PASS | Client-side JSON comparison, price changes, added/removed items |
| 11 | Schedules | PASS | CRUD: create/list/delete with cron expressions |
| 12 | MCP Server | PASS | 5 tools, valid JSON configs, copy buttons |

## Zero Checksum Public API (NEW — April 2026)

External-facing API at `/v1/` with full request tracking, idempotency, and billing reconciliation.

**Authentication:** API keys (`sk_live_xxx`, SHA-256 hashed, shown once at creation)

**Endpoints:**
```
POST /v1/scrape          — Scrape URL (sync or async)          [1-5 credits]
POST /v1/crawl           — Crawl website (async, 202)          [1 credit/page]
POST /v1/search          — Web search + scrape results         [1 credit/result]
POST /v1/extract         — Schema-based extraction             [2 credits]
GET  /v1/jobs/{id}       — Poll async job status               [free]
GET  /v1/jobs/{id}/results — Get paginated results             [free]
POST /v1/webhooks        — Register webhook for notifications  [free]
GET  /v1/usage           — Billing reconciliation by date      [free]
GET  /v1/account         — Plan, quota, API key summary        [free]
```

**Admin (Dashboard):**
```
POST   /api/v1/api-keys       — Create API key (returns full key ONCE)
GET    /api/v1/api-keys       — List keys (prefix only)
DELETE /api/v1/api-keys/{id}  — Revoke key
```

**Zero Checksum Features:**
- Every request gets `req_xxx` tracking ID (`X-Request-ID` header)
- `Idempotency-Key` header prevents double-processing (24h TTL)
- Full audit trail in `request_audit_log` table
- Credit tracking per request, reconcilable via `/v1/usage`
- Standard response envelope: `{request_id, status, data, meta, errors}`
- Webhook delivery logging with retry tracking

**Database Tables (5 new):**
- `api_keys` — Key management with SHA-256 hash storage
- `idempotency_keys` — Request deduplication with 24h TTL
- `request_audit_log` — Full audit trail (method, endpoint, credits, duration, IP)
- `async_jobs` — Long-running job tracking (crawl, async scrape)
- `webhook_delivery_log` — Delivery attempts with status codes

## E2E Test Suite

**File:** `tests/e2e/test_live_e2e.py` (37 tests, 100% pass rate)

**Run:** `run_e2e.bat` or `C:\Python314\python.exe -m pytest tests/e2e/test_live_e2e.py -v`

**Coverage:** All 12 workflows tested against live deployed site with real API credentials.

**Loop mode:** `python tests/e2e/test_live_e2e.py --loop 10 --interval 300`

## Completed Phases

| Phase | Name | Status |
|-------|------|--------|
| 1-2 | Planning & Design | COMPLETE |
| 3 | Architecture Scaffolding | COMPLETE — 26 directories, 7 contracts, 10 protocols |
| 4 | Implementation | COMPLETE — 69 tasks, 525 tests |
| 4+ | Production Readiness | COMPLETE — Redis queue, webhooks, scheduler, UI |
| 5 | QA Testing | COMPLETE — 124 use cases, 706 tests |
| 6 | Stealth Upgrade | COMPLETE — curl_cffi, Camoufox, 14 device profiles |
| 7 | Extraction Overhaul | COMPLETE — 6-tier cascade, PKR + 30 currencies |
| 8 | Operational Upgrades | COMPLETE — Resource blocking, XHR interception, dedup |
| 9 | HYDRA | COMPLETE — Crawl, search, extract, MCP, social extractors |
| 10 | Workflow Fixes + Public API | COMPLETE — 12 workflows verified, Zero Checksum API |

## Key Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | THIS FILE — project context |
| `docs/final_specs.md` | Full platform specification |
| `docs/WORKFLOW_FIX_LOG.xlsx` | Workflow verification log (20/22 PASS) |
| `tests/e2e/test_live_e2e.py` | 37 live E2E tests |
| `run_e2e.bat` | Test runner for Windows |
| `WORKFLOW_FIX_PROMPT.md` | Workflow fix requirements |
| `services/control-plane/routers/public_api.py` | Zero Checksum Public API (9 endpoints) |
| `services/control-plane/middleware/api_key_auth.py` | API key authentication |
| `services/control-plane/middleware/idempotency.py` | Idempotency key management |
| `packages/core/storage/models_public_api.py` | 5 new DB tables for public API |

## Coding Conventions

- Pydantic v2 for all data models
- `async def` for all I/O operations
- Protocol classes for interfaces (not ABC)
- structlog for logging
- No hardcoded secrets — always env vars
- No `print()` — use logging
- Type hints on all function signatures
- Underscores in Python package names (no hyphens)
- Lazy initialization for HTTP clients

## Repository

**Canonical Remote:** `https://github.com/fahad-scraper/Scraper-app`
**Auth:** GitHub PAT from `.env` (`GITHUB_PAT`)
