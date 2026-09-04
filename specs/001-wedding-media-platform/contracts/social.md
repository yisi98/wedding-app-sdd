# Contract: Social Engagement (`/api/v1/media/{id}/...`)

Implements US4 / FR-SOCIAL. All require an access token.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/media/{id}/reactions` | Body `{ reaction_type: like\|love\|laugh }`. Toggling logic: same type → remove; different type → replace. Enforced by UNIQUE(user_id, media_id). |
| GET | `/media/{id}/comments` | List non-deleted comments. |
| POST | `/media/{id}/comments` | Add a comment. |
| DELETE | `/media/{id}/comments/{cid}` | Soft-delete. Author may delete own; admin may delete any; else **403**. |
| POST | `/media/{id}/favorites` | Toggle favorite for current user (UNIQUE per user/item). |
| GET | `/media/favorites` | List the caller's favorited items (ready + visible), newest favorite first. |
| POST | `/media/favorites/bulk-remove` | Body `{ media_ids: [1..200 ids] }`. Removes the caller's favorite rows only; returns `{ removed, skipped }` where `skipped` covers ids the caller had not favorited. Added 2026-09-04 for bulk actions on the favorites page. |
| POST | `/media/{id}/view` | Increment the item's view counter. |

**Invariant**: at most one reaction per user per item; switching type never yields more
than one (SC-007). Denormalized counts on `media` updated by the service layer.
