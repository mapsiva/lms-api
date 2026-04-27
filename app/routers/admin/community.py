"""Community admin router."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.admin_community import (
    ChannelCreate,
    ChannelResponse,
    HideResponse,
    ReportResponse,
    SpaceCreate,
    SpaceResponse,
    SuspendResponse,
)
from app.services import admin_community as admin_community_service

router = APIRouter(prefix="/admin/community", tags=["admin:community"])


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports(
    status: str = "pending",
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_community_service.list_reports(db, tenant.id, status)


@router.patch("/reports/{report_id}", response_model=ReportResponse)
async def resolve_report(
    report_id: uuid.UUID,
    status: str,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_community_service.resolve_report(db, tenant.id, report_id, status)


@router.post("/users/{user_id}/suspend", response_model=SuspendResponse)
async def suspend_user(
    user_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await admin_community_service.suspend_user(db, tenant.id, user_id)
    return {"suspended": True}


@router.post("/spaces", status_code=201, response_model=SpaceResponse)
async def create_space(
    body: SpaceCreate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_community_service.create_space(
        db, tenant.id, body.name, body.description
    )


@router.post("/spaces/{space_id}/channels", status_code=201, response_model=ChannelResponse)
async def create_channel(
    space_id: uuid.UUID,
    body: ChannelCreate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await admin_community_service.create_channel(
        db,
        tenant_id=tenant.id,
        space_id=space_id,
        name=body.name,
        channel_type=body.channel_type,
        post_policy=body.post_policy,
    )


@router.patch("/posts/{post_id}/hide", response_model=HideResponse)
async def hide_post(
    post_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await admin_community_service.hide_post(db, tenant.id, post_id)
    return {"hidden": True}


@router.patch("/comments/{comment_id}/hide", response_model=HideResponse)
async def hide_comment(
    comment_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await admin_community_service.hide_comment(db, tenant.id, comment_id)
    return {"hidden": True}
