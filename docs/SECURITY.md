# Security Hardening (T087)

Posture for the Wedding Media Platform, mapped to the constitution.

## Secrets (Principle III)
- All secrets live only in `backend/.env`; `.gitignore` excludes `.env`/`.env.*` (only
  `.env.example` is committed). Verified: `git ls-files | grep .env` → `.env.example` only.
- No hardcoded secret assignments in tracked source (scanned).
- CI/review should run a secret scanner (e.g. gitleaks) on every PR.

## Authentication (Principle II)
- One shared event password, bcrypt-hashed in prod (`EVENT_PASSWORD_HASH`).
- JWT access token (15 min) + rotating refresh token (7 days), refresh stored as SHA-256
  hash; rotation revokes the prior token; logout revokes all.
- **Rate limiting** at nginx: `/api/v1/auth/login` capped at 10 req/min/IP (burst 5),
  general API at 30 req/s/IP — blunts brute-force against the event password.

## Transport & CORS
- nginx terminates TLS and redirects HTTP→HTTPS.
- CORS is environment-driven: `DEBUG=true` allows all origins with credentials off;
  production uses an explicit `CORS_ORIGINS` allow-list with credentials on.

## Data exposure
- Legacy `users.email` column is excluded from every API response and the CSV export
  (verified: no `email` field in `backend/src/schemas` responses). See [T088 note](../specs/001-wedding-media-platform/data-model.md).
- Hidden media never appears in guest gallery/detail/share (enforced in queries + share
  resolution).

## Uploads
- Presigned-URL PUT scopes each upload to a single object key; type/size validated and
  duplicates rejected at `init` before any storage write.
- nginx `client_max_body_size 550m` matches the video size ceiling.

## Recommended follow-ups
- Add gitleaks to CI. Consider per-IP app-level throttling as defense-in-depth behind nginx.
