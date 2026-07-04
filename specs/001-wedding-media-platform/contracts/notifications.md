# Contract: Activity & Notifications (`/api/v1`)

Implements US6 / FR-RT (activity feed, web push, optional email).

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/activity` | access token | Recent-activity feed: `new_upload` \| `new_reaction` \| `new_comment` \| `new_favorite` events, newest first. |
| POST | `/push/subscribe` | access token | Register a web-push subscription `{ endpoint, p256dh, auth }`. |
| DELETE | `/push/subscribe` | access token | Unsubscribe (stop delivery). |
| GET | `/push/vapid-public-key` | none | Return the VAPID public key for client subscription. |

**Email**: optional SMTP notifications via aiosmtplib, **disabled** when `SMTP_HOST` is
empty (FR-025) — no attempt is made and nothing fails. Live toasts are delivered over the
WebSocket channel (see `websocket.md`), not this REST surface.
