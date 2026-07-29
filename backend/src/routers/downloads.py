"""Downloads router — bulk ZIP (US9 / contracts/downloads.md)."""

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from ..deps import CurrentUser, DbDep
from ..services import zip_service

router = APIRouter(prefix="/api/v1/downloads", tags=["downloads"])


class BulkDownloadRequest(BaseModel):
    media_ids: list[int] = Field(default_factory=list)


@router.post("/bulk")
async def bulk_download(body: BulkDownloadRequest, user: CurrentUser, session: DbDep) -> Response:
    data = await zip_service.build_zip(session, body.media_ids)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=wedding-media.zip"},
    )
