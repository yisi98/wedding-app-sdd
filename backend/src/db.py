"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings

_settings = get_settings()

engine = create_async_engine(_settings.database_url, future=True)

if engine.dialect.name == "sqlite":
    # SQLite ignores foreign keys unless told otherwise per-connection, unlike PostgreSQL
    # (prod), which always enforces them. Without this, ON DELETE SET NULL/CASCADE
    # behavior (e.g. media surviving a deleted uploader) silently doesn't happen in
    # dev/local SQLite — rows just go dangling instead.
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async session."""
    async with async_session_factory() as session:
        yield session
