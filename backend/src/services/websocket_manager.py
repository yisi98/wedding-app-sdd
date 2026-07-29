"""In-process WebSocket connection manager with an optional Redis pub/sub bridge.

`broadcast` fans a message out to all locally-connected clients. When `REDIS_URL` is set,
`publish` also publishes to a Redis channel so other backend workers can rebroadcast to
their own clients (a subscriber loop is started in the app lifespan). Without Redis (dev/
test), publish == local broadcast.
"""

import json

from ..config import get_settings


class ConnectionManager:
    def __init__(self) -> None:
        self.active: set = set()

    async def connect(self, websocket) -> None:
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket) -> None:
        self.active.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        for websocket in list(self.active):
            try:
                await websocket.send_json(message)
            except Exception:  # noqa: BLE001 — drop dead connections
                self.disconnect(websocket)

    async def publish(self, message: dict) -> None:
        """Broadcast locally and, if configured, fan out to other workers via Redis."""
        await self.broadcast(message)
        settings = get_settings()
        if settings.redis_url:
            try:
                import redis.asyncio as aioredis

                client = aioredis.from_url(settings.redis_url)
                await client.publish(settings.activity_channel, json.dumps(message))
                await client.aclose()
            except Exception:  # noqa: BLE001 — real-time is best-effort
                pass


manager = ConnectionManager()
