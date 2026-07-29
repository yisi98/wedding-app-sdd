"""T047: reactions — toggle off same type, switch keeps count at one (US4 / SC-007)."""

from tests.conftest import auth_headers, seed_media, seed_user


async def _media(client) -> int:
    uid = await seed_user("ReactOwner")
    return await seed_media(uid, filename="r.png")


async def test_reaction_toggles_off_with_same_type(client):
    headers = await auth_headers(client, "Reactor")
    media_id = await _media(client)

    r1 = await client.post(f"/api/v1/media/{media_id}/reactions", json={"reaction_type": "like"}, headers=headers)
    assert r1.json() == {"reaction_type": "like", "reaction_count": 1}

    r2 = await client.post(f"/api/v1/media/{media_id}/reactions", json={"reaction_type": "like"}, headers=headers)
    assert r2.json() == {"reaction_type": None, "reaction_count": 0}


async def test_switching_reaction_type_keeps_count_one(client):
    headers = await auth_headers(client, "Switcher")
    media_id = await _media(client)

    await client.post(f"/api/v1/media/{media_id}/reactions", json={"reaction_type": "like"}, headers=headers)
    r = await client.post(f"/api/v1/media/{media_id}/reactions", json={"reaction_type": "love"}, headers=headers)
    assert r.json() == {"reaction_type": "love", "reaction_count": 1}


async def test_reaction_on_hidden_media_404(client):
    headers = await auth_headers(client, "Reactor2")
    uid = await seed_user("HiddenOwner")
    media_id = await seed_media(uid, is_visible=False)
    r = await client.post(f"/api/v1/media/{media_id}/reactions", json={"reaction_type": "like"}, headers=headers)
    assert r.status_code == 404
