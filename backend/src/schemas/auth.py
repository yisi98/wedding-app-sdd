"""Pydantic v2 contracts for the auth surface.

`UserOut` intentionally omits `email` — the legacy column is never exposed (research.md).
"""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=150)
    event_password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ProfileUpdate(BaseModel):
    language_preference: str | None = Field(default=None, pattern="^(en|zh|ru)$")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    language_preference: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
