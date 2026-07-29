"""Regression tests for QA-identified bugs."""

from datetime import date

from tests.conftest import (
    TestSession,
    admin_headers,
    auth_headers,
    make_png,
    seed_media,
    seed_user,
    sha256_hex,
)

from src.models.event_config import SINGLETON_ID, EventConfig


async def _upload(client, headers, name="o.png", color=(3, 4, 5)):
    png = make_png(color=color)
    body = {
        "original_filename": name,
        "mime_type": "image/png",
        "file_size": len(png),
        "file_hash": sha256_hex(png),
    }
    init = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    key = init.json()["storage_key"]
    await client.put(f"/api/v1/media/upload/raw?key={key}", content=png, headers=headers)
    await client.post(
        "/api/v1/media/upload/confirm", json={"media_id": init.json()["media_id"]}, headers=headers
    )
    return key, png


# --- Media serving (the /media-object gap) ---


async def test_serve_original_and_thumbnail_objects(client):
    headers = await auth_headers(client, "Server")
    key, png = await _upload(client, headers)

    original = await client.get(f"/media-object/{key}")
    assert original.status_code == 200
    assert original.content == png
    assert original.headers["content-type"].startswith("image/")

    file_hash = key.split("/")[1]
    thumb = await client.get(f"/media-object/media/{file_hash}/thumb.jpg")
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/jpeg"


async def test_serve_unknown_object_404(client):
    r = await client.get("/media-object/media/nope/missing.png")
    assert r.status_code == 404


# --- Dedup race: unique-constraint hit must become 409, not 500 ---


async def test_dedup_race_returns_409(client, monkeypatch):
    headers = await auth_headers(client, "Racer")
    png = make_png(color=(9, 9, 9))
    file_hash = sha256_hex(png)
    await seed_media(await seed_user("RaceOwner"), file_hash=file_hash)

    # Simulate the pre-insert lookup missing the row (the race window).
    from src.services import deduplication

    async def _none(*args, **kwargs):
        return None

    monkeypatch.setattr(deduplication, "find_by_hash", _none)

    body = {
        "original_filename": "r.png",
        "mime_type": "image/png",
        "file_size": len(png),
        "file_hash": file_hash,
    }
    r = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    assert r.status_code == 409


# --- Upload size: server must validate ACTUAL bytes, not the declared size ---


async def test_raw_upload_rejects_oversize_actual_bytes(client):
    headers = await auth_headers(client, "Liar")
    async with TestSession() as session:
        config = await session.get(EventConfig, SINGLETON_ID)
        config.max_image_bytes = 10  # shrink the limit
        await session.commit()

    png = make_png()  # ~70 bytes, over the shrunk 10-byte limit
    body = {
        "original_filename": "x.png",
        "mime_type": "image/png",
        "file_size": 5,  # the client LIES: declares 5 bytes
        "file_hash": sha256_hex(png),
    }
    init = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    assert init.status_code == 200  # passes init on the (fake) declared size
    key = init.json()["storage_key"]

    raw = await client.put(f"/api/v1/media/upload/raw?key={key}", content=png, headers=headers)
    assert raw.status_code == 413  # actual bytes rejected


# --- Gallery date_to must be inclusive of the whole day ---


async def test_gallery_date_to_is_inclusive(client):
    headers = await auth_headers(client, "Dater")
    await seed_media(await seed_user("DateOwner"), filename="today.png")
    today = date.today().isoformat()
    r = await client.get(f"/api/v1/media?date_to={today}", headers=headers)
    assert any(m["original_filename"] == "today.png" for m in r.json()["items"])


# --- Deactivation must take effect immediately, even with a still-valid access token ---


async def test_deactivated_user_is_blocked_immediately(client):
    admin = await admin_headers(client)
    guest = await auth_headers(client, "WillBeGone")
    gid = (await client.get("/api/v1/auth/me", headers=guest)).json()["id"]

    await client.patch(f"/api/v1/admin/users/{gid}", json={"is_active": False}, headers=admin)

    # The guest's existing (unexpired) access token must now be rejected.
    assert (await client.get("/api/v1/auth/me", headers=guest)).status_code == 401
