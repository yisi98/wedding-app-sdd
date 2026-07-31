"""Web push fan-out (FR-024): stored subscriptions must actually be sent to."""

from src.config import Settings
from src.models.user import User
from src.services import push_service
from tests.conftest import TestSession, auth_headers, make_png, seed_user, sha256_hex


async def _subscribe(client, headers, endpoint):
    return await client.post(
        "/api/v1/push/subscribe",
        json={"endpoint": endpoint, "p256dh": "key", "auth": "auth"},
        headers=headers,
    )


async def test_subscribe_then_unsubscribe(client):
    headers = await auth_headers(client, "PushGuest")
    assert (await _subscribe(client, headers, "https://push.test/a")).status_code == 204
    r = await client.request(
        "DELETE",
        "/api/v1/push/subscribe",
        json={"endpoint": "https://push.test/a", "p256dh": "", "auth": ""},
        headers=headers,
    )
    assert r.status_code == 204


async def test_fanout_skips_the_actor_and_targets_everyone_else(monkeypatch):
    """The person who caused the event should not be pushed about their own action."""
    actor_id = await seed_user("Actor")
    other_id = await seed_user("Other")

    async with TestSession() as session:
        from src.models.push_subscription import PushSubscription

        session.add(PushSubscription(user_id=actor_id, endpoint="e/actor", p256dh="k", auth="a"))
        session.add(PushSubscription(user_id=other_id, endpoint="e/other", p256dh="k", auth="a"))
        await session.commit()

        sent_to = []
        monkeypatch.setattr(
            push_service, "send_push", lambda sub, payload, settings: sent_to.append(sub.endpoint) or True
        )
        settings = Settings(vapid_private_key="x", vapid_public_key="y")
        actor = await session.get(User, actor_id)

        count = await push_service.notify_subscribers(
            session, {"title": "t", "body": "b"}, actor, settings
        )

    assert sent_to == ["e/other"], sent_to
    assert count == 1


async def test_fanout_is_a_noop_without_vapid(monkeypatch):
    uid = await seed_user("NoVapid")
    async with TestSession() as session:
        from src.models.push_subscription import PushSubscription

        session.add(PushSubscription(user_id=uid, endpoint="e/x", p256dh="k", auth="a"))
        await session.commit()
        called = []
        monkeypatch.setattr(push_service, "send_push", lambda *a: called.append(1) or True)
        other = await session.get(User, uid)
        # Settings with no private key: nothing should be attempted.
        assert await push_service.notify_subscribers(session, {}, other, Settings()) == 0
        assert called == []


async def test_upload_triggers_a_push_to_other_guests(client, monkeypatch):
    """End-to-end: confirming an upload fans out to a subscriber who isn't the uploader."""
    watcher = await auth_headers(client, "Watcher")
    await _subscribe(client, watcher, "https://push.test/watcher")

    payloads = []
    monkeypatch.setattr(
        push_service,
        "send_push",
        lambda sub, payload, settings: payloads.append((sub.endpoint, payload)) or True,
    )
    monkeypatch.setattr(
        "src.services.activity.get_settings",
        lambda: Settings(vapid_private_key="x", vapid_public_key="y"),
    )

    uploader = await auth_headers(client, "Uploader2")
    png = make_png(color=(3, 5, 7))
    body = {
        "original_filename": "pushme.png",
        "mime_type": "image/png",
        "file_size": len(png),
        "file_hash": sha256_hex(png),
    }
    init = await client.post("/api/v1/media/upload/init", json=body, headers=uploader)
    key = init.json()["storage_key"]
    await client.put(f"/api/v1/media/upload/raw?key={key}", content=png, headers=uploader)
    await client.post(
        "/api/v1/media/upload/confirm", json={"media_id": init.json()["media_id"]}, headers=uploader
    )

    assert [e for e, _ in payloads] == ["https://push.test/watcher"], payloads
    assert payloads[0][1]["event_type"] == "new_upload"
    assert "Uploader2" in payloads[0][1]["body"]
