# Bundled Resources — AI Scraper Desktop

This directory contains resources that are bundled into the Windows EXE (and other
platform installers) by Tauri at build time. Files placed here are accessible at
runtime via `tauri::api::path::resource_dir()`.

## What to bundle

### 1. Python Runtime (Embedded)

For standalone desktop operation, bundle an embedded Python distribution so users
do not need a system-wide Python install.

- **Source:** [python-build-standalone](https://github.com/indygreg/python-build-standalone)
- **Version:** Python 3.11.x (match `pyproject.toml` requires-python)
- **Variant:** `cpython-3.11.*-x86_64-pc-windows-msvc-install_only.tar.gz`
- **Location:** `resources/python/` (extract the distribution here)
- **Size:** ~40 MB compressed, ~120 MB extracted

The Tauri shell plugin command in `tauri.conf.json` references `python` — update the
PATH or use an absolute path to `resources/python/python.exe` at runtime.

### 2. Control-Plane Service

The embedded FastAPI control plane runs locally on port 8321.

- **What to include:**
  - `packages/` — contracts, core, connectors (Python source)
  - `services/control-plane/` — FastAPI app, routers, middleware
  - `requirements-desktop.txt` — minimal pip dependencies for desktop mode
- **Location:** `resources/service/`
- **Note:** The desktop build uses SQLite (not PostgreSQL), filesystem storage
  (not S3), and in-memory queue/cache (not Redis).

### 3. Default Configuration

- **`resources/config/default.env`** — Default environment variables for desktop mode:
  ```
  SCRAPER_MODE=desktop
  DATABASE_URL=sqlite+aiosqlite:///~/ai-scraper/scraper.db
  STORAGE_BACKEND=filesystem
  STORAGE_PATH=~/ai-scraper/artifacts
  QUEUE_BACKEND=memory
  CACHE_BACKEND=memory
  LOG_LEVEL=info
  HOST=127.0.0.1
  PORT=8321
  ```

### 4. Sample Tasks

Optional sample task definitions for first-run experience:

- **`resources/samples/product-scrape.json`** — Example product extraction task
- **`resources/samples/listing-scrape.json`** — Example listing extraction task
- **`resources/samples/article-scrape.json`** — Example article extraction task

## Build integration

Resources listed in `tauri.conf.json` under `bundle.resources` are automatically
included in the installer. Update the resources array as files are added:

```json
{
  "bundle": {
    "resources": [
      "resources/python/**",
      "resources/service/**",
      "resources/config/**",
      "resources/samples/**"
    ]
  }
}
```

## Size budget

| Resource            | Compressed | Extracted |
|---------------------|-----------|-----------|
| Python runtime      | ~40 MB    | ~120 MB   |
| Control-plane code  | ~2 MB     | ~5 MB     |
| pip dependencies    | ~15 MB    | ~50 MB    |
| Config + samples    | <1 MB     | <1 MB     |
| **Total**           | **~58 MB**| **~176 MB** |

The NSIS installer compresses resources, so the final `.exe` installer should be
approximately 60-70 MB.
