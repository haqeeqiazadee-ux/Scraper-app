# CLAUDE.md — Project Context for AI Scraping Platform

> This file is the authoritative context document for Claude Code sessions working on this project.

## Project Overview

**Name:** AI Scraping Platform (formerly Scrapling Pro v3.0)
**Type:** Production-grade, cloud-agnostic AI-powered web scraping platform
**Repo:** haqeeqiazadee-ux/Scraper-app

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
- **Browser Automation:** Playwright
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

**All Phases COMPLETE — Platform Production-Ready**

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
| `system/lessons.md` | What we've learned (63 lessons) |
| `system/final_step_logs.md` | Per-task execution evidence |

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
