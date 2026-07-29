"""initial schema — users, refresh_tokens, media, event_config

Revision ID: 0001
Revises:
Create Date: 2026-07-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("language_preference", sa.String(5), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean, nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "media",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uploader_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("media_type", sa.String(10), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("thumbnail_path", sa.String(512), nullable=True),
        sa.Column("optimized_path", sa.String(512), nullable=True),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("duration", sa.Float, nullable=True),
        sa.Column("exif_data", sa.JSON, nullable=True),
        sa.Column("phash", sa.String(64), nullable=True),
        sa.Column("lqip", sa.Text, nullable=True),
        sa.Column("view_count", sa.Integer, nullable=False),
        sa.Column("reaction_count", sa.Integer, nullable=False),
        sa.Column("comment_count", sa.Integer, nullable=False),
        sa.Column("favorite_count", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_visible", sa.Boolean, nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_media_uploader_id", "media", ["uploader_id"])
    op.create_index("ix_media_file_hash", "media", ["file_hash"], unique=True)
    op.create_index("ix_media_phash", "media", ["phash"])

    op.create_table(
        "event_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uploads_enabled", sa.Boolean, nullable=False),
        sa.Column("max_image_bytes", sa.Integer, nullable=False),
        sa.Column("max_video_bytes", sa.Integer, nullable=False),
        sa.Column("event_name", sa.String(200), nullable=False),
        sa.Column("event_date", sa.Date, nullable=True),
        *_timestamps(),
    )


def downgrade() -> None:
    op.drop_table("event_config")
    op.drop_table("media")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
