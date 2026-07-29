"""Object-serving route.

Serves media bytes from storage. Keys embed the content SHA-256, so they act as
unguessable capability URLs — matching how AliCloud OSS/CDN serve media in production
(public-read bucket fronted by the app). No Authorization header is possible from an
`<img>`/`<video>` tag, so this endpoint is unauthenticated by design; privacy relies on
the unguessable key. In production `NEXT_PUBLIC_MEDIA_BASE` points the frontend straight
at the CDN and this route is unused.
"""

import mimetypes

from fastapi import APIRouter, HTTPException, Response, status

from ..services.storage import get_storage

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/heic", ".heic")

router = APIRouter(tags=["objects"])


@router.get("/media-object/{key:path}")
async def serve_object(key: str) -> Response:
    try:
        data = get_storage().get(key)
    except Exception:  # noqa: BLE001 — missing object
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
