# Deployment Runbook (AliCloud) — go-live by 2026-09-15

Supports T089 (prod-like validation) and T090 (production deploy). These are **go-live
gates that require live AliCloud infrastructure and an active ICP filing** — they are
executed by the operator, not automatable from a dev machine.

## Prerequisites (Principle I & VII)
- [ ] ICP filing active for the domain (mandatory before public go-live).
- [ ] AliCloud RDS (PostgreSQL 15), Redis, and OSS bucket provisioned in a mainland region.
- [ ] TLS certs placed in `infra/nginx/certs/` (`fullchain.pem`, `privkey.pem`).
- [ ] `backend/.env` filled: `DATABASE_URL` (asyncpg → RDS), `REDIS_URL`, OSS
      `STORAGE_*`, `EVENT_PASSWORD_HASH`, `JWT_SECRET`, `VAPID_*`, `CORS_ORIGINS`,
      `DEBUG=false`. Set `NEXT_PUBLIC_API_BASE` / `NEXT_PUBLIC_MEDIA_BASE` (CDN) for the frontend.
- [ ] **Set `ADMIN_PASSWORD`** (and optionally `ADMIN_USERNAME`) before the first
      `alembic upgrade head`. The admin account is seeded on migration/startup and
      defaults to `admin` / `admin12345`, which is public knowledge — anyone who
      reaches the site could otherwise sign in and delete guests and media. Seeding
      never overwrites an existing account, so if the default was already created,
      rotate it by signing in and changing it rather than by editing the env alone.

## Admin access
The panel lives at `/admin` and is visible only to the admin account. Sign in on the
normal login screen with the admin username and `ADMIN_PASSWORD` — the shared event
password does not grant admin. From there: dashboard stats, guest management
(promote/demote, deactivate/reactivate, delete), media moderation (hide/show, delete),
CSV export, and the archive-mode switch that closes uploads after the event.

## Deploy
```bash
cd infra
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d      # runs alembic upgrade head on start
```

## Smoke test (quickstart.md steps 1–10) — T089
Run the [quickstart](../specs/001-wedding-media-platform/quickstart.md) validation against
the deployed URL: login → upload+dedup → gallery → social → share → real-time → PWA
install/offline → admin moderation → bulk ZIP → `/health`.

> Automated coverage already proves these flows: `cd backend && uv run pytest` = 62
> integration tests green, and `cd frontend && npm run build` succeeds. The remaining
> step is running the same scenarios end-to-end against the deployed stack.

## Load test (SC-003) — see infra/loadtest/
Run 150 concurrent users against staging; require ~0% errors and p95 within budget.

## Go-live checklist (T090)
- [ ] ICP active · [ ] migrations applied · [ ] smoke test green · [ ] load test passed
- [ ] EN/ZH/RU parity (`node scripts/check_i18n_parity.mjs` → OK) · [ ] backups configured
