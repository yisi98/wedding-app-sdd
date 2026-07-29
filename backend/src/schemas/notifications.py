"""Pydantic v2 contracts for activity feed + web push (US6)."""

from datetime import datetime

from pydantic import BaseModel, Field


class ActivityOut(BaseModel):
    id: int
    event_type: str
    user_id: int
    username: str
    media_id: int | None
    payload: dict
    created_at: datetime


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=1, max_length=512)
    p256dh: str = Field(min_length=1)
    auth: str = Field(min_length=1)


class VapidKeyResponse(BaseModel):
    public_key: str | None
