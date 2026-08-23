"""Downloads router — bulk ZIP (US9 / contracts/downloads.md)."""

from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..deps import CurrentUser, DbDep
from ..i18n import t
from ..services import zip_service

router = APIRouter(prefix="/api/v1/downloads", tags=["downloads"])


class BulkDownloadRequest(BaseModel):
    media_ids: list[int] = Field(default_factory=list)


@router.post("/bulk")
async def bulk_download(
    body: BulkDownloadRequest, user: CurrentUser, session: DbDep
) -> StreamingResponse:
    entries = await zip_service.load_entries(session, body.media_ids)
    filename = t("archive_filename", user.language_preference)
    # ASCII fallback for clients that ignore filename*, plus the RFC 5987 encoded form
    # (filename*=UTF-8''...) so ZH/RU names render correctly where it's supported.
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii")
    disposition = f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"
    return StreamingResponse(
        zip_service.stream_zip(entries),
        media_type="application/zip",
        headers={"Content-Disposition": disposition},
    )
