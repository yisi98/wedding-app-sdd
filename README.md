# Wedding Media Platform

A private, password-protected, trilingual (English / 中文 / Русский) PWA for collecting and
sharing photos and videos from a single ~150-guest wedding. China-first infrastructure
(AliCloud), real-time engagement, offline-tolerant. Built with **Spec-Driven Development**
using [Spec Kit](https://github.com/github/spec-kit).

Production deadline: **2026-09-15** (wedding 2026-10-10).

## Status

Built spec-first: constitution → spec → plan → tasks → implementation. **88 / 90 spec tasks done**, plus post-audit fixes and hardening.

| Area | Status |
|------|--------|
| Backend (US1–US9) | ✅ Complete — **101 integration tests passing** |
| Alembic migrations (0001–0004) | ✅ Verified (upgrade + downgrade) |
| Frontend (Next.js 14 PWA) | ✅ `npm run build` passes (8 routes) |
| Infra (Docker, nginx, CI) | ✅ Config complete |
| EN/ZH/RU parity | ✅ `node scripts/check_i18n_parity.mjs` → OK |
| Production deploy + ICP (T089/T090) | ⏳ Requires live AliCloud + ICP filing — see [docs/DEPLOY.md](docs/DEPLOY.md) |

The design lives under [`specs/001-wedding-media-platform/`](specs/001-wedding-media-platform/):
[spec](specs/001-wedding-media-platform/spec.md) ·
[plan](specs/001-wedding-media-platform/plan.md) ·
[data-model](specs/001-wedding-media-platform/data-model.md) ·
[contracts](specs/001-wedding-media-platform/contracts/) ·
[tasks](specs/001-wedding-media-platform/tasks.md).

## Architecture

```
Browser (Next.js PWA) ──HTTP + WebSocket──► nginx (TLS, WS, rate-limit)
                                              ├─► FastAPI (async SQLAlchemy) ─► PostgreSQL
                                              │      ├─ Celery ─ Redis broker ─► MinIO / AliCloud OSS
                                              │      └─ Redis pub/sub ─► WebSocket clients
                                              └─► Next.js server
```

- **Backend**: FastAPI · Python 3.12 (`uv`) · SQLAlchemy 2 async · Alembic · Pydantic v2 ·
  JWT (access + rotating refresh) · Celery · Pillow (thumbnail/WebP/LQIP/dHash) · pywebpush.
- **Frontend**: Next.js 14 (App Router) · TypeScript · Tailwind · react-i18next · Zustand · axios.
- **Storage**: S3-compatible (MinIO dev / AliCloud OSS prod); local filesystem backend for zero-infra dev.

## Quick start

**Run the whole app locally — one command, no Docker, no external services:**

```bash
./scripts/dev.sh            # app on http://localhost:3000, API on :8000
./scripts/dev.sh --reset    # same, but wipe the local database and uploads first
```

It creates `backend/.env` and `frontend/.env.local` on first run, installs
dependencies, and starts both servers. Requires `uv` and Node 20+; `ffmpeg` is optional
(without it videos still upload, but get no thumbnail, duration, or transcode).

Sign in with **any name** plus the event password (the `EVENT_PASSWORD` value that
`dev.sh` writes into `backend/.env`), or as the built-in admin (`admin` / the
`ADMIN_PASSWORD` value).

To reach it from a phone on the same wi-fi, browse to `http://<your-LAN-IP>:3000` and
point `NEXT_PUBLIC_API_BASE` in `frontend/.env.local` at `http://<your-LAN-IP>:8000` —
otherwise the phone's browser calls `localhost` and finds nothing.

**Running the pieces individually:**

```bash
cd backend
uv sync
uv run pytest -q            # 101 integration tests
uv run uvicorn src.main:app --reload   # dev API on :8000 (creates tables under DEBUG)

cd frontend
npm install
npm run dev                 # http://localhost:3000   (npm run build to type-check)
```

**Only Docker installed, nothing else?**

```bash
docker compose -f infra/docker-compose.local.yml up --build
```

Two containers, zero-infra path (SQLite + local filesystem), no `.env` to prepare —
same sign-in credentials as above. Slower to start than `scripts/dev.sh` (it builds
images) but needs nothing on the host beyond Docker itself.

**Full stack with real infra** (PostgreSQL + Redis + MinIO):

```bash
cp backend/.env.example backend/.env      # then edit
docker compose -f infra/docker-compose.dev.yml up
```

See [quickstart.md](specs/001-wedding-media-platform/quickstart.md) for the end-to-end smoke test.

## Project layout

```
backend/     FastAPI app (src/{routers,services,models,schemas,workers,i18n}), Alembic, tests
frontend/    Next.js PWA (src/{app,components,stores,lib,locales}, public/{manifest,sw.js})
infra/       docker-compose.dev/prod, nginx (TLS+WS+rate-limit), loadtest (locust)
docs/        SECURITY.md, DEPLOY.md
scripts/     dev.sh (run everything locally), check_i18n_parity.mjs
specs/       Spec-Kit artifacts for feature 001
```

## Key conventions

- **Auth**: display name + one shared event password; accounts auto-created (get-or-create).
  No email, no per-user password, no registration.
- **Admin**: one built-in account, seeded automatically when the database is created —
  username `admin`, password from `ADMIN_PASSWORD` (override with `ADMIN_USERNAME` /
  `ADMIN_PASSWORD`; seed from a bcrypt hash with `ADMIN_PASSWORD_HASH`). It signs in on
  the same screen as guests but with its own password;
  the shared event password never grants admin. **Change the password before go-live.**
- **Dedup**: every media file is content-addressed by a unique SHA-256 hash.
- **Media URLs**: served via CDN in prod (`NEXT_PUBLIC_MEDIA_BASE`); in dev the backend
  serves bytes at `GET /media-object/{key}`.
- **i18n**: every user-facing string exists in EN/ZH/RU (enforced by the parity script).
- **Secrets**: only in `backend/.env` (git-ignored) — never committed.

## Testing

```bash
cd backend && uv run pytest -q       # 101 backend integration tests
cd frontend && npm run build         # frontend type-check + build
node scripts/check_i18n_parity.mjs   # EN/ZH/RU parity
```

## License

Private project.
