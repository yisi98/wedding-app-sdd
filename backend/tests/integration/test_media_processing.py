"""T033: background processing outputs — derivations + end-to-end ready (US2 / FR-009)."""

import io
import shutil

import pytest
from sqlalchemy import select

from src.models.activity_event import EVENT_NEW_UPLOAD, ActivityEvent
from src.models.media import STATUS_PROCESSING, Media
from src.workers.media_processing import (
    WEB_SAFE_VIDEO_TYPES,
    process_and_announce,
    process_image,
    process_video,
)
from tests.conftest import (
    TestSession,
    auth_headers,
    make_heic,
    make_jpeg_with_orientation,
    make_mp4,
    make_png,
    sha256_hex,
)

needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requires the system ffmpeg/ffprobe binaries",
)


def test_process_image_produces_derivations():
    png = make_png(width=64, height=48, color=(30, 60, 90))
    d = process_image(png)
    assert d.width == 64 and d.height == 48
    assert d.thumbnail and d.optimized
    assert d.lqip.startswith("data:image/jpeg;base64,")
    assert len(d.phash) == 16  # 8x8 dHash → 16 hex chars


@pytest.mark.parametrize(
    ("orientation", "expected"),
    [
        (1, (200, 100)),  # already upright
        (3, (200, 100)),  # 180° — dimensions unchanged
        (6, (100, 200)),  # portrait phone shot, the common case
        (8, (100, 200)),  # portrait the other way
        (5, (100, 200)),  # transposed
        (7, (100, 200)),
    ],
)
def test_exif_orientation_is_baked_into_derivatives(orientation, expected):
    """Derivatives are re-encoded and lose the EXIF tag, so the rotation must be applied
    to the pixels — otherwise portrait phone photos render sideways everywhere."""
    from PIL import Image

    d = process_image(make_jpeg_with_orientation(orientation))
    assert (d.width, d.height) == expected

    thumb = Image.open(io.BytesIO(d.thumbnail))
    # The thumbnail keeps the corrected aspect ratio (it is only scaled down).
    assert (thumb.width > thumb.height) == (expected[0] > expected[1])

    optimized = Image.open(io.BytesIO(d.optimized))
    assert (optimized.width, optimized.height) == expected


def test_orientation_metadata_is_still_recorded():
    """Applying the rotation must not throw the EXIF away — it is kept for the record."""
    d = process_image(make_jpeg_with_orientation(6))
    assert d.exif.get("274") == "6"


def test_process_image_decodes_heic():
    heic = make_heic(width=40, height=30)
    d = process_image(heic)
    assert d.width == 40 and d.height == 30
    assert d.thumbnail and d.optimized


@needs_ffmpeg
def test_process_video_produces_thumbnail_and_duration():
    mp4 = make_mp4(duration=1.0, fmt="mp4")
    v = process_video(mp4, "video/mp4")
    assert v.duration is not None and v.duration > 0
    assert v.thumbnail is not None
    # mp4 is already web-safe — no transcode needed.
    assert v.playable is None


@needs_ffmpeg
def test_process_video_transcodes_non_web_safe_container():
    avi = make_mp4(duration=1.0, fmt="avi")
    assert "video/x-msvideo" not in WEB_SAFE_VIDEO_TYPES
    v = process_video(avi, "video/x-msvideo")
    assert v.duration is not None
    assert v.thumbnail is not None
    assert v.playable is not None  # transcoded to a browser-playable MP4


async def test_end_to_end_upload_becomes_ready_with_derivations(client):
    headers = await auth_headers(client)
    png = make_png(width=50, height=40, color=(200, 30, 30))
    body = {
        "original_filename": "photo.png",
        "mime_type": "image/png",
        "file_size": len(png),
        "file_hash": sha256_hex(png),
    }
    init = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    key = init.json()["storage_key"]
    await client.put(f"/api/v1/media/upload/raw?key={key}", content=png, headers=headers)
    confirm = await client.post(
        "/api/v1/media/upload/confirm", json={"media_id": init.json()["media_id"]}, headers=headers
    )
    media = confirm.json()
    assert media["status"] == "ready"
    assert media["width"] == 50 and media["height"] == 40
    assert media["lqip"].startswith("data:image/jpeg;base64,")
    assert media["thumbnail_path"] and media["optimized_path"]


@needs_ffmpeg
async def test_end_to_end_video_upload_gets_thumbnail_and_transcode(client):
    headers = await auth_headers(client)
    avi = make_mp4(duration=1.0, fmt="avi")
    body = {
        "original_filename": "clip.avi",
        "mime_type": "video/x-msvideo",
        "file_size": len(avi),
        "file_hash": sha256_hex(avi),
    }
    init = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    key = init.json()["storage_key"]
    await client.put(f"/api/v1/media/upload/raw?key={key}", content=avi, headers=headers)
    confirm = await client.post(
        "/api/v1/media/upload/confirm", json={"media_id": init.json()["media_id"]}, headers=headers
    )
    media = confirm.json()
    assert media["status"] == "ready"
    assert media["duration"] is not None and media["duration"] > 0
    assert media["thumbnail_path"]  # poster frame
    assert media["optimized_path"]  # transcoded playable MP4


async def test_end_to_end_portrait_photo_is_stored_upright(client):
    """A portrait phone photo must report upright dimensions after the full upload flow."""
    headers = await auth_headers(client, "PortraitGuest")
    jpeg = make_jpeg_with_orientation(6)  # 200x100 pixels, displays as 100x200
    body = {
        "original_filename": "portrait.jpg",
        "mime_type": "image/jpeg",
        "file_size": len(jpeg),
        "file_hash": sha256_hex(jpeg),
    }
    init = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    key = init.json()["storage_key"]
    await client.put(f"/api/v1/media/upload/raw?key={key}", content=jpeg, headers=headers)
    confirm = await client.post(
        "/api/v1/media/upload/confirm", json={"media_id": init.json()["media_id"]}, headers=headers
    )
    media = confirm.json()
    assert media["status"] == "ready"
    assert (media["width"], media["height"]) == (100, 200), "stored sideways"


async def test_original_download_keeps_the_untouched_bytes(client):
    """Rotation applies to derivatives only — the original must be byte-identical."""
    headers = await auth_headers(client, "OriginalGuest")
    jpeg = make_jpeg_with_orientation(6)
    body = {
        "original_filename": "keepme.jpg",
        "mime_type": "image/jpeg",
        "file_size": len(jpeg),
        "file_hash": sha256_hex(jpeg),
    }
    init = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    key = init.json()["storage_key"]
    await client.put(f"/api/v1/media/upload/raw?key={key}", content=jpeg, headers=headers)
    await client.post(
        "/api/v1/media/upload/confirm", json={"media_id": init.json()["media_id"]}, headers=headers
    )
    served = await client.get(f"/media-object/{key}")
    assert served.content == jpeg


async def test_worker_processing_announces_new_upload_once_ready(client):
    """Prod (Celery) path: confirm returns while the item is still processing, and the
    worker must broadcast new_upload when it finishes — that broadcast is what makes
    every open gallery refetch and show the item without a manual reload."""
    headers = await auth_headers(client, "WorkerGuest")
    png = make_png(width=40, height=30)
    body = {
        "original_filename": "late.png",
        "mime_type": "image/png",
        "file_size": len(png),
        "file_hash": sha256_hex(png),
    }
    init = await client.post("/api/v1/media/upload/init", json=body, headers=headers)
    media_id = init.json()["media_id"]
    key = init.json()["storage_key"]
    await client.put(f"/api/v1/media/upload/raw?key={key}", content=png, headers=headers)

    # Simulate prod confirm: hand off to the worker instead of processing inline, so
    # the item sits in `processing` after confirm has already returned to the client.
    async with TestSession() as session:
        media = await session.get(Media, media_id)
        media.status = STATUS_PROCESSING
        await session.commit()

    async with TestSession() as session:
        await process_and_announce(session, media_id)

    async with TestSession() as session:
        media = await session.get(Media, media_id)
        assert media.status == "ready"
        events = (
            await session.execute(
                select(ActivityEvent).where(
                    ActivityEvent.media_id == media_id,
                    ActivityEvent.event_type == EVENT_NEW_UPLOAD,
                )
            )
        ).scalars().all()
        assert len(events) == 1, "worker must announce exactly one new_upload event"
