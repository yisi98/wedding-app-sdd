"""Web-push (VAPID) service (US6 / FR-024).

Persists subscriptions and sends notifications via pywebpush (imported lazily so the
dependency is only needed when actually sending).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models.push_subscription import PushSubscription
from ..models.user import User


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


def send_push(subscription: PushSubscription, payload: dict, settings: Settings) -> bool:
    """Best-effort send via pywebpush; returns False if push isn't configured/available."""
    if not settings.vapid_private_key:
        return False
    try:
        from pywebpush import webpush  # imported lazily

        import json

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
