"""Default admin account: seeded on a fresh database, signs in with its own password."""

from src.config import get_settings
from src.services import auth as auth_service
from tests.conftest import EVENT_PASSWORD, TestSession, login


async def _seed_admin() -> None:
    async with TestSession() as session:
        await auth_service.ensure_default_admin(session, get_settings())


async def test_default_admin_can_sign_in_and_is_admin(client):
    await _seed_admin()

    r = await login(client, "admin", "admin12345")
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "admin"

    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert (await client.get("/api/v1/admin/stats", headers=headers)).status_code == 200


async def test_event_password_does_not_grant_admin(client):
    """The shared guest password must not open the admin account."""
    await _seed_admin()
    assert (await login(client, "admin", EVENT_PASSWORD)).status_code == 401


async def test_wrong_admin_password_rejected(client):
    await _seed_admin()
    assert (await login(client, "admin", "not-the-password")).status_code == 401


async def test_seeding_is_idempotent_and_preserves_a_changed_password(client):
    await _seed_admin()
    async with TestSession() as session:
        from sqlalchemy import select

        from src.models.user import User

        user = (
            await session.execute(select(User).where(User.username == "admin"))
        ).scalar_one()
        user.hashed_password = auth_service.hash_password("rotated-password")
        await session.commit()

    await _seed_admin()  # a later restart must not reset the password

    assert (await login(client, "admin", "rotated-password")).status_code == 200
    assert (await login(client, "admin", "admin12345")).status_code == 401


async def test_guests_still_use_the_shared_event_password(client):
    await _seed_admin()
    r = await login(client, "Ordinary Guest", EVENT_PASSWORD)
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "guest"


async def test_deactivated_user_cannot_log_in(client):
    from sqlalchemy import select

    from src.models.user import User

    assert (await login(client, "Soon Gone", EVENT_PASSWORD)).status_code == 200
    async with TestSession() as session:
        user = (
            await session.execute(select(User).where(User.username == "Soon Gone"))
        ).scalar_one()
        user.is_active = False
        await session.commit()

    assert (await login(client, "Soon Gone", EVENT_PASSWORD)).status_code == 401
