import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
)
from app.services import product as product_service

router = APIRouter(prefix="/admin/products", tags=["admin:products"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
):
    return await product_service.list_products(db, tenant.id, status)


@router.post("", status_code=201, response_model=ProductResponse)
async def create_product(
    body: ProductCreate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.create_product(db, tenant.id, body)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.update_product(db, tenant.id, product_id, body)


@router.patch("/{product_id}/status", response_model=ProductResponse)
async def update_product_status(
    product_id: uuid.UUID,
    body: ProductStatusUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await product_service.update_product_status(
        db, tenant.id, product_id, body.status
    )
