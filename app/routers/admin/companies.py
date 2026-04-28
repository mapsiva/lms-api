import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.services import company as company_service

router = APIRouter(prefix="/admin/companies", tags=["admin:companies"])


@router.get("")
async def list_companies(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
):
    return await company_service.list_companies(db, tenant.id, status)


@router.post("", status_code=201)
async def create_company(
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.create_company(db, tenant.id, body)


@router.get("/{company_id}")
async def get_company(
    company_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.get_company(db, company_id, tenant.id)


@router.patch("/{company_id}")
async def update_company(
    company_id: uuid.UUID,
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.update_company(db, company_id, tenant.id, body)


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await company_service.delete_company(db, company_id, tenant.id)


# ── Members ──────────────────────────────────────────────────────────────────


@router.get("/{company_id}/members")
async def list_members(
    company_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.list_members(db, company_id, tenant.id)


@router.post("/{company_id}/members/bulk-import")
async def bulk_import_members(
    company_id: uuid.UUID,
    file: UploadFile,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.bulk_import_members(db, company_id, tenant.id, file)


@router.post("/{company_id}/members/invite")
async def invite_member(
    company_id: uuid.UUID,
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.invite_member(db, company_id, tenant.id, body)


@router.delete("/{company_id}/members/{user_id}", status_code=204)
async def remove_member(
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await company_service.remove_member(db, company_id, tenant.id, user_id)


# ── Reports ──────────────────────────────────────────────────────────────────


@router.get("/{company_id}/report")
async def company_report(
    company_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await company_service.company_report(db, company_id, tenant.id)
