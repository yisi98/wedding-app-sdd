"""Reaction — a single guest's like/love/laugh on a media item (unique per user+item)."""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin

REACTION_LIKE = "like"
REACTION_LOVE = "love"
REACTION_LAUGH = "laugh"
REACTION_TYPES = (REACTION_LIKE, REACTION_LOVE, REACTION_LAUGH)


class Reaction(Base, TimestampMixin):
    __tablename__ = "reactions"
    __table_args__ = (UniqueConstraint("user_id", "media_id", name="uq_reaction_user_media"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id", ondelete="CASCADE"), index=True)
    reaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
