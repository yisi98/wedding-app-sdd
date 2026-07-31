"""Admin event config — archive mode and limits (FR-010)."""

from tests.conftest import admin_headers, auth_headers, make_png, sha256_hex


async def _try_upload(client, headers, name="party.png"):
    png = make_png(color=(1, 2, 3))
    return await client.post(
        "/api/v1/media/upload/init",
        json={
            "original_filename": name,
            "mime_type": "image/png",
            "file_size": len(png),
            "file_hash": sha256_hex(png),
        },
        headers=headers,
    )


async def test_get_config_returns_defaults(client):
    admin = await admin_headers(client)
    r = await client.get("/api/v1/admin/config", headers=admin)
    assert r.status_code == 200
    assert r.json()["uploads_enabled"] is True


async def test_archive_mode_blocks_then_restores_uploads(client):
    admin = await admin_headers(client)
    guest = await auth_headers(client, "ArchiveGuest")

    off = await client.patch(
        "/api/v1/admin/config", json={"uploads_enabled": False}, headers=admin
    )
    assert off.json()["uploads_enabled"] is False

    blocked = await _try_upload(client, guest)
    assert blocked.status_code == 403
    assert "closed" in blocked.json()["detail"].lower()

    await client.patch("/api/v1/admin/config", json={"uploads_enabled": True}, headers=admin)
    assert (await _try_upload(client, guest)).status_code == 200


async def test_patch_only_touches_supplied_fields(client):
    admin = await admin_headers(client)
    await client.patch(
        "/api/v1/admin/config", json={"event_name": "Yi & Sasha"}, headers=admin
    )
    r = await client.patch(
        "/api/v1/admin/config", json={"max_image_bytes": 1234}, headers=admin
    )
    body = r.json()
    assert body["max_image_bytes"] == 1234
    assert body["event_name"] == "Yi & Sasha"  # untouched by the second patch
    assert body["uploads_enabled"] is True


async def test_config_is_admin_only(client):
    guest = await auth_headers(client, "NosyGuest")
    assert (await client.get("/api/v1/admin/config", headers=guest)).status_code == 403
    assert (
        await client.patch(
            "/api/v1/admin/config", json={"uploads_enabled": False}, headers=guest
        )
    ).status_code == 403
