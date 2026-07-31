"""Media router — upload endpoints (US2 / contracts/media.md). Gallery reads land in US3.

`PUT /media/upload/raw` is a dev-only stand-in for the client's direct PUT to object
storage; in production the client uploads straight to the presigned OSS URL.
"""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request, status

from ..deps import CurrentUser, DbDep, SettingsDep
from ..i18n import t
from ..schemas.media import (
    GalleryResponse,
    MediaOut,
    UploadConfirmRequest,
    UploadInitRequest,
    UploadInitResponse,
)
from ..services import media as media_service
from ..services.storage import get_storage

router = APIRouter(prefix="/api/v1/media", tags=["media"])


@router.get("", response_model=GalleryResponse)
async def list_gallery(
    user: CurrentUser,
    session: DbDep,
    media_type: Annotated[Literal["image", "video"] | None, Query()] = None,
    uploader: Annotated[str | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    sort: Annotated[
        Literal["newest", "oldest", "most_viewed", "most_liked"], Query()
    ] = "newest",
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GalleryResponse:
    items, has_more = await media_service.list_gallery(
        session,
        media_type=media_type,
        uploader=uploader,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return GalleryResponse(
        items=[MediaOut.model_validate(m) for m in items],
        has_more=has_more,
        next_offset=(offset + limit) if has_more else None,
    )


@router.get("/ids", response_model=list[int])
async def list_gallery_ids(
    user: CurrentUser,
    session: DbDep,
    media_type: Annotated[Literal["image", "video"] | None, Query()] = None,
    uploader: Annotated[str | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[int]:
    """All media ids matching the given filters — backs "select all matching filter"."""
    return await media_service.list_gallery_ids(
        session, media_type=media_type, uploader=uploader, date_from=date_from, date_to=date_to
    )


@router.post("/upload/init", response_model=UploadInitResponse)
async def upload_init(
    body: UploadInitRequest, user: CurrentUser, session: DbDep, settings: SettingsDep
) -> UploadInitResponse:
    media, upload_url = await media_service.init_upload(session, user, body, settings)
    await session.commit()
    return UploadInitResponse(
        media_id=media.id, upload_url=upload_url, storage_key=media.storage_path, status=media.status
    )


@router.put("/upload/raw", status_code=status.HTTP_204_NO_CONTENT)
async def upload_raw(key: str, request: Request, user: CurrentUser, session: DbDep) -> None:
    """Dev-only stand-in for the direct client→OSS PUT.

    Only available with the local storage backend; in production the client uploads
    straight to the presigned OSS URL. Validates the *actual* byte size against the
    configured limit (the declared size at init is not trusted) and records the truth.
    """
    from sqlalchemy import select

    from ..models.event_config import SINGLETON_ID, EventConfig
    from ..models.media import MEDIA_IMAGE, STATUS_PENDING, Media
    from ..services.storage import LocalStorage

    storage = get_storage()
    if not isinstance(storage, LocalStorage):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    result = await session.execute(
        select(Media).where(Media.storage_path == key, Media.uploader_id == user.id)
    )
    media = result.scalar_one_or_none()
    if media is None or media.status != STATUS_PENDING:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=t("media_not_found", user.language_preference)
        )

    body = await request.body()
    config = await session.get(EventConfig, SINGLETON_ID)
    max_bytes = (
        (config.max_image_bytes if config else 50 * 1024 * 1024)
        if media.media_type == MEDIA_IMAGE
        else (config.max_video_bytes if config else 500 * 1024 * 1024)
    )
    if len(body) > max_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, detail=t("file_too_large", user.language_preference)
        )

    storage.put(key, body)
    media.file_size = len(body)  # record the actual size, not the client's declared one
    await session.commit()


@router.post("/upload/confirm", response_model=MediaOut)
async def upload_confirm(
    body: UploadConfirmRequest, user: CurrentUser, session: DbDep, settings: SettingsDep
) -> MediaOut:
    media = await media_service.confirm_upload(session, user, body.media_id, settings)
    await session.commit()
    await session.refresh(media)
    return MediaOut.model_validate(media)


@router.get("/uploaders", response_model=list[str])
async def list_uploaders(user: CurrentUser, session: DbDep) -> list[str]:
    return await media_service.list_uploaders(session)


@router.get("/{media_id}", response_model=MediaOut)
async def get_media(media_id: int, user: CurrentUser, session: DbDep) -> MediaOut:
    media = await media_service.get_visible_item(session, media_id, user.language_preference)
    return MediaOut.model_validate(media)


@router.get("/{media_id}/similar", response_model=list[MediaOut])
async def get_similar(media_id: int, user: CurrentUser, session: DbDep) -> list[MediaOut]:
    items = await media_service.find_similar(session, media_id, user.language_preference)
    return [MediaOut.model_validate(m) for m in items]
