"""Pydantic v2 contracts for media upload + read (US2/US3)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UploadInitRequest(BaseModel):
    original_filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    file_size: int = Field(gt=0)
    file_hash: str = Field(min_length=64, max_length=64)  # SHA-256 hex


class UploadInitResponse(BaseModel):
    media_id: int
    upload_url: str
    storage_key: str
    status: str


class UploadConfirmRequest(BaseModel):
    media_id: int


class MediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uploader_id: int
    uploader_name: str
    filename: str
    original_filename: str
    file_hash: str
    media_type: str
    mime_type: str
    storage_path: str
    status: str
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    lqip: str | None = None
    thumbnail_path: str | None = None
    optimized_path: str | None = None
    view_count: int
    reaction_count: int
    comment_count: int
    favorite_count: int
    is_visible: bool
    created_at: datetime


class GalleryResponse(BaseModel):
    items: list["MediaOut"]
    has_more: bool
    next_offset: int | None = None
