"""Media router — upload endpoints (US2 / contracts/media.md). Gallery reads land in US3.

`PUT /media/upload/raw` is a dev-only stand-in for the client's direct PUT to object
storage; in production the client uploads straight to the presigned OSS URL.
"""

from fastapi import APIRouter, HTTPException, Request, status

from ..deps import CurrentUser, DbDep, SettingsDep
from ..i18n import t
from ..schemas.media import (
    MediaOut,
    UploadConfirmRequest,
    UploadInitRequest,
    UploadInitResponse,
)
from ..services import media as media_service
from ..services.storage import get_storage

router = APIRouter(prefix="/api/v1/media", tags=["media"])


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
    """Dev-only: accept bytes for a pending media object and store them."""
    from sqlalchemy import select

    from ..models.media import STATUS_PENDING, Media

    result = await session.execute(
        select(Media).where(Media.storage_path == key, Media.uploader_id == user.id)
    )
    media = result.scalar_one_or_none()
    if media is None or media.status != STATUS_PENDING:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=t("media_not_found", user.language_preference))
    body = await request.body()
    get_storage().put(key, body)


@router.post("/upload/confirm", response_model=MediaOut)
async def upload_confirm(
    body: UploadConfirmRequest, user: CurrentUser, session: DbDep, settings: SettingsDep
) -> MediaOut:
    media = await media_service.confirm_upload(session, user, body.media_id, settings)
    await session.commit()
    await session.refresh(media)
    return MediaOut.model_validate(media)
