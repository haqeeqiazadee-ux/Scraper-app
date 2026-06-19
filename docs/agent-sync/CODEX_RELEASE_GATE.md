# Codex Release Gate

Codex is the final QA gate for this mission. Claude and Antigravity may implement and inspect, but production-ready status requires Codex-side verification from code, git, deploy evidence, and live endpoint checks.

## Current Gate Status

- Overall: NOT READY
- Frontend deploy route fix: PASS
- Backend API key revoke hotfix: PASS
- Apify-style dashboard UI: NOT DONE
- End-to-end SaaS workflow proof: PARTIAL
- Secret-handling discipline: NEEDS STRICT CONTINUATION GUARDRAILS
- Global raw exception leakage: OPEN
- Main branch provenance: OPEN

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
