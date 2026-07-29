"""T076: every /admin/* route refuses non-admins with 403 (US8 / FR-034)."""

import pytest

from tests.conftest import auth_headers


@pytest.mark.parametrize(
    ("method", "path", "json"),
    [
        ("GET", "/api/v1/admin/stats", None),
        ("GET", "/api/v1/admin/users", None),
        ("PATCH", "/api/v1/admin/users/1", {"role": "admin"}),
        ("DELETE", "/api/v1/admin/users/1", None),
        ("GET", "/api/v1/admin/media", None),
        ("PATCH", "/api/v1/admin/media/1/visibility", {"is_visible": True}),
        ("GET", "/api/v1/admin/export/media", None),
    ],
)
async def test_non_admin_forbidden(client, method, path, json):
    headers = await auth_headers(client, "PlainGuest")
    r = await client.request(method, path, json=json, headers=headers)
    assert r.status_code == 403
