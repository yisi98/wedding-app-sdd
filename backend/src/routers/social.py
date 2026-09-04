"""Social router — reactions, comments, favorites, views (US4 / contracts/social.md).

Included BEFORE the media router so `GET /media/favorites` resolves before the
`GET /media/{media_id}` path-param route.
"""

from fastapi import APIRouter, status

from ..deps import CurrentUser, DbDep
from ..schemas.media import MediaOut
from ..schemas.social import (
    BulkFavoriteRemoveRequest,
    BulkFavoriteRemoveResponse,
    CommentCreate,
    CommentOut,
    FavoriteState,
    ReactionRequest,
    ReactionState,
)
from ..services import social as social_service

router = APIRouter(prefix="/api/v1/media", tags=["social"])


@router.get("/favorites", response_model=list[MediaOut])
async def list_favorites(user: CurrentUser, session: DbDep) -> list[MediaOut]:
    items = await social_service.list_favorites(session, user)
    return [MediaOut.model_validate(m) for m in items]


# Declared BEFORE any /{media_id} route so "bulk-remove" is never parsed as a media_id.
@router.post("/favorites/bulk-remove", response_model=BulkFavoriteRemoveResponse)
async def bulk_remove_favorites(
    body: BulkFavoriteRemoveRequest, user: CurrentUser, session: DbDep
) -> BulkFavoriteRemoveResponse:
    removed, skipped = await social_service.remove_favorites_bulk(session, user, body.media_ids)
    await session.commit()
    return BulkFavoriteRemoveResponse(removed=removed, skipped=skipped)


@router.post("/{media_id}/reactions", response_model=ReactionState)
async def react(
    media_id: int, body: ReactionRequest, user: CurrentUser, session: DbDep
) -> ReactionState:
    reaction_type, count = await social_service.toggle_reaction(
        session, user, media_id, body.reaction_type
    )
    await session.commit()
    return ReactionState(reaction_type=reaction_type, reaction_count=count)


@router.get("/{media_id}/comments", response_model=list[CommentOut])
async def get_comments(media_id: int, user: CurrentUser, session: DbDep) -> list[CommentOut]:
    rows = await social_service.list_comments(session, media_id)
    return [
        CommentOut(
            id=c.id,
            media_id=c.media_id,
            user_id=c.user_id,
            username=username,
            content=c.content,
            created_at=c.created_at,
        )
        for c, username in rows
    ]


@router.post("/{media_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def create_comment(
    media_id: int, body: CommentCreate, user: CurrentUser, session: DbDep
) -> CommentOut:
    comment = await social_service.add_comment(session, user, media_id, body.content)
    await session.commit()
    return CommentOut(
        id=comment.id,
        media_id=comment.media_id,
        user_id=comment.user_id,
        username=user.username,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.delete("/{media_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_comment(
    media_id: int, comment_id: int, user: CurrentUser, session: DbDep
) -> None:
    await social_service.delete_comment(session, user, media_id, comment_id)
    await session.commit()


@router.post("/{media_id}/favorites", response_model=FavoriteState)
async def favorite(media_id: int, user: CurrentUser, session: DbDep) -> FavoriteState:
    favorited, count = await social_service.toggle_favorite(session, user, media_id)
    await session.commit()
    return FavoriteState(favorited=favorited, favorite_count=count)


@router.post("/{media_id}/view")
async def add_view(media_id: int, user: CurrentUser, session: DbDep) -> dict:
    count = await social_service.increment_view(session, user, media_id)
    await session.commit()
    return {"view_count": count}
