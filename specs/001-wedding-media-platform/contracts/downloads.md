# Contract: Bulk Download (`/api/v1/downloads`)

Implements US9 / FR-BULK.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/downloads/bulk` | access token | Body `{ media_ids: [id, ...] }`. Streams a server-side ZIP containing exactly the requested (visible, ready) items. |

**Notes**: ZIP is streamed to avoid buffering large archives in memory. Hidden/failed
items are excluded even if requested.
