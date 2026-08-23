# Quickstart & Validation Guide: Wedding Media Platform

A run/validate guide proving the feature works end to end. This is not implementation
code — see [tasks.md](./tasks.md) for the build steps.

## Prerequisites

- Python 3.12 + `uv` (backend), Node 20 + `npm` (frontend)
- For the **full stack**: Docker + Docker Compose (PostgreSQL 15, Redis 7, MinIO) and
  ffmpeg on PATH (video duration).
- A `.env` file (never committed) — see [`backend/.env.example`](../../backend/.env.example)
  for every variable. On Windows/WSL2, point DB/Redis hosts at the WSL bridge IP, not
  `localhost`.

> **Zero-infra dev/test path**: with `DEBUG=true` and no storage keys set, the backend uses
> SQLite + a local filesystem storage backend and processes uploads inline — so
> `uv run pytest` and `uv run uvicorn src.main:app --reload` work with **no Docker, Redis,
> or MinIO**. Media bytes are served from `GET /media-object/{key}`.

## Bring up infrastructure

```bash
docker compose -f infra/docker-compose.dev.yml up -d   # postgres, redis, minio
cd backend && uv run alembic upgrade head               # apply migrations 0001–0003
```

## Run the services

```bash
# Backend API
cd backend && uv run uvicorn src.main:app --reload
# Celery worker (Windows dev: add --pool=solo)
cd backend && uv run celery -A src.workers.celery_app worker --loglevel=info
# Frontend PWA
cd frontend && npm install && npm run dev
```

## Smoke test (maps to Success Criteria)

1. **Login (US1/SC-001)**: open the app, enter a new display name + event password → you
   reach the gallery. Wrong password → rejected. Re-enter same name → same account.
2. **Upload + dedup (US2/SC-002)**: upload a photo → it appears `processing` then `ready`
   with a thumbnail. Upload the same file again → told it already exists; not re-stored.
3. **Gallery (US3)**: scroll (lazy loading + placeholders), filter/sort/search, open the
   lightbox → navigation, download, and a "similar photos" strip.
4. **Social (US4/SC-007)**: react twice with the same type → net zero; switch type →
   count stays one. Add + delete your own comment. Favorite an item.
5. **Real-time (US6/SC-008)**: with two sessions, act in one → a live toast appears in the
   other; `/activity` lists the event.
6. **PWA (US7/SC-006)**: install to home screen; go offline → previously loaded content
   still viewable; images blur up.
7. **Admin (US8/SC-005, SC-009)**: hide a media item → gone from the guest gallery, still
   in `/admin/media`. Non-admin hitting `/admin/*` → 403. Export media CSV.
8. **Bulk (US9)**: multi-select → bulk download returns one ZIP of those items.
9. **Health (FR-038)**: `GET /api/v1/health` → 200; stop Redis → 503.

US5 (sharing) was withdrawn by constitution amendment 1.1.0; there is no share step.

## Test suite

```bash
cd backend && uv run pytest tests/integration -q   # every endpoint covered (baseline 97)
```

## Go-live gates (before 2026-09-15, SC-010)

- ICP filing active (Principle I).
- Load test sustaining 150 concurrent users passes (SC-003).
- EN/ZH/RU string parity verified (SC-004).
- Production smoke test (steps 1–10) green.
