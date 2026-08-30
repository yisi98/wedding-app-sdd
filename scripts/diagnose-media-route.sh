#!/usr/bin/env bash
# diagnose-media-route.sh — the media-object route returns 404 with no redirect to OSS.
# Checks: which objects.py version is on disk vs inside the running image, what the
# backend returns directly (bypassing nginx), and whether a presigned GET to OSS works.
set -e
cd /opt/wedding-app/infra

echo "== 1. objects.py on the HOST (/opt/wedding-app/backend) =="
grep -n "presigned\|RedirectResponse\|storage.get" /opt/wedding-app/backend/src/routers/objects.py || echo "  (no presigned/redirect markers found!)"

echo ""
echo "== 2. objects.py inside the RUNNING backend container =="
docker compose -f docker-compose.prod.yml exec -T backend sh -c \
  'grep -n "presigned\|RedirectResponse" /app/src/routers/objects.py' || echo "  (no presigned/redirect markers in container!)"

echo ""
echo "== 3. Which routes does the running app actually have? =="
docker compose -f docker-compose.prod.yml exec -T backend sh -c \
  'uv run python -c "from src.main import app; print([r.path for r in app.routes if \"media-object\" in getattr(r, \"path\", \"\")])"'

echo ""
echo "== 4. Direct backend call (bypassing nginx) for media id=13 thumb =="
KEY=$(docker compose -f docker-compose.prod.yml exec -T backend uv run python - <<'PYEOF'
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import get_settings
from src.models.media import Media


async def m():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        r = (await s.execute(select(Media).where(Media.id == 13))).scalar_one()
        print(r.thumbnail_path)

asyncio.run(m())
PYEOF
)
echo "key: $KEY"
docker compose -f docker-compose.prod.yml exec -T backend sh -c \
  "curl -s -o /dev/null -w 'backend direct: %{http_code}\n' http://localhost:8000/api/v1/media-object/$KEY"

echo ""
echo "== 5. Presign + fetch straight from OSS (no backend route involved) =="
docker compose -f docker-compose.prod.yml exec -T backend uv run python - <<PYEOF
from src.services.storage import get_storage

url = get_storage().presigned_get_url("$KEY")
print("presigned URL host:", url.split("/")[2])
import urllib.request
try:
    with urllib.request.urlopen(url) as resp:
        print("OSS GET status:", resp.status, "bytes:", len(resp.read()))
except Exception as e:
    print("OSS GET FAILED:", e)
PYEOF
