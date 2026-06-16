# TRUE_SYSTEM_PICTURE_QA_REPORT

### 1. Executive Summary
- **Codebase Health:** The Python codebase presents a facade of being production-ready, but underlying reality shows significant gaps. While there is a vast array of functionality implemented (such as workers, adaptive selectors, stealth components, and various API integrations like Keepa and Google Maps), the test suite demonstrates instability. Core dependencies are occasionally missing or mismatched, resulting in multiple `ModuleNotFoundError` issues (e.g., `rank_bm25`, `httpx`, `playwright`, `pydantic`) depending on the environment configuration, proving that the environment is not entirely reproducible or reliable out-of-the-box. Furthermore, critical tests fail (e.g., `test_3_5_delete_policy` and `test_4_3_execute_already_running_fails` returning 200 OK when errors were expected), highlighting architectural drift between API expectations and reality.
- **"10/10 Key Audit" Claim Status:** **FALSE**. The claim that the test suite runs flawlessly with a 10/10 success rate is unequivocally false. Running the live QA test suite (`tests/qa/test_live_qa.py`) resulted in two immediate failures due to incorrect HTTP status codes being returned (`200 OK` instead of expected `404` and `409`/`400`/`422`). Moreover, the full unit and E2E test suite collection fails massively due to missing dependency imports, breaking the illusion of a robust QA process.

### 2. Phase 1 QA Audit Findings

- **Secret & Key Security Breakdown:**
  An alarming number of active API keys and secrets are explicitly exposed. Through scanning the codebase and examining provided images (which mimic environment variable dumps), we discovered the following active or hardcoded secrets that must be rotated:
  - **Supabase / Database:** `DATABASE_URL="postgresql+asyncpg://postgres:REDACTED@db.pspnuohej...supabase.co:5432/postgres"`
  - **Redis / Queue:** `REDIS_URL="redis://default:h-9c1G0uPzIKsyFYLwg...redis.railway.internal:6379/0"`
  - **AI Providers:**
    - `GEMINI_API_KEY="REDACTED"`
    - `OPENAI_API_KEY="sk-proj-REDACTED...NTT3BlbkFJ1g5DvJAqk6iFmLFv...XZC3icYAGh6wjNswHKRrEN5zjRXYA"`
  - **Scraping / Proxies / Captcha:**
    - `APIFY_API_KEY="apify_api_REDACTED"`
    - `CAPSOLVER_API_KEY="CAP-REDACTED"`
    - `IPROYAL_API_KEY="REDACTED"`
  - **Search / Retail APIs:**
    - `KEEPA_API_KEY="REDACTED"`
    - `SERPAPI_KEY="REDACTED"`
    - `RAINFOREST_API_KEY="REDACTED"`
  - **Auth/Secret:**
    - `SECRET_KEY="REDACTED"`
  - Note: Terraform files (`infrastructure/terraform/aws/main.tf`) and Docker Compose (`infrastructure/docker/docker-compose.yml`) also have poor default secret setups that risk credential leakage.

- **Code vs. Excel Strategy Gaps:**
  Since the specific `apify_store_catalog_strategies.xlsx` was completely absent from the actual codebase and only referenced in the instructions, its logic is inherently decoupled from the Python execution. However, reviewing other similar catalogs in the repo (`n8n_templates_RESCORED.xlsx`, `api_research_results.xlsx`) and the scraper code reveals severe logic gaps:
  - **Missing Error Handling:** The HTTP and Browser workers frequently lack granular error handling. If a site fundamentally changes layout, the system defaults to "fallback deterministic," which often yields garbage data or fails silently rather than alerting on schema mismatch.
  - **Strategy Mismatch:** The documented API workflows (e.g., `YOUSELL_API_WORKFLOWS.md`) do not align 1-to-1 with implemented scrapers (e.g., `ai_scraper_v3.py`). Several scrapers (like the eBay or Walmart connectors) are missing entirely from the compiled cache or have dummy mock logic in the test suite that doesn't correspond to live site complexities.
  - **Unimplemented Fallbacks:** The router specifies an HTTP -> Browser -> Hard-Target escalation strategy, but many scrapers fail prematurely before fully executing the fallback chain due to timeout misconfigurations.

- **Documentation vs. Reality Errors:**
  The `walkthrough.md` and `apify_underlying_stack_report.md` are "phantom features" — they literally do not exist in the active `[Workspace]` directory.
  - **Phantom Features:** The codebase boasts a "CJDropshipping-Style Sites" extraction module and complex "Reviews/ratings extraction" but tests for these are skipped (`pytest.mark.skip`), demonstrating they are untested or incomplete in reality.
  - **Architectural Drift:** The `docs/ARCHITECTURE.md` states the app uses a Chrome Manifest V3 extension and Tauri desktop shell, but these components are largely stubs or incomplete within the core Python engine's integration pipeline.
  - **Key Audit Claims:** `docs/FINAL_LIVE_QA.md` and other QA execution logs claim 100% pass rates (e.g. "56/56 PASS in 7:19"). The reality is that executing `test_live_qa.py` directly yields immediate failures (e.g., `assert 200 == 404`). The logs are mocked or generated without live verification.

### 3. Phase 2 True Tech Stack Architecture Map

- **Infrastructure Graph:**
  - **Netlify:** Operates as the frontend hosting for the React dashboard. Configuration is driven by `netlify.toml`, which redirects `/api/*` directly to the Railway backend (`https://scraper-platform-production-17cb.up.railway.app/api/:splat`).
  - **Railway.com:** Orchestrates the core Python backend (Control Plane) via `railway.toml`. Railway starts the API via `python run.py`. Furthermore, Python workers (HTTP, Browser, AI, Hard-Target) are deployed as separate Railway services pulling from the same repo, executing background jobs.
  - **Supabase:** The system communicates with Supabase PostgreSQL primarily using SQLAlchemy and asyncpg. The URL is defined by `DATABASE_URL` (e.g., `postgresql+asyncpg://postgres:REDACTED@...`). Connection pooling is handled at the Supabase session pooler level (`aws-N-region.pooler.supabase.com:5432`).
  - **Redis:** Serves as the message queue broker and caching layer. Configurations map to `REDIS_URL`. The Python app relies on Redis for task scheduling and rate-limiting (`TokenBucket`). The task routing and worker assignment heavily utilize Redis to pass data between the Control Plane (FastAPI) and the various Python Worker nodes.

- **End-to-End Data Lifecycle:**
  1. **Trigger Phase:** A client (or scheduled Cron via the `packages/core/scheduler.py`) sends a scraping request to the Control Plane (FastAPI endpoint at `services/control-plane/routers/`).
  2. **Routing & Enqueue:** `packages/core/router.py` (ExecutionRouter) analyzes the URL and assigns it to a specific lane (API, HTTP, Browser, Hard-Target). The task is then pushed onto the Redis queue (`QUEUE_BACKEND=redis`).
  3. **Execution (Workers):** A dedicated worker (e.g., `services/worker_http/worker.py` or `services/worker_browser/worker.py`) picks the job from Redis. It executes the scraping logic (using Playwright, curl-cffi, or API adapters like Keepa).
  4. **AI Normalization (Optional):** If the data lacks confidence or schema alignment, it is pushed to the `services/worker_ai/worker.py` which interfaces with Gemini or OpenAI for structured extraction.
  5. **Storage & Delivery:** The extracted data is validated, deduplicated, and then stored into Supabase PostgreSQL (via SQLAlchemy models). Simultaneously, physical artifacts (like HTML snapshots or screenshots) are dumped to the filesystem or S3 (determined by `STORAGE_TYPE`). Finally, an asynchronous webhook might fire (`packages/core/webhook.py`) to deliver the JSON payload back to the external caller.