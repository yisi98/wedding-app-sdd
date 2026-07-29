"""T048: comments — add, list, own vs admin soft-delete (US4)."""

from tests.conftest import auth_headers, login, seed_media, seed_user


async def test_add_and_list_comment(client):
    headers = await auth_headers(client, "Commenter")
    media_id = await seed_media(await seed_user("COwner"), filename="c.png")

    created = await client.post(
        f"/api/v1/media/{media_id}/comments", json={"content": "Lovely!"}, headers=headers
    )
    assert created.status_code == 201
    assert created.json()["content"] == "Lovely!"
    assert created.json()["username"] == "Commenter"

    listed = await client.get(f"/api/v1/media/{media_id}/comments", headers=headers)
    assert [c["content"] for c in listed.json()] == ["Lovely!"]


async def test_author_can_delete_own_comment(client):
    headers = await auth_headers(client, "Author")
    media_id = await seed_media(await seed_user("COwner2"), filename="c2.png")
    cid = (
        await client.post(
            f"/api/v1/media/{media_id}/comments", json={"content": "mine"}, headers=headers
        )
    ).json()["id"]

    d = await client.delete(f"/api/v1/media/{media_id}/comments/{cid}", headers=headers)
    assert d.status_code == 204
    listed = await client.get(f"/api/v1/media/{media_id}/comments", headers=headers)
    assert listed.json() == []


async def test_non_author_non_admin_cannot_delete(client):
    author = await auth_headers(client, "Author2")
    media_id = await seed_media(await seed_user("COwner3"), filename="c3.png")
    cid = (
        await client.post(
            f"/api/v1/media/{media_id}/comments", json={"content": "hands off"}, headers=author
        )
    ).json()["id"]

    other = await auth_headers(client, "Stranger")
    d = await client.delete(f"/api/v1/media/{media_id}/comments/{cid}", headers=other)
    assert d.status_code == 403


async def test_admin_can_delete_any_comment(client):
    author = await auth_headers(client, "Author3")
    media_id = await seed_media(await seed_user("COwner4"), filename="c4.png")
    cid = (
        await client.post(
            f"/api/v1/media/{media_id}/comments", json={"content": "moderate me"}, headers=author
        )
    ).json()["id"]

    # Promote a user to admin via seed, then log in as them.
    await seed_user("BossAdmin", role="admin")
    token = (await login(client, "BossAdmin")).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {token}"}
    d = await client.delete(f"/api/v1/media/{media_id}/comments/{cid}", headers=admin_headers)
    assert d.status_code == 204
