import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    is_read: bool
    created_at: Any


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    total: int
    page: int
    page_size: int


class BroadcastRequest(BaseModel):
    type: str | None = "broadcast"
    title: str
    body: str | None = None
    data: dict[str, Any] | None = None


class PushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
