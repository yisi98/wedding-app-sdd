"""T023: POST /auth/login — get-or-create, wrong password 401, no email leak (US1)."""

from tests.conftest import EVENT_PASSWORD, login


async def test_login_creates_guest_and_returns_tokens(client):
    r = await login(client, "Anna")
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == "Anna"
    assert body["user"]["role"] == "guest"
    # Legacy email column must never be exposed.
    assert "email" not in body["user"]


async def test_login_is_get_or_create(client):
    r1 = await login(client, "Anna")
    r2 = await login(client, "Anna")
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["user"]["id"] == r2.json()["user"]["id"]


async def test_login_wrong_event_password_rejected(client):
    r = await login(client, "Mallory", password="wrong-password")
    assert r.status_code == 401
