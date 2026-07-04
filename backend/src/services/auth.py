"""Authentication service.

Implements the password-only, get-or-create model (ADR-002 / FR-AUTH):
- One shared event password gates all access (bcrypt hash in prod, plaintext in dev).
- Accounts are created on first login by display name and reused thereafter.
- Sessions use a short-lived JWT access token plus a rotating refresh token whose
  SHA-256 hash is stored; rotation revokes the previous token; logout revokes all.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models.refresh_token import RefreshToken
from ..models.user import ROLE_GUEST, User

# Sentinel stored in users.hashed_password for password-less guests.
GUEST_PASSWORD_SENTINEL = "!"


def verify_event_password(password: str, settings: Settings) -> bool:
    """Verify against a bcrypt hash when configured, else a constant-time plaintext compare."""
    if settings.event_password_hash:
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), settings.event_password_hash.encode("utf-8")
            )
        except ValueError:
            return False
    return secrets.compare_digest(password, settings.event_password)


async def get_or_create_user(session: AsyncSession, display_name: str) -> User:
    """Return the existing user for this display name, or create a new guest."""
    display_name = display_name.strip()
    result = await session.execute(select(User).where(User.username == display_name))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(username=display_name, role=ROLE_GUEST, hashed_password=GUEST_PASSWORD_SENTINEL)
        session.add(user)
        await session.flush()
    return user


def create_access_token(user: User, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def issue_refresh_token(
    session: AsyncSession, user: User, settings: Settings
) -> str:
    """Create and persist a new refresh token; return the raw (unhashed) token to the client."""
    raw = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days)
    session.add(
        RefreshToken(user_id=user.id, token_hash=_hash_token(raw), expires_at=expires)
    )
    await session.flush()
    return raw


async def rotate_refresh_token(
    session: AsyncSession, raw_token: str, settings: Settings
) -> tuple[str, str, User] | None:
    """Validate + rotate a refresh token.

    Returns (new_access, new_refresh, user) or None if the token is missing, revoked,
    expired, or its user is inactive. A rotated token is revoked and cannot be reused.
    """
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw_token))
    )
    token = result.scalar_one_or_none()
    if token is None or token.is_revoked:
        return None

    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None

    user = await session.get(User, token.user_id)
    if user is None or not user.is_active:
        return None

    # Revoke the presented token (rotation) and issue a fresh pair.
    token.is_revoked = True
    await session.flush()
    new_refresh = await issue_refresh_token(session, user, settings)
    new_access = create_access_token(user, settings)
    return new_access, new_refresh, user


async def revoke_all_refresh_tokens(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))
        .values(is_revoked=True)
    )
