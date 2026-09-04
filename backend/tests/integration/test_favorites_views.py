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


async def test_bulk_remove_favorites(client):
    headers = await auth_headers(client, "BulkFan")
    owner = await seed_user("BulkOwner")
    kept = await seed_media(owner, filename="kept.png")
    gone = await seed_media(owner, filename="gone.png")
    for mid in (kept, gone):
        await client.post(f"/api/v1/media/{mid}/favorites", headers=headers)

    # Remove one favorited item plus an id that was never favorited.
    r = await client.post(
        "/api/v1/media/favorites/bulk-remove",
        headers=headers,
        json={"media_ids": [gone, 999999]},
    )
    assert r.status_code == 200
    assert r.json() == {"removed": [gone], "skipped": [999999]}

    listed = await client.get("/api/v1/media/favorites", headers=headers)
    assert [m["id"] for m in listed.json()] == [kept]

    # Denormalized count on the removed item is decremented.
    detail = await client.get(f"/api/v1/media/{gone}", headers=headers)
    assert detail.json()["favorite_count"] == 0


async def test_bulk_remove_favorites_touches_only_caller(client):
    mine = await auth_headers(client, "MineFan")
    theirs = await auth_headers(client, "TheirFan")
    media_id = await seed_media(await seed_user("SharedOwner"), filename="shared.png")
    for h in (mine, theirs):
        await client.post(f"/api/v1/media/{media_id}/favorites", headers=h)

    r = await client.post(
        "/api/v1/media/favorites/bulk-remove", headers=mine, json={"media_ids": [media_id]}
    )
    assert r.json() == {"removed": [media_id], "skipped": []}

    # The other user's favorite is untouched; the item keeps a count of 1.
    listed = await client.get("/api/v1/media/favorites", headers=theirs)
    assert [m["id"] for m in listed.json()] == [media_id]
    detail = await client.get(f"/api/v1/media/{media_id}", headers=mine)
    assert detail.json()["favorite_count"] == 1


async def test_bulk_remove_favorites_requires_auth(client):
    r = await client.post("/api/v1/media/favorites/bulk-remove", json={"media_ids": [1]})
    assert r.status_code == 401
