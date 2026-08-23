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
      defaults to `admin` / `dev-only-admin-pass`, which is public knowledge — anyone who
      reaches the site could otherwise sign in and delete guests and media. Seeding
      never overwrites an existing account, so if the default was already created,
      rotate it by signing in and changing it rather than by editing the env alone.

## Admin access
The panel lives at `/admin` and is visible only to the admin account. Sign in on the
normal login screen with the admin username and `ADMIN_PASSWORD` — the shared event
password does not grant admin. From there: dashboard stats, guest management
(promote/demote, deactivate/reactivate, delete), media moderation (hide/show, delete),
CSV export, and the archive-mode switch that closes uploads after the event.

## Staging without ICP — you can test today

ICP filing gates **production**, not testing. Deploy the same stack to an Alibaba Cloud
region outside the mainland — **Hong Kong** — where no ICP filing is required, and both
T086 (load) and T089 (smoke) can run now.

```bash
# Same compose file; only the endpoints differ.
cd infra && docker compose -f docker-compose.prod.yml up -d
```

Put the OSS bucket in the **same region as the instance**. A Hong Kong app in front of a
mainland bucket adds a cross-border hop to every presigned upload and makes the load-test
numbers meaningless. Run the load generator in that region too, for the same reason.

**What Hong Kong staging proves**: everything about the stack — OSS presigned uploads,
Celery workers actually processing, the service worker over real TLS on a real domain,
web push to a real phone, 150 concurrent users, and all 9 quickstart steps.

**What it does not prove**: the mainland network path. Hong Kong is reachable from the
mainland without a VPN, but it crosses the border, so latency is higher and more variable
than a mainland-region deployment — exactly the thing Principle I exists to protect.
Treat a Hong Kong pass as "the software is correct", not as "guests will have a good
time". T089 still has to be repeated against production.

**Do not put real guest data or the real event password on staging.** Use a throwaway
`EVENT_PASSWORD` and a separate `ADMIN_PASSWORD`.

## Getting the ICP filing started — buy the instance first

The filing has a prerequisite that catches people out: **you must already own a mainland
ECS instance before you can file.** It has to be in a mainland region, on the subscription
billing method for **3 months or longer**, with a public IP. Alibaba Cloud can only file
on behalf of a server it hosts.

So provisioning mainland infrastructure is step 1 of the filing, not something that waits
for it. Buying the mainland ECS today starts the clock; Hong Kong staging runs in parallel.

Alibaba Cloud's own review takes 1–2 business days, after which it goes to the provincial
communications administration for the final review — that second stage is the slow and
variable part, and is outside anyone's control.

For a private wedding gallery, an **individual filing** applies. It needs a mainland ID
and phone (Yisi's), and **the domain registrant must match the filing subject**, so
register the domain in the same name you file under or the application will bounce.

## Deploy
```bash
cd infra
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d      # runs alembic upgrade head on start
```

## Smoke test (quickstart.md steps 1–9) — T089
Run the [quickstart](../specs/001-wedding-media-platform/quickstart.md) validation against
the deployed URL: login → upload+dedup → gallery → social → real-time → PWA
install/offline → admin moderation → bulk ZIP → `/health`. There is no share step; US5 was
withdrawn by constitution amendment 1.1.0.

> Automated coverage already proves these flows: `cd backend && uv run pytest` = 97
> integration tests green, `cd frontend && npm run test:pwa` = 4 PWA specs green, and
> `npm run build` succeeds. The remaining step is running the same scenarios end-to-end
> against the deployed stack, on a real phone over a mainland connection.

## Load test (SC-003) — see infra/loadtest/
Run 150 concurrent users against staging; require ~0% errors and p95 within budget.

> The script covers browse **and** upload, and grades itself: it exits non-zero if any
> p95 budget or the 0.5% failure ratio is missed, so it can gate the release. Set
> `LOADTEST_EVENT_PASSWORD` in the environment. Budgets and knobs are documented in
> `infra/loadtest/README.md`. Purge the `loadtest-` accounts and media afterwards.

## Go-live checklist (T090)
- [ ] ICP active · [ ] migrations applied · [ ] smoke test green · [ ] load test passed
- [ ] EN/ZH/RU parity (`node scripts/check_i18n_parity.mjs` → OK) · [ ] backups configured
