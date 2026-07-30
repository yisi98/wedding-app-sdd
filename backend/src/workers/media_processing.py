"""Background media processing (US2 / FR-009).

For images, produces a 400x400 thumbnail, a WebP-optimized version, an LQIP blur
placeholder, a perceptual hash (dHash), dimensions, and EXIF. HEIC/HEIF and AVIF sources
are decoded via pillow-heif / pillow-avif-plugin, registered at import time below.

For videos, produces a best-effort poster-frame thumbnail and duration via the system
`ffmpeg`/`ffprobe` binaries, and — for containers/codecs most browsers can't play natively
(anything other than MP4/WebM) — an H.264/AAC MP4 transcode used for in-app playback. The
original upload is never altered or replaced; only these additional derivatives are stored
alongside it, so downloads always return the exact bytes the guest uploaded.

The image work uses Pillow (+ a tiny numpy dHash) and needs no external services, so it is
directly unit-testable. `process_media` is called eagerly in dev/test and via Celery in prod.
"""

import base64
import io
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.media import MEDIA_IMAGE, STATUS_FAILED, STATUS_READY, Media
from ..services.storage import get_storage

THUMBNAIL_SIZE = (400, 400)
LQIP_WIDTH = 16

# Containers/codecs that play natively via an HTML5 <video> tag in mainstream browsers
# without a server-side transcode.
WEB_SAFE_VIDEO_TYPES = {"video/mp4", "video/webm"}


def _register_extra_pillow_formats() -> None:
    """Best-effort HEIC/HEIF and AVIF decode support; silently absent if not installed."""
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except Exception:  # noqa: BLE001, S110 — HEIC/HEIF support is best-effort
        pass
    try:
        import pillow_avif  # noqa: F401 — side-effect registers the AVIF codec
    except Exception:  # noqa: BLE001, S110 — AVIF support is best-effort
        pass


_register_extra_pillow_formats()


@dataclass
class ImageDerivations:
    width: int
    height: int
    thumbnail: bytes
    optimized: bytes
    lqip: str
    phash: str
    exif: dict = field(default_factory=dict)


@dataclass
class VideoDerivations:
    duration: float | None
    thumbnail: bytes | None
    playable: bytes | None  # H.264/AAC MP4 transcode; only set when the source isn't web-safe


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
    from PIL import Image, ImageOps

    original = Image.open(io.BytesIO(data))
    original.load()

    # Capture EXIF from the original: exif_transpose() drops the Orientation tag once it
    # has been applied, and the metadata is worth keeping for the record.
    exif: dict = {}
    raw_exif = getattr(original, "_getexif", lambda: None)()
    if raw_exif:
        exif = {str(k): str(v) for k, v in raw_exif.items()}

    # Phones store a landscape frame plus an Orientation tag rather than rotating pixels.
    # Browsers honour that tag on the original file, but every derivative below is
    # re-encoded and loses it — so bake the rotation in first, or portrait photos show up
    # sideways in the grid and the lightbox and report transposed dimensions.
    image = ImageOps.exif_transpose(original) or original
    width, height = image.width, image.height

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


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _probe_duration(path: str) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
            capture_output=True,
            timeout=30,
            check=True,
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception:  # noqa: BLE001 — best-effort
        return None


def _extract_thumbnail(path: str, duration: float | None) -> bytes | None:
    """A poster frame partway into the clip (or the first frame if duration is unknown)."""
    seek = min(1.0, duration / 2) if duration else 0.0
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg") as dst:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{seek:.2f}",
                    "-i",
                    path,
                    "-frames:v",
                    "1",
                    "-vf",
                    f"scale={THUMBNAIL_SIZE[0]}:{THUMBNAIL_SIZE[1]}:force_original_aspect_ratio=decrease",
                    dst.name,
                ],
                check=True,
                timeout=30,
                capture_output=True,
            )
            dst.seek(0)
            return dst.read() or None
    except Exception:  # noqa: BLE001 — best-effort
        return None


def _transcode_to_mp4(path: str) -> bytes | None:
    """H.264/AAC MP4 for browser playback of containers most browsers can't play natively."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4") as dst:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-i",
                    path,
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-movflags",
                    "+faststart",
                    dst.name,
                ],
                check=True,
                timeout=600,
                capture_output=True,
            )
            dst.seek(0)
            return dst.read() or None
    except Exception:  # noqa: BLE001 — best-effort; the guest can still download the original
        return None


def process_video(data: bytes, mime_type: str) -> VideoDerivations:
    if not _ffmpeg_available():
        return VideoDerivations(duration=None, thumbnail=None, playable=None)

    with tempfile.NamedTemporaryFile(suffix=".input") as src:
        src.write(data)
        src.flush()
        duration = _probe_duration(src.name)
        thumbnail = _extract_thumbnail(src.name, duration)
        playable = _transcode_to_mp4(src.name) if mime_type not in WEB_SAFE_VIDEO_TYPES else None

    return VideoDerivations(duration=duration, thumbnail=thumbnail, playable=playable)


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
            v = process_video(data, media.mime_type)
            media.duration = v.duration
            if v.thumbnail is not None:
                thumb_key = f"media/{media.file_hash}/thumb.jpg"
                storage.put(thumb_key, v.thumbnail)
                media.thumbnail_path = thumb_key
            if v.playable is not None:
                playable_key = f"media/{media.file_hash}/playable.mp4"
                storage.put(playable_key, v.playable)
                media.optimized_path = playable_key
        media.status = STATUS_READY
    except Exception:  # noqa: BLE001 — treat any processing error as a failed item
        media.status = STATUS_FAILED
    await session.flush()
