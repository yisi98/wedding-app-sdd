# Mainland-China Deployment Runbook

Step by step, for a mainland-only setup (no Hong Kong staging). Everything runs in one
mainland region on Alibaba Cloud, and the public site goes live only once the ICP filing
is granted.

**Deadline context**: SC-010 requires production live by **2026-09-15**; the wedding is
2026-10-10. The ICP filing is the only step whose duration you do not control, so start
Phase 1 and Phase 2 on the same day.

---

## Phase 0 — Account (30 minutes)

1. Create an account on **www.aliyun.com** — the mainland site. This is *not* the same
   as an alibabacloud.com (international) account; the two are separate entities and an
   international account cannot hold a mainland ICP filing.
2. Complete real-name verification on the account with Yisi's Chinese ID.
3. Everything below is done under this account, in Yisi's name. Individual (个人) filing
   is the right category for a private wedding gallery.

---

## Phase 1 — Domain (start day 1; ~6–8 days before it is filing-ready)

1. Register the domain **on Aliyun**, under Yisi's name. The registrant details must
   match the ICP filing subject exactly, or the filing is rejected.
2. Pick a TLD accepted by MIIT for filing — `.com`, `.cn`, `.net` are safe. Avoid novelty
   TLDs; many are not approved.
3. Complete **domain real-name verification (实名认证)**. Third-party review takes
   3–5 business days.
4. **Then wait ~3 more days.** The verification result has to synchronise into the
   communications administration's database before a filing can reference it. Submitting
   earlier is the most common cause of a bounced application.

*Do not point DNS at anything yet.*

---

## Phase 2 — Infrastructure (start day 1, in parallel)

Region: **China (Beijing)** — closest to the guests and the venue.

### 2.1 ECS instance — this is the filing prerequisite

Alibaba Cloud will only file on behalf of a server it hosts, so the instance must exist
before Phase 3 can begin.

- Region: mainland (Beijing)
- Billing: **subscription, 3 months or longer** (this is a hard filing requirement — a
  pay-as-you-go instance does not qualify)
- Public IP: required
- Size: 4 vCPU / 8 GB is comfortable. The Celery worker does image decode, resize, WebP
  and perceptual hashing per upload, and 150 guests uploading after the ceremony is the
  peak.
- Disk: 100 GB SSD
- OS: Ubuntu 22.04 or Alibaba Cloud Linux 3

### 2.2 Bandwidth — the trap worth understanding

Set the public bandwidth to **pay-by-traffic** with a high peak (100 Mbps), not a small
fixed allowance. A 1–5 Mbps default would throttle the whole event.

The architecture helps here: guests upload **directly to OSS** via presigned URLs, so
photo bytes never pass through the ECS instance. Serve media from OSS as well
(`NEXT_PUBLIC_MEDIA_BASE`) and the ECS only carries API traffic and HTML.

### 2.3 OSS bucket

- Same region as the ECS (Beijing). A cross-region bucket adds a hop to every upload.
- ACL: **private**. The app issues presigned URLs; the storage keys embed a content
  SHA-256, so they are unguessable capability URLs.
- Enable CORS for the site origin, methods `PUT, GET, HEAD`, **AllowedHeaders `*`** —
  the browser PUT includes a `Content-Type` header that is part of the signature, and
  OSS rejects the upload if CORS blocks that header. Expose `ETag` too.

**How media reaches the gallery.** With a private bucket there are exactly two options:

1. **Backend-served (recommended default).** Leave `NEXT_PUBLIC_MEDIA_BASE` empty. The
   frontend then loads media via `GET /media-object/{key}`, which the backend streams
   from OSS with its own credentials. Works out of the box, keeps the bucket private.
   Cost: photo/video bytes pass through the ECS, so the pay-by-traffic bandwidth cap
   must cover the gallery viewing load, not just API traffic.
2. **AliCloud CDN (if bandwidth cost bites).** Point a CDN acceleration domain at the
   bucket with private-bucket back-to-origin authorization (私有 Bucket 回源授权), and
   set `NEXT_PUBLIC_MEDIA_BASE` to the CDN domain. Note the CDN domain **also needs an
   ICP filing**, so this cannot be done before Phase 3 completes.

### 2.4 Database

Two options:

- **RDS PostgreSQL 15** — what `plan.md` specifies. Managed backups, less to go wrong.
- **Postgres in a container on the ECS** — cheaper and quicker for a one-off event, but
  backups become your job.

For a single wedding either is defensible. Take RDS if the cost is acceptable; the
managed backup is worth it for irreplaceable photos.

### 2.5 Security group — keep it closed for now

Allow inbound **only from your own IP addresses** during Phases 2–4:

- `22` (SSH) — your IPs only
- `8443` (temporary testing port) — your IPs only

Leave 80 and 443 **closed**. Alibaba Cloud blocks them automatically for an unfiled
domain anyway, and a site that is publicly reachable during the filing review can get
the application rejected.

---

## Phase 3 — ICP filing (start as soon as Phases 1 and 2 are done)

This is the long pole. Nothing you do shortens the second stage.

1. Open the ICP filing console on aliyun.com (备案), or use the **Aliyun app**, which
   handles the face-scan verification more smoothly than the desktop flow.
2. Choose **individual (个人)** filing.
3. Have ready: Yisi's Chinese ID (both sides), a mainland phone number for SMS, the
   domain, and the ECS instance ID.
4. Site description: describe it accurately as a private, password-protected photo
   gallery for a personal wedding. Do not describe it as anything commercial — an
   individual filing does not cover commercial content, and a mismatch causes rejection.
5. **Alibaba Cloud's own review: 1–2 business days.**
6. It is then forwarded to the provincial communications administration for the final
   review. This stage is the slow, variable one and is outside anyone's control. Expect
   SMS verification during it.

While this runs, continue to Phase 4 — but keep the site private.

---

## Phase 4 — Deploy and test privately (while the filing is pending)

You can run the full stack on the mainland instance now, reachable only by you.

> **Getting the code onto the instance.** `github.com` is blocked or unreliable from
> mainland ECS. Either push the repo to Aliyun Codeup / a Gitee mirror first, or ship a
> tarball from your own machine (`git archive -o wedding-app.tar.gz HEAD` → `scp` it up
> and extract). Do not plan on `git clone` from GitHub working on the instance.

```bash
# on the ECS (after getting the code up via Codeup/Gitee/scp)
cd wedding-app-sdd
cp backend/.env.example backend/.env
```

Fill `backend/.env`:

| Variable | Value |
|---|---|
| `DEBUG` | `false` |
| `DATABASE_URL` | `postgresql+asyncpg://…` (RDS or local container) |
| `EVENT_PASSWORD_HASH` | bcrypt hash of the real event password — set the hash, leave `EVENT_PASSWORD` unset |
| `JWT_SECRET` | a long random string |
| `ADMIN_PASSWORD` | **set before the first migration** — see the warning below |
| `STORAGE_ENDPOINT` | `https://oss-cn-beijing.aliyuncs.com` |
| `STORAGE_REGION` | `cn-beijing` — must match the bucket's region; OSS SigV4 signing fails without it |
| `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` | a RAM user limited to this bucket, not the root account keys |
| `STORAGE_BUCKET` | your bucket name |
| `REDIS_URL` | `redis://redis:6379/0` |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | **leave unset for a mainland deployment** — see the web push note below |
| `CORS_ORIGINS` | `["https://your-domain.cn"]` — JSON array; a bare URL crashes pydantic-settings at startup |

> **Compose interpolates `$` inside `backend/.env`** (it is read via `env_file`). Bcrypt
> hashes like `$2b$12$…` get mangled — the `$salt` segment is treated as an unset
> variable (warning `The "…" variable is not set`) and blanked out, silently breaking
> login. Double every `$`: `$$2b$$12$$…`. Same applies to any database password
> containing `$`.

Frontend values go in `infra/.env` — `docker compose build` forwards them as build args,
because Next.js bakes `NEXT_PUBLIC_*` into the client bundle **at build time** (runtime
container env has no effect):

- `NEXT_PUBLIC_API_BASE=https://your-domain.cn`
- `NEXT_PUBLIC_MEDIA_BASE` — leave empty to serve media through the backend (option 1 in
  2.3), or set to the CDN domain (option 2)
- `NEXT_PUBLIC_ICP_NUMBER` — added and rebuilt in Phase 5, once the filing is granted

> **Set `ADMIN_PASSWORD` before the first `alembic upgrade head`.** The admin account is
> seeded during migration and defaults to `admin` / `admin12345`, which is public in this
> repository. Seeding never overwrites an existing account, so if the default is created
> once, changing the env afterwards does nothing — you would have to log in and change it
> by hand. Anyone reaching the site could otherwise delete every guest and photo.

> **Web push on the mainland.** Guests' browsers register push subscriptions with the
> push service built into their browser — for Chrome-family Android, that is FCM
> (`fcm.googleapis.com`), which is blocked in mainland China, so those messages would
> never arrive. Leaving the VAPID keys unset is the correct mainland configuration: the
> backend then skips sending entirely and the frontend hides the push toggle, so nothing
> promises what cannot be delivered. Guests with the app open still get real-time updates
> through the WebSocket layer, which is the reliable path for domestic users.

### Building images on the mainland

Docker Hub, PyPI, and the npm registry are slow or unreachable from a mainland host.
Two levers, both off by default (without them the build behaves exactly as elsewhere):

**1. Docker Hub mirror accelerator** — fixes every image pull (`nginx:1.27`, `redis:7`,
and the Python/Node bases). Create `/etc/docker/daemon.json` on the ECS:

```json
{ "registry-mirrors": ["https://<your-accelerator>.mirror.aliyuncs.com"] }
```

The accelerator URL comes from the Aliyun console: Container Registry → Mirror
Accelerator (容器镜像服务 → 镜像加速器). Restart Docker afterwards.

**2. Build-time mirrors** — if the accelerator is not enough, create `infra/.env`
(docker compose reads it automatically; it is git-ignored):

```
PYTHON_IMAGE=<mirror-host>/python:3.12-slim
NODE_IMAGE=<mirror-host>/node:20-slim
UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/
APT_MIRROR=mirrors.aliyun.com
NPM_REGISTRY=https://registry.npmmirror.com
# runtime pulls, only needed if daemon.json mirrors are unavailable:
NGINX_IMAGE=<mirror-host>/nginx:1.27
REDIS_IMAGE=<mirror-host>/redis:7
```

Then build normally — `docker compose -f docker-compose.prod.yml build` picks the values
up. Aliyun Container Registry (ACR) hosts mirrors of the official images, or use any
trusted mirror reachable from the instance.

Bring it up on the temporary port by changing the nginx port mapping in
`infra/docker-compose.prod.yml` from `"443:443"` to `"8443:443"`, then:

```bash
cd infra
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

Reach it at `https://<ecs-public-ip>:8443` from your allow-listed IP. A self-signed
certificate is fine at this stage; the browser warning is expected.

**Run the two outstanding gates here** — neither needs the filing:

- **T086 — load test.** `infra/loadtest/README.md`. Run the generator from another
  Beijing-region instance so you measure the server, not your home uplink.
- **T089 — smoke test.** `quickstart.md` steps 1–9, on a real phone, on a mainland
  mobile connection.

Purge the `loadtest-` accounts and media afterwards.

---

## Phase 5 — Go live (once the filing is granted)

1. Point the domain's DNS at the ECS public IP.
2. Issue a real TLS certificate for the domain and place `fullchain.pem` and
   `privkey.pem` in `infra/nginx/certs/`.
3. Restore the port mapping to `"80:80"` and `"443:443"`.
4. Open 80 and 443 in the security group **to the world** — this is the first moment the
   site is public.
5. Add the ICP number to the frontend environment and rebuild:
   `NEXT_PUBLIC_ICP_NUMBER="京ICP备xxxxxxxx号-1"`. `BeianFooter` renders it linked to
   beian.miit.gov.cn, which is a legal display requirement for mainland hosting.
6. Re-run the T089 smoke test against the real domain.

---

## Phase 6 — PSB filing (公安备案) — within 30 days, do not skip

A separate filing from the ICP one, made through the national public-security portal
after the site is live. **Miss the 30-day window and the ICP filing can be revoked.**

1. Register at the Internet Security Administration portal and submit the site details.
2. Review typically takes 3–5 working days.
3. When granted, set `NEXT_PUBLIC_PSB_NUMBER` and `NEXT_PUBLIC_PSB_CODE` and rebuild —
   `BeianFooter` then displays it linked to the enquiry page. If the bureau supplies a
   badge image, save it under `frontend/public/` and set `NEXT_PUBLIC_PSB_LOGO`; do not
   hotlink it, as Principle I forbids external asset hosts.

---

## Timeline

| Day | Action |
|---|---|
| 1 | Aliyun account, register domain, start real-name verification, buy ECS + OSS + RDS |
| 4–6 | Real-name verification completes |
| 7–9 | Sync window; then submit the ICP filing |
| 8–11 | Alibaba Cloud preliminary review |
| — | Provincial review (variable; the unknown) |
| in parallel | Deploy on port 8443, run T086 and T089 |
| on grant | Open 80/443, add the ICP number, re-run the smoke test |
| within 30 days | PSB filing, add the number |

**The risk is Phase 3's second stage.** If it has not cleared with a week to spare before
2026-09-15, the fallback is a Hong Kong region, which needs no filing — see
`DEPLOY.md`. Worth keeping in mind, not worth planning around yet.
