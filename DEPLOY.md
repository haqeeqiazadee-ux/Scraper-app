# Deployment Guide — Netlify + Supabase + Railway + Redis

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Netlify    │────▶│  Railway (API)   │────▶│    Supabase      │
│  (Frontend)  │     │  Control Plane   │     │  (PostgreSQL)    │
│  React/Vite  │     │  + Workers       │     │                  │
└─────────────┘     └───────┬──────────┘     └──────────────────┘
                            │
                    ┌───────▼──────────┐
                    │  Railway (Redis) │
                    │  Queue + Cache   │
                    └──────────────────┘
```

## Step 1: Supabase — Create Database Tables

1. Go to https://supabase.com/dashboard → select project `pspnuohejsbcavdtardv`
2. Open **SQL Editor** → **New query**
3. Paste contents of `infrastructure/supabase/001_initial_schema.sql`
4. Click **Run** — creates 6 tables + indexes

## Step 2: Railway — Deploy Backend

1. Go to https://railway.app → **New Project** → **Deploy from GitHub repo**
2. Select `fahad-scraper/Scraper-app`
3. Add **Redis plugin**: click **+ New** → **Database** → **Redis**
4. Set environment variables in Railway dashboard:

   ```
   DATABASE_URL=postgresql+asyncpg://postgres:KLKLinnii%232H@db.pspnuohejsbcavdtardv.supabase.co:5432/postgres
   GEMINI_API_KEY=<your-key>
   SECRET_KEY=<generated-secret>
   QUEUE_BACKEND=redis
   CORS_ORIGINS=https://YOUR-SITE.netlify.app
   LOG_LEVEL=INFO
   STORAGE_TYPE=filesystem
   STORAGE_PATH=/app/artifacts
   ```

   > `REDIS_URL` is auto-injected by the Redis plugin.

5. Railway auto-detects `railway.toml` and deploys.
6. Note the public URL (e.g. `https://scraper-api-production.up.railway.app`)

### Optional: Deploy Workers as Separate Services

For each worker, click **+ New** → **Service** → same GitHub repo:

| Service | Override Start Command |
|---------|----------------------|
| HTTP Worker | `python -m services.worker_http.main` |
| Browser Worker | `python -m services.worker_browser.main` |
| AI Worker | `python -m services.worker_ai.main` |
| Hard-Target Worker | `python -m services.worker_hard_target.main` |

Each worker shares the same Redis (link the Redis plugin to each service).

## Step 3: Netlify — Deploy Frontend

1. Go to https://app.netlify.com → **Add new site** → **Import from Git**
2. Select `fahad-scraper/Scraper-app`
3. Netlify auto-detects `netlify.toml` settings:
   - Base: `apps/web`
   - Build: `npm install && npm run build`
   - Publish: `apps/web/dist`
4. Set environment variable:
   ```
   VITE_API_URL=https://YOUR-RAILWAY-URL.railway.app/api/v1
   ```
5. Update `netlify.toml` proxy redirect with your actual Railway URL
6. Redeploy

## Step 4: Wire CORS

Update `CORS_ORIGINS` on Railway to include your Netlify URL:
```
CORS_ORIGINS=https://your-site.netlify.app
```

## Verify

```bash
# Backend health
curl https://YOUR-RAILWAY-URL.railway.app/health

# Frontend
open https://your-site.netlify.app
```

## Files Reference

| File | Purpose |
|------|---------|
| `netlify.toml` | Netlify build + redirects config |
| `railway.toml` | Railway deploy config |
| `infrastructure/docker/Dockerfile.railway` | Docker image for Railway |
| `infrastructure/supabase/001_initial_schema.sql` | Database schema SQL |
| `.env.production.example` | Production env template |
| `.env` | Local credentials (gitignored, never committed) |
