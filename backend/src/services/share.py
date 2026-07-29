"""Sharing service (US5 / FR-SHARE).

Creates opaque share tokens for the gallery or a single item; resolving a token increments
its access count and enforces expiry. A share never exposes a media item that has since
become hidden, non-ready, or deleted.
"""

import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..i18n import t
from ..models.media import STATUS_READY, Media
from ..models.share_link import ShareLink
from ..models.user import User
from ..services.media import get_visible_item


async def create_share(
    session: AsyncSession,
    user: User,
    media_id: int | None,
    expires_at: datetime | None,
) -> ShareLink:
    if media_id is not None:
        # Validate the target exists and is currently shareable.
        await get_visible_item(session, media_id, user.language_preference)
    link = ShareLink(
        token=secrets.token_urlsafe(24),
        media_id=media_id,
        created_by_id=user.id,
        expires_at=expires_at,
    )
    session.add(link)
    await session.flush()
    return link


async def resolve_share(session: AsyncSession, token: str) -> tuple[str, ShareLink, Media | None]:
    link = (
        await session.execute(select(ShareLink).where(ShareLink.token == token))
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=t("media_not_found"))

    if link.expires_at is not None:
        expires = link.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_410_GONE, detail=t("media_not_found"))

    link.access_count += 1
    await session.flush()

    if link.media_id is None:
        return "gallery", link, None

    media = await session.get(Media, link.media_id)
    if media is None or not media.is_visible or media.status != STATUS_READY:
        # Link is valid but its target is no longer available; do not expose it.
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=t("media_not_found"))
    return "item", link, media
