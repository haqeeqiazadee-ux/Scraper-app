# TASK: Full-Stack SaaS Productionization & UI Development

## 1. OBJECTIVE & EXECUTIVE FLOW
You are tasked with transforming this Python-based scraping pipeline into a production-grade SaaS application. You must execute this transition in three strict phases: **Phase 1 (Critical Backend Fixes)**, **Phase 2 (MVP UI Development)**, and **Phase 3 (Scaling & DevOps)**.

Do not proceed to the next phase until the current phase passes all test validations. Use `pytest tests/qa/test_live_qa.py` to verify backend integrity constantly.

---

## 2. PHASE 1: CRITICAL BACKEND & STEALTH INFRASTRUCTURE
*Goal: Ensure the scraping engine is secure and can bypass real-world blocks before connecting a UI.*

### Step 1: Secrets Management (12-Factor App Compliance)
1. **Remove Local State:** Scan the entire repository for `.env` files, `.env.production.example`, or hardcoded API keys.
2. **Environment Injection:** Refactor `packages/core/config.py` (or equivalent configuration files) to use strict environment variable parsing (e.g., via Pydantic `BaseSettings`). If a required variable (like `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`) is missing, the application must crash on startup.
3. **Validation:** Assert that no secrets exist in the git history or source code.

### Step 2: Proxy & Fingerprint Stealth Engine
1. **Dynamic Proxy Routing:** Modify `packages/connectors/hard_target_worker.py` and `services/worker-hard-target/worker.py` to accept dynamic proxy URIs (e.g., BrightData or Oxylabs residential endpoints) loaded from environment variables.
2. **Evasion Fallback:** Implement a retry mechanism in the `ExecutionRouter` and HTTP/Browser workers. If a request receives a `403 Forbidden`, `429 Too Many Requests`, or CAPTCHA challenge, automatically invalidate the current proxy session and re-queue the task with a fresh IP.
3. **Browser Evasion:** For Playwright workers (`worker-browser`), integrate anti-detect configurations (e.g., hiding `webdriver`, randomizing user-agents and screen resolutions) to bypass Datadome/Cloudflare.

---

## 3. PHASE 2: MVP UI DASHBOARD (FRONTEND)
*Goal: Build a user interface on Netlify that connects to the stabilized FastAPI Control Plane.*

### Step 1: Frontend Scaffolding
1. **Initialize App:** In a new directory `apps/frontend`, bootstrap a React or Next.js application.
2. **Configuration:** Set up a `netlify.toml` file to deploy the static assets and proxy `/api/*` requests to the Railway backend (`https://scraper-platform-production-17cb.up.railway.app`).

### Step 2: Core SaaS Views
1. **Authentication:** Implement a basic login/tenant mechanism (can be mock JWT or Supabase Auth) to match the `tenant_id` logic required by the Control Plane.
2. **Dashboard/Job Submission:** Create a UI form that allows a user to input a Target URL, select an extraction mode (e.g., Raw HTML, AI Schema), and submit a POST request to `/api/v1/tasks`.
3. **Results View:** Create a polling mechanism or WebSockets connection to track task status. Once `status == "completed"`, fetch and display the extracted JSON data in a formatted data grid or code block.

---

## 4. PHASE 3: SCALING, DEVOPS & OBSERVABILITY
*Goal: Ensure the platform can handle 10,000+ concurrent scraping jobs without dropping data.*

### Step 1: Infrastructure Isolation & Queuing
1. **Worker Split:** Update `railway.toml` or `docker-compose.yml` to ensure `worker-http` and `worker-browser` run as strictly isolated services. Assign different RAM/CPU allocations (Browser gets high RAM, HTTP gets low RAM).
2. **Redis Persistence:** Configure the Redis connection client to enforce AOF (Append-Only File) persistence parameters to prevent queue loss during restarts.
3. **Supabase Pooling:** Update the `DATABASE_URL` format in the code to strictly expect the Supabase IPv4 Transaction pooler port (6543) rather than the direct database port (5432).

### Step 2: Artifact Storage Migration
1. **S3/R2 Integration:** Update the `ResultRepository` (`packages/core/storage/repositories.py`). Instead of storing large HTML blobs or `extracted_data` arrays directly in PostgreSQL, integrate `boto3`.
2. **Logic:** Upload large payloads to an AWS S3 or Cloudflare R2 bucket. Save only the `s3_object_key` or URL in the Supabase database.

### Step 3: Observability (Sentry)
1. **Sentry SDK:** Install `sentry-sdk`.
2. **Implementation:** Inject Sentry initialization into the FastAPI app lifecycle (`services/control-plane/app.py`) and into the worker process entrypoints. Ensure unhandled exceptions and AI schema validation failures trigger alerts.

### Step 4: CI/CD Pipeline
1. **GitHub Actions:** Create `.github/workflows/deploy.yml`.
2. **Pipeline Steps:**
   - On push to `main`, spin up a Python container.
   - Run `pip install -r requirements-dev.txt`.
   - Run security checks: `pip-audit` and `bandit -r packages services`.
   - Run `pytest tests/qa/test_live_qa.py`.
   - On success, trigger the Railway deployment webhook.

---

## 5. CONSTRAINTS & OUTPUTS
- **Verification:** After every major step, run the `pytest` suite. Do not proceed to the next step if tests fail.
- **Code Purity:** Ensure all new code adheres to `flake8` and `black` formatting.
- **Reporting:** Keep a rolling log of your actions. When complete, provide a summary of the deployed architecture.
