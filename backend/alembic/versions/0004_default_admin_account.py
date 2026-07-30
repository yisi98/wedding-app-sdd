"""Seed the built-in admin account.

Guests share one event password and carry a sentinel in ``hashed_password``; this account
instead holds a real bcrypt hash and signs in with its own password, which is what makes
the admin panel reachable on a fresh deployment.

The password is read from ADMIN_PASSWORD (default ``admin12345``) at upgrade time. The
insert is skipped when an account with that username already exists, so re-running is
safe and never clobbers a password changed after the fact.
"""

import os

import bcrypt
import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels = None
depends_on = None

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin12345")


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("SELECT 1 FROM users WHERE username = :u LIMIT 1"), {"u": ADMIN_USERNAME}
    ).first()
    if exists:
        return
    hashed = bcrypt.hashpw(ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    # is_active is bound rather than a literal so the statement works on both
    # PostgreSQL (prod) and SQLite (local).
    bind.execute(
        sa.text(
            "INSERT INTO users (username, hashed_password, role, language_preference, is_active)"
            " VALUES (:u, :p, 'admin', 'en', :active)"
        ),
        {"u": ADMIN_USERNAME, "p": hashed, "active": True},
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("DELETE FROM users WHERE username = :u AND role = 'admin'"),
        {"u": ADMIN_USERNAME},
    )
