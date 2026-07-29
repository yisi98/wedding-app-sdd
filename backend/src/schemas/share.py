"""Pydantic v2 contracts for sharing (US5)."""

from datetime import datetime

from pydantic import BaseModel

from .media import MediaOut


class ShareCreateRequest(BaseModel):
    media_id: int | None = None  # None ⇒ whole-gallery share
    expires_at: datetime | None = None


class ShareCreateResponse(BaseModel):
    token: str
    url: str
    media_id: int | None
    expires_at: datetime | None


class ShareResolveResponse(BaseModel):
    type: str  # "gallery" | "item"
    access_count: int
    media: MediaOut | None = None
    expires_at: datetime | None = None
