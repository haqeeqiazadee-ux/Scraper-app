# CLAUDE.md — Project Context for AI Scraping Platform

> **INHERITS FROM:** `~/.claude/CLAUDE.md` (Global Master Directives)

## Project Summary

**Name:** AI Scraping Platform
**Live Site:** https://myscraper.netlify.app
**Backend API:** https://scraper-platform-production-17cb.up.railway.app
**Public API:** https://scraper-platform-production-17cb.up.railway.app/v1
**Repo:** https://github.com/fahad-scraper/Scraper-app
**Owner:** Muhammad Usman
**Status:** PRODUCTION — All phases complete, 56 E2E tests passing, 24 public API endpoints

## Architecture

**Monorepo** — React/Vite frontend (Netlify) + FastAPI backend (Railway) + scraping engine.

```
/
+-- apps/web/                  # React + Vite SPA (Netlify)
+-- packages/
|   +-- contracts/             # Pydantic v2 schemas
|   +-- core/                  # Engine: router, extractors, crawl_manager, mcp_server
|   +-- connectors/            # HTTP (curl_cffi), browser (Playwright), Keepa, Maps
+-- services/control-plane/    # FastAPI backend (Railway)
|   +-- routers/               # 24 routers including smart_scrape.py, public_api.py
|   +-- middleware/             # auth, rate_limit, quota, api_key_auth, idempotency
|   +-- utils/                 # response envelopes, error codes
+-- tests/e2e/                 # 56+ Playwright + httpx live E2E tests
+-- infrastructure/            # Docker, Terraform, Helm
+-- docs/                      # Specs, YOUSELL_API_WORKFLOWS.md, WORKFLOW_FIX_LOG.xlsx
+-- system/                    # todo.md, execution_trace.md, lessons.md
```

## Deployment

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend | Netlify | https://myscraper.netlify.app |
| Backend | Railway | https://scraper-platform-production-17cb.up.railway.app |
| Database | Supabase | PostgreSQL 15 |

**Environment Variables (Railway):** DATABASE_URL, SECRET_KEY, SERPER_API_KEY, KEEPA_API_KEY, GEMINI_API_KEY, CORS_ORIGINS

## Smart Scraper — Core Engine

**One endpoint:** `POST /api/v1/smart-scrape`

Auto-detects and executes the optimal scraping strategy:

```
Input: { target: "URL or search query", intent?, schema?, cookies?, max_pages?, max_depth? }

Step 0: Platform API detection (BEFORE any HTML parsing)
  - amazon.com → Keepa API (ASIN lookup, keyword search, bestsellers)
  - Shopify sites → /products.json API (250 products, ~3s)
  - WooCommerce → /wp-json/wc/store/v1/products API

Step 1: Route via ExecutionRouter
  - Known hard-targets (LinkedIn, etc.) → Browser/HardTarget lane
  - Default → HTTP lane first

Step 2: Execute with auto-escalation
  - HTTP → Browser → HardTarget (based on results + anti-bot detection)
  - JS detection: if bytes_downloaded < 10KB + items ≤ 10 → escalate

Step 3: Extract (3-tier cascade)
  - Tier 1: Shopify/WooCommerce API
  - Tier 2: DOM group detection (price + name + link containers)
  - Tier 3: Deterministic 9-tier cascade + trafilatura + full DOM

Step 4: Filter by intent (products/content/contacts/links/everything)
Step 5: Schema matching (if custom fields requested)
Step 6: Save to database + return results
```

### Platform Routing

| URL Contains | Routes To | Speed |
|---|---|---|
| amazon.com | Keepa API | ~2-5s |
| Shopify (any) | /products.json | ~3s |
| WooCommerce | REST API | ~3s |
| ebay.com | Own scraper (DOM) | ~6s |
| Search query (no URL) | Serper → scrape results | ~4s |
| Everything else | HTTP → Browser escalation | ~5-30s |

## Zero Checksum Public API — 24 Endpoints at `/v1/`

| # | Endpoint | Credits | Description |
|---|----------|---------|-------------|
| 1 | POST /v1/scrape | 1-5 | Scrape URL (sync/async) |
| 2 | POST /v1/crawl | 1/page | Crawl website (async 202) |
| 3 | POST /v1/search | 1/result | Web search via Serper |
| 4 | POST /v1/extract | 2 | Schema-based extraction |
| 5-6 | GET /v1/jobs/{id} | 0 | Poll status + results |
| 7 | POST /v1/webhooks | 0 | Register webhook |
| 8-9 | GET /v1/usage, /v1/account | 0 | Billing + account |
| 10-12 | POST /v1/auth-session, /v1/auth-scrape, GET /v1/auth-sessions | 0-2 | Authenticated scraping |
| 13-15 | POST /v1/amazon/* | 3 | Keepa product/search/deals |
| 16 | POST /v1/maps | 2 | Google Maps businesses |
| 17-18 | POST /v1/facebook/* | 0-5 | Facebook session + scrape |
| 19-20 | GET/POST /v1/templates | 0-2 | List + run templates |
| 21-23 | POST/GET/DELETE /v1/schedules | 0 | Schedule CRUD |
| 24 | GET /v1/presets | 0 | Platform presets |

**Auth:** API keys (`sk_live_xxx`) — `POST /api/v1/api-keys` to create
**Tracking:** Every request gets `req_xxx` ID, idempotency keys, full audit trail

## E2E Test Suite — 56 Tests, 100% Pass

**Files:**
- `tests/e2e/test_all_workflows.py` — 56 tests across 18 categories
- `tests/e2e/test_live_e2e.py` — 37 original workflow tests
- `tests/e2e/test_superdrugs.py` — 12 superdrugs.pk regression tests
- `tests/e2e/test_smart_scraper.py` — 11 smart scraper tests

**Run:** `run_e2e.bat` or `C:\Python314\python.exe -m pytest tests/e2e/test_all_workflows.py -v`

**Coverage:** Smart Scrape, Amazon/Keepa, Shopify, eBay, static sites, Web Search, Schema Extract, Google Maps, Templates, Results/Export, Schedules, Change Detection, MCP Server, Crawl, API Keys, Public API, UI Flow, YOUSELL platform requests

## Frontend — Unified Scraper Page

**One page at `/scraper`** with:
- URL/query input + Scrape button
- Field picker: 22 checkboxes in 5 groups (Product, Condition, Content, Logistics, Contact)
- Advanced Options: cookies, schema, max pages, crawl depth, output format
- Live escalation timeline
- Results: stats grid + data table + Download CSV/JSON
- Auto-saves to Results & Export page

**Other pages:** Amazon (Keepa), Google Maps, Facebook Groups, Templates, Results & Export, Change Detection, Schedules, MCP Server, API Keys

## Database Tables (25 total)

**Core:** tasks, policies, sessions, runs, results, artifacts
**Public API:** api_keys, idempotency_keys, request_audit_log, async_jobs, webhook_delivery_log

## Completed Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1-3 | Planning, Design, Architecture | COMPLETE |
| 4 | Implementation (69 tasks, 525 tests) | COMPLETE |
| 4+ | Production Readiness | COMPLETE |
| 5 | QA Testing (124 use cases, 706 tests) | COMPLETE |
| 6 | Stealth Upgrade (curl_cffi, Camoufox) | COMPLETE |
| 7 | Extraction Overhaul (6-tier cascade) | COMPLETE |
| 8 | Operational Upgrades | COMPLETE |
| 9 | HYDRA (crawl, search, extract, MCP) | COMPLETE |
| 10 | Workflow Fixes + Public API | COMPLETE |
| 11 | Smart Scraper + Universal Extraction | COMPLETE |

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async)
- **Frontend:** React 18, TypeScript, Vite, TanStack Query
- **Database:** PostgreSQL 15 (Supabase), SQLite (dev)
- **HTTP:** curl_cffi (TLS/JA3 impersonation), httpx (fallback)
- **Browser:** Playwright + Chromium (installed on Railway)
- **AI:** Google Gemini, OpenAI (fallback)
- **APIs:** Keepa (Amazon), Serper (search + Google Maps)
- **Testing:** pytest, Playwright, httpx (56 live E2E tests)

## Key Files

| File | Purpose |
|------|---------|
| `services/control-plane/routers/smart_scrape.py` | Smart Scraper engine (auto-scaling) |
| `services/control-plane/routers/public_api.py` | Zero Checksum API (24 endpoints) |
| `services/control-plane/routers/execution.py` | Lane execution + escalation |
| `apps/web/src/pages/ScraperPage.tsx` | Unified scraper UI |
| `tests/e2e/test_all_workflows.py` | 56 E2E tests |
| `docs/YOUSELL_API_WORKFLOWS.md` | 27 scrape request examples |
| `packages/core/crawl_manager.py` | BFS recursive crawler |
| `packages/core/router.py` | Execution lane router |

## Coding Conventions

- Pydantic v2 for all data models
- `async def` for all I/O operations
- Protocol classes for interfaces (not ABC)
- structlog for logging
- No hardcoded secrets — always env vars
- Type hints on all function signatures
- Lazy imports to avoid circular dependencies

## Repository

**Canonical Remote:** `https://github.com/fahad-scraper/Scraper-app`
