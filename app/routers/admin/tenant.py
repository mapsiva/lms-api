import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.core.redis_client import get_redis
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import (
    TenantBrandingResponse,
    TenantBrandingUpdate,
    TenantSettingsResponse,
    TenantSettingsUpdate,
)

router = APIRouter(prefix="/admin/tenant", tags=["admin:tenant"])

_TENANT_CACHE_TTL = 300


async def _load_tenant_orm(tenant_id: uuid.UUID, db: AsyncSession) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    return result.scalar_one()


async def _invalidate_tenant_cache(tenant: Tenant) -> None:
    redis = get_redis()
    if not redis:
        return
    keys = []
    if tenant.custom_domain:
        keys.append(f"tenant:host:{tenant.custom_domain}")
    if tenant.subdomain:
        keys.append(f"tenant:host:{tenant.subdomain}")
    if keys:
        await redis.delete(*keys)


@router.get("/branding", response_model=TenantBrandingResponse)
async def get_branding(
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    t = await _load_tenant_orm(tenant.id, db)
    return t


@router.patch("/branding", response_model=TenantBrandingResponse)
async def update_branding(
    body: TenantBrandingUpdate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    t = await _load_tenant_orm(tenant.id, db)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(t, field, value)
    await db.commit()
    await db.refresh(t)
    await _invalidate_tenant_cache(t)
    return t


@router.get("/settings", response_model=TenantSettingsResponse)
async def get_settings_endpoint(
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    t = await _load_tenant_orm(tenant.id, db)
    return t


@router.patch("/settings", response_model=TenantSettingsResponse)
async def update_settings(
    body: TenantSettingsUpdate,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    t = await _load_tenant_orm(tenant.id, db)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(t, field, value)
    await db.commit()
    await db.refresh(t)
    await _invalidate_tenant_cache(t)
    return t
