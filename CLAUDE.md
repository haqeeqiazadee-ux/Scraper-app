# CLAUDE.md — Project Context for AI Scraping Platform

> This file is the authoritative context document for Claude Code sessions working on this project.

## Repository

**Canonical Remote:** `https://github.com/fahad-scraper/Scraper-app`
Always use this repo for all git operations (fetch, pull, push). Do not use any other remote.

**Authentication:** If git push fails with auth errors, read the GitHub PAT from `.env` (`GITHUB_PAT`) and set the remote URL:
```
git remote set-url origin https://<TOKEN>@github.com/fahad-scraper/Scraper-app.git
```

## Project Overview

**Name:** AI Scraping Platform (formerly Scrapling Pro v3.0)
**Type:** Production-grade, cloud-agnostic AI-powered web scraping platform
**Repo:** fahad-scraper/Scraper-app

## Architecture

This is a **monorepo** with the following structure:

```
/
├── apps/                    # Runtime shells (front ends)
│   ├── web/                 # React + Vite web dashboard
│   ├── desktop/             # Tauri v2 Windows EXE
│   ├── extension/           # Chrome Manifest V3 extension
│   └── companion/           # Native messaging host
├── packages/                # Shared libraries
│   ├── contracts/           # Pydantic data contracts (Task, Policy, Session, Run, Result, Artifact, Billing)
│   ├── core/                # Core engine (router, session manager, AI provider, storage interfaces)
│   └── connectors/          # Connector adapters (HTTP, browser, proxy, CAPTCHA, API)
├── services/                # Backend services
│   ├── control-plane/       # FastAPI control plane
│   ├── worker-http/         # HTTP lane worker
│   ├── worker-browser/      # Browser lane worker (Playwright)
│   └── worker-ai/           # AI normalization worker
├── infrastructure/          # Deployment
│   ├── docker/              # Dockerfiles + docker-compose
│   ├── terraform/           # Cloud IaC (AWS/GCP/Azure)
│   └── helm/                # Kubernetes Helm chart
├── tests/                   # Test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/                 # Build/deploy/utility scripts
├── docs/                    # Project documentation
│   ├── final_specs.md       # SOURCE OF TRUTH — full platform specification
│   └── tasks_breakdown.md   # 69 tasks across 24 epics
├── system/                  # Project tracking (mandatory, always update)
│   ├── execution_trace.md   # Chronological decision trace
│   ├── development_log.md   # Engineering log
│   ├── todo.md              # Current actionable queue
│   ├── lessons.md           # Persistent learning memory
│   └── final_step_logs.md   # Detailed per-task execution ledger
├── scraper_pro/             # LEGACY — existing v3.0 code (reference only)
└── CLAUDE.md                # THIS FILE
```

## Key Design Principles

1. **One shared platform** — EXE, extension, SaaS, self-hosted share the same core
2. **Cloud-agnostic** — No vendor lock-in; abstractions for storage, queue, secrets
3. **AI as augmentation** — Deterministic parsers first; AI for routing, repair, normalization
4. **Contract-driven** — All components use shared Pydantic schemas
5. **Fallback chains** — Every extraction has primary → secondary → tertiary fallback

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2
- **Database:** PostgreSQL 15+ (cloud/self-hosted), SQLite (desktop)
- **Cache/Queue:** Redis 7+ / Valkey (cloud), in-memory (desktop)
- **Object Storage:** S3-compatible (cloud), filesystem (desktop)
- **Browser Automation:** Camoufox (primary, C++-level stealth), Playwright (fallback)
- **HTTP Client:** curl_cffi (browser TLS/JA3 impersonation), httpx (fallback)
- **Desktop Shell:** Tauri v2 (Rust + WebView)
- **Extension:** Chrome Manifest V3
- **AI Providers:** Google Gemini (default), OpenAI, Anthropic, Ollama (local)
- **Testing:** pytest + pytest-asyncio + testcontainers
- **Linting:** ruff
- **CI/CD:** GitHub Actions

## Mandatory Workflow

Before starting any work:
1. Read `docs/final_specs.md` (source of truth)
2. Read relevant section of `docs/tasks_breakdown.md`
3. Read `system/todo.md` (current queue)
4. Read `system/lessons.md` (avoid past mistakes)
5. Read latest entries in `system/execution_trace.md`

After completing any task:
1. Update `system/todo.md`
2. Update `system/execution_trace.md`
3. Update `system/development_log.md`
4. Update `system/final_step_logs.md`
5. Update `system/lessons.md` if anything was learned
6. Update `CLAUDE.md` if architecture or conventions changed

## Current Phase

**All Phases COMPLETE — Platform Production-Hardened**

**Phase 3 — Architecture Scaffolding (COMPLETE)**
- Monorepo folder structure created (26 directories)
- Python tooling configured (ruff, pytest, mypy, coverage)
- packages/contracts: 7 Pydantic v2 schemas implemented
- packages/core: 10 Protocol interfaces + ExecutionRouter
- packages/connectors: 6 adapter implementations (HTTP, browser, proxy, CAPTCHA, API, hard-target)
- services/control-plane: FastAPI app with task/policy CRUD + health endpoints

**Phase 4 — Incremental Implementation (COMPLETE)**
- All 69 original tasks completed
- 525 tests passing across 22+ test modules

**Phase 4+ — Production Readiness Gap Closure (COMPLETE)**
- Redis distributed queue consumer + worker consumption loops
- Hard-target execution lane (stealth browser + fingerprint randomization)
- Rate limit enforcement + quota management (token bucket + tenant quotas)
- Callback webhook executor (HMAC-SHA256 signed) + task scheduler (cron/interval)
- Web UI wired to real API (full client, hooks, auth context, login page)
- 648 tests passing, 6 skipped, 0 failed

**Phase 5 — Use-Case QA Testing (COMPLETE)**
- 4 QA sessions covering all 18 phases of qa_strategy.md
- 124 use cases passed, 52 skipped (external services), 5 bugs fixed
- Browser lane verified with Chromium v141 (SPA rendering, screenshots, stealth)
- Hard-target lane verified (fingerprint randomization, CAPTCHA detection, escalation chain)
- E-commerce scenarios verified (25-item PLP, PDP JSON-LD, Shopify detection)
- 706 tests passing, 0 failed

**Phase 6 — Stealth Upgrade (COMPLETE)**
- curl_cffi for browser-matching TLS/JA3/HTTP2 (replaces httpx in HTTP lane)
- 14 coherent device profiles across 8 geo regions (all signals consistent)
- Camoufox C++-level stealth for hard-target lane (0% detection on CreepJS)
- Human behavioral simulation: Bezier mouse curves, log-normal delays, idle jitter
- Warm-up navigation + Google referrer chains

**Phase 7 — Universal Extraction Overhaul (COMPLETE)**
- 6-tier extraction cascade: JSON-LD → Microdata → Open Graph → DOM Discovery → CSS (50+ selectors) → Validated Fallback
- Noise filtering rejects nav labels, section headers, items without product signals
- Quality-based confidence scoring (weighted by name/price/image, not field coverage)
- PKR + 30 other currencies with domain-priority disambiguation

**Phase 8 — Pro-Level Operational Upgrades (COMPLETE)**
- Browser resource blocking (images/CSS/fonts/ads) — 60-80% faster page loads
- API/XHR interception — captures JSON payloads from SPAs
- URL-level deduplication — prevents scraping the same URL twice
- Post-extraction data validation — rejects garbage (zero prices, placeholder names, fake images)

## Coding Conventions

- Use Pydantic v2 for all data models
- Use `async def` for all I/O operations
- Use Protocol classes for interfaces (not ABC)
- Use structlog for logging
- Tests go in `tests/` mirroring the source structure
- No hardcoded secrets — always env vars or secrets manager
- No `print()` statements — use logging
- Type hints on all function signatures
- No hyphens in Python package directory names — use underscores or symlinks
- Use lazy initialization for clients (create on first request, not import time)

## Important Files

| File | Purpose |
|------|---------|
| `docs/final_specs.md` | Full platform specification (1233 lines, 24 sections) |
| `docs/tasks_breakdown.md` | 69 tasks across 24 epics with dependency graph |
| `docs/qa_strategy.md` | Use-case-based QA plan (18 phases, 170+ use cases) |
| `docs/qa_execution_log.md` | Chronological record of every QA test run |
| `system/todo.md` | Current task queue |
| `system/execution_trace.md` | Decision audit trail |
| `system/development_log.md` | Engineering log |
| `system/lessons.md` | What we've learned (82 lessons) |
| `system/final_step_logs.md` | Per-task execution evidence |

## Key New Modules (Phase 6-8)

| File | Purpose |
|------|---------|
| `packages/core/device_profiles.py` | 14 coherent browser identity profiles for anti-detection |
| `packages/core/human_behavior.py` | Bezier mouse curves, scroll simulation, idle jitter, warm-up nav |
| `packages/connectors/http_collector.py` | curl_cffi HTTP client with TLS/JA3 browser impersonation |
| `packages/connectors/hard_target_worker.py` | Camoufox stealth browser + Playwright fallback |
| `packages/connectors/browser_worker.py` | Resource blocking, API interception, device profiles, Load More |
| `packages/core/url_discovery.py` | Sitemap.xml parser + robots.txt compliance checker |
| `packages/core/circuit_breaker.py` | Per-domain circuit breaker (CLOSED/OPEN/HALF_OPEN) |
| `packages/core/waf_token_manager.py` | AWS WAF token lifecycle (Amazon cookie management) |
| `packages/core/response_cache.py` | Two-tier HTTP response cache (memory LRU + disk) |

## Legacy Code (scraper_pro/)

The `scraper_pro/` directory contains the original Scrapling Pro v3.0 code. It is **reference only** — do not import from it in new code. Reusable components are being ported to `packages/`.

| Legacy File | Port Destination |
|-------------|-----------------|
| core/fallback_chain.py | packages/core/fallback.py |
| proxy_manager.py | packages/connectors/proxy_adapter.py |
| ai_scraper_v3.py (GeminiAI) | packages/core/ai_providers/gemini.py |
| smart_exporter.py | packages/core/exporter.py |
| engine_v2.py (CaptchaSolver) | packages/connectors/captcha_adapter.py |
| core/smart_extractors.py | packages/contracts/ + packages/core/normalizer.py |
