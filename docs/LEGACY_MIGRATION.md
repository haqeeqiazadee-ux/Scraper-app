# Legacy Code Migration Guide

## Overview

The `scraper_pro/` directory contains the original Scrapling Pro v3.0 codebase. It is **reference-only** and should not be imported in production code. All reusable components have been ported to the new architecture.

## Migration Map

| Legacy File | New Location | Status |
|---|---|---|
| `scraper_pro/ai_scraper_v3.py` | `packages/core/ai_providers/gemini.py` | Ported |
| `scraper_pro/engine_v2.py` (CaptchaSolver) | `packages/connectors/captcha_adapter.py` | Ported |
| `scraper_pro/proxy_manager.py` | `packages/connectors/proxy_adapter.py` | Ported |
| `scraper_pro/smart_exporter.py` | `packages/core/normalizer.py` | Ported |
| `scraper_pro/core/fallback_chain.py` | `packages/core/escalation.py` | Ported |
| `scraper_pro/core/smart_extractors.py` | `packages/contracts/` + `packages/core/normalizer.py` | Ported |
| `scraper_pro/web_dashboard.py` | `apps/web/` (React rewrite) | Replaced |
| `scraper_pro/verticals/` | `packages/core/ai_providers/deterministic.py` | Consolidated |

## What Changed

1. **Monolithic to modular** — Single-file scraper split into packages/contracts, packages/core, packages/connectors
2. **Flask to FastAPI** — Web dashboard replaced with React + FastAPI control plane
3. **Sync to async** — All I/O operations now use async/await
4. **No hardcoded keys** — API keys moved to environment variables and secrets manager
5. **Multi-tenant** — All operations scoped by tenant_id
6. **Protocol-based** — Interfaces use `typing.Protocol` instead of ABC

## Legacy Code Status

The `scraper_pro/` directory can be safely removed or moved to an archive branch. No production code imports from it. The README.md at root has been updated to reflect the new architecture.
