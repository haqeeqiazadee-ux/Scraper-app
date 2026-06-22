# Secrets Access Notes

Updated: 2026-06-19

Private API file for local agents:

`C:\Users\PC\Scraper-app-main\.agent-secrets\api-for-scraper.txt`

Fresh-clone copy for active work:

`C:\Users\PC\Scraper-app-fresh\.agent-secrets\api-for-scraper.txt`

Rules for Claude, Antigravity, and Codex:

- The file may be read locally when API credentials are required for setup or verification.
- Do not print, paste, summarize, commit, screenshot, or log any secret values.
- When documenting environment status, write only `PRESENT`, `MISSING`, `USED`, or `BLOCKED`.
- If a key is missing, document the provider and signup/configuration need in the API key requirements sheet.
- Keep `.agent-secrets/` out of git. It is intentionally listed in `.gitignore`.

If a command unexpectedly prints secrets, stop using that command and treat the transcript/log as sensitive.
