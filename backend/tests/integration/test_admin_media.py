"""T075: admin media moderation (list incl. hidden, visibility, guest 404) + CSV (US8)."""

from tests.conftest import admin_headers, auth_headers, seed_media, seed_user


async def test_admin_media_includes_hidden_and_toggles_visibility(client):
    admin = await admin_headers(client)
    guest = await auth_headers(client, "GuestViewer")
    uid = await seed_user("ModOwner")
    hidden_id = await seed_media(uid, filename="hidden.png", is_visible=False)

    # Admin list includes hidden.
    admin_list = await client.get("/api/v1/admin/media", headers=admin)
    assert hidden_id in {m["id"] for m in admin_list.json()}

    # Guest cannot see it.
    assert (await client.get(f"/api/v1/media/{hidden_id}", headers=guest)).status_code == 404

    # Admin makes it visible; guest can now see it.
    shown = await client.patch(
        f"/api/v1/admin/media/{hidden_id}/visibility", json={"is_visible": True}, headers=admin
    )
    assert shown.json()["is_visible"] is True
    assert (await client.get(f"/api/v1/media/{hidden_id}", headers=guest)).status_code == 200


async def test_export_media_csv(client):
    admin = await admin_headers(client)
    uid = await seed_user("CsvOwner")
    await seed_media(uid, filename="export_me.png")

    r = await client.get("/api/v1/admin/export/media", headers=admin)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "export_me.png" in r.text
    assert "email" not in r.text.splitlines()[0]  # no email column
