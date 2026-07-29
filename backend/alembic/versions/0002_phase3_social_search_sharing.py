"""phase 3 — reactions, comments, favorites, share_links

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "reactions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_id", sa.Integer, sa.ForeignKey("media.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reaction_type", sa.String(10), nullable=False),
        sa.UniqueConstraint("user_id", "media_id", name="uq_reaction_user_media"),
        *_timestamps(),
    )
    op.create_index("ix_reactions_user_id", "reactions", ["user_id"])
    op.create_index("ix_reactions_media_id", "reactions", ["media_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_id", sa.Integer, sa.ForeignKey("media.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_deleted", sa.Boolean, nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_comments_user_id", "comments", ["user_id"])
    op.create_index("ix_comments_media_id", "comments", ["media_id"])

    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_id", sa.Integer, sa.ForeignKey("media.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "media_id", name="uq_favorite_user_media"),
        *_timestamps(),
    )
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])
    op.create_index("ix_favorites_media_id", "favorites", ["media_id"])

    op.create_table(
        "share_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("media_id", sa.Integer, sa.ForeignKey("media.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("access_count", sa.Integer, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_share_links_token", "share_links", ["token"], unique=True)


def downgrade() -> None:
    op.drop_table("share_links")
    op.drop_table("favorites")
    op.drop_table("comments")
    op.drop_table("reactions")
