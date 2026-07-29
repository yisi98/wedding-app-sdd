"""Activity service (US6 / FR-RT).

Records activity events and pushes them live to connected clients. Called from the media
and social services when notable actions occur.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.activity_event import ActivityEvent
from ..models.user import User
from ..services.websocket_manager import manager


async def record(
    session: AsyncSession,
    event_type: str,
    user: User,
    media_id: int | None = None,
    payload: dict | None = None,
) -> ActivityEvent:
    payload = payload or {}
    event = ActivityEvent(
        event_type=event_type, user_id=user.id, media_id=media_id, payload=payload
    )
    session.add(event)
    await session.flush()
    await manager.publish(
        {
            "event_type": event_type,
            "user": user.username,
            "media_id": media_id,
            "payload": payload,
        }
    )
    return event


async def list_recent(session: AsyncSession, limit: int = 50) -> list[tuple[ActivityEvent, str]]:
    rows = await session.execute(
        select(ActivityEvent, User.username)
        .join(User, User.id == ActivityEvent.user_id)
        .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
        .limit(limit)
    )
    return list(rows.all())
