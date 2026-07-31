"""Let a deleted user's uploads and share links survive them.

``media.uploader_id`` and ``share_links.created_by_id`` were NOT NULL foreign keys with no
``ondelete`` behavior, so deleting a user who had ever uploaded a photo or created a share
link failed with a foreign-key violation on any database that enforces FKs (PostgreSQL
always does; SQLite only under ``PRAGMA foreign_keys=ON``, which is why this hid in dev).
Photos are communal — the album shouldn't lose pictures because one guest's account was
removed — so both columns become nullable with ``ON DELETE SET NULL``.

The original columns were declared with a bare ``ForeignKey("users.id")`` (no explicit
constraint name), so SQLite reflects them as unnamed and PostgreSQL auto-names them
``<table>_<column>_fkey``. Batch mode's ``drop_constraint`` can't target either reliably by
guessing a name, so instead we reflect the live table, swap the constraint object directly,
and hand the corrected table to ``copy_from`` — batch mode then recreates around it.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-31
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels = None
depends_on = None


def _swap_fk(
    table: sa.Table, column: str, ref: str, name: str, *, ondelete: str | None
) -> None:
    for fk in [c for c in table.constraints if isinstance(c, sa.ForeignKeyConstraint)]:
        if column in fk.column_keys:
            table.constraints.discard(fk)
    table.append_constraint(
        sa.ForeignKeyConstraint([column], [ref], name=name, ondelete=ondelete)
    )


def upgrade() -> None:
    bind = op.get_bind()

    media = sa.Table("media", sa.MetaData(), autoload_with=bind)
    _swap_fk(media, "uploader_id", "users.id", "fk_media_uploader_id_users", ondelete="SET NULL")
    with op.batch_alter_table("media", copy_from=media) as batch_op:
        batch_op.alter_column("uploader_id", existing_type=sa.Integer, nullable=True)

    share_links = sa.Table("share_links", sa.MetaData(), autoload_with=bind)
    _swap_fk(
        share_links,
        "created_by_id",
        "users.id",
        "fk_share_links_created_by_id_users",
        ondelete="SET NULL",
    )
    with op.batch_alter_table("share_links", copy_from=share_links) as batch_op:
        batch_op.alter_column("created_by_id", existing_type=sa.Integer, nullable=True)


def downgrade() -> None:
    bind = op.get_bind()

    share_links = sa.Table("share_links", sa.MetaData(), autoload_with=bind)
    _swap_fk(
        share_links, "created_by_id", "users.id", "fk_share_links_created_by_id_users", ondelete=None
    )
    with op.batch_alter_table("share_links", copy_from=share_links) as batch_op:
        batch_op.alter_column("created_by_id", existing_type=sa.Integer, nullable=False)

    media = sa.Table("media", sa.MetaData(), autoload_with=bind)
    _swap_fk(media, "uploader_id", "users.id", "fk_media_uploader_id_users", ondelete=None)
    with op.batch_alter_table("media", copy_from=media) as batch_op:
        batch_op.alter_column("uploader_id", existing_type=sa.Integer, nullable=False)
