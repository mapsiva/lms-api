import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.services import enrollment as enrollment_service

router = APIRouter(prefix="/admin/enrollments", tags=["admin:enrollments"])


@router.get("")
async def list_enrollments(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    product_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await enrollment_service.list_enrollments(
        db, tenant.id, status, user_id, product_id, limit, offset
    )


@router.post("", status_code=201)
async def create_enrollment(
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await enrollment_service.create_enrollment(db, tenant.id, body)


@router.patch("/{enrollment_id}")
async def update_enrollment(
    enrollment_id: uuid.UUID,
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await enrollment_service.update_enrollment(db, tenant.id, enrollment_id, body)


@router.delete("/{enrollment_id}", status_code=204)
async def delete_enrollment(
    enrollment_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await enrollment_service.delete_enrollment(db, tenant.id, enrollment_id)


@router.post("/bulk")
async def bulk_enrollments(
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await enrollment_service.bulk_enrollments(db, tenant.id, body)
