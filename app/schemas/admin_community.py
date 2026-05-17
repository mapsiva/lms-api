"""Admin community schemas."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    post_id: Optional[uuid.UUID]
    comment_id: Optional[uuid.UUID]
    reporter_id: uuid.UUID
    reason: Optional[str]
    ai_flagged: bool
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]


class SpaceCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: Optional[str] = None


class SpaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime


class ChannelCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    channel_type: str = "discussion"
    post_policy: str = "open"


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    space_id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    channel_type: str
    post_policy: str
    is_active: bool
    created_at: datetime


class HideResponse(BaseModel):
    hidden: bool


class PinResponse(BaseModel):
    pinned: bool


class SuspendResponse(BaseModel):
    suspended: bool
