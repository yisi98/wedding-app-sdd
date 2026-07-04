"""Event configuration — singleton row (id=1) holding platform-wide settings."""

from datetime import date

from sqlalchemy import Boolean, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin

DEFAULT_MAX_IMAGE_BYTES = 50 * 1024 * 1024  # 50 MB
DEFAULT_MAX_VIDEO_BYTES = 500 * 1024 * 1024  # 500 MB
SINGLETON_ID = 1


class EventConfig(Base, TimestampMixin):
    __tablename__ = "event_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=SINGLETON_ID)
    uploads_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_image_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_MAX_IMAGE_BYTES
    )
    max_video_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_MAX_VIDEO_BYTES
    )
    event_name: Mapped[str] = mapped_column(String(200), nullable=False, default="Our Wedding")
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
