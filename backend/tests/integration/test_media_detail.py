"""T041: GET /media/{id} (hidden → 404) and /media/{id}/similar (US3)."""

from tests.conftest import auth_headers, seed_media, seed_user


async def test_get_visible_item(client):
    headers = await auth_headers(client)
    uid = await seed_user("DetailAnna")
    media_id = await seed_media(uid, filename="shown.png")
    r = await client.get(f"/api/v1/media/{media_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["original_filename"] == "shown.png"


async def test_hidden_item_returns_404(client):
    headers = await auth_headers(client)
    uid = await seed_user("DetailBoris")
    media_id = await seed_media(uid, filename="secret.png", is_visible=False)
    r = await client.get(f"/api/v1/media/{media_id}", headers=headers)
    assert r.status_code == 404


async def test_similar_ranks_by_phash_distance(client):
    headers = await auth_headers(client)
    uid = await seed_user("DetailChen")
    target = await seed_media(uid, filename="target.png", phash="0000000000000000")
    near = await seed_media(uid, filename="near.png", phash="0000000000000001")  # distance 1
    await seed_media(uid, filename="far.png", phash="ffffffffffffffff")  # distance 64

    r = await client.get(f"/api/v1/media/{target}/similar", headers=headers)
    assert r.status_code == 200
    items = r.json()
    assert items[0]["id"] == near
