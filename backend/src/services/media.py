"""Media service — upload init/confirm (US2). Gallery reads are added with US3.

Upload is the 2-step presigned flow (ADR-003): init validates type/size, enforces the
uploads switch, and deduplicates by SHA-256; the client then PUTs bytes to storage; confirm
enqueues background processing (eager in dev/test, Celery in prod).
"""

import re
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..i18n import t
from ..models.event_config import SINGLETON_ID, EventConfig
from ..models.media import (
    MEDIA_IMAGE,
    MEDIA_VIDEO,
    STATUS_PENDING,
    STATUS_PROCESSING,
    STATUS_READY,
    Media,
)
from ..models.user import User
from ..schemas.media import UploadInitRequest
from ..services import deduplication
from ..services.storage import get_storage
from ..workers.media_processing import process_media

SORT_COLUMNS = {
    "newest": desc(Media.created_at),
    "oldest": asc(Media.created_at),
    "most_viewed": desc(Media.view_count),
    "most_liked": desc(Media.reaction_count),
}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _media_type_for(mime_type: str, settings: Settings) -> str | None:
    if mime_type in settings.allowed_image_types:
        return MEDIA_IMAGE
    if mime_type in settings.allowed_video_types:
        return MEDIA_VIDEO
    return None


def _safe_filename(name: str) -> str:
    cleaned = _SAFE_NAME.sub("_", name).strip("._") or "file"
    return cleaned[:120]


async def init_upload(
    session: AsyncSession, user: User, body: UploadInitRequest, settings: Settings
) -> tuple[Media, str]:
    lang = user.language_preference
    config = await session.get(EventConfig, SINGLETON_ID)
    if config is not None and not config.uploads_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=t("uploads_closed", lang))

    media_type = _media_type_for(body.mime_type, settings)
    if media_type is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=t("invalid_file_type", lang))

    max_bytes = (
        (config.max_image_bytes if config else 50 * 1024 * 1024)
        if media_type == MEDIA_IMAGE
        else (config.max_video_bytes if config else 500 * 1024 * 1024)
    )
    if body.file_size > max_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail=t("file_too_large", lang))

    existing = await deduplication.find_by_hash(session, body.file_hash)
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"message": t("duplicate_media", lang), "media_id": existing.id},
        )

    filename = _safe_filename(body.original_filename)
    storage_key = f"media/{body.file_hash}/{filename}"
    media = Media(
        uploader_id=user.id,
        filename=filename,
        original_filename=body.original_filename,
        file_hash=body.file_hash,
        file_size=body.file_size,
        mime_type=body.mime_type,
        media_type=media_type,
        storage_path=storage_key,
        status=STATUS_PENDING,
    )
    session.add(media)
    try:
        await session.flush()
    except IntegrityError:
        # Concurrent identical upload won the file_hash unique constraint first.
        await session.rollback()
        existing = await deduplication.find_by_hash(session, body.file_hash)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "message": t("duplicate_media", lang),
                "media_id": existing.id if existing else None,
            },
        )
    upload_url = get_storage().presigned_put_url(storage_key)
    return media, upload_url


async def get_owned_pending(session: AsyncSession, user: User, media_id: int) -> Media:
    media = await session.get(Media, media_id)
    if media is None or media.uploader_id != user.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=t("media_not_found", user.language_preference)
        )
    return media


async def confirm_upload(
    session: AsyncSession, user: User, media_id: int, settings: Settings
) -> Media:
    media = await get_owned_pending(session, user, media_id)
    media.status = STATUS_PROCESSING
    await session.flush()

    if settings.redis_url:
        # Production: hand off to the Celery worker (imported lazily).
        from ..workers.celery_app import celery_app

        celery_app.send_task("process_media", args=[media.id])
    else:
        # Dev/test: process inline (eager).
        await process_media(session, media)

    if media.status == STATUS_READY:
        from ..models.activity_event import EVENT_NEW_UPLOAD
        from ..services import activity as activity_service

        await activity_service.record(session, EVENT_NEW_UPLOAD, user, media.id)
    return media


# --- US3: Gallery & discovery -------------------------------------------------

async def list_gallery(
    session: AsyncSession,
    *,
    media_type: str | None = None,
    uploader: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    sort: str = "newest",
    limit: int = 24,
    offset: int = 0,
) -> tuple[list[Media], bool]:
    """Ready + visible media only (FR-015). Returns (items, has_more)."""
    stmt = select(Media).where(Media.status == STATUS_READY, Media.is_visible.is_(True))
    if media_type:
        stmt = stmt.where(Media.media_type == media_type)
    if uploader:
        stmt = stmt.join(User, User.id == Media.uploader_id).where(User.username == uploader)
    if date_from:
        stmt = stmt.where(Media.created_at >= date_from)
    if date_to:
        # Inclusive of the whole `date_to` day (created_at is a timestamp).
        stmt = stmt.where(Media.created_at < date_to + timedelta(days=1))
    if q:
        stmt = stmt.where(Media.original_filename.ilike(f"%{q}%"))

    stmt = stmt.order_by(SORT_COLUMNS.get(sort, SORT_COLUMNS["newest"]), desc(Media.id))
    stmt = stmt.limit(limit + 1).offset(offset)
    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    return rows[:limit], has_more


async def list_uploaders(session: AsyncSession) -> list[str]:
    """Distinct usernames with at least one ready + visible upload, for the gallery filter."""
    stmt = (
        select(User.username)
        .join(Media, Media.uploader_id == User.id)
        .where(Media.status == STATUS_READY, Media.is_visible.is_(True))
        .distinct()
        .order_by(User.username)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_visible_item(session: AsyncSession, media_id: int, lang: str = "en") -> Media:
    """A single ready + visible item; hidden or non-ready → 404 (FR-015)."""
    media = await session.get(Media, media_id)
    if media is None or not media.is_visible or media.status != STATUS_READY:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=t("media_not_found", lang))
    return media


def _hamming(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


async def find_similar(
    session: AsyncSession, media_id: int, lang: str = "en", limit: int = 6
) -> list[Media]:
    """Visually similar items ranked by dHash Hamming distance (FR-014)."""
    target = await get_visible_item(session, media_id, lang)
    if not target.phash:
        return []
    stmt = select(Media).where(
        Media.status == STATUS_READY,
        Media.is_visible.is_(True),
        Media.id != media_id,
        Media.phash.is_not(None),
    )
    candidates = list((await session.execute(stmt)).scalars().all())
    candidates.sort(key=lambda m: _hamming(target.phash, m.phash))
    return candidates[:limit]
