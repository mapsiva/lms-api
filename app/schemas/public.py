"""Response schemas for public routes."""
from typing import Any

from pydantic import BaseModel


class LandingPageDetailResponse(BaseModel):
    slug: str
    title: str
    seo_description: str | None
    seo_keywords: str | None
    jsx_code: str | None
    css_code: str | None
    product_id: str | None
    page_metadata: dict[str, Any] | None


class LeadCaptureResponse(BaseModel):
    status: str
    lead_id: str


class LandingPageAnalyticsResponse(BaseModel):
    slug: str
    views: int
    leads: int
    conversion_rate: float
