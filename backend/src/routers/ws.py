"""WebSocket router (US6 / contracts/websocket.md).

Clients connect with `?token=<access token>`. On connect the server sends a hello frame,
then keeps the connection open; application events are pushed via the connection manager.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import get_settings
from ..services import auth as auth_service
from ..services.websocket_manager import manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None) -> None:
    settings = get_settings()
    payload = auth_service.decode_access_token(token or "", settings)
    if payload is None or "sub" not in payload:
        await websocket.close(code=1008)  # policy violation
        return
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected"})
        while True:
            await websocket.receive_text()  # keepalive; inbound messages ignored
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:  # noqa: BLE001
        manager.disconnect(websocket)
