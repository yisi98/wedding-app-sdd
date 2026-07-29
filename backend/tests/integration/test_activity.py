"""T060: GET /activity feed reflects actions (US6)."""

from tests.conftest import auth_headers, seed_media, seed_user


async def test_activity_feed_records_reaction_and_comment(client):
    headers = await auth_headers(client, "Active")
    media_id = await seed_media(await seed_user("AOwner"), filename="a.png")

    await client.post(f"/api/v1/media/{media_id}/reactions", json={"reaction_type": "love"}, headers=headers)
    await client.post(f"/api/v1/media/{media_id}/comments", json={"content": "nice"}, headers=headers)

    feed = await client.get("/api/v1/activity", headers=headers)
    assert feed.status_code == 200
    types = {e["event_type"] for e in feed.json()}
    assert "new_reaction" in types and "new_comment" in types
    # newest first
    assert feed.json()[0]["event_type"] == "new_comment"


async def test_activity_requires_auth(client):
    r = await client.get("/api/v1/activity")
    assert r.status_code == 401
