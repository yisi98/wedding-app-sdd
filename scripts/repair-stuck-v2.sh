#!/usr/bin/env bash
# repair-stuck-v2.sh — robust re-processing of stuck media rows: one DB session per
# item (a failed item no longer poisons the rest), checks object existence in OSS,
# prints a clear per-item verdict.
set -e
cd /opt/wedding-app/infra

docker compose -f docker-compose.prod.yml exec -T backend uv run python - <<'PYEOF'
import asyncio
import traceback

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import get_settings
from src.models.media import Media
from src.services.storage import get_storage
from src.workers.media_processing import process_media


async def main() -> None:
    engine = create_async_engine(get_settings().database_url)
    storage = get_storage()

    async with AsyncSession(engine) as s:
        ids = list((await s.execute(
            select(Media.id).where(Media.status.in_(["failed", "processing", "pending"]))
        )).scalars().all())

    if not ids:
        print("no stuck rows — all clear")
        return

    print(f"stuck rows: {ids}")
    for mid in ids:
        # Fresh session per item: a failure here must not break the others.
        async with AsyncSession(engine) as s:
            m = await s.get(Media, mid)
            exists = storage.exists(m.storage_path)
            if not exists:
                # The original bytes never made it to OSS (aborted upload) — mark failed.
                m.status = "failed"
                await s.commit()
                print(f"  id={mid} ({m.original_filename}) -> failed (object missing in OSS — re-upload needed)")
                continue
            try:
                m.status = "processing"
                await process_media(s, m)
                await s.commit()
                await s.refresh(m)
                print(f"  id={mid} ({m.original_filename}) -> {m.status}")
            except Exception:
                await s.rollback()
                print(f"  id={mid} ({m.original_filename}) -> ERROR:")
                traceback.print_exc()


asyncio.run(main())
PYEOF

echo ""
echo "== Sanity: final status of every row =="
docker compose -f docker-compose.prod.yml exec -T backend uv run python - <<'PYEOF'
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import get_settings
from src.models.media import Media


async def m():
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        rows = (await s.execute(select(Media).order_by(Media.id))).scalars().all()
        for r in rows:
            print(f"  id={r.id} {r.status:10s} {r.original_filename}")

asyncio.run(m())
PYEOF
