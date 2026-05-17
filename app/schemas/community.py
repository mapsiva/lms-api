"""Student-facing community schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SpaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    has_access: bool
    created_at: datetime


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    space_id: uuid.UUID
    name: str
    channel_type: str
    post_policy: str
    is_active: bool
    has_access: bool
    created_at: datetime


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    body: str
    likes_count: int
    comments_count: int
    is_hidden: bool
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    post_id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    body: str
    is_hidden: bool
    created_at: datetime
