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

    async with AsyncSession(engine, expire_on_commit=False) as s:
        ids = list(
            (await s.execute(select(Media.id).where(Media.status.in_(["failed", "processing", "pending"]))))
            .scalars()
            .all()
        )

    if not ids:
        print("no stuck rows - all clear")
        return

    print(f"stuck rows: {ids}")
    for mid in ids:
        async with AsyncSession(engine, expire_on_commit=False) as s:
            m = await s.get(Media, mid)
            exists = storage.exists(m.storage_path)
            if not exists:
                m.status = "failed"
                await s.commit()
                print(f"  id={mid} ({m.original_filename}) -> failed (object missing in OSS)")
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

    print("--- final status of all rows ---")
    async with AsyncSession(engine, expire_on_commit=False) as s:
        rows = (await s.execute(select(Media.id, Media.status, Media.original_filename).order_by(Media.id))).all()
        for r in rows:
            print(f"  id={r[0]} {r[1]:10s} {r[2]}")


asyncio.run(main())
