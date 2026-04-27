"""Admin landing pages router."""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.landing_page import LandingPage, PageView
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/admin/landing-pages", tags=["admin:landing-pages"])


@router.get("")
async def list_landing_pages(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LandingPage).where(LandingPage.tenant_id == tenant.id)
    )
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "slug": r.slug,
                "title": r.title,
                "status": r.status,
                "product_id": str(r.product_id) if r.product_id else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.post("", status_code=201)
async def create_landing_page(
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    page = LandingPage(
        tenant_id=tenant.id,
        slug=body["slug"],
        title=body["title"],
        seo_description=body.get("seo_description"),
        seo_keywords=body.get("seo_keywords"),
        jsx_code=body.get("jsx_code"),
        css_code=body.get("css_code"),
        status=body.get("status", "draft"),
        product_id=body.get("product_id"),
        page_metadata=body.get("page_metadata"),
    )
    db.add(page)
    await db.commit()
    await db.refresh(page)
    return {"id": str(page.id)}


@router.get("/{page_id}")
async def get_landing_page(
    page_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    page = await db.get(LandingPage, page_id)
    if not page or page.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Landing page not found")
    return {
        "id": str(page.id),
        "slug": page.slug,
        "title": page.title,
        "seo_description": page.seo_description,
        "seo_keywords": page.seo_keywords,
        "jsx_code": page.jsx_code,
        "css_code": page.css_code,
        "status": page.status,
        "product_id": str(page.product_id) if page.product_id else None,
        "page_metadata": page.page_metadata,
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
    }


@router.patch("/{page_id}")
async def update_landing_page(
    page_id: uuid.UUID,
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    page = await db.get(LandingPage, page_id)
    if not page or page.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Landing page not found")
    for field in body:
        if hasattr(page, field):
            setattr(page, field, body[field])
    await db.commit()
    await db.refresh(page)
    return {"id": str(page.id)}


@router.delete("/{page_id}", status_code=204)
async def delete_landing_page(
    page_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    page = await db.get(LandingPage, page_id)
    if not page or page.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Landing page not found")
    await db.delete(page)
    await db.commit()
    return


@router.get("/{page_id}/analytics")
async def landing_page_analytics(
    page_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    page = await db.get(LandingPage, page_id)
    if not page or page.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Landing page not found")

    views_result = await db.execute(
        select(func.count(PageView.id)).where(PageView.page_id == page_id)
    )
    total_views = views_result.scalar() or 0

    leads_result = await db.execute(
        select(func.count(LandingPage.id))
        .select_from(LandingPage)
        .where(LandingPage.id == page_id)
    )
    # Lead count is approximate; for MVP use lead records from webhook.Leads
    from app.models.webhook import Lead

    leads_result = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.utm_campaign == page.slug, Lead.tenant_id == tenant.id
        )
    )
    total_leads = leads_result.scalar() or 0

    return {
        "page_id": str(page_id),
        "views": total_views,
        "leads": total_leads,
        "conversion_rate": round(total_leads / total_views, 4) if total_views else 0.0,
    }
