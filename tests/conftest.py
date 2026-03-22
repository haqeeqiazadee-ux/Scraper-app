"""
Shared test fixtures for the AI Scraping Platform test suite.
"""

import sys
from pathlib import Path
from uuid import uuid4

import pytest

# Ensure packages are importable from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))


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
