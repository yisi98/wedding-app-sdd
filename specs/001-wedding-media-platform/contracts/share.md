# Contract: Sharing (`/api/v1/share`)

Implements US5 / FR-SHARE.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/share` | access token | Body `{ media_id?: id, expires_at?: datetime }`. `media_id` null ⇒ whole-gallery share. Returns `{ token, url }`; the client renders a QR code + native Web Share / copy-link. |
| GET | `/share/{token}` | none (token is the credential) | Resolve a share token to the gallery or single item; increments `access_count`. Expired token → **404/410**. If the target item is now hidden/deleted, it is not exposed. |
