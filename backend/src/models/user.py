"""User entity — a guest or admin, identified by unique display name (get-or-create)."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin

ROLE_GUEST = "guest"
ROLE_ADMIN = "admin"

LANGUAGES = ("en", "zh", "ru")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    # Legacy column: intentionally excluded from every API response (see research.md).
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Sentinel for password-less guests; real admins may carry a bcrypt hash.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, default="!")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=ROLE_GUEST)
    language_preference: Mapped[str] = mapped_column(String(5), nullable=False, default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN
