"""Control plane configuration — loaded from environment variables."""

from __future__ import annotations

import os
from pydantic import Field
import os
from pydantic import Field
import os
import os
from pydantic_settings import BaseSettings, SettingsConfigDict, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    workers: int = 4

    # Database
    database_url: str

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


    environment: str = Field(default="development", env="ENVIRONMENT")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    model_config = SettingsConfigDict(
        env_file=".env" if os.getenv("ENVIRONMENT", "development") != "production" else None,
        case_sensitive=False,
        extra="ignore"
    )




import os
if os.environ.get("ENVIRONMENT") == "production":
    settings = Settings(_env_file=None)
else:
    settings = Settings()

