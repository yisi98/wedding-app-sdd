#!/usr/bin/env bash
# diagnose-processing.sh — find why media processing fails on prod, print the real
# traceback (process_media swallows exceptions by design), then retry the failed
# items inline and report their final status.
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
from src.workers.media_processing import process_image, process_media


async def main() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with AsyncSession(engine) as s:
        rows = (await s.execute(select(Media).order_by(Media.id.desc()).limit(5))).scalars().all()
        print("== recent media rows ==")
        for m in rows:
            print(f"  id={m.id} status={m.status} type={m.media_type} path={m.storage_path}")

        # Step 1: can we read the object back from OSS?
        m12 = next((m for m in rows if m.id == 12), None)
        if m12 is None:
            print("media id=12 not found; nothing to diagnose")
            return
        storage = get_storage()
        try:
            data = storage.get(m12.storage_path)
            print(f"\n== storage.get OK: {len(data)} bytes ==")
        except Exception:
            print("\n== storage.get FAILED ==")
            traceback.print_exc()
            return

        # Step 2: does image processing itself work (this is where the swallowed error lives)?
        try:
            d = process_image(data)
            print(f"\n== process_image OK: {d.width}x{d.height}, thumb={len(d.thumbnail)}B, webp={len(d.optimized)}B ==")
        except Exception:
            print("\n== process_image FAILED (this is the bug) ==")
            traceback.print_exc()
            return

        # Step 3: can we write derivatives to OSS?
        try:
            prefix = "media/" + m12.file_hash
            storage.put(prefix + "/thumb.jpg", d.thumbnail)
            storage.put(prefix + "/optimized.webp", d.optimized)
            print("\n== derivative PUTs OK ==")
        except Exception:
            print("\n== derivative PUTs FAILED ==")
            traceback.print_exc()
            return

        # Everything works in isolation -> re-run full processing for ids 11 and 12
        print("\n== retrying process_media for ids 11 and 12 ==")
        for m in rows:
            if m.id in (11, 12) and m.status in ("processing", "failed"):
                await process_media(s, m)
                await s.commit()
                await s.refresh(m)
                print(f"  id={m.id} -> {m.status}")


asyncio.run(main())
PYEOF
