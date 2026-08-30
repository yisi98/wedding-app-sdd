#!/bin/bash
# Check worker logs and the e2e test media row status.
cd /opt/wedding-app/infra

echo "=== WORKER LOGS ==="
docker logs infra-worker-1 --tail 60 2>&1 | grep -v 'Building\|Installed\|Uninstalled\|Built\|Downloading\|Downloaded\|Prepared'

echo "=== MEDIA ROW ==="
docker compose -f docker-compose.prod.yml exec -T backend uv run python - <<'PYEOF'
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from src.config import get_settings
from src.models.media import Media

async def m():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        rows = (await s.execute(select(Media).order_by(Media.id.desc()).limit(5))).scalars().all()
        for r in rows:
            print(f"id={r.id} status={r.status} thumb={r.thumbnail_path} err={r.processing_error}")

asyncio.run(m())
PYEOF
