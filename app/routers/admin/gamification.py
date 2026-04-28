"""Admin gamification router — badge and special event management."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.gamification import (
    BadgeAdminResponse,
    BadgeCreate,
    BadgeUpdate,
    SpecialEventCreate,
    SpecialEventResponse,
)
from app.services import admin_gamification as svc

router = APIRouter(prefix="/admin/gamification", tags=["admin-gamification"])


@router.get("/badges", response_model=list[BadgeAdminResponse])
async def list_badges(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_badges(db, tenant.id)


@router.post("/badges", response_model=BadgeAdminResponse, status_code=201)
async def create_badge(
    data: BadgeCreate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_badge(db, tenant.id, data)


@router.patch("/badges/{badge_id}", response_model=BadgeAdminResponse)
async def update_badge(
    badge_id: uuid.UUID,
    data: BadgeUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await svc.update_badge(db, tenant.id, badge_id, data)


@router.delete("/badges/{badge_id}", status_code=204)
async def delete_badge(
    badge_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await svc.delete_badge(db, tenant.id, badge_id)


@router.get("/events", response_model=list[SpecialEventResponse])
async def list_special_events(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_special_events(db, tenant.id)


@router.post("/events", response_model=SpecialEventResponse, status_code=201)
async def create_special_event(
    data: SpecialEventCreate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_special_event(db, tenant.id, data)


@router.delete("/events/{event_id}", status_code=204)
async def delete_special_event(
    event_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await svc.delete_special_event(db, tenant.id, event_id)
