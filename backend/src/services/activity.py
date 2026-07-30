"""Activity service (US6 / FR-RT).

Records activity events and pushes them live to connected clients. Called from the media
and social services when notable actions occur.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models.activity_event import ActivityEvent
from ..models.user import User
from ..services import push_service
from ..services.websocket_manager import manager

logger = logging.getLogger("wmp.activity")

# Notification copy is English-only: a push is composed server-side for many recipients at
# once, and the payload carries no per-recipient language. The in-app feed is translated.
_PUSH_TITLES = {
    "new_upload": "New photo",
    "new_reaction": "New reaction",
    "new_comment": "New comment",
    "new_favorite": "New favourite",
}
_PUSH_BODIES = {
    "new_upload": "added something new",
    "new_reaction": "reacted to a photo",
    "new_comment": "left a comment",
    "new_favorite": "favourited a photo",
}


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
    message = {
        "event_type": event_type,
        "user": user.username,
        "media_id": media_id,
        "payload": payload,
    }
    await manager.publish(message)

    # Also reach guests who don't have the app open (FR-024). No-op when VAPID isn't
    # configured, and never allowed to fail the action that triggered it.
    try:
        await push_service.notify_subscribers(
            session,
            {
                "title": _PUSH_TITLES.get(event_type, "Our Wedding"),
                "body": f"{user.username} {_PUSH_BODIES.get(event_type, '')}".strip(),
                "event_type": event_type,
                "url": f"/gallery?media={media_id}" if media_id else "/gallery",
            },
            user,
            get_settings(),
        )
    except Exception:
        logger.warning("Push fan-out failed for %s", event_type, exc_info=True)

    return event


async def list_recent(session: AsyncSession, limit: int = 50) -> list[tuple[ActivityEvent, str]]:
    rows = await session.execute(
        select(ActivityEvent, User.username)
        .join(User, User.id == ActivityEvent.user_id)
        .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
        .limit(limit)
    )
    return list(rows.all())
