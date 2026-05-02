"""Public routes (no auth required)."""
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.public import (
    InviteAcceptRequest,
    InviteAcceptResponse,
    LandingPageAnalyticsResponse,
    LandingPageDetailResponse,
    LeadCaptureResponse,
)
from app.services import public as public_service

router = APIRouter(tags=["public"])


@router.get("/p/{slug}", response_model=LandingPageDetailResponse)
async def get_landing_page(
    slug: str,
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    page = await public_service.get_published_landing_page(db, tenant.id, slug)
    await public_service.track_page_view(db, page, request)

    return LandingPageDetailResponse(
        slug=page.slug,
        title=page.title,
        seo_description=page.seo_description,
        seo_keywords=page.seo_keywords,
        jsx_code=page.jsx_code,
        css_code=page.css_code,
        product_id=str(page.product_id) if page.product_id else None,
        page_metadata=page.page_metadata,
    )


@router.post("/p/{slug}/lead", status_code=201, response_model=LeadCaptureResponse)
async def capture_lead(
    slug: str,
    body: dict[str, Any],
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    page = await public_service.get_published_landing_page(db, tenant.id, slug)
    lead = await public_service.capture_lead(db, tenant.id, page, body, request)
    return LeadCaptureResponse(status="ok", lead_id=str(lead.id))


@router.get("/p/{slug}/analytics", response_model=LandingPageAnalyticsResponse)
async def landing_page_analytics(
    slug: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    total_views, total_leads = await public_service.get_landing_page_analytics(
        db, tenant.id, slug
    )
    conversion_rate = round(total_leads / total_views, 4) if total_views else 0.0
    return LandingPageAnalyticsResponse(
        slug=slug,
        views=total_views,
        leads=total_leads,
        conversion_rate=conversion_rate,
    )


@router.post("/invites/{token}/accept", response_model=InviteAcceptResponse)
async def accept_company_invite(
    token: str,
    body: InviteAcceptRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await public_service.accept_company_invite(
        db, tenant.id, token, body.model_dump(exclude_unset=True)
    )
    from app.core.config import get_settings

    settings = get_settings()
    return InviteAcceptResponse(
        access_token=result["access_token"],
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=result["user_id"],
        company_id=result["company_id"],
    )
