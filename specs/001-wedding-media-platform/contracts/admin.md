# Contract: Admin Console (`/api/v1/admin`)

Implements US8 / FR-ADMIN. **Every** endpoint requires `role = admin`; non-admin → **403**.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin/stats` | Totals (media, users, views, reactions, comments, storage bytes), media-by-type, media-by-status, uploads last 7 days, top 5 by views. |
| GET | `/admin/users` | List/search/paginate users. |
| PATCH | `/admin/users/{id}` | Promote guest→admin, deactivate. **Cannot modify own admin account → 4xx** (FR-031). |
| DELETE | `/admin/users/{id}` | Delete a user. **Cannot delete own admin account** (FR-031). |
| GET | `/admin/media` | List all media **including hidden** (guest gallery never shows hidden). |
| PATCH | `/admin/media/{id}/visibility` | Hide/show toggle. |
| GET | `/admin/export/media` | CSV export of all media metadata. |

**Guard rail**: an admin operating on their own account for modification/deletion is
refused, preventing self-lockout.
