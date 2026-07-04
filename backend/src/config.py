"""Application configuration.

`get_settings()` is `@lru_cache`d, so configuration is read once per process. Changing
`.env` therefore requires a backend restart to take effect (documented constraint in
research.md).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    debug: bool = True

    # Database
    database_url: str = "sqlite+aiosqlite:///./wedding.db"

    # Event access (Principle II/III). Prefer EVENT_PASSWORD_HASH (bcrypt) in production.
    event_password: str = "dev-only-event-pass"
    event_password_hash: str | None = None

    # Auth / JWT
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7

    # Real-time / storage / email (wired in later user stories)
    redis_url: str | None = None
    smtp_host: str | None = None

    # Production CORS allow-list (only used when debug is False)
    cors_origins: list[str] = Field(default_factory=list)


@lru_cache
def get_settings() -> Settings:
    return Settings()
