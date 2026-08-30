"""Object-serving route.

Serves media bytes from storage. Keys embed the content SHA-256, so they act as
unguessable capability URLs. No Authorization header is possible from an
`<img>`/`<video>` tag, so this endpoint is unauthenticated by design; privacy relies on
the unguessable key.

With S3-compatible storage (AliCloud OSS in prod) the route never proxies bytes: it
redirects to a short-lived presigned GET URL, which lets OSS serve HTTP Range
requests (required for `<video>` seeking on iOS Safari) and keeps large media out of
the backend process. LocalStorage (dev/test) has no presigning and serves bytes
inline instead.
"""

import mimetypes

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import RedirectResponse

from ..services.storage import get_storage

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/heic", ".heic")

router = APIRouter(tags=["objects"])


@router.get("/media-object/{key:path}")
async def serve_object(key: str) -> Response:
    storage = get_storage()
    presigned = storage.presigned_get_url(key)
    if presigned is not None:
        # Short-lived redirect: the signed OSS URL expires, so don't let clients cache
        # the redirect for long (the object behind it carries its own immutable cache
        # headers via the signature's ResponseCacheControl).
        return RedirectResponse(
            presigned, status_code=307, headers={"Cache-Control": "private, max-age=300"}
        )
    try:
        data = storage.get(key)
    except Exception:  # noqa: BLE001 — missing object
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
