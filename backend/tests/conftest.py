"""Test fixtures: an in-memory async SQLite database and an ASGI HTTP client.

Integration tests run against a real (in-memory) database via StaticPool, with the app's
`get_db` dependency overridden to the test session. Env vars are set before importing the
app so `get_settings()` (lru-cached) picks them up.
"""

import io
import os
import tempfile

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("EVENT_PASSWORD", "dev-only-event-pass")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("DEBUG", "false")  # skip lifespan create_all; the fixture owns schema
os.environ.setdefault("STORAGE_DIR", tempfile.mkdtemp(prefix="wmp-storage-"))

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db import get_db
from src.main import app
from src.models import Base
from src.models.event_config import SINGLETON_ID, EventConfig

EVENT_PASSWORD = "dev-only-event-pass"

test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


async def _override_get_db():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def _schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        session.add(EventConfig(id=SINGLETON_ID))
        await session.commit()
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def login(client: AsyncClient, name: str = "Anna", password: str = EVENT_PASSWORD):
    return await client.post(
        "/api/v1/auth/login", json={"display_name": name, "event_password": password}
    )


async def auth_headers(client: AsyncClient, name: str = "Anna") -> dict:
    token = (await login(client, name)).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def admin_headers(client: AsyncClient, name: str = "Boss") -> dict:
    await seed_user(name, role="admin")  # create as admin, then log in as them
    token = (await login(client, name)).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_png(width: int = 32, height: int = 24, color: tuple = (200, 100, 50)) -> bytes:
    """A small valid PNG for upload/processing tests."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def make_heic(width: int = 32, height: int = 24, color: tuple = (60, 120, 180)) -> bytes:
    """A small valid HEIC for upload/processing tests (via pillow-heif)."""
    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="HEIF")
    return buf.getvalue()


def make_mp4(width: int = 64, height: int = 48, duration: float = 1.0, fmt: str = "mp4") -> bytes:
    """A tiny real video via the system ffmpeg, for processing tests. `fmt="avi"` for a
    non-web-safe container that should trigger the MP4 transcode path."""
    import shutil
    import subprocess
    import tempfile

    if shutil.which("ffmpeg") is None:
        return b""
    with tempfile.NamedTemporaryFile(suffix=f".{fmt}") as dst:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"testsrc=size={width}x{height}:rate=10:duration={duration}",
                "-pix_fmt",
                "yuv420p",
                dst.name,
            ],
            check=True,
            timeout=30,
        )
        dst.seek(0)
        return dst.read()


def sha256_hex(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


async def seed_user(name: str, role: str = "guest") -> int:
    from src.models.user import User

    async with TestSession() as session:
        user = User(username=name, hashed_password="!", role=role)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def seed_media(
    uploader_id: int,
    *,
    filename: str = "pic.png",
    media_type: str = "image",
    status: str = "ready",
    is_visible: bool = True,
    view_count: int = 0,
    reaction_count: int = 0,
    phash: str | None = None,
    file_hash: str | None = None,
) -> int:
    import secrets

    from src.models.media import Media

    async with TestSession() as session:
        media = Media(
            uploader_id=uploader_id,
            filename=filename,
            original_filename=filename,
            file_hash=file_hash or secrets.token_hex(32),
            file_size=100,
            mime_type="image/png",
            media_type=media_type,
            storage_path=f"media/{secrets.token_hex(8)}/{filename}",
            status=status,
            is_visible=is_visible,
            view_count=view_count,
            reaction_count=reaction_count,
            phash=phash,
        )
        session.add(media)
        await session.commit()
        await session.refresh(media)
        return media.id
