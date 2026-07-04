# Phase 0 Research & Decisions: Wedding Media Platform

All spec-level unknowns resolve to the decisions below. There are no open
`NEEDS CLARIFICATION` items. Architecture Decision Records (ADR 001–005) capture the
load-bearing choices; a Known Constraints section captures operational gotchas.

## ADR-001: FastAPI + Next.js two-tier stack

- **Decision**: FastAPI (Python 3.12, async SQLAlchemy 2) back end + Next.js 14 (App
  Router, TypeScript) front end, communicating over HTTP + WebSocket.
- **Rationale**: Async FastAPI handles concurrent uploads and WebSocket fan-out well and
  fits the team's Python skill set; Next.js gives a strong mobile-first PWA with i18n and
  SSR. Both run cleanly in Docker on AliCloud.
- **Alternatives considered**: Django + DRF (heavier, sync-first, weaker WS story);
  single Next.js full-stack (couples media processing to the web tier); SvelteKit
  (smaller ecosystem for the required i18n/PWA/push libraries).

## ADR-002: Password-only auth (event password + auto-created accounts + admin role)

- **Decision**: One shared event password (bcrypt-hashed, in `.env`) plus a
  get-or-create account keyed on display name. JWT access token (15 min) + rotating
  refresh token (7 days, SHA-256 hashed at rest); logout revokes all refresh tokens. Role
  is `guest` or `admin`. No `/register`, no email, no per-user password.
- **Rationale**: Directly implements Principle II (Frictionless Guest Access) while
  keeping Principle III (Privacy by Default) — content stays gated, sessions are
  short-lived, and refresh rotation limits token replay.
- **Alternatives considered**: Per-guest magic links (needs email — blocked by no-email
  rule and China deliverability); OAuth/social login (blocked providers, adds friction);
  long-lived single token (weaker security, no revocation).

## ADR-003: AliCloud OSS + CDN for media, MinIO in dev

- **Decision**: S3-compatible object storage via boto3 — MinIO locally, AliCloud OSS in
  production — with presigned-URL direct upload (init → client-to-OSS PUT → confirm).
  Media is served through AliCloud CDN.
- **Rationale**: Satisfies Principle I (China-First); presigned direct upload keeps large
  video bytes off the API tier, supporting the 150-concurrent target. boto3's S3 API works
  identically against MinIO and OSS, so dev and prod share one code path.
- **Alternatives considered**: AWS S3/CloudFront (blocked in China); storing bytes in
  Postgres (does not scale to video); proxying uploads through FastAPI (API becomes the
  bottleneck under concurrent uploads).

## ADR-004: Trilingual i18n via react-i18next (frontend) + gettext (API messages)

- **Decision**: Frontend strings live in react-i18next resource bundles (`en`/`zh`/`ru`);
  API-generated messages are localized with gettext catalogs keyed by the user's
  `language_preference`. Fonts are self-hosted.
- **Rationale**: Enforces the EN/ZH/RU parity quality bar on both tiers; self-hosted fonts
  keep Principle I intact (no Google Fonts CDN).
- **Alternatives considered**: Frontend-only i18n (server error messages would leak a
  single language); a translation SaaS (external dependency, China access risk).

## ADR-005: SHA-256 content-hash deduplication

- **Decision**: The client (or confirm step) computes a SHA-256 of file content; `media.
  file_hash` is a UNIQUE column. Upload-init checks the hash and short-circuits duplicates
  before any storage write. A separate perceptual hash (pHash) powers "similar photos"
  discovery but does not gate dedup.
- **Rationale**: Implements Principle VI (Deduplication & Integrity) deterministically;
  the DB uniqueness constraint makes concurrent identical uploads race-safe (only one wins).
- **Alternatives considered**: pHash-only dedup (false positives would drop distinct
  photos); filename/size heuristics (unreliable); no dedup (storage bloat, cluttered
  gallery).

## Known Constraints & Operational Gotchas

- **LRU-cached settings**: `get_settings()` is `@lru_cache`d, so configuration changes
  require a backend restart to take effect. Tests must not rely on mid-process config
  mutation.
- **Windows/WSL2 dev networking**: Local infra (Postgres/Redis) runs in WSL2/Podman; the
  DB/Redis hosts live at the WSL bridge IP (e.g. `172.24.62.171`), not `localhost`, and
  that IP can change on restart. Dev `.env` must be updated when the bridge IP changes.
- **Celery on Windows**: The worker runs with `--pool=solo` on Windows dev machines.
- **CORS by environment**: `DEBUG=True` allows all origins (`["*"]`, credentials off);
  production uses an explicit allow-list with credentials on.
- **Legacy `users.email` column**: The schema retains a nullable `email` column that is
  intentionally excluded from every API response (a remnant; candidate for a future
  cleanup migration). Do not surface it.
