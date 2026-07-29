"""Bulk ZIP download (US9 / FR-BULK).

Builds a ZIP of the requested ready + visible media. Hidden/failed/missing items are
excluded even if requested. Entry names are id-prefixed to avoid collisions.

Note: assembled in-memory here for simplicity; a production build should stream the ZIP
(the contract notes this) to avoid buffering large video archives.
"""

import io
import logging
import zipfile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.media import STATUS_READY, Media
from ..services.storage import get_storage

logger = logging.getLogger("wmp.zip")


async def build_zip(session: AsyncSession, media_ids: list[int]) -> bytes:
    if not media_ids:
        return _empty_zip()
    rows = (
        await session.execute(
            select(Media).where(
                Media.id.in_(media_ids),
                Media.status == STATUS_READY,
                Media.is_visible.is_(True),
            )
        )
    ).scalars().all()

    storage = get_storage()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for media in rows:
            try:
                data = storage.get(media.storage_path)
            except Exception:
                logger.warning("Skipping unreadable media %s in bulk ZIP", media.id, exc_info=True)
                continue
            archive.writestr(f"{media.id}_{media.original_filename}", data)
    return buffer.getvalue()


def _empty_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w"):
        pass
    return buffer.getvalue()
