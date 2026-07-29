"""Social engagement service (US4 / FR-SOCIAL).

Enforces the invariants: at most one reaction per guest per item (toggle same type off,
switch type keeps count at one); own-or-admin comment deletion; unique favorites; view
counting. Denormalized counts on `media` are kept in sync here.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..i18n import t
from ..models.comment import Comment
from ..models.favorite import Favorite
from ..models.media import STATUS_READY, Media
from ..models.reaction import Reaction
from ..models.user import User
from ..services.media import get_visible_item


async def toggle_reaction(
    session: AsyncSession, user: User, media_id: int, reaction_type: str
) -> tuple[str | None, int]:
    media = await get_visible_item(session, media_id, user.language_preference)
    existing = (
        await session.execute(
            select(Reaction).where(Reaction.user_id == user.id, Reaction.media_id == media_id)
        )
    ).scalar_one_or_none()

    if existing is None:
        session.add(Reaction(user_id=user.id, media_id=media_id, reaction_type=reaction_type))
        media.reaction_count += 1
        current: str | None = reaction_type
    elif existing.reaction_type == reaction_type:
        await session.delete(existing)
        media.reaction_count = max(0, media.reaction_count - 1)
        current = None
    else:
        existing.reaction_type = reaction_type  # switch type; count unchanged
        current = reaction_type

    await session.flush()
    return current, media.reaction_count


async def add_comment(session: AsyncSession, user: User, media_id: int, content: str) -> Comment:
    media = await get_visible_item(session, media_id, user.language_preference)
    comment = Comment(user_id=user.id, media_id=media_id, content=content)
    session.add(comment)
    media.comment_count += 1
    await session.flush()
    return comment


async def list_comments(session: AsyncSession, media_id: int) -> list[tuple[Comment, str]]:
    rows = await session.execute(
        select(Comment, User.username)
        .join(User, User.id == Comment.user_id)
        .where(Comment.media_id == media_id, Comment.is_deleted.is_(False))
        .order_by(Comment.created_at.asc(), Comment.id.asc())
    )
    return list(rows.all())


async def delete_comment(
    session: AsyncSession, user: User, media_id: int, comment_id: int
) -> None:
    comment = await session.get(Comment, comment_id)
    if comment is None or comment.media_id != media_id or comment.is_deleted:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=t("media_not_found", user.language_preference)
        )
    if comment.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail=t("not_authenticated", user.language_preference)
        )
    comment.is_deleted = True
    media = await session.get(Media, media_id)
    if media is not None:
        media.comment_count = max(0, media.comment_count - 1)
    await session.flush()


async def toggle_favorite(session: AsyncSession, user: User, media_id: int) -> tuple[bool, int]:
    media = await get_visible_item(session, media_id, user.language_preference)
    existing = (
        await session.execute(
            select(Favorite).where(Favorite.user_id == user.id, Favorite.media_id == media_id)
        )
    ).scalar_one_or_none()

    if existing is None:
        session.add(Favorite(user_id=user.id, media_id=media_id))
        media.favorite_count += 1
        favorited = True
    else:
        await session.delete(existing)
        media.favorite_count = max(0, media.favorite_count - 1)
        favorited = False

    await session.flush()
    return favorited, media.favorite_count


async def list_favorites(session: AsyncSession, user: User) -> list[Media]:
    rows = await session.execute(
        select(Media)
        .join(Favorite, Favorite.media_id == Media.id)
        .where(
            Favorite.user_id == user.id,
            Media.status == STATUS_READY,
            Media.is_visible.is_(True),
        )
        .order_by(Favorite.created_at.desc())
    )
    return list(rows.scalars().all())


async def increment_view(session: AsyncSession, user: User, media_id: int) -> int:
    media = await get_visible_item(session, media_id, user.language_preference)
    media.view_count += 1
    await session.flush()
    return media.view_count
