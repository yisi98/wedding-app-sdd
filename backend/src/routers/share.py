"""Share router (US5 / contracts/share.md). Resolving a token needs no auth."""

from fastapi import APIRouter

from ..deps import CurrentUser, DbDep
from ..schemas.media import MediaOut
from ..schemas.share import ShareCreateRequest, ShareCreateResponse, ShareResolveResponse
from ..services import share as share_service

router = APIRouter(prefix="/api/v1/share", tags=["share"])


@router.post("", response_model=ShareCreateResponse)
async def create_share(
    body: ShareCreateRequest, user: CurrentUser, session: DbDep
) -> ShareCreateResponse:
    link = await share_service.create_share(session, user, body.media_id, body.expires_at)
    await session.commit()
    return ShareCreateResponse(
        token=link.token,
        url=f"/share/{link.token}",
        media_id=link.media_id,
        expires_at=link.expires_at,
    )


@router.get("/{token}", response_model=ShareResolveResponse)
async def resolve_share(token: str, session: DbDep) -> ShareResolveResponse:
    kind, link, media = await share_service.resolve_share(session, token)
    await session.commit()
    return ShareResolveResponse(
        type=kind,
        access_count=link.access_count,
        media=MediaOut.model_validate(media) if media is not None else None,
        expires_at=link.expires_at,
    )
