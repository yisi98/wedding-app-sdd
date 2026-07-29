"""ShareLink — a token granting access to the gallery or a single item (US5)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ShareLink(Base, TimestampMixin):
    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # NULL media_id ⇒ whole-gallery share.
    media_id: Mapped[int | None] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), nullable=True
    )
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
