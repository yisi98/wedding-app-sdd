"""Shared FastAPI dependencies: settings, DB session, current user, admin guard."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .db import get_db
from .i18n import t
from .models.user import User
from .services import auth as auth_service

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    settings: SettingsDep,
    session: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    lang = "en"
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=t("not_authenticated", lang)
        )
    token = authorization.split(" ", 1)[1].strip()
    payload = auth_service.decode_access_token(token, settings)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=t("not_authenticated", lang)
        )
    user = await session.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=t("account_inactive", lang)
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=t("admin_required", user.language_preference),
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]
