"""Pydantic v2 contracts for the admin console (US8)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from .media import MediaOut


class AdminStats(BaseModel):
    total_media: int
    total_users: int
    total_views: int
    total_reactions: int
    total_comments: int
    storage_bytes: int
    media_by_type: dict[str, int]
    media_by_status: dict[str, int]
    uploads_last_7_days: int
    top_by_views: list[dict]


class UserAdminOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    language_preference: str
    created_at: datetime


class UserListResponse(BaseModel):
    items: list[UserAdminOut]
    has_more: bool


class UserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(guest|admin)$")
    is_active: bool | None = None


class VisibilityRequest(BaseModel):
    is_visible: bool


class MediaListResponse(BaseModel):
    items: list["MediaOut"]
    has_more: bool


class EventConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uploads_enabled: bool
    max_image_bytes: int
    max_video_bytes: int
    event_name: str
    event_date: date | None


class EventConfigUpdate(BaseModel):
    """Every field optional — omitted ones are left untouched."""

    uploads_enabled: bool | None = None
    max_image_bytes: int | None = Field(default=None, gt=0)
    max_video_bytes: int | None = Field(default=None, gt=0)
    event_name: str | None = Field(default=None, min_length=1, max_length=200)
    event_date: date | None = None
