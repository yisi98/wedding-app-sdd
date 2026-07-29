"""Pydantic v2 contracts for social engagement (US4)."""

from datetime import datetime

from pydantic import BaseModel, Field

from ..models.reaction import REACTION_TYPES


class ReactionRequest(BaseModel):
    reaction_type: str = Field(pattern=f"^({'|'.join(REACTION_TYPES)})$")


class ReactionState(BaseModel):
    reaction_type: str | None
    reaction_count: int


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    media_id: int
    user_id: int
    username: str
    content: str
    created_at: datetime


class FavoriteState(BaseModel):
    favorited: bool
    favorite_count: int
