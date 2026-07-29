"""ActivityEvent — a record of a notable action for the feed and live notifications."""

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin

EVENT_NEW_UPLOAD = "new_upload"
EVENT_NEW_REACTION = "new_reaction"
EVENT_NEW_COMMENT = "new_comment"
EVENT_NEW_FAVORITE = "new_favorite"


class ActivityEvent(Base, TimestampMixin):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    media_id: Mapped[int | None] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), nullable=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
