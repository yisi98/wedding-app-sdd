"""Content-hash deduplication (Principle VI / FR-007).

The client sends a SHA-256 of file content at upload-init. `find_by_hash` checks the
`media.file_hash` unique column; the DB constraint additionally makes concurrent identical
uploads race-safe (only one row wins).
"""

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.media import Media


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def find_by_hash(session: AsyncSession, file_hash: str) -> Media | None:
    result = await session.execute(select(Media).where(Media.file_hash == file_hash))
    return result.scalar_one_or_none()
