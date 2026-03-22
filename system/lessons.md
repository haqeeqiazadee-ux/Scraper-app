# Lessons Learned

## Phase 0 Observations

1. **Existing code is monolithic** — The scraper_pro/ codebase is a single-app scraper with no platform architecture. Refactoring into shared core + multiple runtime shells will require significant restructuring.

2. **Reusable components identified** — proxy_manager.py, AI extraction logic, smart_exporter.py, verticals/templates system, and core/fallback_chain.py contain valuable logic that should be preserved and refactored into shared packages.

3. **API key embedded in code** — README mentions Gemini API key is "embedded in code" — this is a security issue that must be fixed early (move to environment variables / secrets management).

4. **No test infrastructure** — Tests exist but are ad-hoc scripts, not structured test suites. Need proper pytest setup with fixtures and CI integration.

## Phase 1 Observations

5. **Spec writing clarifies architecture** — Writing detailed specs for all 24 sections exposed several implicit decisions that needed to be made explicit (e.g., SQLite for desktop, in-memory queue for desktop mode, native messaging for extension-companion).

6. **AI must be optional** — Deterministic extraction (CSS, JSON-LD, regex) should be the default. AI is expensive and slow — use only for repair, normalization, and routing. This is a key principle.

7. **Storage abstraction is critical** — The platform must work with PostgreSQL+S3+Redis in cloud AND SQLite+filesystem+in-memory on desktop. Design the interfaces first, implementations second.

## Phase 2 Observations

8. **69 tasks is manageable** — Breaking the project into 69 granular tasks across 24 epics gives clear visibility. The critical path has 12 sequential tasks.

9. **Front ends can parallelize** — Web dashboard, Windows EXE, and browser extension development can happen in parallel once the API is working. This is important for timeline optimization.

10. **Migration should happen early** — Extracting reusable code from scraper_pro/ into new packages should happen alongside architecture scaffolding, not after. This prevents duplicate work.
