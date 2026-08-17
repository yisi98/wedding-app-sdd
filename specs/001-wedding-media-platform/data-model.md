# Phase 1 Data Model: Wedding Media Platform

Storage: PostgreSQL 15 via async SQLAlchemy 2, migrated with Alembic. All tables carry
`created_at` / `updated_at` timestamps unless noted. Ten tables across three migrations.

## Entities

### users

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| username | string, **unique** | the guest's chosen display name; login key (get-or-create) |
| email | string, nullable | **legacy — excluded from all API responses** (ADR gotcha) |
| hashed_password | string | sentinel value for guests; real hash only conceptually (auth is event-password based) |
| role | enum(`guest`,`admin`) | authorization |
| language_preference | enum(`en`,`zh`,`ru`) | drives localized API messages |
| is_active | bool | deactivation revokes access |

### refresh_tokens

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| user_id | FK→users | |
| token_hash | string | SHA-256 of the refresh token (never stored in plaintext) |
| expires_at | datetime | 7-day lifetime |
| is_revoked | bool | set on rotation and on logout (all user tokens) |

### media

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| uploader_id | FK→users | owner |
| filename | string | stored/generated name |
| original_filename | string | as provided by guest |
| file_hash | string, **unique** | SHA-256 content hash (dedup key, Principle VI) |
| file_size | int | bytes |
| mime_type | string | validated on upload-init |
| media_type | enum(`image`,`video`) | |
| storage_path / thumbnail_path / optimized_path | string | object-storage keys |
| width / height | int, nullable | images/videos |
| duration | float, nullable | videos |
| exif_data | JSON, nullable | extracted capture metadata |
| phash | string, nullable | perceptual hash for "similar photos" |
| lqip | string, nullable | low-quality blur placeholder (data URI/base64) |
| view_count | int | denormalized counter |
| status | enum(`pending`,`processing`,`ready`,`failed`) | processing lifecycle |
| is_visible | bool | admin moderation; guests never see `false` |

### reactions

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| user_id | FK→users | |
| media_id | FK→media | |
| reaction_type | enum(`like`,`love`,`laugh`) | |
| — | **UNIQUE(user_id, media_id)** | at most one reaction per guest per item |

### comments

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| user_id | FK→users | author |
| media_id | FK→media | |
| content | text | |
| is_deleted | bool | soft delete (author or admin) |

### favorites

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| user_id | FK→users | |
| media_id | FK→media | |
| — | **UNIQUE(user_id, media_id)** | personal bookmark, once per item |

### activity_events

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| event_type | enum(`new_upload`,`new_reaction`,`new_comment`,`new_favorite`) | |
| user_id | FK→users | actor |
| media_id | FK→media, nullable | subject |
| payload | JSON | event detail for the feed/toasts |

### push_subscriptions

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| user_id | FK→users | |
| endpoint | string | web-push endpoint |
| p256dh | string | client public key |
| auth | string | auth secret |

### event_config (singleton, id=1)

| Field | Type | Notes |
|-------|------|-------|
| id | PK (=1) | single row |
| uploads_enabled | bool | global archive-mode switch (FR-010) |
| max_image_bytes / max_video_bytes | int | size limits (defaults: 50 MB / 500 MB) |
| event_name | string | display |
| event_date | date | display |

## Relationships (summary)

- `users` 1─* `media`, `reactions`, `comments`, `favorites`, `refresh_tokens`,
  `push_subscriptions`, `activity_events`.
- `media` 1─* `reactions`, `comments`, `favorites`, `activity_events`.
- Denormalized counts (reactions/comments/favorites/views) live on `media` for fast
  gallery rendering and are kept in sync by the service layer.

## Validation Rules (from requirements)

- `media.file_hash` UNIQUE enforces FR-007 dedup at the database level (race-safe).
- `reactions` and `favorites` UNIQUE(user_id, media_id) enforce FR-016 / FR-018.
- Uploads rejected when `mime_type` disallowed or size exceeds `event_config` limits
  (FR-008) and when `uploads_enabled = false` (FR-010).
- Guest-facing queries MUST filter `is_visible = true` and `status = ready` (FR-015).
- `username` UNIQUE enforces get-or-create identity (FR-001).

## State Transitions

- **media.status**: `pending` → `processing` → `ready`; any stage may go to `failed`.
  Only `ready` (and `is_visible = true`) media appears in guest views.
- **refresh_tokens**: active → revoked (on rotation or logout); a rotated token is never
  reusable (FR-005).

## Legacy `users.email` (T088)

The `users.email` column is retained by the schema but is **intentionally excluded from
every API response and the admin CSV export** (verified). It is a legacy remnant; a future
cleanup migration may drop it once confirmed unused by any consumer. Do not add it to any
response schema.

## Migrations

- `0001_initial_schema` — users, refresh_tokens, media, event_config (US1–US3 core).
- `0002_phase3_social_search_sharing` — reactions, comments, favorites, share_links;
  search/discovery indexes (US4; the share_links half is withdrawn — see below).
- `0003_phase4_realtime_pwa` — activity_events, push_subscriptions (US6, US7).

## Withdrawn tables

- `share_links` — created by `0002_phase3_social_search_sharing`, dropped by
  `0005_drop_share_links`. Withdrawn together with FR-020/FR-021 under constitution
  amendment 1.1.0 (2026-08-17). Both migrations are kept so the history replays cleanly
  on a fresh database; do not squash them.
- `media.uploader_id` became nullable in `0006_nullable_uploader_fk` with
  `ondelete="SET NULL"`, so deleting a user preserves that user's uploads rather than
  failing on the foreign key.
