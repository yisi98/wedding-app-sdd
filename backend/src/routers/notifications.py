"""Notifications router — activity feed + web push (US6 / contracts/notifications.md)."""

from fastapi import APIRouter, status

from ..deps import CurrentUser, DbDep, SettingsDep
from ..schemas.notifications import ActivityOut, PushSubscribeRequest, VapidKeyResponse
from ..services import activity as activity_service
from ..services import push_service

router = APIRouter(prefix="/api/v1", tags=["notifications"])


@router.get("/activity", response_model=list[ActivityOut])
async def get_activity(user: CurrentUser, session: DbDep) -> list[ActivityOut]:
    rows = await activity_service.list_recent(session)
    return [
        ActivityOut(
            id=e.id,
            event_type=e.event_type,
            user_id=e.user_id,
            username=username,
            media_id=e.media_id,
            payload=e.payload,
            created_at=e.created_at,
        )
        for e, username in rows
    ]


@router.post("/push/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def subscribe(body: PushSubscribeRequest, user: CurrentUser, session: DbDep) -> None:
    await push_service.subscribe(session, user, body.endpoint, body.p256dh, body.auth)
    await session.commit()


@router.delete("/push/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(body: PushSubscribeRequest, user: CurrentUser, session: DbDep) -> None:
    await push_service.unsubscribe(session, user, body.endpoint)
    await session.commit()


@router.get("/push/vapid-public-key", response_model=VapidKeyResponse)
async def vapid_public_key(settings: SettingsDep) -> VapidKeyResponse:
    return VapidKeyResponse(public_key=push_service.vapid_public_key(settings))
