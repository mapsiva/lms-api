"""Admin landing pages router."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.landing_page import (
    LandingPageAnalytics,
    LandingPageCreate,
    LandingPageDetail,
    LandingPageIdResponse,
    LandingPageListItem,
    LandingPageLinkCreate,
    LandingPageLinkResponse,
    LandingPageUpdate,
)
from app.services import landing_page as landing_page_service

router = APIRouter(prefix="/admin/landing-pages", tags=["admin:landing-pages"])


@router.get("", response_model=list[LandingPageListItem])
async def list_landing_pages(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await landing_page_service.list_landing_pages(db, tenant.id)


@router.post("", status_code=201, response_model=LandingPageIdResponse)
async def create_landing_page(
    body: LandingPageCreate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await landing_page_service.create_landing_page(db, tenant.id, body)


@router.get("/{page_id}", response_model=LandingPageDetail)
async def get_landing_page(
    page_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await landing_page_service.get_landing_page(db, tenant.id, page_id)


@router.patch("/{page_id}", response_model=LandingPageIdResponse)
async def update_landing_page(
    page_id: uuid.UUID,
    body: LandingPageUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await landing_page_service.update_landing_page(db, tenant.id, page_id, body)


@router.delete("/{page_id}", status_code=204)
async def delete_landing_page(
    page_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await landing_page_service.delete_landing_page(db, tenant.id, page_id)
    return


@router.get("/{page_id}/analytics", response_model=LandingPageAnalytics)
async def landing_page_analytics(
    page_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await landing_page_service.get_landing_page_analytics(db, tenant.id, page_id)


@router.post("/{page_id}/links", response_model=LandingPageLinkResponse)
async def generate_landing_page_link(
    page_id: uuid.UUID,
    body: LandingPageLinkCreate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await landing_page_service.generate_landing_page_link(
        db, tenant.id, page_id, body
    )
