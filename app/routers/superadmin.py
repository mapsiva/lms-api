"""Superadmin routes (no tenant binding)."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.services import superadmin as superadmin_service

router = APIRouter(prefix="/superadmin", tags=["superadmin"])

_bearer = HTTPBearer(auto_error=False)


def require_super_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    from app.core.errors import AppError
    from app.core.error_codes import ErrorCode

    if not credentials:
        raise AppError(ErrorCode.NOT_AUTHENTICATED)
    payload = decode_token(credentials.credentials)
    if payload.get("role") != "super_admin":
        raise AppError(ErrorCode.SUPERADMIN_REQUIRED)
    return payload


@router.get("/tenants")
async def list_tenants(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _super_admin: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await superadmin_service.list_tenants(db, page, per_page)


@router.post("/tenants", status_code=201)
async def create_tenant(
    body: TenantCreate,
    _super_admin: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await superadmin_service.create_tenant(db, body)


@router.patch("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    _super_admin: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await superadmin_service.update_tenant(db, tenant_id, body)


@router.get("/tenants/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: uuid.UUID,
    _super_admin: dict = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    return await superadmin_service.get_tenant_stats(db, tenant_id)
