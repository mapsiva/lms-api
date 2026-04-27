"""Pydantic schemas for landing pages."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LandingPageListItem(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    status: str
    product_id: uuid.UUID | None = None
    created_at: datetime | None = None


class LandingPageCreate(BaseModel):
    slug: str
    title: str
    seo_description: str | None = None
    seo_keywords: str | None = None
    jsx_code: str | None = None
    css_code: str | None = None
    status: str = "draft"
    product_id: uuid.UUID | None = None
    page_metadata: dict[str, Any] | None = None


class LandingPageUpdate(BaseModel):
    slug: str | None = None
    title: str | None = None
    seo_description: str | None = None
    seo_keywords: str | None = None
    jsx_code: str | None = None
    css_code: str | None = None
    status: str | None = None
    product_id: uuid.UUID | None = None
    page_metadata: dict[str, Any] | None = None


class LandingPageDetail(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    seo_description: str | None = None
    seo_keywords: str | None = None
    jsx_code: str | None = None
    css_code: str | None = None
    status: str
    product_id: uuid.UUID | None = None
    page_metadata: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LandingPageIdResponse(BaseModel):
    id: uuid.UUID


class LandingPageAnalytics(BaseModel):
    page_id: uuid.UUID
    views: int
    leads: int
    conversion_rate: float
