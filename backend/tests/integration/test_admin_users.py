"""T074: admin user management — list/search, promote, deactivate, self-guard (US8)."""

from tests.conftest import admin_headers, seed_media, seed_user


async def _me_id(client, headers) -> int:
    return (await client.get("/api/v1/auth/me", headers=headers)).json()["id"]


async def test_list_and_search_users(client):
    headers = await admin_headers(client)
    await seed_user("Alice")
    await seed_user("Alfred")
    await seed_user("Bob")

    r = await client.get("/api/v1/admin/users?q=Al", headers=headers)
    names = {u["username"] for u in r.json()["items"]}
    assert names == {"Alice", "Alfred"}


async def test_promote_and_deactivate(client):
    headers = await admin_headers(client)
    uid = await seed_user("Promotable")

    promoted = await client.patch(
        f"/api/v1/admin/users/{uid}", json={"role": "admin"}, headers=headers
    )
    assert promoted.json()["role"] == "admin"

    deactivated = await client.patch(
        f"/api/v1/admin/users/{uid}", json={"is_active": False}, headers=headers
    )
    assert deactivated.json()["is_active"] is False


async def test_cannot_modify_or_delete_own_account(client):
    headers = await admin_headers(client)
    my_id = await _me_id(client, headers)

    patched = await client.patch(
        f"/api/v1/admin/users/{my_id}", json={"is_active": False}, headers=headers
    )
    assert patched.status_code == 400

    deleted = await client.delete(f"/api/v1/admin/users/{my_id}", headers=headers)
    assert deleted.status_code == 400


async def test_delete_other_user(client):
    headers = await admin_headers(client)
    uid = await seed_user("Deletable")
    r = await client.delete(f"/api/v1/admin/users/{uid}", headers=headers)
    assert r.status_code == 204


async def test_delete_user_with_uploads_keeps_their_media(client):
    headers = await admin_headers(client)
    uid = await seed_user("Uploader")
    media_id = await seed_media(uid)

    r = await client.delete(f"/api/v1/admin/users/{uid}", headers=headers)
    assert r.status_code == 204

    media = await client.get(f"/api/v1/media/{media_id}", headers=headers)
    assert media.status_code == 200
    assert media.json()["uploader_id"] is None
    assert media.json()["uploader_name"] is None
