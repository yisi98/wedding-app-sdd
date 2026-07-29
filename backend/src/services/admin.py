"""Admin service (US8 / FR-ADMIN).

Dashboard stats, user management, media moderation, CSV export. Guard rail: an admin can
never modify or delete their own admin account (prevents self-lockout, FR-031).
"""

import csv
import io
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..i18n import t
from ..models.comment import Comment
from ..models.media import Media
from ..models.reaction import Reaction
from ..models.user import User


async def get_stats(session: AsyncSession) -> dict:
    total_media = await session.scalar(select(func.count(Media.id))) or 0
    total_users = await session.scalar(select(func.count(User.id))) or 0
    total_views = await session.scalar(select(func.coalesce(func.sum(Media.view_count), 0))) or 0
    total_reactions = await session.scalar(select(func.count(Reaction.id))) or 0
    total_comments = (
        await session.scalar(
            select(func.count(Comment.id)).where(Comment.is_deleted.is_(False))
        )
        or 0
    )
    storage_bytes = await session.scalar(select(func.coalesce(func.sum(Media.file_size), 0))) or 0

    by_type = {
        row[0]: row[1]
        for row in (
            await session.execute(
                select(Media.media_type, func.count(Media.id)).group_by(Media.media_type)
            )
        ).all()
    }
    by_status = {
        row[0]: row[1]
        for row in (
            await session.execute(
                select(Media.status, func.count(Media.id)).group_by(Media.status)
            )
        ).all()
    }

    week_ago = datetime.now(UTC) - timedelta(days=7)
    uploads_last_7 = (
        await session.scalar(select(func.count(Media.id)).where(Media.created_at >= week_ago)) or 0
    )

    top_rows = (
        await session.execute(
            select(Media.id, Media.original_filename, Media.view_count)
            .order_by(Media.view_count.desc())
            .limit(5)
        )
    ).all()
    top_by_views = [
        {"id": r[0], "filename": r[1], "view_count": r[2]} for r in top_rows
    ]

    return {
        "total_media": total_media,
        "total_users": total_users,
        "total_views": total_views,
        "total_reactions": total_reactions,
        "total_comments": total_comments,
        "storage_bytes": storage_bytes,
        "media_by_type": by_type,
        "media_by_status": by_status,
        "uploads_last_7_days": uploads_last_7,
        "top_by_views": top_by_views,
    }


async def list_users(
    session: AsyncSession, q: str | None, limit: int, offset: int
) -> tuple[list[User], bool]:
    stmt = select(User)
    if q:
        stmt = stmt.where(User.username.ilike(f"%{q}%"))
    stmt = stmt.order_by(User.id.asc()).limit(limit + 1).offset(offset)
    rows = list((await session.execute(stmt)).scalars().all())
    return rows[:limit], len(rows) > limit


def _guard_not_self(admin: User, user_id: int) -> None:
    if admin.id == user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=t("admin_required", admin.language_preference)
        )


async def _get_user(session: AsyncSession, admin: User, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=t("media_not_found", admin.language_preference)
        )
    return user


async def update_user(
    session: AsyncSession,
    admin: User,
    user_id: int,
    role: str | None,
    is_active: bool | None,
) -> User:
    _guard_not_self(admin, user_id)  # cannot modify own admin account
    user = await _get_user(session, admin, user_id)
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    await session.flush()
    return user


async def delete_user(session: AsyncSession, admin: User, user_id: int) -> None:
    _guard_not_self(admin, user_id)  # cannot delete own admin account
    user = await _get_user(session, admin, user_id)
    await session.delete(user)
    await session.flush()


async def list_all_media(session: AsyncSession, limit: int, offset: int) -> tuple[list[Media], bool]:
    stmt = select(Media).order_by(Media.created_at.desc()).limit(limit + 1).offset(offset)
    rows = list((await session.execute(stmt)).scalars().all())
    return rows[:limit], len(rows) > limit


async def set_visibility(
    session: AsyncSession, admin: User, media_id: int, is_visible: bool
) -> Media:
    media = await session.get(Media, media_id)
    if media is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=t("media_not_found", admin.language_preference)
        )
    media.is_visible = is_visible
    await session.flush()
    return media


async def export_media_csv(session: AsyncSession) -> str:
    rows = (await session.execute(select(Media).order_by(Media.id.asc()))).scalars().all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id", "filename", "original_filename", "media_type", "mime_type", "file_size",
            "status", "is_visible", "uploader_id", "view_count", "reaction_count",
            "comment_count", "favorite_count", "created_at",
        ]
    )
    for m in rows:
        writer.writerow(
            [
                m.id, m.filename, m.original_filename, m.media_type, m.mime_type, m.file_size,
                m.status, m.is_visible, m.uploader_id, m.view_count, m.reaction_count,
                m.comment_count, m.favorite_count, m.created_at.isoformat(),
            ]
        )
    return buffer.getvalue()
