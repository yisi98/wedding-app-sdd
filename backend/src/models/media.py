"""Media entity — an uploaded photo or video, content-addressed by SHA-256 hash."""


from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .user import User

MEDIA_IMAGE = "image"
MEDIA_VIDEO = "video"

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_READY = "ready"
STATUS_FAILED = "failed"


class Media(Base, TimestampMixin):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable + SET NULL: a deleted guest's photos stay in the album (Principle: photos
    # are communal), they just lose their attribution.
    uploader_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # selectin: async-safe eager load, so `uploader_name` below works for every read path
    # (gallery list, single item, similar, admin) without touching each call site.
    uploader: Mapped[User | None] = relationship(lazy="selectin")
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # SHA-256 content hash — unique dedup key (Principle VI).
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    media_type: Mapped[str] = mapped_column(String(10), nullable=False)

    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    optimized_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    exif_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    phash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lqip: Mapped[str | None] = mapped_column(Text, nullable=True)

    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Denormalized engagement counts for fast gallery rendering/sort (maintained by the
    # social service in US4).
    reaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    favorite_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_PENDING)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @property
    def uploader_name(self) -> str | None:
        return self.uploader.username if self.uploader else None
