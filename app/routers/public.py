"""Public routes (no auth required)."""
import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant
from app.models.landing_page import LandingPage, PageView
from app.models.tenant import Tenant
from app.models.webhook import Lead

router = APIRouter(tags=["public"])


@router.get("/p/{slug}")
async def get_landing_page(
    slug: str,
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LandingPage).where(
            LandingPage.tenant_id == tenant.id,
            LandingPage.slug == slug,
            LandingPage.status == "published",
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Track view
    ip = request.client.host if request.client else ""
    ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else None
    view = PageView(
        page_id=page.id,
        ip_hash=ip_hash,
        user_agent=request.headers.get("user-agent"),
        utm_source=request.query_params.get("utm_source"),
        utm_medium=request.query_params.get("utm_medium"),
        utm_campaign=request.query_params.get("utm_campaign"),
        utm_term=request.query_params.get("utm_term"),
        utm_content=request.query_params.get("utm_content"),
    )
    db.add(view)
    await db.commit()

    return {
        "slug": page.slug,
        "title": page.title,
        "seo_description": page.seo_description,
        "seo_keywords": page.seo_keywords,
        "jsx_code": page.jsx_code,
        "css_code": page.css_code,
        "product_id": str(page.product_id) if page.product_id else None,
        "page_metadata": page.page_metadata,
    }


@router.post("/p/{slug}/lead", status_code=201)
async def capture_lead(
    slug: str,
    body: dict[str, Any],
    request: Request,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LandingPage).where(
            LandingPage.tenant_id == tenant.id,
            LandingPage.slug == slug,
            LandingPage.status == "published",
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    email = body.get("email", "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    lead = Lead(
        tenant_id=tenant.id,
        email=email,
        name=body.get("name"),
        source="landing_page",
        utm_source=request.query_params.get("utm_source"),
        utm_medium=request.query_params.get("utm_medium"),
        utm_campaign=request.query_params.get("utm_campaign"),
        utm_term=request.query_params.get("utm_term"),
        utm_content=request.query_params.get("utm_content"),
        product_id=page.product_id,
    )
    db.add(lead)
    await db.commit()

    return {"status": "ok", "lead_id": str(lead.id)}


@router.get("/p/{slug}/analytics")
async def landing_page_analytics(
    slug: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LandingPage).where(
            LandingPage.tenant_id == tenant.id,
            LandingPage.slug == slug,
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    views_result = await db.execute(
        select(func.count(PageView.id)).where(PageView.page_id == page.id)
    )
    total_views = views_result.scalar() or 0

    leads_result = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.tenant_id == tenant.id,
            Lead.utm_campaign == slug,
        )
    )
    total_leads = leads_result.scalar() or 0

    return {
        "slug": slug,
        "views": total_views,
        "leads": total_leads,
        "conversion_rate": round(total_leads / total_views, 4) if total_views else 0.0,
    }
