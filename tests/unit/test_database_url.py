from packages.core.storage.database import _normalize_database_url


def test_normalize_database_url_adds_asyncpg_and_escapes_password() -> None:
    url = _normalize_database_url(
        "postgresql://postgres:p@ss#word@db.example.supabase.co:5432/postgres"
    )

    assert url.startswith("postgresql+asyncpg://")
    assert "p%40ss%23word" in url
    assert url.endswith("@db.example.supabase.co:5432/postgres")


def test_normalize_database_url_preserves_non_postgres_url() -> None:
    url = "sqlite+aiosqlite:///./scraper.db"

    assert _normalize_database_url(url) == url
