"""Pydantic v2 contracts for the admin console (US8)."""

from datetime import datetime

from pydantic import BaseModel, Field


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
