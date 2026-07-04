"""Test fixtures: an in-memory async SQLite database and an ASGI HTTP client.

Integration tests run against a real (in-memory) database via StaticPool, with the app's
`get_db` dependency overridden to the test session. Env vars are set before importing the
app so `get_settings()` (lru-cached) picks them up.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("EVENT_PASSWORD", "let-us-celebrate")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("DEBUG", "false")  # skip lifespan create_all; the fixture owns schema

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from src.db import get_db  # noqa: E402
from src.main import app  # noqa: E402
from src.models import Base  # noqa: E402
from src.models.event_config import SINGLETON_ID, EventConfig  # noqa: E402

EVENT_PASSWORD = "let-us-celebrate"

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
