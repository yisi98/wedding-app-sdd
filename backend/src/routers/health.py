"""Health router — implements contracts/ops.md (FR-038).

Probes the database (and Redis when configured); returns 503 if any core dependency is
degraded. Redis is wired in with US6; until then it reports "not_configured".
"""

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from ..deps import DbDep, SettingsDep

router = APIRouter(prefix="/api/v1", tags=["ops"])


@router.get("/health")
async def health(session: DbDep, settings: SettingsDep, response: Response) -> dict:
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001 - report degraded, don't leak internals
        checks["database"] = "degraded"

    if settings.redis_url:
        # Full Redis probe is added in US6; presence of a URL is reported for now.
        checks["redis"] = "configured"
    else:
        checks["redis"] = "not_configured"

    healthy = checks.get("database") == "ok"
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if healthy else "degraded", "checks": checks}
