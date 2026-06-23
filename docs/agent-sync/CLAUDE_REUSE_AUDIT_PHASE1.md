## Phase 1 Reuse Audit Report

### 1. File Disposition Matrix

| File | In `verified`? | In `fresh`? | Action | Notes |
|------|:-:|:-:|--------|-------|
| `services/control-plane/routers/actors.py` | No | Yes (96 lines) | **REUSE** | 5 FastAPI routes, clean envelope pattern |
| `packages/core/actor_catalog/registry.py` | No | Yes (214 lines) | **REUSE** | Frozen dataclass, singleton, lazy-load |
| `scripts/generate_actor_catalog.py` | No | Yes (348 lines) | **REUSE** | CSV→JSON, hash-based idempotency, 3 outputs |
| `tests/unit/test_actor_catalog.py` | No | Yes (238 lines) | **REUSE** | 20 tests, covers generation/search/secrets |
| `apps/web/src/pages/ActorsPage.tsx` | No | Yes (745 lines) | **REUSE** | Chunk-loaded catalog browser, filters, sort |
| `apps/web/src/pages/ActorDetailPage.tsx` | No | Yes (350 lines) | **REUSE** | Detail view with API+chunk fallback |
| `generated/apify_actor_catalog.json` | No | Yes | **REUSE/REGENERATE** | Codex verified `26,555,488` bytes at `C:\Users\PC\Scraper-app-fresh\packages\core\actor_catalog\generated\apify_actor_catalog.json` |
| `apifyActors.generated.json` | No | Yes | **REUSE/REGENERATE** | Codex verified `19,899,217` bytes at `C:\Users\PC\Scraper-app-fresh\apps\web\src\data\apifyActors.generated.json` |
| `apps/web/public/data/actors/` | No | Yes | **REUSE/REGENERATE** | Codex verified chunk files exist, including `chunk-0.json`, `chunk-1.json`, `chunk-10.json` |
| `docs/agent-sync/*` (verified) | Yes (16 files, 25MB R&D) | — | **EXTEND** | Phase 0 research packet is complete |
| `docs/agent-sync/*` (fresh) | — | Yes (9 handoff docs) | **MERGE selectively** | CLAUDE_STATUS + RELEASE_GATE useful |

**Summary:** All 6 source files in `fresh` are useful prior work and should be reviewed/ported into `verified`. Codex independently verified the generated catalog artifacts and source CSV exist in `fresh`; they are not empty.

### 2. Gaps Before Phase 1 Can Be Committed

| Gap | Severity | Resolution |
|-----|----------|------------|
| **Source CSV missing in verified** (`docs/apify_catalog_implementation_mapping.csv`) | **BLOCKER** | Exists in `fresh` at `6,884,499` bytes; port or regenerate from the R&D matrix before running tests. |
| **Generated JSONs missing in verified** | HIGH | Exists in `fresh`; preferably port source CSV + generator and regenerate in verified, then compare count/hash. |
| **No `__init__.py`** in `packages/core/actor_catalog/` | MEDIUM | Verify fresh has it; if not, create with registry export. |
| **Router not registered** in FastAPI app | MEDIUM | `actors.py` router must be included in `services/control-plane/main.py` (or `app.py`). |
| **Frontend routes not wired** | MEDIUM | `ActorsPage` and `ActorDetailPage` need entries in the React router config. |
| **XLSX store metadata** (optional enrichment) | LOW | Pricing fields default to `unknown` without it. Non-blocking. |
| **IMPLEMENTATION_LEDGER not updated** | LOW | Must record reuse decision per project CLAUDE.md boundary rules. |

### 3. Test Commands for Phase 1 Verification

```bash
# Unit tests (after copying files into verified)
C:\Python314\python.exe -m pytest tests/unit/test_actor_catalog.py -v

# Generator smoke test (after CSV exists)
C:\Python314\python.exe scripts/generate_actor_catalog.py --dry-run

# Backend API smoke (after router wired + server running)
curl http://localhost:8000/api/v1/actors?limit=5
curl http://localhost:8000/api/v1/actors/stats
curl http://localhost:8000/api/v1/actors/categories

# Frontend build check
cd apps/web && npm run build

# Existing E2E regression (must not break)
C:\Python314\python.exe -m pytest tests/e2e/test_all_workflows.py -v
```

### 4. Collision Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **`docs/agent-sync/` overlap** | Both repos have this dir with different files. Verified has 16 R&D files; fresh has 9 handoff docs. | Merge by filename — no naming collisions found. Copy fresh's `CLAUDE_STATUS.md` and `CODEX_RELEASE_GATE.md` into verified. |
| **`CLAUDE.md` divergence** | Verified's CLAUDE.md is modified on current branch. Fresh may have different project metadata. | Keep verified's version; it has the authoritative project context. |
| **`packages/core/` structure** | Fresh adds `actor_catalog/` subpackage. Must not break existing `router.py`, `crawl_manager.py`, `mcp_server.py` imports. | New subpackage is isolated — no shared imports. Safe. |
| **Frontend route conflicts** | New pages add to router. Existing pages (`/scraper`, `/amazon`, etc.) must not shift. | Additive change only — append `/actors` and `/actors/:id` routes. |
| **Python dependency drift** | Fresh may pin different versions. | Compare `requirements.txt` / `pyproject.toml` before merge. Actor code uses only stdlib + pydantic + fastapi (already in verified). |

**Bottom line:** The source files and generated catalog artifacts from `fresh` are the Phase 1 reuse base. Phase 1 should port the generator/source/catalog code, regenerate or verify the 27,753-row outputs in `verified`, wire backend and frontend routes, and run catalog tests/build checks.

## Codex Verification Note

Claude CLI completed the reuse audit but incorrectly reported several generated artifacts as empty. Codex verified the files directly in `C:\Users\PC\Scraper-app-fresh` and corrected the table above before using this report as a phase gate.
