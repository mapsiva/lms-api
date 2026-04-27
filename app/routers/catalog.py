"""Public product catalog (no auth required)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.schemas.catalog import CatalogProductDetail, CatalogProductListItem
from app.services import catalog as catalog_service

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("", response_model=list[CatalogProductListItem])
async def list_catalog(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await catalog_service.list_catalog_products(db, tenant.id)


@router.get("/{slug}", response_model=CatalogProductDetail)
async def get_catalog_product(
    slug: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await catalog_service.get_catalog_product(db, tenant.id, slug)
