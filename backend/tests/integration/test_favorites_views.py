"""T049: favorites (toggle, list, uniqueness) + view increment (US4)."""

from tests.conftest import auth_headers, seed_media, seed_user


async def test_favorite_toggle_and_list(client):
    headers = await auth_headers(client, "Fan")
    media_id = await seed_media(await seed_user("FOwner"), filename="f.png")

    on = await client.post(f"/api/v1/media/{media_id}/favorites", headers=headers)
    assert on.json() == {"favorited": True, "favorite_count": 1}

    listed = await client.get("/api/v1/media/favorites", headers=headers)
    assert [m["id"] for m in listed.json()] == [media_id]

    off = await client.post(f"/api/v1/media/{media_id}/favorites", headers=headers)
    assert off.json() == {"favorited": False, "favorite_count": 0}

    listed2 = await client.get("/api/v1/media/favorites", headers=headers)
    assert listed2.json() == []


async def test_view_increments(client):
    headers = await auth_headers(client, "Viewer")
    media_id = await seed_media(await seed_user("VOwner"), filename="v.png")

    first = await client.post(f"/api/v1/media/{media_id}/view", headers=headers)
    second = await client.post(f"/api/v1/media/{media_id}/view", headers=headers)
    assert first.json()["view_count"] == 1
    assert second.json()["view_count"] == 2
