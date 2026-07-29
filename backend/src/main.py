"""FastAPI application factory.

CORS is environment-driven (research.md): DEBUG allows all origins with credentials off;
production uses an explicit allow-list with credentials on. In DEBUG the schema is created
from ORM metadata for zero-setup local runs; production uses Alembic migrations.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import engine
from .models import Base
from .models.event_config import SINGLETON_ID, EventConfig
from .routers import admin as admin_router
from .routers import auth as auth_router
from .routers import downloads as downloads_router
from .routers import health as health_router
from .routers import media as media_router
from .routers import notifications as notifications_router
from .routers import share as share_router
from .routers import social as social_router
from .routers import ws as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.debug:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Ensure the singleton event_config row exists.
        from sqlalchemy import select

        from .db import async_session_factory

        async with async_session_factory() as session:
            existing = await session.get(EventConfig, SINGLETON_ID)
            if existing is None:
                session.add(EventConfig(id=SINGLETON_ID))
                await session.commit()
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

    app.include_router(health_router.router)
    app.include_router(auth_router.router)
    # social before media so /media/favorites resolves before /media/{media_id}
    app.include_router(social_router.router)
    app.include_router(media_router.router)
    app.include_router(share_router.router)
    app.include_router(notifications_router.router)
    app.include_router(ws_router.router)
    app.include_router(admin_router.router)
    app.include_router(downloads_router.router)
    return app


app = create_app()
