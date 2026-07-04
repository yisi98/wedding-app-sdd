# Contract: Media & Gallery (`/api/v1/media`)

Implements US2 (upload) and US3 (gallery/discovery). All require an access token.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/media` | Gallery list. Query: `type`, `uploader`, `date_from`, `date_to`, `q` (filename ILIKE), `sort` (`newest`\|`oldest`\|`most_viewed`\|`most_liked`), pagination cursor. Returns only `status=ready` **and** `is_visible=true` items with denormalized counts + `lqip`. |
| GET | `/media/{id}` | Single item detail. Hidden/nonexistent → **404** (FR-015). |
| GET | `/media/{id}/similar` | "Similar photos" strip via pHash proximity. |
| GET | `/media/favorites` | Current user's favorited items (US4). |
| POST | `/media/upload/init` | Validate `mime_type` + size against `event_config`; check `file_hash`. Duplicate → **409/duplicate** (no store). Uploads paused → refused (FR-010). Else return a presigned PUT URL + media id (status `pending`). |
| POST | `/media/upload/confirm` | Client PUT-to-storage done; enqueue background processing (Celery). Sets status `processing`. |
| DELETE | `/media/{id}` | **Admin only** — delete media. Non-admin → **403**. |

**Upload flow**: `init` (validate + dedup) → client uploads bytes directly to object
storage → `confirm` (enqueue processing). Background worker produces 400×400 thumbnail,
WebP-optimized version, pHash, LQIP, EXIF, and video duration, then sets `ready` (or
`failed`).
