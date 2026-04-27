"""Landing page business logic."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.landing_page import LandingPage, PageView
from app.models.webhook import Lead
from app.schemas.landing_page import (
    LandingPageAnalytics,
    LandingPageCreate,
    LandingPageDetail,
    LandingPageIdResponse,
    LandingPageListItem,
    LandingPageUpdate,
)


async def list_landing_pages(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[LandingPageListItem]:
    result = await db.execute(
        select(LandingPage).where(LandingPage.tenant_id == tenant_id)
    )
    rows = result.scalars().all()
    return [
        LandingPageListItem(
            id=r.id,
            slug=r.slug,
            title=r.title,
            status=r.status,
            product_id=r.product_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


async def create_landing_page(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: LandingPageCreate,
) -> LandingPageIdResponse:
    page = LandingPage(
        tenant_id=tenant_id,
        slug=data.slug,
        title=data.title,
        seo_description=data.seo_description,
        seo_keywords=data.seo_keywords,
        jsx_code=data.jsx_code,
        css_code=data.css_code,
        status=data.status,
        product_id=data.product_id,
        page_metadata=data.page_metadata,
    )
    db.add(page)
    await db.commit()
    await db.refresh(page)
    return LandingPageIdResponse(id=page.id)


async def get_landing_page(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page_id: uuid.UUID,
) -> LandingPageDetail:
    page = await db.get(LandingPage, page_id)
    if not page or page.tenant_id != tenant_id:
        raise AppError(ErrorCode.LANDING_PAGE_NOT_FOUND)

    return LandingPageDetail(
        id=page.id,
        slug=page.slug,
        title=page.title,
        seo_description=page.seo_description,
        seo_keywords=page.seo_keywords,
        jsx_code=page.jsx_code,
        css_code=page.css_code,
        status=page.status,
        product_id=page.product_id,
        page_metadata=page.page_metadata,
        created_at=page.created_at,
        updated_at=page.updated_at,
    )


async def update_landing_page(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page_id: uuid.UUID,
    data: LandingPageUpdate,
) -> LandingPageIdResponse:
    page = await db.get(LandingPage, page_id)
    if not page or page.tenant_id != tenant_id:
        raise AppError(ErrorCode.LANDING_PAGE_NOT_FOUND)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(page, field):
            setattr(page, field, value)

    await db.commit()
    await db.refresh(page)
    return LandingPageIdResponse(id=page.id)


async def delete_landing_page(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page_id: uuid.UUID,
) -> None:
    page = await db.get(LandingPage, page_id)
    if not page or page.tenant_id != tenant_id:
        raise AppError(ErrorCode.LANDING_PAGE_NOT_FOUND)
    await db.delete(page)
    await db.commit()


async def get_landing_page_analytics(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page_id: uuid.UUID,
) -> LandingPageAnalytics:
    page = await db.get(LandingPage, page_id)
    if not page or page.tenant_id != tenant_id:
        raise AppError(ErrorCode.LANDING_PAGE_NOT_FOUND)

    views_result = await db.execute(
        select(func.count(PageView.id)).where(PageView.page_id == page_id)
    )
    total_views = views_result.scalar() or 0

    leads_result = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.utm_campaign == page.slug,
            Lead.tenant_id == tenant_id,
        )
    )
    total_leads = leads_result.scalar() or 0

    return LandingPageAnalytics(
        page_id=page_id,
        views=total_views,
        leads=total_leads,
        conversion_rate=round(total_leads / total_views, 4) if total_views else 0.0,
    )
