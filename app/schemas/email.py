"""Pydantic schemas for email marketing."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Audiences
# ---------------------------------------------------------------------------
class AudienceCreate(BaseModel):
    name: str
    filter_json: dict[str, Any] | None = None


class AudienceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    filter_json: dict[str, Any] | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
class TemplateCreate(BaseModel):
    name: str
    subject: str
    html_body: str


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    subject: str
    html_body: str
    created_at: datetime


class SystemTemplateResponse(BaseModel):
    key: str
    name: str
    description: str
    category: str
    subject: str
    html_body: str
    required_variables: list[str]
    sample_context: dict[str, Any]


class SystemTemplatePreviewRequest(BaseModel):
    context: dict[str, Any] | None = None


class SystemTemplatePreviewResponse(BaseModel):
    key: str
    subject: str
    html_body: str


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------
class CampaignCreate(BaseModel):
    name: str
    template_id: uuid.UUID
    audience_id: uuid.UUID


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    template_id: uuid.UUID
    audience_id: uuid.UUID
    status: str
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    sent_count: int
    created_at: datetime


class CampaignSendResponse(BaseModel):
    status: str
    recipients: int


# ---------------------------------------------------------------------------
# Automations
# ---------------------------------------------------------------------------
class AutomationCreate(BaseModel):
    name: str
    trigger_event: str | None = None
    steps: list[Any] | None = None


class AutomationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    trigger_event: str | None = None
    steps: list[Any] | None = None
    is_active: bool
    created_at: datetime
