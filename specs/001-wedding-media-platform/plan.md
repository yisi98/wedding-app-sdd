# Implementation Plan: Wedding Media Platform

**Branch**: `001-wedding-media-platform` | **Date**: 2026-07-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-wedding-media-platform/spec.md`

**Note**: This file is the `/speckit-plan` output. Design details live in the companion
artifacts: [research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/), [quickstart.md](./quickstart.md).

## Summary

Deliver a private, password-protected, trilingual (EN/中文/Русский) PWA for collecting
and sharing photos and videos from a single ~150-guest wedding, with real-time
engagement and China-resident hosting. The approach is a two-tier web application: a
Next.js PWA front end and a FastAPI (async) back end backed by PostgreSQL, Redis, and
S3-compatible object storage (MinIO in dev, AliCloud OSS in prod). Media is uploaded
directly to object storage via presigned URLs, deduplicated by SHA-256, and post-processed
asynchronously by Celery workers (thumbnails, WebP, pHash, LQIP, EXIF, duration).
Real-time updates flow over WebSockets bridged through Redis pub/sub. All infrastructure
is China-resident with no blocked third-party dependencies.

## Technical Context

**Language/Version**: Backend Python 3.12; Frontend TypeScript (Node 20) with Next.js 14 (App Router)

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, python-jose (JWT),
  bcrypt, boto3, Celery, Redis client, Pillow, ffmpeg-python, imagehash (pHash),
  pywebpush (VAPID), aiosmtplib
- Frontend: Next.js 14, TailwindCSS, react-i18next, Zustand, axios

**Storage**: PostgreSQL 15 (AliCloud RDS in prod); S3-compatible object storage —
MinIO (dev) / AliCloud OSS (prod) via boto3; Redis 7 (cache, Celery broker, pub/sub)

**Testing**: pytest with async integration tests covering every API endpoint (baseline
119 tests, all passing); frontend component/E2E tests as needed

**Target Platform**: Linux server (Docker) behind nginx TLS; mobile-first browsers /
installable PWA. Deployed on AliCloud for mainland-China access.

**Project Type**: Web application (separate `backend/` and `frontend/`)

**Performance Goals**: Sustain 150 concurrent users browsing and uploading without
visible degradation; infinite-scroll gallery stays responsive via denormalized counts
and lazy loading; real-time notifications delivered within a few seconds.

**Constraints**: China-first (no Google/Facebook/AWS/external CDNs, self-hosted fonts,
ICP filing before go-live); privacy-by-default (all content behind event password, no
public indexing, secrets only in `.env`); mobile-first + offline-tolerant (PWA + service
worker + LQIP required); SHA-256 dedup; full EN/ZH/RU parity; hard production deadline
2026-09-15.

**Scale/Scope**: Single wedding event, ~150 guests, ~10 database tables, ~30 API
endpoints across 9 capability areas, 9 prioritized user stories.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies |
|-----------|------------------------|
| I. China-First Infrastructure | AliCloud OSS + RDS + self-hosted assets; no Google/Facebook/AWS/external CDN; ICP filing tracked as a go-live gate. No blocked dependency appears in the dependency list. |
| II. Frictionless Guest Access | Auth is name + shared event password with get-or-create; no `/register`, no email, no per-user password (see contracts/auth). |
| III. Privacy by Default | All `/api/v1` routes require the event-gated session; secrets (password hash, JWT secret, VAPID keys, SMTP creds) sourced only from `.env`; no public indexing. |
| IV. Full-Featured, Not MVP | All 9 user stories (US1–US9) are planned; none descoped. |
| V. Mobile-First & Offline-Tolerant | Next.js PWA with manifest, service worker offline cache, and LQIP blur-up (US7) are first-class, not optional. |
| VI. Deduplication & Integrity | `media.file_hash` is a unique SHA-256 column; upload-init rejects/deduplicates by hash. |
| VII. Hard-Deadline Discipline | Incremental, independently shippable user stories; MVP (US1–US3) first; deadline 2026-09-15 is SC-010. |
| Quality: test-per-endpoint | Every endpoint in `contracts/` has an integration test task in `tasks.md`. |
| Quality: 150 concurrent | Load test is a Polish-phase task and a go-live gate. |
| Quality: EN/ZH/RU parity | i18n scaffolding is Foundational; parity check is a Polish-phase task. |

**Result**: PASS — no violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-wedding-media-platform/
├── plan.md              # This file
├── research.md          # Phase 0 output (decisions/ADRs)
├── data-model.md        # Phase 1 output (entities, migrations)
├── quickstart.md        # Phase 1 output (run/validate guide)
├── contracts/           # Phase 1 output (API contracts by area)
│   ├── auth.md
│   ├── media.md
│   ├── social.md
│   ├── share.md
│   ├── downloads.md
│   ├── notifications.md
│   ├── admin.md
│   ├── websocket.md
│   └── ops.md
├── checklists/
│   └── requirements.md  # Spec quality checklist (/speckit-specify output)
└── tasks.md             # /speckit-tasks output
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── main.py               # FastAPI app factory, router registration, CORS, health
│   ├── config.py             # get_settings() (lru_cached) from .env
│   ├── db.py                 # async engine/session
│   ├── routers/              # HTTP layer: auth, media, social, share, downloads,
│   │                         #   notifications, admin, ws, health
│   ├── services/             # business logic: auth, media, social, activity, storage,
│   │                         #   deduplication, email_service, push_service,
│   │                         #   websocket_manager, zip_service
│   ├── models/               # SQLAlchemy ORM models (one per entity)
│   ├── schemas/              # Pydantic v2 request/response contracts
│   ├── workers/              # Celery app + media_processing tasks
│   └── i18n/                 # gettext message catalogs (en/zh/ru) for API messages
├── alembic/                  # migrations: 0001_initial, 0002_phase3, 0003_phase4
└── tests/
    └── integration/          # pytest integration tests (one per endpoint)

frontend/
├── src/
│   ├── app/                  # Next.js App Router routes (login, gallery, admin, share)
│   ├── components/           # UI components (gallery grid, lightbox, uploader, toasts)
│   ├── stores/               # Zustand stores (auth, gallery, realtime)
│   ├── lib/                  # axios client, ws client, i18n init
│   └── locales/              # react-i18next resources: en / zh / ru
├── public/                   # manifest, icons, service worker, self-hosted fonts
└── tests/

infra/
├── docker-compose.dev.yml    # postgres, redis, minio, backend, worker, frontend
├── docker-compose.prod.yml
└── nginx/                    # TLS termination + reverse proxy config

.github/workflows/            # CI: lint + test + Docker build
```

**Structure Decision**: Web application layout with separate `backend/` and `frontend/`
trees plus an `infra/` directory for Docker/nginx. This matches the two-tier architecture
(FastAPI API + Next.js PWA) and keeps the async worker, migrations, and integration tests
co-located with the backend. Backend layering is strict: `routers/` (HTTP) → `services/`
(business logic) → `models/` (ORM), with `schemas/` holding Pydantic contracts and
`workers/` holding Celery tasks.

## Complexity Tracking

> No constitution violations — this section is intentionally empty.
