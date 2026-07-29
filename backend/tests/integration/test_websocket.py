"""T062: WebSocket connect + broadcast fan-out (US6)."""

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.config import get_settings
from src.main import app
from src.models.user import User
from src.services import auth as auth_service
from src.services.websocket_manager import ConnectionManager


def test_ws_rejects_without_valid_token():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws"):
        pass


def test_ws_accepts_valid_token_and_sends_hello():
    settings = get_settings()
    token = auth_service.create_access_token(User(id=1, username="Ws", role="guest"), settings)
    client = TestClient(app)
    with client.websocket_connect(f"/ws?token={token}") as ws:
        assert ws.receive_json() == {"type": "connected"}


async def test_manager_broadcasts_to_all_connections():
    manager = ConnectionManager()

    class FakeWS:
        def __init__(self):
            self.received = []

        async def send_json(self, data):
            self.received.append(data)

    a, b = FakeWS(), FakeWS()
    manager.active.update({a, b})
    await manager.broadcast({"event_type": "new_upload"})
    assert a.received == b.received == [{"event_type": "new_upload"}]
