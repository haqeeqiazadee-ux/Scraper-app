"""Control plane configuration — loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    workers: int = 4

    # Database
    database_url: str = "sqlite+aiosqlite:///./scraper.db"

    # Redis
    redis_url: str = ""

    # Object storage
    storage_type: str = "filesystem"
    storage_path: str = "./artifacts"

    # AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Auth
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15

    # Public API (Zero Checksum)
    api_key_prefix: str = "sk_live_"
    idempotency_key_ttl_hours: int = 24
    audit_log_retention_days: int = 90
    async_job_result_ttl_hours: int = 24
    public_api_rate_limit_per_minute: int = 60

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


settings = Settings()
