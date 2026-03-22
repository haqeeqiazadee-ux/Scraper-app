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

30. **Comma disambiguation in prices** — "5,000" vs "29,99": use regex `^\d{1,3}(,\d{3})+$` to detect thousands separator. If it matches, remove commas. Otherwise treat comma as decimal. This handles USD, EUR, PKR formats correctly.

31. **Escalation context must be per-task** — Each task gets its own EscalationContext tracking depth and attempts. Don't use global state — concurrent tasks would interfere with each other.

32. **Session health drives automatic status transitions** — Health score thresholds (0.7 degraded, 0.3 invalid) combined with consecutive failure count give reliable session lifecycle management without manual intervention.

33. **Docker health checks are essential** — Use `pg_isready` for PostgreSQL, `redis-cli ping` for Redis, and HTTP health endpoint for the API. Docker Compose `depends_on: condition: service_healthy` ensures proper startup order.

34. **Use PyJWT not python-jose** — PyJWT (`import jwt`) is the actively maintained library. python-jose is unmaintained and has known CVEs. PyJWT's `jwt.encode`/`jwt.decode` API is clean and sufficient for HS256/RS256.

35. **HTTPBearer with auto_error=False** — Setting `auto_error=False` on FastAPI's `HTTPBearer` security scheme lets you return a custom 401 response instead of the generic one. This gives better error messages for missing vs invalid tokens.

36. **Composition over inheritance for enhanced managers** — `PersistentSessionManager` wraps `SessionManager` via composition rather than subclassing. This keeps the in-memory manager unchanged and testable independently, while the persistent layer adds storage concerns. The pattern works well when adding cross-cutting features (persistence, caching, metrics) to existing classes.

37. **run_in_executor for file I/O in async code** — `asyncio.get_running_loop().run_in_executor(None, sync_fn)` is sufficient for filesystem operations without adding aiofiles as a dependency. The default executor (ThreadPoolExecutor) handles concurrent file reads/writes well for moderate workloads.

38. **Lightweight metrics without prometheus_client** — A simple MetricsCollector with dict-based counters/gauges/histograms and Prometheus text export is sufficient for most use cases. Avoids adding prometheus_client as a hard dependency while remaining compatible with standard Prometheus scraping. Thread safety via `threading.Lock` is essential since FastAPI middleware runs across async contexts.

## Final Verification Observations

39. **Documentation-as-code works** — Keeping ARCHITECTURE.md, DEPLOYMENT.md, and CHANGELOG.md in the repo alongside the code ensures they stay in sync. Separate wikis or Confluence pages drift quickly.

40. **__init__.py audits catch import issues early** — One missing __init__.py in proxy_providers/ would have caused import failures at runtime. Automated checks for package completeness should be part of CI.

41. **Minor TODOs are acceptable at milestone** — The 3 TODO comments found (latency tracking, health check DB probe, CORS restriction) are all enhancement-level. Shipping with known minor TODOs documented is better than blocking release.

42. **Test count as project health metric** — Tracking test counts (436 passing) across milestones gives a concrete measure of project health. The ratio of test files (22) to source files (56) indicates areas where additional coverage would be valuable.

43. **System tracking files provide audit trail** — The execution_trace.md, development_log.md, and final_step_logs.md together create a complete audit trail of every decision and implementation. This is invaluable for onboarding new contributors and understanding why things were built the way they are.
