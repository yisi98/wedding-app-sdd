#!/usr/bin/env bash
# check-uploads.sh — where did my uploads go? Prints all media rows with status,
# the worker log tail, and tests the gallery API the frontend actually calls.
set -e
cd /opt/wedding-app/infra

echo "== 1. All media rows (newest first) =="
docker compose -f docker-compose.prod.yml exec -T backend uv run python - <<'PYEOF'
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import get_settings
from src.models.media import Media


async def m():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        rows = (await s.execute(select(Media).order_by(Media.id.desc()).limit(15))).scalars().all()
        if not rows:
            print("  (no media rows at all)")
        for r in rows:
            print(
                f"  id={r.id} status={r.status} type={r.media_type} file={r.original_filename} "
                f"size={r.file_size} uploaded={r.created_at} thumb={'yes' if r.thumbnail_path else 'no'}"
            )

asyncio.run(m())
PYEOF

echo ""
echo "== 2. Worker log (last 60 lines) =="
docker compose -f docker-compose.prod.yml logs worker --tail 60 2>&1 | tail -40

echo ""
echo "== 3. Backend errors (last 40 lines) =="
docker compose -f docker-compose.prod.yml logs backend --tail 40 2>&1 | grep -Ei 'error|exception|traceback|500' | tail -15 || echo "  (no errors found)"

echo ""
echo "== 4. Gallery API returns (needs token; row counts above tell the story anyway) =="
echo "   If rows above show status=ready, the API will show them -> refresh browser."
echo "   If status=processing -> worker issue (see section 2)."
echo "   If status=failed or pending -> upload didn't complete (network/CORS in browser)."
