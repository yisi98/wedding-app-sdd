"""T031: POST /media/upload/init — validation, size limits, duplicate, uploads-paused (US2)."""

from src.models.event_config import SINGLETON_ID, EventConfig
from tests.conftest import TestSession, auth_headers, make_png, sha256_hex


def _init_body(data: bytes, mime="image/png", name="pic.png", size=None) -> dict:
    return {
        "original_filename": name,
        "mime_type": mime,
        "file_size": size if size is not None else len(data),
        "file_hash": sha256_hex(data),
    }


async def test_init_accepts_valid_image(client):
    headers = await auth_headers(client)
    png = make_png()
    r = await client.post("/api/v1/media/upload/init", json=_init_body(png), headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["media_id"] and body["upload_url"]
    assert body["storage_key"].startswith("media/")
    assert body["status"] == "pending"


async def test_init_rejects_disallowed_type(client):
    headers = await auth_headers(client)
    png = make_png()
    body = _init_body(png, mime="application/pdf", name="doc.pdf")
    r = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    assert r.status_code == 400


async def test_init_rejects_oversize_image(client):
    headers = await auth_headers(client)
    png = make_png()
    body = _init_body(png, size=60 * 1024 * 1024)  # over the 50 MB image limit
    r = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    assert r.status_code == 413


async def test_init_deduplicates_identical_content(client):
    headers = await auth_headers(client)
    png = make_png(color=(10, 20, 30))
    first = await client.post("/api/v1/media/upload/init", json=_init_body(png), headers=headers)
    assert first.status_code == 200
    dupe = await client.post("/api/v1/media/upload/init", json=_init_body(png), headers=headers)
    assert dupe.status_code == 409
    assert dupe.json()["detail"]["media_id"] == first.json()["media_id"]


async def test_init_blocked_when_uploads_paused(client):
    headers = await auth_headers(client)
    async with TestSession() as session:
        config = await session.get(EventConfig, SINGLETON_ID)
        config.uploads_enabled = False
        await session.commit()

    png = make_png(color=(1, 2, 3))
    r = await client.post("/api/v1/media/upload/init", json=_init_body(png), headers=headers)
    assert r.status_code == 403
