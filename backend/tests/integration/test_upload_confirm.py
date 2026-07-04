"""T032: POST /media/upload/confirm — enqueue/process, status transition (US2)."""

from tests.conftest import auth_headers, make_png, sha256_hex


async def _init_and_upload(client, headers, png) -> int:
    body = {
        "original_filename": "pic.png",
        "mime_type": "image/png",
        "file_size": len(png),
        "file_hash": sha256_hex(png),
    }
    init = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    assert init.status_code == 200
    key = init.json()["storage_key"]
    # Simulate the client's direct PUT to object storage.
    put = await client.put(f"/api/v1/media/upload/raw?key={key}", content=png, headers=headers)
    assert put.status_code == 204
    return init.json()["media_id"]


async def test_confirm_processes_to_ready(client):
    headers = await auth_headers(client)
    png = make_png(color=(120, 200, 80))
    media_id = await _init_and_upload(client, headers, png)

    r = await client.post(
        "/api/v1/media/upload/confirm", json={"media_id": media_id}, headers=headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["media_type"] == "image"


async def test_confirm_unknown_media_returns_404(client):
    headers = await auth_headers(client)
    r = await client.post(
        "/api/v1/media/upload/confirm", json={"media_id": 99999}, headers=headers
    )
    assert r.status_code == 404
