# Contract: Media & Gallery (`/api/v1/media`)

Implements US2 (upload) and US3 (gallery/discovery). All require an access token unless noted.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/media` | Gallery list. Query: `media_type`, `uploader`, `date_from`, `date_to` (**inclusive of the whole day**), `q` (filename ILIKE), `sort` (`newest`\|`oldest`\|`most_viewed`\|`most_liked`), `limit`, `offset`. Returns only `status=ready` **and** `is_visible=true` items with denormalized counts + `lqip`; response `{ items, has_more, next_offset }`. |
| GET | `/media/count` | Total ready + visible items matching the same filters (`media_type`, `uploader`, `date_from`, `date_to`) without pagination — backs the gallery's "N items" badge. |
| GET | `/media/ids` | All media ids matching the given filters — backs "select all matching filter". |
| GET | `/media/{id}` | Single item detail (`MediaOut`, includes `storage_path`). Hidden/nonexistent → **404** (FR-015). |
| GET | `/media/{id}/similar` | "Similar photos" strip via dHash proximity. |
| GET | `/media/favorites` | Current user's favorited items (US4). |
| POST | `/media/upload/init` | Validate `mime_type` + declared size against `event_config`; check `file_hash`. Duplicate → **409** `{message, media_id}` (no store; also enforced by the DB unique constraint, so a concurrent race still returns 409). Uploads paused → **403** (FR-010). Else return `{ media_id, upload_url, storage_key, status: "pending" }`. |
| PUT | `/media/upload/raw?key=…` | **Dev/local-storage only** stand-in for the direct client→OSS PUT. Validates the **actual** byte size against the limit (declared size is not trusted) and records the true size. Returns **404** when S3 storage is configured. |
| POST | `/media/upload/confirm` | Client upload done; enqueue background processing (Celery in prod, inline/eager in dev). Sets status `processing` → `ready`/`failed`. |
| DELETE | `/media/{id}` | **Owner only** — delete the caller's own upload (original + derivatives + row; comments/reactions/favorites cascade; the file hash is freed for re-upload). Someone else's item or a missing id → **404** (FR-039, added 2026-08-30; previously admin-only via `/admin/media/{id}`, which remains the path for deleting *any* user's media). |
| POST | `/media/bulk-delete` | **Multi-select delete** — body `{ media_ids }` (1–100). Deletes only the caller's own uploads among the ids; ids belonging to someone else (or already gone) are never deleted and are returned in `skipped` so the client keeps those tiles visible. Response `{ deleted, skipped }` (FR-039 extension, added 2026-08-31). |

**Media bytes** are served at `GET /media-object/{key}` (app-root, unauthenticated — keys
embed the content SHA-256 so they are unguessable capability URLs, matching CDN serving in
prod). In production `NEXT_PUBLIC_MEDIA_BASE` points the client straight at the AliCloud CDN.

**Upload flow**: `init` (validate + dedup, returns a presigned URL) → client uploads bytes
(directly to OSS in prod via the presigned URL; via `/upload/raw` in local dev) → `confirm`
(enqueue processing). Background worker produces a 400×400 thumbnail, WebP-optimized
version, dHash, LQIP, EXIF, and (for video) duration, then sets `ready` (or `failed`).
