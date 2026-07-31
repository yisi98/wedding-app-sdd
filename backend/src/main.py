"""FastAPI application factory.

CORS is environment-driven (research.md): DEBUG allows all origins with credentials off;
production uses an explicit allow-list with credentials on. DEBUG runs Alembic migrations
on startup for zero-setup local runs; production applies them as a separate deploy step.

DEBUG used to take a `create_all` shortcut instead of running migrations, but that only
creates tables that don't exist yet — it silently never applies a schema change (e.g. a new
nullable/ondelete on an existing column) to a database file left over from an earlier run,
so a fixed bug would keep reproducing in any dev environment with a pre-existing wedding.db.
Migrations are idempotent, so running them on every DEBUG startup is still zero-setup.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger("wmp")
from .models.event_config import SINGLETON_ID, EventConfig
from .routers import admin as admin_router
from .routers import auth as auth_router
from .routers import downloads as downloads_router
from .routers import health as health_router
from .routers import media as media_router
from .routers import notifications as notifications_router
from .routers import objects as objects_router
from .routers import social as social_router
from .routers import ws as ws_router
from .services import auth as auth_service


def _run_migrations() -> None:
    # alembic's env.py drives its own asyncio.run(); called via run_in_executor so it gets
    # a fresh thread with no event loop already running in it.
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    try:
        command.upgrade(cfg, "head")
    except Exception as exc:
        if "already exists" in str(exc):
            # A wedding.db from before this project switched DEBUG from create_all to
            # real migrations (see module docstring) has every table but no Alembic
            # version stamped, so upgrade tries to create tables that are already
            # there. Local dev data is disposable — starting over is the fix.
            raise RuntimeError(
                "Migration failed: the local database has tables but no Alembic "
                "version recorded (likely created before this project used "
                "migrations in DEBUG mode). Delete it and start fresh — "
                "`./scripts/dev.sh --reset`, or `rm backend/wedding.db`."
            ) from exc
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    from .db import async_session_factory

    if settings.debug:
        await asyncio.get_running_loop().run_in_executor(None, _run_migrations)
        # Ensure the singleton event_config row exists.
        async with async_session_factory() as session:
            existing = await session.get(EventConfig, SINGLETON_ID)
            if existing is None:
                session.add(EventConfig(id=SINGLETON_ID))
                await session.commit()

    # Seed the built-in admin on every start, not just in debug: production schema comes
    # from Alembic rather than create_all, and this keeps the account recoverable if it
    # is ever removed. Idempotent, and tolerant of a database that isn't migrated yet.
    try:
        async with async_session_factory() as session:
            await auth_service.ensure_default_admin(session, settings)
    except Exception:
        logger.warning("Could not seed the default admin account", exc_info=True)

    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Wedding Media Platform API", version="0.1.0", lifespan=lifespan)

    if settings.debug:
        allow_origins, allow_credentials = ["*"], False
    else:
        allow_origins, allow_credentials = settings.cors_origins, True

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Log the detail; return a generic message so internals are never leaked.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(health_router.router)
    app.include_router(auth_router.router)
    # social before media so /media/favorites resolves before /media/{media_id}
    app.include_router(social_router.router)
    app.include_router(media_router.router)
    app.include_router(notifications_router.router)
    app.include_router(ws_router.router)
    app.include_router(admin_router.router)
    app.include_router(downloads_router.router)
    app.include_router(objects_router.router)
    return app


app = create_app()
