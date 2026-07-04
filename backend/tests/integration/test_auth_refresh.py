"""T024: POST /auth/refresh — rotation + reused-token 401 (US1 / FR-005)."""

from tests.conftest import login


async def test_refresh_rotates_and_old_token_cannot_be_reused(client):
    tokens = (await login(client, "Boris")).json()
    old_refresh = tokens["refresh_token"]

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200
    rotated = r.json()
    assert rotated["access_token"] and rotated["refresh_token"]
    assert rotated["refresh_token"] != old_refresh

    # The rotated (old) token is now revoked and must not be reusable.
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401


async def test_refresh_with_garbage_token_rejected(client):
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert r.status_code == 401
