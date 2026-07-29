"""T061: web-push subscribe/unsubscribe + VAPID public key (US6)."""

from tests.conftest import auth_headers


def _sub() -> dict:
    return {"endpoint": "https://push.example.cn/abc", "p256dh": "key", "auth": "secret"}


async def test_subscribe_then_unsubscribe(client):
    headers = await auth_headers(client, "Subscriber")
    r = await client.post("/api/v1/push/subscribe", json=_sub(), headers=headers)
    assert r.status_code == 204
    # Re-subscribing the same endpoint is idempotent.
    r2 = await client.post("/api/v1/push/subscribe", json=_sub(), headers=headers)
    assert r2.status_code == 204

    d = await client.request("DELETE", "/api/v1/push/subscribe", json=_sub(), headers=headers)
    assert d.status_code == 204


async def test_vapid_public_key_endpoint(client):
    headers = await auth_headers(client, "KeyReader")
    r = await client.get("/api/v1/push/vapid-public-key", headers=headers)
    assert r.status_code == 200
    assert "public_key" in r.json()
