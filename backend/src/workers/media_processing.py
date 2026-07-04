"""Background media processing (US2 / FR-009).

For images, produces a 400x400 thumbnail, a WebP-optimized version, an LQIP blur
placeholder, a perceptual hash (dHash), dimensions, and EXIF. For videos, records a
best-effort duration (ffmpeg) and marks ready. Failures set status ``failed``.

The image work uses Pillow (+ a tiny numpy dHash) and needs no external services, so it is
directly unit-testable. `process_media` is called eagerly in dev/test and via Celery in prod.
"""

import base64
import io
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.media import MEDIA_IMAGE, STATUS_FAILED, STATUS_READY, Media
from ..services.storage import get_storage

THUMBNAIL_SIZE = (400, 400)
LQIP_WIDTH = 16


@dataclass
class ImageDerivations:
    width: int
    height: int
    thumbnail: bytes
    optimized: bytes
    lqip: str
    phash: str
    exif: dict = field(default_factory=dict)


def _dhash(image, hash_size: int = 8) -> str:
    """Row-wise difference hash → hex string. Robust and dependency-light."""
    import numpy as np

    small = image.convert("L").resize((hash_size + 1, hash_size))
    pixels = np.asarray(small, dtype=np.int16)
    diff = pixels[:, 1:] > pixels[:, :-1]
    bits = 0
    for bit in diff.flatten():
        bits = (bits << 1) | int(bool(bit))
    return f"{bits:0{hash_size * hash_size // 4}x}"


def _lqip(image) -> str:
    """Tiny blurred JPEG as a base64 data URI for blur-up loading (Principle V)."""
    ratio = LQIP_WIDTH / max(image.width, 1)
    tiny = image.convert("RGB").resize((LQIP_WIDTH, max(1, int(image.height * ratio))))
    buf = io.BytesIO()
    tiny.save(buf, format="JPEG", quality=30)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def process_image(data: bytes) -> ImageDerivations:
    from PIL import Image

    image = Image.open(io.BytesIO(data))
    image.load()
    width, height = image.width, image.height

    exif: dict = {}
    raw_exif = getattr(image, "_getexif", lambda: None)()
    if raw_exif:
        exif = {str(k): str(v) for k, v in raw_exif.items()}

    thumb = image.convert("RGB").copy()
    thumb.thumbnail(THUMBNAIL_SIZE)
    thumb_buf = io.BytesIO()
    thumb.save(thumb_buf, format="JPEG", quality=85)

    opt_buf = io.BytesIO()
    image.convert("RGB").save(opt_buf, format="WEBP", quality=82)

    return ImageDerivations(
        width=width,
        height=height,
        thumbnail=thumb_buf.getvalue(),
        optimized=opt_buf.getvalue(),
        lqip=_lqip(image),
        phash=_dhash(image),
        exif=exif,
    )


async def process_media(session: AsyncSession, media: Media) -> None:
    """Generate derivations for a stored media object and mark it ready (or failed)."""
    storage = get_storage()
    try:
        data = storage.get(media.storage_path)
    except Exception:  # noqa: BLE001 — missing/unreadable object
        media.status = STATUS_FAILED
        await session.flush()
        return

    try:
        if media.media_type == MEDIA_IMAGE:
            d = process_image(data)
            thumb_key = f"media/{media.file_hash}/thumb.jpg"
            opt_key = f"media/{media.file_hash}/optimized.webp"
            storage.put(thumb_key, d.thumbnail)
            storage.put(opt_key, d.optimized)
            media.width, media.height = d.width, d.height
            media.thumbnail_path, media.optimized_path = thumb_key, opt_key
            media.lqip, media.phash, media.exif_data = d.lqip, d.phash, d.exif
        else:
            media.duration = _video_duration(data)
        media.status = STATUS_READY
    except Exception:  # noqa: BLE001 — treat any processing error as a failed item
        media.status = STATUS_FAILED
    await session.flush()


def _video_duration(data: bytes) -> float | None:
    """Best-effort video duration; returns None if ffmpeg is unavailable."""
    try:
        import tempfile

        import ffmpeg  # type: ignore

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(data)
            probe = ffmpeg.probe(tmp.name)
        return float(probe["format"]["duration"])
    except Exception:  # noqa: BLE001
        return None
