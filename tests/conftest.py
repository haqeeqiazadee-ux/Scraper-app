"""
Shared test fixtures for the AI Scraping Platform test suite.
"""

import sys
from pathlib import Path
from uuid import uuid4

import pytest

# Ensure packages are importable from repo root
ROOT = str(Path(__file__).parent.parent)
sys.path.insert(0, ROOT)

# Windows fix: services/control_plane is a broken symlink (text file, not real symlink).
# Create proper module mappings for hyphenated directory names.
import os
import types

_services_dir = os.path.join(ROOT, "services")

def _register_hyphenated_package(parent_mod_name: str, parent_dir: str, hyphenated: str):
    """Register a hyphenated directory as a Python package under its underscore name."""
    underscore = hyphenated.replace("-", "_")
    mod_name = f"{parent_mod_name}.{underscore}"
    pkg_dir = os.path.join(parent_dir, hyphenated)
    if os.path.isdir(pkg_dir) and mod_name not in sys.modules:
        mod = types.ModuleType(mod_name)
        mod.__path__ = [pkg_dir]
        mod.__package__ = mod_name
        sys.modules[mod_name] = mod

if "services" not in sys.modules:
    services_mod = types.ModuleType("services")
    services_mod.__path__ = [_services_dir]
    services_mod.__package__ = "services"
    _init = os.path.join(_services_dir, "__init__.py")
    if os.path.exists(_init):
        exec(open(_init).read(), services_mod.__dict__)
    sys.modules["services"] = services_mod

for _hyphenated in ["control-plane", "worker-http", "worker-browser", "worker-ai", "worker-hard-target"]:
    _register_hyphenated_package("services", _services_dir, _hyphenated)


@pytest.fixture
def tenant_id() -> str:
    """Default tenant ID for testing."""
    return "test-tenant-001"


@pytest.fixture
def sample_url() -> str:
    """Sample URL for testing."""
    return "https://example.com/products"


@pytest.fixture
def sample_task_id():
    """Generate a unique task ID."""
    return uuid4()
