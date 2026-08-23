"""Let a deleted user's uploads survive them.

``media.uploader_id`` was a NOT NULL foreign key with no ``ondelete`` behavior, so deleting
a user who had ever uploaded a photo failed with a foreign-key violation on any database
that enforces FKs (PostgreSQL always does; SQLite only under ``PRAGMA foreign_keys=ON``,
which is why this hid in dev). Photos are communal — the album shouldn't lose pictures
because one guest's account was removed — so the column becomes nullable with
``ON DELETE SET NULL``.

(The equivalent fix for ``share_links.created_by_id`` is moot: 0005 dropped that table.)

The original column was declared with a bare ``ForeignKey("users.id")`` (no explicit
constraint name), so SQLite reflects it as unnamed and PostgreSQL auto-names it
``media_uploader_id_fkey``. Batch mode's ``drop_constraint`` can't target either reliably by
guessing a name, so instead we reflect the live table, swap the constraint object directly,
and hand the corrected table to ``copy_from`` — batch mode then recreates around it.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-31
"""

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
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


def downgrade() -> None:
    bind = op.get_bind()

    media = sa.Table("media", sa.MetaData(), autoload_with=bind)
    _swap_fk(media, "uploader_id", "users.id", "fk_media_uploader_id_users", ondelete=None)
    with op.batch_alter_table("media", copy_from=media) as batch_op:
        batch_op.alter_column("uploader_id", existing_type=sa.Integer, nullable=False)
