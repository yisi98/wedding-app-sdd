---
description: "Task list for Wedding Media Platform implementation"
---

# Tasks: Wedding Media Platform

**Input**: Design documents from `/specs/001-wedding-media-platform/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED. The constitution mandates an integration test for every API
endpoint, so each user-story phase writes contract/integration tests before implementation.

**Organization**: Tasks are grouped by user story (US1–US9) so each can be built, tested,
and demoed independently. MVP = US1 + US2 + US3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1–US9 (setup/foundational/polish tasks have no story label)
- File paths follow the web-app layout in plan.md: `backend/src/...`, `frontend/src/...`

## Path Conventions

- Backend: `backend/src/{routers,services,models,schemas,workers,i18n}/`, tests in
  `backend/tests/integration/`, migrations in `backend/alembic/`
- Frontend: `frontend/src/{app,components,stores,lib,locales}/`, assets in `frontend/public/`
- Infra: `infra/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton, tooling, and local infrastructure

- [X] T001 Create the `backend/` and `frontend/` project trees per plan.md structure
- [X] T002 Initialize backend Python 3.12 project with `uv` and dependencies (FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, python-jose, bcrypt, boto3, Celery, redis, Pillow, ffmpeg-python, imagehash, pywebpush, aiosmtplib, pytest) in `backend/pyproject.toml`
- [X] T003 [P] Initialize frontend Next.js 14 + TypeScript project with deps (TailwindCSS, react-i18next, Zustand, axios) in `frontend/package.json`
- [X] T004 [P] Author `infra/docker-compose.dev.yml` (PostgreSQL 15, Redis 7, MinIO, backend, worker, frontend)
- [X] T005 [P] Add `infra/nginx/` reverse-proxy + TLS config and `infra/docker-compose.prod.yml`
- [X] T006 [P] Configure backend linting/formatting (ruff/black) and frontend eslint/prettier
- [X] T007 [P] Add `.env.example` (EVENT_PASSWORD_HASH, JWT_SECRET, VAPID keys, storage keys, DATABASE_URL, REDIS_URL, optional SMTP_HOST) and ensure `.env` + `.claude/` are git-ignored
- [X] T008 [P] Add GitHub Actions CI (`.github/workflows/ci.yml`): lint + pytest + Docker build

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T009 Implement `backend/src/config.py` with `@lru_cache get_settings()` reading `.env` (document restart-to-reload behavior)
- [X] T010 Implement async engine/session in `backend/src/db.py`
- [X] T011 Create the FastAPI app factory in `backend/src/main.py` (router registration, env-based CORS: `["*"]` when DEBUG else explicit allow-list)
- [X] T012 Initialize Alembic in `backend/alembic/` and wire the async migration environment
- [X] T013 Author migration `0001_initial_schema` (users, refresh_tokens, media, event_config) in `backend/alembic/versions/`
- [X] T014 [P] Create base ORM models in `backend/src/models/` for `user.py`, `refresh_token.py`, `media.py`, `event_config.py` per data-model.md
- [X] T015 [P] Create Celery app in `backend/src/workers/celery_app.py` (Redis broker; `--pool=solo` note for Windows)
- [X] T016 [P] Implement `backend/src/services/storage.py` (boto3 S3 client, presigned URL init/confirm, MinIO↔OSS parity)
- [X] T017 [P] Implement `backend/src/services/deduplication.py` (SHA-256 hashing + hash-existence check)
- [X] T018 [P] Configure error handling + structured logging middleware in `backend/src/main.py`
- [X] T019 Implement `backend/src/i18n/` gettext catalogs (en/zh/ru) + message resolver keyed on `language_preference`
- [X] T020 [P] Set up frontend i18n init in `frontend/src/lib/i18n.ts` with `frontend/src/locales/{en,zh,ru}.json` and self-hosted fonts in `frontend/public/`
- [X] T021 [P] Implement shared axios client + auth interceptor in `frontend/src/lib/api.ts` and Zustand auth store in `frontend/src/stores/auth.ts`
- [X] T022 Implement `GET /api/v1/health` (DB + Redis probes, 503 on degraded) in `backend/src/routers/health.py` + integration test in `backend/tests/integration/test_health.py`

**Checkpoint**: Foundation ready — user stories can now begin

---

## Phase 3: User Story 1 - Guest Access & Authentication (Priority: P1) 🎯 MVP

**Goal**: Name + event password admits a guest (get-or-create) with rotating sessions

**Independent Test**: New name + correct password → admitted; wrong password → 401; same
name → same account; rotated refresh token → 401

### Tests for User Story 1 ⚠️ (write first, ensure they FAIL)

- [X] T023 [P] [US1] Integration test for `POST /auth/login` (new account, get-or-create, wrong password 401) in `backend/tests/integration/test_auth_login.py`
- [X] T024 [P] [US1] Integration test for `POST /auth/refresh` rotation + reused-token 401 in `backend/tests/integration/test_auth_refresh.py`
- [X] T025 [P] [US1] Integration test for `POST /auth/logout` (revoke all), `GET /auth/me` (no email), `PUT /auth/profile` in `backend/tests/integration/test_auth_session.py`

### Implementation for User Story 1

- [X] T026 [US1] Implement `backend/src/services/auth.py` (event-password verify, get-or-create user, JWT access 15 min, refresh 7 days w/ rotation, revoke-all)
- [X] T027 [P] [US1] Add Pydantic auth schemas in `backend/src/schemas/auth.py` (exclude `email` from all responses)
- [X] T028 [US1] Implement `backend/src/routers/auth.py` (`/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`, `/auth/profile`) + access-token dependency
- [X] T029 [P] [US1] Build login screen (display name + event password, single form) in `frontend/src/app/login/page.tsx`
- [X] T030 [US1] Wire silent access-token refresh via rotating refresh token in `frontend/src/lib/api.ts`

**Checkpoint**: US1 fully functional and independently testable (MVP entry point)

---

## Phase 4: User Story 2 - Media Upload with Deduplication (Priority: P1)

**Goal**: Multi-file upload with progress, SHA-256 dedup, and background processing

**Independent Test**: Upload new file → ready; re-upload same file → duplicate, not stored;
over-limit/disallowed → rejected; archive mode → refused

### Tests for User Story 2 ⚠️

- [X] T031 [P] [US2] Integration test for `POST /media/upload/init` (validation, size limits, duplicate 409, uploads-paused) in `backend/tests/integration/test_upload_init.py`
- [X] T032 [P] [US2] Integration test for `POST /media/upload/confirm` (enqueue, status processing) in `backend/tests/integration/test_upload_confirm.py`
- [X] T033 [P] [US2] Integration test for background processing outputs (thumbnail/webp/phash/lqip/exif/duration → ready|failed) in `backend/tests/integration/test_media_processing.py`

### Implementation for User Story 2

- [X] T034 [US2] Implement `backend/src/services/media.py` upload-init (validate mime/size vs `event_config`, dedup via T017, presigned URL, `uploads_enabled` gate)
- [X] T035 [US2] Implement upload-confirm (persist media `processing`, enqueue Celery task) in `backend/src/services/media.py`
- [X] T036 [P] [US2] Implement media processing task (400×400 thumbnail, WebP, pHash, LQIP, EXIF, video duration) in `backend/src/workers/media_processing.py`
- [X] T037 [P] [US2] Add media/upload Pydantic schemas in `backend/src/schemas/media.py`
- [X] T038 [US2] Implement `backend/src/routers/media.py` upload endpoints (`/media/upload/init`, `/media/upload/confirm`)
- [X] T039 [P] [US2] Build drag-and-drop multi-upload component with per-file + total progress in `frontend/src/components/Uploader.tsx`

**Checkpoint**: US1 + US2 work independently

---

## Phase 5: User Story 3 - Gallery Browsing & Discovery (Priority: P1)

**Goal**: Infinite-scroll gallery with filter/sort/search and a full-screen lightbox

**Independent Test**: Gallery lazy-loads; filter/sort/search update results; lightbox
navigates + shows similar; hidden media absent

### Tests for User Story 3 ⚠️

- [X] T040 [P] [US3] Integration test for `GET /media` (filters, sort, search, pagination, excludes hidden/non-ready) in `backend/tests/integration/test_gallery_list.py`
- [X] T041 [P] [US3] Integration test for `GET /media/{id}` (hidden → 404) and `GET /media/{id}/similar` in `backend/tests/integration/test_media_detail.py`

### Implementation for User Story 3

- [X] T042 [US3] Implement gallery query in `backend/src/services/media.py` (type/uploader/date/`q` ILIKE filters, sort newest/oldest/most_viewed/most_liked, `is_visible`+`ready` guard, denormalized counts)
- [X] T043 [US3] Implement pHash "similar" lookup in `backend/src/services/media.py`
- [X] T044 [US3] Implement `backend/src/routers/media.py` read endpoints (`GET /media`, `/media/{id}`, `/media/{id}/similar`)
- [X] T045 [P] [US3] Build infinite-scroll gallery grid with lazy loading + skeletons in `frontend/src/components/GalleryGrid.tsx` and `frontend/src/stores/gallery.ts`
- [X] T046 [P] [US3] Build lightbox (image/video, keyboard/swipe nav, download, similar strip) in `frontend/src/components/Lightbox.tsx`

**Checkpoint**: MVP (US1–US3) complete — deployable/demoable

---

## Phase 6: User Story 4 - Social Engagement (Priority: P2)

**Goal**: Reactions (toggle/switch), comments (soft delete), favorites, view counts

**Independent Test**: Same-type react twice → net zero; switch → count one; delete own
comment; favorite appears in list; views increment

### Tests for User Story 4 ⚠️

- [X] T047 [P] [US4] Integration test for reactions toggle/replace invariant in `backend/tests/integration/test_reactions.py`
- [X] T048 [P] [US4] Integration test for comments add/soft-delete (author vs admin) in `backend/tests/integration/test_comments.py`
- [X] T049 [P] [US4] Integration test for favorites (list, uniqueness) + view increment in `backend/tests/integration/test_favorites_views.py`

### Implementation for User Story 4

- [X] T050 [P] [US4] Add migration `0002_phase3_social_search_sharing` (reactions, comments, favorites, share_links + indexes) in `backend/alembic/versions/`
- [X] T051 [P] [US4] Create `reaction.py`, `comment.py`, `favorite.py` models in `backend/src/models/`
- [X] T052 [US4] Implement `backend/src/services/social.py` (reaction toggle/replace, comment soft-delete rules, favorites, view increment, denormalized count updates)
- [X] T053 [US4] Implement social endpoints in `backend/src/routers/social.py` (`/media/{id}/reactions|comments|favorites|view`, `GET /media/favorites`)
- [X] T054 [P] [US4] Add reaction/comment/favorite UI to `frontend/src/components/Lightbox.tsx` and a favorites view in `frontend/src/app/favorites/page.tsx`

**Checkpoint**: US1–US4 independently functional

---

## Phase 7: User Story 5 - Sharing — WITHDRAWN

**Descoped by constitution amendment 1.1.0 (2026-08-17).** The feature was built, then
removed from the codebase during development; the amendment records the couple's decision
to leave it out rather than rebuild it before the 2026-09-15 deadline.

T055–T059 are **withdrawn, not completed**. They had been marked `[X]`, but none of their
artifacts exist: `test_share.py`, `models/share_link.py`, `services/share.py`,
`routers/share.py`, `components/ShareDialog.tsx`, `app/share/[token]/page.tsx`. The IDs
are retired and not reused.

- ~~T055 [P] [US5] Integration test for `POST /share` + `GET /share/{token}`~~ — withdrawn
- ~~T056 [P] [US5] Create `share_link.py` model~~ — withdrawn
- ~~T057 [US5] Implement `backend/src/services/share.py`~~ — withdrawn
- ~~T058 [US5] Implement `backend/src/routers/share.py`~~ — withdrawn
- ~~T059 [P] [US5] Build share UI + share landing~~ — withdrawn

**Checkpoint**: US1–US4 independently functional

---

## Phase 8: User Story 6 - Real-Time & Notifications (Priority: P2)

**Goal**: Live WebSocket toasts, activity feed, web push, optional email

**Independent Test**: Act in one session → toast in another + feed lists it; subscribe →
push; unsubscribe → stop; no SMTP → no email attempted

### Tests for User Story 6 ⚠️

- [X] T060 [P] [US6] Integration test for `GET /activity` feed in `backend/tests/integration/test_activity.py`
- [X] T061 [P] [US6] Integration test for push subscribe/unsubscribe + `GET /push/vapid-public-key` in `backend/tests/integration/test_push.py`
- [X] T062 [P] [US6] Integration/functional test for `/ws` broadcast via Redis pub/sub in `backend/tests/integration/test_websocket.py`

### Implementation for User Story 6

- [X] T063 [P] [US6] Add migration `0003_phase4_realtime_pwa` (activity_events, push_subscriptions) + models `activity_event.py`, `push_subscription.py` in `backend/`
- [X] T064 [US6] Implement `backend/src/services/activity.py` (record events) and `backend/src/services/websocket_manager.py` (Redis pub/sub bridge)
- [X] T065 [P] [US6] Implement `backend/src/services/push_service.py` (pywebpush/VAPID) and `backend/src/services/email_service.py` (aiosmtplib, no-op when SMTP_HOST empty)
- [X] T066 [US6] Implement `backend/src/routers/notifications.py` (`/activity`, `/push/subscribe`, `/push/vapid-public-key`) and `backend/src/routers/ws.py` (`/ws`)
- [X] T067 [US6] Emit activity events + publish to Redis from upload/reaction/comment/favorite services (wire into T034/T052)
- [X] T068 [P] [US6] Build live-toast + activity-feed UI and push subscribe toggle in `frontend/src/stores/realtime.ts` and `frontend/src/components/ActivityFeed.tsx`

**Checkpoint**: US1–US6 independently functional

---

## Phase 9: User Story 7 - Progressive Web App (Priority: P2)

**Goal**: Installable, offline-tolerant, LQIP blur-up

**Independent Test**: Install to home screen; offline → previously loaded content viewable;
images blur up

### Tests for User Story 7 ⚠️

- [X] T069 [P] [US7] Functional/E2E test: manifest present, service worker registers, offline cache serves prior content in `frontend/tests/pwa.spec.ts` — reopened and genuinely delivered 2026-08-17: 4 Playwright specs (installability + every manifest icon resolving, worker reaches `activated`, offline reload still renders the shell, `/api/` never cached), run against a production build and wired into CI

### Implementation for User Story 7

- [X] T070 [P] [US7] Add PWA manifest + icons in `frontend/public/manifest.webmanifest`
- [X] T071 [US7] Implement service worker (offline caching, add-to-home-screen prompt) in `frontend/public/sw.js` and register it in `frontend/src/app/layout.tsx`
- [X] T072 [P] [US7] Implement LQIP blur-up image component (uses `media.lqip`) in `frontend/src/components/BlurImage.tsx` and use it in the gallery grid

**Checkpoint**: US1–US7 independently functional

---

## Phase 10: User Story 8 - Admin Console (Priority: P2)

**Goal**: Stats dashboard, user management, moderation, CSV export, with self-account guard

**Independent Test**: Dashboard totals; promote/deactivate; hide item → gone from guest
gallery, present in admin list; non-admin → 403; CSV export

### Tests for User Story 8 ⚠️

- [X] T073 [P] [US8] Integration test for `GET /admin/stats` in `backend/tests/integration/test_admin_stats.py`
- [X] T074 [P] [US8] Integration test for user mgmt (list/search, promote, deactivate, delete, self-account guard) in `backend/tests/integration/test_admin_users.py`
- [X] T075 [P] [US8] Integration test for media moderation (list incl. hidden, visibility toggle, guest 404) + CSV export in `backend/tests/integration/test_admin_media.py`
- [X] T076 [P] [US8] Integration test asserting non-admin → 403 on every `/admin/*` route in `backend/tests/integration/test_admin_authz.py`

### Implementation for User Story 8

- [X] T077 [US8] Implement admin-role dependency/guard (incl. own-account protection) in `backend/src/services/auth.py`
- [X] T078 [US8] Implement admin stats + user-management + moderation logic in `backend/src/services/media.py`/`auth.py` and CSV export in a helper
- [X] T079 [US8] Implement `backend/src/routers/admin.py` (`/admin/stats`, `/admin/users[...]`, `/admin/media`, `/admin/media/{id}/visibility`, `/admin/export/media`)
- [X] T080 [P] [US8] Build admin dashboard + user table + moderation UI in `frontend/src/app/admin/page.tsx`

**Checkpoint**: US1–US8 independently functional

---

## Phase 11: User Story 9 - Bulk Download (Priority: P3)

**Goal**: Multi-select → single streamed ZIP

**Independent Test**: Select several items → one ZIP with exactly those items

### Tests for User Story 9 ⚠️

- [X] T081 [P] [US9] Integration test for `POST /downloads/bulk` (ZIP contents, excludes hidden) in `backend/tests/integration/test_bulk_download.py`

### Implementation for User Story 9

- [X] T082 [US9] Implement `backend/src/services/zip_service.py` (streamed ZIP of requested visible/ready items)
- [X] T083 [US9] Implement `backend/src/routers/downloads.py` (`POST /downloads/bulk`)
- [X] T084 [P] [US9] Add multi-select + bulk-download action to `frontend/src/components/GalleryGrid.tsx`

**Checkpoint**: All user stories independently functional

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Quality bars and go-live gates

- [X] T085 [P] EN/ZH/RU string-parity audit across `frontend/src/locales/*` and `backend/src/i18n/*` (SC-004)
- [ ] T086 Load test sustaining 150 concurrent users (browse + upload) with a report in `infra/loadtest/` (SC-003) — GO-LIVE GATE. Reopened 2026-08-17 (had been marked done without ever running). Script now covers upload as well as browse, grades itself against numeric p95 budgets and exits non-zero on a miss; verified end-to-end against a local backend, including the failure path. **Remaining: the 150-user run against staging**, which needs the deployed stack
- [X] T087 [P] Security hardening pass: verify no secrets in repo, prod CORS allow-list, presigned-URL scope, rate limiting
- [X] T088 [P] Confirm `users.email` is excluded from every response; add cleanup-migration note
- [ ] T089 Run full `quickstart.md` validation (steps 1–9) against a prod-like deploy — BLOCKED: needs deployed stack (core flows covered by 97 integration tests + frontend build; see docs/DEPLOY.md)
- [ ] T090 Production deploy + smoke test on AliCloud with ICP filing active (SC-010, deadline 2026-09-15) — BLOCKED on the ICP filing (operator task; runbook in docs/DEPLOY.md). Note: filing requires a mainland ECS on a 3-month subscription to already exist, so buying it is step 1 of the filing, not blocked by it. T086/T089 do not need ICP and can run on a Hong Kong region now — see "Staging without ICP" in the runbook

---

## Phase 13: Post-Plan Changes (back-filled 2026-08-17)

**Purpose**: Work that shipped after `/speckit-tasks` ran and never entered the artifacts.
Recorded here by `/speckit-converge` so `tasks.md` matches the repository. All are already
merged and covered by the green suite; they are logged for traceability, not to be redone.

### Delivered

- [X] T091 [P] Apply the editorial-monochrome theme (paper/charcoal/terracotta tokens) in `frontend/tailwind.config.ts` and global styles
- [X] T092 Replace the top nav with a left sidebar on desktop and a bottom tab bar on mobile (`md:` breakpoint) in `frontend/src/components/Nav.tsx`, with custom stroke icons in `frontend/src/components/icons.tsx` (Principle V, mobile-first)
- [X] T093 Split the upload entry point by input type in `frontend/src/lib/useUploader.ts` and `frontend/src/components/Uploader.tsx`: drag-and-drop on desktop only, a single picker control on mobile. Fixes the silent iOS Safari failure — `input[type=file].click()` must run in the same synchronous task as the tap to keep transient user activation (FR-006, amended)
- [X] T094 [P] Clear completed items from the upload progress list automatically and add a show/hide toggle to the event-password field (`UploadProgressList.tsx`, `login/page.tsx`)
- [X] T095 [P] Remove the "By status" and "Uploads (7d)" panels from the admin dashboard; `/admin/stats` keeps returning both fields (FR-029, amended)
- [X] T096 [P] Rename the event to "Natasha & Yisi's Wedding" across `frontend/src/locales/{en,zh,ru}.json` (Chinese: 娜塔莎和易斯的婚礼) and use the localized name for the bulk-download archive filename (FR-036, SC-004)
- [X] T097 Fix full-screen photo rendering in iOS Safari — images were zoomed and cropped instead of fitting the viewport (`Lightbox.tsx`, FR-014)
- [X] T098 Fix admin delete-user failing on the media foreign key: migration `0006_nullable_uploader_fk` makes `media.uploader_id` nullable with `ondelete="SET NULL"`, plus `PRAGMA foreign_keys=ON` for SQLite in `backend/src/db.py`, which ignores FKs by default where PostgreSQL does not (FR-030)
- [X] T099 Run Alembic on startup via `run_in_executor` in `backend/src/main.py`, and fail with an actionable message when an existing `wedding.db` has tables but no Alembic stamp — `create_all` only creates missing tables and never migrates an existing schema
- [X] T100 [P] Drop `share_links` (migration `0005_drop_share_links`) and remove the share service, router, model and UI — the change that constitution amendment 1.1.0 later formalised

### Outstanding

- [X] T101 [P] Delete the stale `share.cpython-312.pyc` and `share_link.cpython-312.pyc` bytecode under `backend/src/**/__pycache__/` — the last on-disk trace of the withdrawn module

**Checkpoint**: repository state and specification artifacts agree.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup — BLOCKS all user stories
- **User Stories (Phases 3–11)**: all depend on Foundational; then proceed in priority
  order (P1: US1→US2→US3, then P2: US4–US8, then P3: US9). US2/US3 build on US1's auth;
  US4/US5 add the 0002 migration; US6 adds the 0003 migration.
- **Polish (Phase 12)**: depends on all targeted stories being complete

### User Story Dependencies

- **US1 (P1)**: after Foundational — no story deps (MVP entry)
- **US2 (P1)**: after Foundational — uses US1 auth
- **US3 (P1)**: after Foundational — uses US1 auth; reads US2 media
- **US4, US5 (P2)**: after Foundational — introduce 0002 migration; independently testable
- **US6 (P2)**: after Foundational — 0003 migration; wires into upload/social event emit
- **US7 (P2)**: after Foundational — frontend-centric; uses US3 gallery + `media.lqip`
- **US8 (P2)**: after Foundational — moderation affects US3 visibility
- **US9 (P3)**: after Foundational — operates over US3 media

### Within Each User Story

- Tests written and failing before implementation
- Models → services → routers → frontend
- Story complete and independently testable before the next priority

### Parallel Opportunities

- All `[P]` Setup tasks (T003–T008) run together
- Foundational `[P]` tasks (T014–T021) run together after T009–T013
- Within a story, `[P]` tests run together, then `[P]` models
- Once Foundational is done, P2 stories US4/US5/US7 can be staffed in parallel by different
  developers (distinct files), integrating independently

---

## Implementation Strategy

### MVP First (US1–US3)

1. Phase 1 Setup → Phase 2 Foundational (CRITICAL, blocks everything)
2. Phase 3 US1 (auth) → Phase 4 US2 (upload) → Phase 5 US3 (gallery)
3. **STOP & VALIDATE**: guests can log in, upload, and browse — deployable MVP

### Incremental Delivery

- MVP (US1–US3) → add US4 → US5 → US6 → US7 → US8 → US9, testing/deploying each
  increment without breaking prior stories.

### Parallel Team Strategy

- Whole team lands Setup + Foundational, then splits P2 stories across developers once the
  MVP is green.

---

## Notes

- `[P]` = different files, no incomplete dependencies; `[Story]` maps a task to US1–US9
- Every API endpoint in `contracts/` has a corresponding integration test task (constitution mandate)
- Verify tests fail before implementing; commit after each task or logical group
- Stop at any checkpoint to validate a story independently
- Go-live gates (T085–T090) protect the 2026-09-15 production deadline
