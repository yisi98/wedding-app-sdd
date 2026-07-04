"""T025: /auth/me, /auth/logout (revoke all), /auth/profile (US1)."""

from tests.conftest import login


def _bearer(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


async def test_me_returns_current_user_without_email(client):
    tokens = (await login(client, "Chen")).json()
    r = await client.get("/api/v1/auth/me", headers=_bearer(tokens["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "Chen"
    assert "email" not in body


async def test_me_requires_authentication(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_logout_revokes_all_refresh_tokens(client):
    tokens = (await login(client, "Dmitri")).json()
    logout = await client.post("/api/v1/auth/logout", headers=_bearer(tokens["access_token"]))
    assert logout.status_code == 204

    # After logout, the previously issued refresh token is revoked.
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401


async def test_profile_update_changes_language(client):
    tokens = (await login(client, "Elena")).json()
    r = await client.put(
        "/api/v1/auth/profile",
        headers=_bearer(tokens["access_token"]),
        json={"language_preference": "ru"},
    )
    assert r.status_code == 200
    assert r.json()["language_preference"] == "ru"
