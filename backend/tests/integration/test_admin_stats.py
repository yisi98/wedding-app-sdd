"""T073: GET /admin/stats (US8)."""

from tests.conftest import admin_headers, seed_media, seed_user


async def test_stats_returns_totals(client):
    headers = await admin_headers(client)
    uid = await seed_user("StatOwner")
    await seed_media(uid, filename="s1.png", view_count=5)
    await seed_media(uid, filename="s2.mp4", media_type="video", view_count=3)

    r = await client.get("/api/v1/admin/stats", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total_media"] == 2
    assert body["total_views"] == 8
    assert body["media_by_type"]["image"] == 1
    assert body["media_by_type"]["video"] == 1
    assert body["top_by_views"][0]["view_count"] == 5
