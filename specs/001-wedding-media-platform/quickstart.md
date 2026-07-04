# Quickstart & Validation Guide: Wedding Media Platform

A run/validate guide proving the feature works end to end. This is not implementation
code — see [tasks.md](./tasks.md) for the build steps.

## Prerequisites

- Docker + Docker Compose (dev infra: PostgreSQL 15, Redis 7, MinIO)
- Python 3.12 + `uv` (backend), Node 20 + `npm` (frontend)
- ffmpeg available on PATH (video duration/processing)
- A `.env` file (never committed) with: `EVENT_PASSWORD_HASH`, `JWT_SECRET`,
  `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY`, storage keys, `DATABASE_URL`, `REDIS_URL`,
  optional `SMTP_HOST`. On Windows/WSL2, point DB/Redis hosts at the WSL bridge IP, not
  `localhost`.

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
5. **Share (US5)**: create a gallery share link → open it (access count increments).
6. **Real-time (US6/SC-008)**: with two sessions, act in one → a live toast appears in the
   other; `/activity` lists the event.
7. **PWA (US7/SC-006)**: install to home screen; go offline → previously loaded content
   still viewable; images blur up.
8. **Admin (US8/SC-005, SC-009)**: hide a media item → gone from the guest gallery, still
   in `/admin/media`. Non-admin hitting `/admin/*` → 403. Export media CSV.
9. **Bulk (US9)**: multi-select → bulk download returns one ZIP of those items.
10. **Health (FR-038)**: `GET /api/v1/health` → 200; stop Redis → 503.

## Test suite

```bash
cd backend && uv run pytest tests/integration -q   # every endpoint covered (baseline 119)
```

## Go-live gates (before 2026-09-15, SC-010)

- ICP filing active (Principle I).
- Load test sustaining 150 concurrent users passes (SC-003).
- EN/ZH/RU string parity verified (SC-004).
- Production smoke test (steps 1–10) green.
