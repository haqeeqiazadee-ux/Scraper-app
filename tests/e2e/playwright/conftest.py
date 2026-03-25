"""
Playwright E2E test fixtures.

Starts the FastAPI backend + Vite dev server, provides Playwright browser/page.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import time
from typing import Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BACKEND_PORT = 8765
FRONTEND_PORT = 5199
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
WEB_DIR = os.path.join(PROJECT_ROOT, "apps", "web")


# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------

def _wait_for_server(url: str, timeout: float = 30.0) -> bool:
    """Wait until a server responds at the given URL."""
    import urllib.request
    import urllib.error

    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def backend_server():
    """Start the FastAPI backend for E2E tests."""
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite+aiosqlite:///e2e_test.db"
    env["QUEUE_BACKEND"] = "memory"
    env["STORAGE_TYPE"] = "filesystem"
    env["STORAGE_PATH"] = "/tmp/e2e_artifacts"
    env["HOST"] = "0.0.0.0"
    env["PORT"] = str(BACKEND_PORT)
    env["LOG_LEVEL"] = "WARNING"
    env["CORS_ORIGINS"] = f"http://localhost:{FRONTEND_PORT}"

    proc = subprocess.Popen(
        [
            "python", "-m", "uvicorn",
            "services.control_plane.app:create_app",
            "--factory",
            "--host", "0.0.0.0",
            "--port", str(BACKEND_PORT),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,
    )

    if not _wait_for_server(f"{BACKEND_URL}/health", timeout=30):
        proc.kill()
        stdout = proc.stdout.read().decode() if proc.stdout else ""
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        pytest.fail(f"Backend failed to start.\nstdout: {stdout}\nstderr: {stderr}")

    yield proc

    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    proc.wait(timeout=10)


@pytest.fixture(scope="session")
def frontend_server(backend_server):
    """Start the Vite dev server for E2E tests."""
    env = os.environ.copy()
    env["VITE_API_URL"] = "/api/v1"
    env["VITE_BACKEND_URL"] = BACKEND_URL

    proc = subprocess.Popen(
        [
            "npx", "vite",
            "--port", str(FRONTEND_PORT),
            "--strictPort",
        ],
        cwd=WEB_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,
    )

    if not _wait_for_server(FRONTEND_URL, timeout=45):
        proc.kill()
        stdout = proc.stdout.read().decode() if proc.stdout else ""
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        pytest.fail(f"Vite dev server failed to start.\nstdout: {stdout}\nstderr: {stderr}")

    yield proc

    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    proc.wait(timeout=10)


# ---------------------------------------------------------------------------
# Playwright fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Launch a headless Chromium browser for the test session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Create a fresh browser context per test (isolated cookies/storage)."""
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 720},
        base_url=FRONTEND_URL,
    )
    yield ctx
    ctx.close()


@pytest.fixture
def page(context: BrowserContext, frontend_server) -> Generator[Page, None, None]:
    """Create a fresh page per test with both servers running."""
    pg = context.new_page()
    yield pg
    pg.close()


@pytest.fixture
def authenticated_page(context: BrowserContext, frontend_server) -> Generator[Page, None, None]:
    """Create a page that is pre-authenticated (JWT in localStorage)."""
    pg = context.new_page()
    # Navigate to login and authenticate
    pg.goto("/login")
    pg.wait_for_load_state("networkidle")
    pg.fill('input[id="login-username"]', "e2e-test-user")
    pg.fill('input[id="login-password"]', "e2e-test-pass")
    pg.click('button[type="submit"]')
    # Wait for redirect to dashboard
    pg.wait_for_url("**/dashboard", timeout=10000)
    yield pg
    pg.close()
