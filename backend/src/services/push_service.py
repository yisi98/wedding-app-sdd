"""Web-push (VAPID) service (US6 / FR-024).

Persists subscriptions and sends notifications via pywebpush (imported lazily so the
dependency is only needed when actually sending).
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models.push_subscription import PushSubscription
from ..models.user import User

logger = logging.getLogger("wmp.push")


async def subscribe(
    session: AsyncSession, user: User, endpoint: str, p256dh: str, auth: str
) -> PushSubscription:
    existing = (
        await session.execute(
            select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.user_id, existing.p256dh, existing.auth = user.id, p256dh, auth
        await session.flush()
        return existing
    sub = PushSubscription(user_id=user.id, endpoint=endpoint, p256dh=p256dh, auth=auth)
    session.add(sub)
    await session.flush()
    return sub


async def unsubscribe(session: AsyncSession, user: User, endpoint: str) -> None:
    existing = (
        await session.execute(
            select(PushSubscription).where(
                PushSubscription.endpoint == endpoint, PushSubscription.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        await session.delete(existing)
        await session.flush()


def vapid_public_key(settings: Settings) -> str | None:
    return settings.vapid_public_key


async def notify_subscribers(
    session: AsyncSession, payload: dict, actor: User, settings: Settings
) -> int:
    """Fan a notification out to every subscriber except the person who caused it.

    Web push is what reaches guests who don't have the app open — the WebSocket only
    covers currently-connected clients (FR-024 vs FR-022). Delivery is best-effort and
    never allowed to fail the request that triggered it; pywebpush is blocking, so each
    send runs off the event loop.
    """
    if not settings.vapid_private_key:
        return 0
    subs = (
        (
            await session.execute(
                select(PushSubscription).where(PushSubscription.user_id != actor.id)
            )
        )
        .scalars()
        .all()
    )
    sent = 0
    for sub in subs:
        try:
            if await asyncio.to_thread(send_push, sub, payload, settings):
                sent += 1
        except Exception:
            logger.warning("Push send failed for subscription %s", sub.id, exc_info=True)
    return sent


def send_push(subscription: PushSubscription, payload: dict, settings: Settings) -> bool:
    """Best-effort send via pywebpush; returns False if push isn't configured/available."""
    if not settings.vapid_private_key:
        return False
    try:
        import json

        from pywebpush import webpush  # imported lazily

        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
        )
        return True
    except Exception:  # noqa: BLE001 — delivery is best-effort
        return False
