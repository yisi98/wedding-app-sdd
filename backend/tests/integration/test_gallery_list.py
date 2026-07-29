"""T040: GET /media — filters, sort, search, excludes hidden/non-ready (US3)."""

from tests.conftest import auth_headers, seed_media, seed_user


async def test_gallery_lists_only_ready_visible(client):
    headers = await auth_headers(client)
    anna = await seed_user("GalleryAnna")
    await seed_media(anna, filename="ready1.png")
    await seed_media(anna, filename="ready2.png")
    await seed_media(anna, filename="hidden.png", is_visible=False)
    await seed_media(anna, filename="pending.png", status="processing")

    r = await client.get("/api/v1/media", headers=headers)
    assert r.status_code == 200
    names = {m["original_filename"] for m in r.json()["items"]}
    assert "ready1.png" in names and "ready2.png" in names
    assert "hidden.png" not in names and "pending.png" not in names


async def test_gallery_filters_by_type_and_search(client):
    headers = await auth_headers(client)
    uid = await seed_user("GalleryBoris")
    await seed_media(uid, filename="beach.png", media_type="image")
    await seed_media(uid, filename="dance.mp4", media_type="video")

    images = await client.get("/api/v1/media?media_type=image", headers=headers)
    assert {m["original_filename"] for m in images.json()["items"]} == {"beach.png"}

    search = await client.get("/api/v1/media?q=dance", headers=headers)
    assert {m["original_filename"] for m in search.json()["items"]} == {"dance.mp4"}


async def test_gallery_sorts_by_most_viewed(client):
    headers = await auth_headers(client)
    uid = await seed_user("GalleryChen")
    await seed_media(uid, filename="low.png", view_count=1)
    await seed_media(uid, filename="high.png", view_count=99)

    r = await client.get("/api/v1/media?sort=most_viewed", headers=headers)
    items = r.json()["items"]
    assert items[0]["original_filename"] == "high.png"


async def test_gallery_requires_auth(client):
    r = await client.get("/api/v1/media")
    assert r.status_code == 401
