"""Bulk ZIP download (US9 / FR-BULK).

Streams a ZIP of the requested ready + visible media. Hidden/failed/missing items are
excluded even if requested. Entry names are id-prefixed to avoid collisions.

`load_entries` does the one DB round-trip up front and returns plain data (not ORM rows),
so the streaming generator below never holds the DB session open while it reads storage and
sends bytes to the client — that could otherwise be a long time for a big multi-select of
large videos. Peak memory is one media file at a time, not the whole archive.
"""

import logging
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.media import STATUS_READY, Media
from ..services.storage import get_storage

logger = logging.getLogger("wmp.zip")


@dataclass
class ZipEntry:
    id: int
    original_filename: str
    storage_path: str


async def load_entries(session: AsyncSession, media_ids: list[int]) -> list[ZipEntry]:
    if not media_ids:
        return []
    rows = (
        await session.execute(
            select(Media).where(
                Media.id.in_(media_ids),
                Media.status == STATUS_READY,
                Media.is_visible.is_(True),
            )
        )
    ).scalars().all()
    return [ZipEntry(id=m.id, original_filename=m.original_filename, storage_path=m.storage_path) for m in rows]


class _StreamSink:
    """A minimal file-like object `zipfile.ZipFile` can write into.

    `tell()` must keep returning the true cumulative offset (zipfile relies on it for the
    central directory), even though `drain()` clears out already-yielded bytes.
    """

    def __init__(self) -> None:
        self._pos = 0
        self._pending = bytearray()

    def write(self, data: bytes) -> int:
        self._pending += data
        self._pos += len(data)
        return len(data)

    def tell(self) -> int:
        return self._pos

    def flush(self) -> None:
        pass

    def drain(self) -> bytes:
        data = bytes(self._pending)
        self._pending.clear()
        return data


def stream_zip(entries: list[ZipEntry]) -> Iterator[bytes]:
    storage = get_storage()
    sink = _StreamSink()
    archive = zipfile.ZipFile(sink, "w", zipfile.ZIP_DEFLATED)
    for entry in entries:
        try:
            data = storage.get(entry.storage_path)
        except Exception:
            logger.warning("Skipping unreadable media %s in bulk ZIP", entry.id, exc_info=True)
            continue
        archive.writestr(f"{entry.id}_{entry.original_filename}", data)
        chunk = sink.drain()
        if chunk:
            yield chunk
    archive.close()
    chunk = sink.drain()
    if chunk:
        yield chunk
