"""Pydantic schemas for webhooks admin."""
from pydantic import BaseModel


class WebhookLogItem(BaseModel):
    id: str
    provider: str
    event_type: str
    signature_valid: bool
    processed: bool
    attempts: int
    error_message: str | None = None
    received_at: str | None = None


class WebhookLogListResponse(BaseModel):
    items: list[WebhookLogItem]
    next_cursor: str | None = None


class ReplayResponse(BaseModel):
    status: str


class TestModeResponse(BaseModel):
    status: str
    duration_seconds: int
