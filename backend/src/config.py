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

    # Object storage. When storage_access_key is set, an S3-compatible backend
    # (MinIO/AliCloud OSS) is used; otherwise a local filesystem backend (dev/test).
    storage_endpoint: str | None = None
    storage_access_key: str | None = None
    storage_secret_key: str | None = None
    storage_bucket: str = "wedding-media"
    storage_dir: str = ".data"  # local backend base directory

    # Upload validation
    allowed_image_types: list[str] = Field(
        default_factory=lambda: [
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
            "image/heic",
            "image/heif",
            "image/bmp",
            "image/tiff",
            "image/avif",
        ]
    )
    allowed_video_types: list[str] = Field(
        default_factory=lambda: [
            "video/mp4",
            "video/quicktime",
            "video/webm",
            # Browsers/OSes disagree on the AVI mime type (Chrome on Linux reports
            # video/vnd.avi; others report video/x-msvideo or video/avi) — accept all.
            "video/x-msvideo",
            "video/avi",
            "video/vnd.avi",
            "video/msvideo",
            "video/x-matroska",
            "video/mpeg",
            "video/3gpp",
            "video/x-ms-wmv",
        ]
    )

    # Real-time
    redis_url: str | None = None
    activity_channel: str = "wmp:activity"

    # Web push (VAPID)
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_subject: str = "mailto:admin@example.com"

    # Email (optional; disabled when smtp_host is empty)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_from: str = "noreply@example.com"

    # Production CORS allow-list (only used when debug is False)
    cors_origins: list[str] = Field(default_factory=list)


@lru_cache
def get_settings() -> Settings:
    return Settings()
