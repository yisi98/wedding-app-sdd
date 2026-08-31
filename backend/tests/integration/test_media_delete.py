"""Guest self-service deletion of own uploads (FR-039): owner-only, cascades, dedup reset."""

from src.models.media import Media
from src.services.storage import get_storage
from tests.conftest import TestSession, auth_headers, seed_media, seed_user


async def test_owner_deletes_own_media(client):
    uid = await seed_user("DelAnna")
    headers = await auth_headers(client, "DelAnna")
    media_id = await seed_media(uid, filename="mine.png")

    r = await client.delete(f"/api/v1/media/{media_id}", headers=headers)
    assert r.status_code == 204

    # Gone from reads too, not just the delete route.
    r = await client.get(f"/api/v1/media/{media_id}", headers=headers)
    assert r.status_code == 404


async def test_cannot_delete_another_users_media(client):
    headers = await auth_headers(client, "DelAnna")
    other = await seed_user("DelMallory")
    media_id = await seed_media(other, filename="yours.png")

    # 404, not 403: another guest's item is indistinguishable from a missing id.
    r = await client.delete(f"/api/v1/media/{media_id}", headers=headers)
    assert r.status_code == 404

    async with TestSession() as s:
        assert await s.get(Media, media_id) is not None  # still there


async def test_delete_requires_auth(client):
    r = await client.delete("/api/v1/media/1")
    assert r.status_code == 401


async def test_delete_removes_stored_objects(client):
    uid = await seed_user("DelBoris")
    headers = await auth_headers(client, "DelBoris")
    media_id = await seed_media(uid, filename="stored.png", file_hash="a" * 64)

    storage = get_storage()
    async with TestSession() as s:
        media = await s.get(Media, media_id)
        keys = [media.storage_path, media.thumbnail_path, media.optimized_path]
    for key in keys:
        if key:
            storage.put(key, b"bytes")

    r = await client.delete(f"/api/v1/media/{media_id}", headers=headers)
    assert r.status_code == 204

    for key in keys:
        if key:
            assert not storage.exists(key)


async def test_delete_cascades_favorites_and_comments(client):
    owner = await seed_user("DelChen")
    owner_headers = await auth_headers(client, "DelChen")
    other_headers = await auth_headers(client, "DelDora")
    media_id = await seed_media(owner, filename="social.png")

    # Another guest engages with the item before the owner deletes it.
    await client.post(f"/api/v1/media/{media_id}/favorites", headers=other_headers)
    await client.post(
        f"/api/v1/media/{media_id}/comments", headers=other_headers, json={"content": "sweet"}
    )

    r = await client.delete(f"/api/v1/media/{media_id}", headers=owner_headers)
    assert r.status_code == 204

    # The favoriting guest's favorites list stays consistent (no dangling rows).
    r = await client.get("/api/v1/media/favorites", headers=other_headers)
    assert r.status_code == 200
    assert r.json() == []


async def test_deleted_hash_can_be_reuploaded(client):
    """Dedup is by file_hash with a unique constraint — deletion must free the hash."""
    uid = await seed_user("DelEve")
    headers = await auth_headers(client, "DelEve")
    file_hash = "b" * 64
    media_id = await seed_media(uid, filename="again.png", file_hash=file_hash)

    r = await client.delete(f"/api/v1/media/{media_id}", headers=headers)
    assert r.status_code == 204

    body = {
        "original_filename": "again.png",
        "mime_type": "image/png",
        "file_size": 100,
        "file_hash": file_hash,
    }
    r = await client.post("/api/v1/media/upload/init", headers=headers, json=body)
    assert r.status_code == 200  # no 409 duplicate_media


# --- Multi-select bulk delete ---------------------------------------------------------


async def test_bulk_delete_own_items(client):
    uid = await seed_user("DelBulk")
    headers = await auth_headers(client, "DelBulk")
    ids = [
        await seed_media(uid, filename=f"bulk{i}.png", file_hash=f"c{i}" * 32)
        for i in range(3)
    ]

    r = await client.post("/api/v1/media/bulk-delete", headers=headers, json={"media_ids": ids})
    assert r.status_code == 200
    assert sorted(r.json()["deleted"]) == sorted(ids)
    assert r.json()["skipped"] == []

    async with TestSession() as s:
        for media_id in ids:
            assert await s.get(Media, media_id) is None


async def test_bulk_delete_mixed_selection_deletes_own_skips_others(client):
    """The whole batch is submitted at once: own items go, other guests' stay."""
    uid = await seed_user("DelMixed")
    headers = await auth_headers(client, "DelMixed")
    other = await seed_user("DelOther")
    own_ids = [
        await seed_media(uid, filename=f"mine{i}.png", file_hash=f"d{i}" * 32)
        for i in range(2)
    ]
    foreign_ids = [
        await seed_media(other, filename=f"theirs{i}.png", file_hash=f"e{i}" * 32)
        for i in range(2)
    ]

    r = await client.post(
        "/api/v1/media/bulk-delete",
        headers=headers,
        json={"media_ids": own_ids + foreign_ids},
    )
    assert r.status_code == 200
    assert sorted(r.json()["deleted"]) == sorted(own_ids)
    assert sorted(r.json()["skipped"]) == sorted(foreign_ids)

    async with TestSession() as s:
        for media_id in foreign_ids:
            assert await s.get(Media, media_id) is not None  # untouched


async def test_bulk_delete_only_foreign_items_deletes_nothing(client):
    headers = await auth_headers(client, "DelNone")
    other = await seed_user("DelOwner")
    foreign_id = await seed_media(other, filename="keep.png")

    r = await client.post(
        "/api/v1/media/bulk-delete", headers=headers, json={"media_ids": [foreign_id]}
    )
    assert r.status_code == 200
    assert r.json()["deleted"] == []
    assert r.json()["skipped"] == [foreign_id]

    async with TestSession() as s:
        assert await s.get(Media, foreign_id) is not None


async def test_bulk_delete_requires_auth(client):
    r = await client.post("/api/v1/media/bulk-delete", json={"media_ids": [1]})
    assert r.status_code == 401


async def test_gallery_count_respects_filters(client):
    uid = await seed_user("DelCount")
    headers = await auth_headers(client, "DelCount")
    other = await seed_user("DelCountB")
    for i in range(2):
        await seed_media(uid, filename=f"count{i}.png", file_hash=f"f{i}" * 32)
    await seed_media(other, filename="count-other.png", file_hash="g" * 64)

    r = await client.get("/api/v1/media/count", headers=headers)
    assert r.status_code == 200
    assert r.json() == 3

    r = await client.get("/api/v1/media/count", headers=headers, params={"uploader": "DelCount"})
    assert r.json() == 2


async def test_gallery_count_requires_auth(client):
    r = await client.get("/api/v1/media/count")
    assert r.status_code == 401
