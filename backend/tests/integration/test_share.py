"""T055: POST /share + GET /share/{token} — access count, expiry, hidden safety (US5)."""

from datetime import datetime, timedelta, timezone

from tests.conftest import TestSession, auth_headers, seed_media, seed_user

from src.models.media import Media


async def test_gallery_share_resolves_and_counts_access(client):
    headers = await auth_headers(client, "Sharer")
    created = await client.post("/api/v1/share", json={}, headers=headers)
    assert created.status_code == 200
    token = created.json()["token"]
    assert created.json()["media_id"] is None

    r1 = await client.get(f"/api/v1/share/{token}")
    assert r1.status_code == 200
    assert r1.json()["type"] == "gallery"
    assert r1.json()["access_count"] == 1

    r2 = await client.get(f"/api/v1/share/{token}")
    assert r2.json()["access_count"] == 2


async def test_item_share_returns_media(client):
    headers = await auth_headers(client, "Sharer2")
    media_id = await seed_media(await seed_user("ShareOwner"), filename="s.png")
    token = (
        await client.post("/api/v1/share", json={"media_id": media_id}, headers=headers)
    ).json()["token"]

    r = await client.get(f"/api/v1/share/{token}")
    assert r.json()["type"] == "item"
    assert r.json()["media"]["id"] == media_id


async def test_expired_link_denied(client):
    headers = await auth_headers(client, "Sharer3")
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    token = (
        await client.post("/api/v1/share", json={"expires_at": past}, headers=headers)
    ).json()["token"]

    r = await client.get(f"/api/v1/share/{token}")
    assert r.status_code == 410


async def test_unknown_token_404(client):
    r = await client.get("/api/v1/share/does-not-exist")
    assert r.status_code == 404


async def test_share_hides_now_hidden_item(client):
    headers = await auth_headers(client, "Sharer4")
    media_id = await seed_media(await seed_user("ShareOwner2"), filename="s2.png")
    token = (
        await client.post("/api/v1/share", json={"media_id": media_id}, headers=headers)
    ).json()["token"]

    # Admin later hides the item.
    async with TestSession() as session:
        media = await session.get(Media, media_id)
        media.is_visible = False
        await session.commit()

    r = await client.get(f"/api/v1/share/{token}")
    assert r.status_code == 404
