# Claude Continuation Prompt - SaaS Repair Mission

You are Claude, the primary builder for the AI Scraping Platform SaaS repair mission. Continue from the existing `saas-repair` branch and do not restart from scratch.

## Fixed Context

- Workdir: `C:\Users\PC\Scraper-app-fresh`
- Branch: `saas-repair`
- Latest known commit: `5c8cd8e`
- Repo: https://github.com/haqeeqiazadee-ux/Scraper-app
- Canonical project context supplied by user: `C:\Users\PC\Scraper-app-main\AGENTS.md`
- Railway project: https://railway.com/project/c63725e4-4da6-4bf2-9fc4-068578a9bde6?environmentId=ffa7f443-0c4e-4dc8-8217-0b9fefe1a8ae
- Netlify project: https://app.netlify.com/projects/myscraper/overview
- Production frontend: https://myscraper.netlify.app
- Production backend: https://scraper.exsel.ai
- Public API: https://scraper.exsel.ai/v1

## Read First

Read these before touching code:

1. `AGENTS.md`
2. `docs/agent-sync/CLAUDE_STATUS.md`
3. `docs/agent-sync/CURRENT_PHASE.md`
4. `docs/agent-sync/CODEX_RELEASE_GATE.md`
5. `docs/agent-sync/SECRETS_ACCESS.md`
6. `docs/agent-sync/API_KEY_REQUIREMENTS.xlsx` if API/env requirements are needed

## Absolute Secret Rules

The previous run exposed a newly generated test API key in the transcript. That key has been revoked. Do not repeat that mistake.

- Never print raw API keys, tokens, database URLs, cookies, webhook secrets, auth headers, or `.agent-secrets` contents.
- Never put a raw `Authorization: Bearer ...` value in a command string that will be visible in logs.
- If you must create or test an API key, write the full raw response only to an ignored file under `.agent-secrets/`, parse it inside a script, and print only HTTP status, key ID, prefix, masked value, and pass/fail.
- If any secret appears in output, stop immediately, revoke/rotate it if possible, and document only non-secret remediation details.
- Do not screenshot pages that show raw secrets.

## Mission

Convert the current deployed app from a technically reachable scraper into a genuinely usable SaaS product. The design target is an Apify client dashboard style: dense left sidebar, top search/filters, actor/task cards, status chips, run table, detail panels, usage/billing/API surfaces, and polished workflow feedback. Use original branding and implementation; do not copy Apify text or assets.

## Current Proven Facts

- `apps/web` React/Vite now deploys on Netlify production.
- Netlify production routes return 200.
- Netlify `/api/*` proxy reaches `https://scraper.exsel.ai`.
- Smart scrape through Netlify proxy has succeeded and saved results.
- API key revoke path was fixed and deployed to Railway deployment `26cbd7b2-5f60-4381-8c42-429c46217083`.
- Temporary exposed test key ID `9b67ef21-f702-4e92-a38c-24f1693b5553` was revoked.
- UI is still not good enough: it appears closer to a minimal scraper shell than an Apify-style SaaS dashboard.
- Global raw exception leakage remains an open risk.
- Production deploys were direct CLI deploys from this working tree/branch; document provenance honestly.

## Work Phases To Continue

### Phase 2 - Apify-Style SaaS Dashboard

Implement a polished SaaS dashboard in `apps/web` using the existing React/Vite stack and existing patterns.

Required UI elements:

- persistent left sidebar navigation with icons
- compact top bar with search, environment/status indicator, and account/actions
- scraper actor/task catalog cards
- task/run status chips
- recent runs table
- detail drawer or side panel for selected run
- usage/credits summary
- API keys, templates, schedules, results/export entry points
- responsive mobile navigation
- no marketing landing page as first screen
- no nested cards, no decorative gradient/orb background, no one-note purple/slate/beige theme
- text must fit at desktop and mobile widths

### Phase 3 - Workflow Functionality

Make the core SaaS workflow actually usable:

- enter URL/query
- choose extraction intent/schema/options
- start scrape
- show progress/escalation timeline
- poll or update until completion
- show saved results
- export CSV/JSON where supported
- link run/results state across pages
- show structured errors without raw internals

### Phase 4 - Security Hardening

Fix or document:

- raw exception leakage in API responses
- `/check-connection` live response after Railway deploy
- API key creation/revoke/list behavior with redacted verification
- tenant headers and auth behavior
- SSRF and target validation risks for scraper endpoints if present

### Phase 5 - Verification

Run focused local and live checks:

- `npm run build` in `apps/web`
- targeted TypeScript/lint checks available in the repo
- relevant backend Python compile/tests for changed backend files
- live route status checks on Netlify production/draft
- live API health and smart scrape smoke
- Playwright screenshots for desktop and mobile after UI changes

## Coordination Rules

- Keep `docs/agent-sync/CURRENT_PHASE.md`, `docs/agent-sync/CLAUDE_STATUS.md`, and `docs/agent-sync/CODEX_RELEASE_GATE.md` updated as facts change.
- Commit coherent chunks to `saas-repair`.
- Push branch after each stable chunk.
- Use draft deploys before production deploys when changing UI.
- Do not claim production-ready until Codex independently verifies.
- If Antigravity is available, use it for visual/runtime inspection only after a local or draft URL exists.

## Output Required

At the end of this continuation, provide:

- files changed
- commits created
- tests run and results
- deploy URLs if any
- screenshots captured if any
- known blockers
- explicit statement of whether Codex final gate should pass or fail
