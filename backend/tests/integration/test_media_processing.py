"""T033: background processing outputs — derivations + end-to-end ready (US2 / FR-009)."""

from src.workers.media_processing import process_image
from tests.conftest import auth_headers, make_png, sha256_hex


def test_process_image_produces_derivations():
    png = make_png(width=64, height=48, color=(30, 60, 90))
    d = process_image(png)
    assert d.width == 64 and d.height == 48
    assert d.thumbnail and d.optimized
    assert d.lqip.startswith("data:image/jpeg;base64,")
    assert len(d.phash) == 16  # 8x8 dHash → 16 hex chars


async def test_end_to_end_upload_becomes_ready_with_derivations(client):
    headers = await auth_headers(client)
    png = make_png(width=50, height=40, color=(200, 30, 30))
    body = {
        "original_filename": "photo.png",
        "mime_type": "image/png",
        "file_size": len(png),
        "file_hash": sha256_hex(png),
    }
    init = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    key = init.json()["storage_key"]
    await client.put(f"/api/v1/media/upload/raw?key={key}", content=png, headers=headers)
    confirm = await client.post(
        "/api/v1/media/upload/confirm", json={"media_id": init.json()["media_id"]}, headers=headers
    )
    media = confirm.json()
    assert media["status"] == "ready"
    assert media["width"] == 50 and media["height"] == 40
    assert media["lqip"].startswith("data:image/jpeg;base64,")
    assert media["thumbnail_path"] and media["optimized_path"]
