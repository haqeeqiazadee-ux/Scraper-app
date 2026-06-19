# Codex Release Gate

Codex is the final QA gate for this mission. Claude and Antigravity may implement and inspect, but production-ready status requires Codex-side verification from code, git, deploy evidence, and live endpoint checks.

## Current Gate Status

- Overall: NOT READY
- Frontend deploy route fix: PASS
- Backend API key revoke hotfix: PASS
- Apify-style dashboard UI: IN PROGRESS — code committed, awaiting deploy + visual review
- End-to-end SaaS workflow proof: PARTIAL
- Secret-handling discipline: NEEDS STRICT CONTINUATION GUARDRAILS
- Global raw exception leakage: OPEN
- Main branch provenance: OPEN

## What Changed This Session

1. TopBar component added: search trigger, environment health badge, account indicator.
2. Layout updated: TopBar integration, mobile hamburger menu, slide-out sidebar with overlay.
3. Dashboard redesigned: stats row, scraper catalog cards (6 scrapers), recent runs table, quick links panel, usage summary, platform info panel.
4. CSS updated: TopBar styles, dashboard layout, catalog cards, runs table, side panels, mobile responsive breakpoints.
5. Frontend build passes: `tsc && vite build` succeeds. CSS 47KB, JS 425KB.

## Required Before Done

1. `apps/web` must present a polished Apify-client-style SaaS dashboard, not a minimal scraper shell.
2. `/scraper` must support a full scrape run with visible progress, saved results, and export controls.
3. API key workflows must be validated with redacted output only.
4. Live Netlify routes must pass desktop and mobile screenshot review.
5. Backend endpoints must return structured error envelopes without raw internal exception detail.
6. Railway and Netlify deployment provenance must be documented.
7. Git status must be clean except intentionally ignored local-only secret/build files.

## Secret Rules

- Never print raw API keys, tokens, database URLs, webhook secrets, cookies, or auth headers.
- Store any raw API response containing secrets only under `.agent-secrets/`.
- Mask raw values before logging or writing status files.
- If a secret appears in a transcript, stop the agent, revoke or rotate the secret, and document only the key ID and remediation.
