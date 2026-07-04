# Contract: Authentication (`/api/v1/auth`)

Implements US1 / FR-AUTH. No `/register` endpoint exists by design.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/login` | none | Submit `{ display_name, event_password }`. Validates event password; get-or-create account by display name; returns `{ access_token, refresh_token, user }`. Wrong password → **401**. |
| POST | `/auth/refresh` | refresh token | Rotate refresh token; returns new `{ access_token, refresh_token }`. A reused/rotated token → **401** (FR-005). |
| POST | `/auth/logout` | access token | Revoke **all** of the user's refresh tokens. |
| GET | `/auth/me` | access token | Return current user (never includes `email`). |
| PUT | `/auth/profile` | access token | Update mutable profile fields (e.g. `language_preference`). |

**Rules**: access token 15 min; refresh token 7 days with rotation; refresh tokens stored
as SHA-256 hashes. Event password is bcrypt-hashed from `.env`. Responses MUST NOT include
`users.email`.
