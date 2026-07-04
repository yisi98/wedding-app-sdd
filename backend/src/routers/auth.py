"""Auth router — implements contracts/auth.md (US1 / FR-AUTH). No /register endpoint."""

from fastapi import APIRouter, HTTPException, status

from ..deps import CurrentUser, DbDep, SettingsDep
from ..i18n import t
from ..schemas.auth import (
    LoginRequest,
    ProfileUpdate,
    RefreshRequest,
    TokenPairResponse,
    TokenResponse,
    UserOut,
)
from ..services import auth as auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: DbDep, settings: SettingsDep) -> TokenResponse:
    if not auth_service.verify_event_password(body.event_password, settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=t("invalid_event_password")
        )
    user = await auth_service.get_or_create_user(session, body.display_name)
    access = auth_service.create_access_token(user, settings)
    refresh = await auth_service.issue_refresh_token(session, user, settings)
    await session.commit()
    return TokenResponse(access_token=access, refresh_token=refresh, user=UserOut.model_validate(user))


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(body: RefreshRequest, session: DbDep, settings: SettingsDep) -> TokenPairResponse:
    rotated = await auth_service.rotate_refresh_token(session, body.refresh_token, settings)
    if rotated is None:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=t("invalid_refresh_token")
        )
    access, new_refresh, _user = rotated
    await session.commit()
    return TokenPairResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: CurrentUser, session: DbDep) -> None:
    await auth_service.revoke_all_refresh_tokens(session, user.id)
    await session.commit()


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.put("/profile", response_model=UserOut)
async def update_profile(body: ProfileUpdate, user: CurrentUser, session: DbDep) -> UserOut:
    if body.language_preference is not None:
        user.language_preference = body.language_preference
    await session.commit()
    await session.refresh(user)
    return UserOut.model_validate(user)
