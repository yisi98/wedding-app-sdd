"""T081: POST /downloads/bulk — ZIP contents, excludes hidden (US9)."""

import io
import zipfile

from tests.conftest import auth_headers, make_png, seed_media, seed_user, sha256_hex


async def _upload_ready(client, headers, name, color) -> int:
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
    return init.json()["media_id"]


async def test_bulk_download_returns_zip_of_selected(client):
    headers = await auth_headers(client, "Downloader")
    id1 = await _upload_ready(client, headers, "one.png", (10, 10, 10))
    id2 = await _upload_ready(client, headers, "two.png", (250, 120, 40))
    hidden = await seed_media(await seed_user("HidOwner"), filename="secret.png", is_visible=False)

    r = await client.post(
        "/api/v1/downloads/bulk", json={"media_ids": [id1, id2, hidden]}, headers=headers
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"

    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert len(names) == 2  # hidden item excluded
    assert any(n.endswith("one.png") for n in names)
    assert any(n.endswith("two.png") for n in names)
