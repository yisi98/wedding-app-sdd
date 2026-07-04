# Contract: Social Engagement (`/api/v1/media/{id}/...`)

Implements US4 / FR-SOCIAL. All require an access token.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/media/{id}/reactions` | Body `{ reaction_type: like\|love\|laugh }`. Toggling logic: same type → remove; different type → replace. Enforced by UNIQUE(user_id, media_id). |
| GET | `/media/{id}/comments` | List non-deleted comments. |
| POST | `/media/{id}/comments` | Add a comment. |
| DELETE | `/media/{id}/comments/{cid}` | Soft-delete. Author may delete own; admin may delete any; else **403**. |
| POST | `/media/{id}/favorites` | Toggle favorite for current user (UNIQUE per user/item). |
| POST | `/media/{id}/view` | Increment the item's view counter. |

**Invariant**: at most one reaction per user per item; switching type never yields more
than one (SC-007). Denormalized counts on `media` updated by the service layer.
