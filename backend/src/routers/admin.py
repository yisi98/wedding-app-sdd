"""Admin router (US8 / contracts/admin.md). Every route requires role=admin (→403 else)."""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from ..deps import AdminUser, DbDep
from ..schemas.admin import (
    AdminStats,
    UserAdminOut,
    UserListResponse,
    UserUpdateRequest,
    VisibilityRequest,
)
from ..schemas.media import MediaOut
from ..services import admin as admin_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def stats(admin: AdminUser, session: DbDep) -> AdminStats:
    return AdminStats(**await admin_service.get_stats(session))


@router.get("/users", response_model=UserListResponse)
async def list_users(
    admin: AdminUser,
    session: DbDep,
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UserListResponse:
    users, has_more = await admin_service.list_users(session, q, limit, offset)
    return UserListResponse(
        items=[UserAdminOut.model_validate(u, from_attributes=True) for u in users],
        has_more=has_more,
    )


@router.patch("/users/{user_id}", response_model=UserAdminOut)
async def update_user(
    user_id: int, body: UserUpdateRequest, admin: AdminUser, session: DbDep
) -> UserAdminOut:
    user = await admin_service.update_user(session, admin, user_id, body.role, body.is_active)
    await session.commit()
    return UserAdminOut.model_validate(user, from_attributes=True)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, admin: AdminUser, session: DbDep) -> None:
    await admin_service.delete_user(session, admin, user_id)
    await session.commit()


@router.get("/media", response_model=list[MediaOut])
async def list_media(
    admin: AdminUser,
    session: DbDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MediaOut]:
    items, _ = await admin_service.list_all_media(session, limit, offset)
    return [MediaOut.model_validate(m) for m in items]


@router.patch("/media/{media_id}/visibility", response_model=MediaOut)
async def set_visibility(
    media_id: int, body: VisibilityRequest, admin: AdminUser, session: DbDep
) -> MediaOut:
    media = await admin_service.set_visibility(session, admin, media_id, body.is_visible)
    await session.commit()
    return MediaOut.model_validate(media)


@router.get("/export/media")
async def export_media(admin: AdminUser, session: DbDep) -> Response:
    csv_text = await admin_service.export_media_csv(session)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=media.csv"},
    )
