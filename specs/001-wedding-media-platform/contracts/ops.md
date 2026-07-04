# Contract: Operations / Health (`/api/v1`)

Implements FR-038.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/health` | none | Liveness/readiness probe. Checks DB **and** Redis connectivity; returns **200** when healthy, **503** when any core dependency is degraded. |

**Notes**: Used by Docker/nginx/AliCloud health checks and by the go-live smoke test. The
response distinguishes which dependency is degraded to aid ops triage.
