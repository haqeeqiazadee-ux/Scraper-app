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

9. **Front ends can parallelize** — Web dashboard, Windows EXE, and browser extension development can happen in parallel once the API is working.

10. **Migration should happen early** — Extracting reusable code from scraper_pro/ into new packages should happen alongside architecture scaffolding, not after.

## Phase 3 Observations

11. **Python package naming: no hyphens** — Python cannot import packages with hyphens in directory names (e.g., `services/control-plane`). Resolved with symlink: `services/control_plane` → `services/control-plane`. **Rule:** Always use underscores in Python package directory names, or create symlinks when convention conflicts.

12. **Pydantic v2 model_config replaces Config class** — In Pydantic v2, use `model_config = {"from_attributes": True}` instead of the old `class Config: orm_mode = True`. This is needed for SQLAlchemy ORM integration.

13. **Protocol > ABC for interfaces** — Using `typing.Protocol` with `@runtime_checkable` provides structural subtyping — implementations don't need to explicitly inherit. This is cleaner for a pluggable architecture.

14. **StrEnum for JSON serialization** — Using `StrEnum` instead of plain `Enum` ensures values serialize naturally to/from JSON without needing custom serializers.

15. **In-memory stores for scaffolding** — The control plane uses in-memory dicts for initial scaffolding. This lets us test the API shape before wiring up the database. Replace with real stores in STORAGE tasks.

16. **Lazy initialization pattern** — Both HttpCollector and PlaywrightBrowserWorker use lazy initialization (create client on first request). This avoids startup overhead and import-time side effects.

17. **Fallback chain is reusable everywhere** — The primary → secondary → tertiary pattern from scraper_pro/core/fallback_chain.py applies to: proxies (datacenter → residential → mobile), CAPTCHAs (service A → B → C), AI providers (Gemini → OpenAI → deterministic), execution lanes (HTTP → browser → hard-target). It's a core architectural pattern.

18. **CLAUDE.md is essential** — Having a project context file that documents architecture, conventions, and workflow ensures consistency across coding sessions. Update it after every significant architectural change.

## Phase 4 Observations

19. **Domain matching needs suffix support** — Exact domain matching fails for subdomains (e.g., `mystore.myshopify.com` should match `myshopify.com`). Always implement suffix matching for domain lookups.

20. **Path traversal protection is critical** — Filesystem-based storage must validate that resolved paths stay within the base directory. Use `Path.resolve()` and check prefix. This is a security requirement, not optional.

21. **TTL in cache needs time.time() comparison** — In-memory cache TTL implementation must compare against `time.time()` on every `get()` call, not just during periodic cleanup. Lazy expiry is simpler and more correct.

22. **Queue ack/nack pattern** — Track dequeued messages as "pending" until ack'd. On nack, re-enqueue the message. This matches Redis/RabbitMQ semantics and enables reliable message processing.

23. **Test early, test often** — Writing tests alongside implementation (not after) caught the router domain matching bug immediately. The 103-test suite now validates all contracts, router logic, and storage backends.

24. **SQLite in-memory for fast tests** — Using `sqlite+aiosqlite:///:memory:` gives instant test databases with zero cleanup. Each test gets a fresh database via fixtures. This is much faster than testcontainers for unit tests.

25. **Tenant isolation via repository pattern** — Every repository method takes `tenant_id` as a parameter and includes it in WHERE clauses. This is the single enforcement point for multi-tenant data isolation. Never query without tenant_id.

26. **Symlinks for Python-hyphenated dirs need correct relative paths** — `ln -s control-plane services/control_plane` (relative from parent) not `ln -s services/control-plane services/control_plane` (absolute-ish). Always create symlinks from the parent directory.

27. **AI providers should always have deterministic fallback** — The AIProviderChain always appends DeterministicProvider as the final fallback. This ensures extraction never completely fails — you always get at least JSON-LD/regex results.

28. **Worker should_escalate flag** — HTTP worker sets `should_escalate=True` when extraction fails (HTTP error, empty results). The control plane uses this to automatically route to browser lane. Clean separation of concerns.

29. **Confidence scoring from field fill rate** — Simple but effective: count non-empty fields / total fields across extracted items. This avoids AI-based confidence estimation and works with deterministic extraction too.
