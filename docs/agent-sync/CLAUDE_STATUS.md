# Claude Status - SaaS Repair Mission

## Current State

- Phase: 2 - Apify-style SaaS dashboard and workflow UX
- Branch: `saas-repair`
- Working directory: `C:\Users\PC\Scraper-app-fresh`
- Latest branch commit: `5c8cd8e`
- Production frontend: https://myscraper.netlify.app
- Production backend: https://scraper.exsel.ai
- Railway project: https://railway.com/project/c63725e4-4da6-4bf2-9fc4-068578a9bde6?environmentId=ffa7f443-0c4e-4dc8-8217-0b9fefe1a8ae
- Netlify project: https://app.netlify.com/projects/myscraper/overview

## Completed

1. Fresh clone created because the original repo metadata was corrupt.
2. `netlify.toml` now deploys `apps/web` React/Vite instead of stale `apps/frontend` Next.js.
3. Netlify SPA fallback and API proxy are configured.
4. Frontend build passed with `npm run build` in `apps/web`.
5. Branch `saas-repair` was pushed to GitHub.
6. Netlify production deploy completed and live routes returned HTTP 200.
7. Netlify proxy to backend `/api/v1/health` returned healthy JSON.
8. Smart scrape through Netlify proxy succeeded and saved results.
9. Backend API key datetime bug was fixed, committed, pushed, and deployed to Railway.
10. The temporary test API key with ID `9b67ef21-f702-4e92-a38c-24f1693b5553` was revoked successfully.

## Commits

- `3ca014f` - fix: deploy React/Vite app instead of stale Next.js, harden /check-connection
- `5c8cd8e` - fix: use naive UTC datetimes for API key lifecycle

## Deployments

- Netlify production URL: https://myscraper.netlify.app
- Netlify production deploy: `6a35b47d34af399c9bdb27ea`
- Netlify production unique URL: https://6a35b47d34af399c9bdb27ea--myscraper.netlify.app
- Railway backend deployment: `26cbd7b2-5f60-4381-8c42-429c46217083`

## Security Incident Handling

- During API-key workflow verification, a newly generated test API key appeared in the Claude transcript.
- Do not repeat, print, paste, screenshot, or commit any raw secret from transcripts, `.agent-secrets`, Railway, Netlify, Supabase, or API responses.
- The exposed test key was revoked successfully by key ID.
- Future API key tests must write full responses only to ignored files under `.agent-secrets/` and print only masked status, key ID, prefix, HTTP code, and pass/fail.
- Do not put raw `Authorization: Bearer ...` values in shell commands, logs, markdown, screenshots, or status files.

## Remaining Work

1. Build the `/scraper` and dashboard experience into an Apify-client-style SaaS UI: dense sidebar navigation, actor/task cards, status chips, run table, detail pane, live timeline, exports, API keys, templates, and schedules.
2. Use the attached Apify reference screenshot as the design target, but implement original branding and layout.
3. Verify the UI with screenshots at desktop and mobile widths.
4. Retest `/check-connection`, `/ready`, public API auth, smart scrape, results, exports, templates, schedules, and error envelopes.
5. Fix global raw exception leakage before final acceptance.
6. Keep deployment provenance clear: current Netlify and Railway production deploys were direct CLI deploys from the `saas-repair` working tree, not a merged `main` deployment.
