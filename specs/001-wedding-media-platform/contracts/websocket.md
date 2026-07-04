# Contract: Real-Time Channel (`/ws`)

Implements US6 / FR-022 (live notifications).

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /ws` (WebSocket upgrade) | access token (query/subprotocol) | Bi-directional channel that pushes live toasts for `new_upload`, `new_reaction`, and `new_comment`. |

**Mechanism**: FastAPI WebSocket endpoint bridged to Redis pub/sub. Application events are
published to a Redis channel; each connected WebSocket subscribes and forwards messages to
its client, so events fan out across multiple backend workers. Message payload mirrors the
corresponding `activity_events` record (`event_type`, `user`, `media`, `payload`).
