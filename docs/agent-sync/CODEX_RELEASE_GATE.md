# Codex Release Gate

Codex is the final QA gate for this mission. Claude and Antigravity may implement and inspect, but production-ready status requires Codex-side verification from code, git, deploy evidence, and live endpoint checks.

## Current Gate Status

- Overall: NOT READY
- Frontend deploy route fix: PASS
- Backend API key revoke hotfix: PASS
- Apify-style dashboard UI: PASS
- Core scraper workflow smoke: PASS
- Secret-handling discipline: PARTIAL
- Global raw exception leakage: OPEN
- Main branch provenance: OPEN

## Verification Evidence

1. `d2ccf9a` is pushed to `origin/saas-repair`.
2. Codex reran `cmd /c npm run build` in `apps/web`; build passed.
3. Netlify production deploy `6a35ba4839d8c89db918ec68` is live at https://myscraper.netlify.app.
4. Live routes `/`, `/dashboard`, `/scraper`, and `/api/v1/health` returned 200.
5. Backend `/health`, `/ready`, `/check-connection`, and `/api/v1/check-connection` returned 200.
6. `/check-connection` response contained only `status` and `timestamp`.
7. Browser QA found no console warnings/errors during dashboard and scraper checks.
8. Desktop screenshot showed Apify-style sidebar, topbar, catalog cards, recent runs, quick links, and usage panel.
9. Mobile screenshot showed clean responsive layout; hamburger interaction opened the sidebar drawer.
10. Scraper UI smoke filled `https://example.com`, completed, saved results, and displayed stats/results.
11. Antigravity read-only visual QA returned PASS with no blockers.

## Required Before Done

1. API key workflows must be validated with redacted output only.
2. Backend endpoints must return structured error envelopes without raw internal exception detail.
3. Railway and Netlify deployment provenance must be normalized or documented for main-branch release.
4. Broader E2E/regression tests should run before declaring the SaaS fully production-complete.

## Secret Rules

- Never print raw API keys, tokens, database URLs, webhook secrets, cookies, or auth headers.
- Store any raw API response containing secrets only under `.agent-secrets/`.
- Mask raw values before logging or writing status files.
- If a secret appears in a transcript, stop the agent, revoke or rotate the secret, and document only the key ID and remediation.
