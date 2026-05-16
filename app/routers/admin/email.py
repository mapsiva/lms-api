"""Email marketing admin router."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.email import (
    AudienceCreate,
    AudienceResponse,
    AutomationCreate,
    AutomationResponse,
    CampaignCreate,
    CampaignResponse,
    CampaignSendResponse,
    SystemTemplatePreviewRequest,
    SystemTemplatePreviewResponse,
    SystemTemplateResponse,
    TemplateCreate,
    TemplateResponse,
)
from app.services import email as email_service

router = APIRouter(prefix="/admin/email", tags=["admin:email"])


# --- Audiences ---

@router.get("/audiences", response_model=list[AudienceResponse])
async def list_audiences(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await email_service.list_audiences(db, tenant.id)


@router.post("/audiences", status_code=201, response_model=AudienceResponse)
async def create_audience(
    body: AudienceCreate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await email_service.create_audience(db, tenant.id, body)


# --- Templates ---

@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await email_service.list_templates(db, tenant.id)


@router.post("/templates", status_code=201, response_model=TemplateResponse)
async def create_template(
    body: TemplateCreate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await email_service.create_template(db, tenant.id, body)


@router.get("/system-templates", response_model=list[SystemTemplateResponse])
async def list_system_templates(
    _tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
):
    return await email_service.list_system_templates()


@router.get("/system-templates/{template_key}", response_model=SystemTemplateResponse)
async def get_system_template(
    template_key: str,
    _tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
):
    templates = await email_service.list_system_templates()
    for template in templates:
        if template.key == template_key:
            return template
    from app.core.error_codes import ErrorCode
    from app.core.errors import AppError

    raise AppError(ErrorCode.TEMPLATE_NOT_FOUND)


@router.post(
    "/system-templates/{template_key}/preview",
    response_model=SystemTemplatePreviewResponse,
)
async def preview_system_template(
    template_key: str,
    body: SystemTemplatePreviewRequest,
    _tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
):
    return await email_service.preview_system_template(template_key, body.context or {})


# --- Campaigns ---

@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await email_service.list_campaigns(db, tenant.id)


@router.post("/campaigns", status_code=201, response_model=CampaignResponse)
async def create_campaign(
    body: CampaignCreate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await email_service.create_campaign(db, tenant.id, body)


@router.post("/campaigns/{campaign_id}/send", response_model=CampaignSendResponse)
async def send_campaign(
    campaign_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await email_service.send_campaign(db, tenant.id, campaign_id)


# --- Automations ---

@router.get("/automations", response_model=list[AutomationResponse])
async def list_automations(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await email_service.list_automations(db, tenant.id)


@router.post("/automations", status_code=201, response_model=AutomationResponse)
async def create_automation(
    body: AutomationCreate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await email_service.create_automation(db, tenant.id, body)


# --- Open tracking ---

@router.get("/track/{send_id}/open.gif")
async def track_open(
    send_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    send = await db.get(email_service.EmailSend, send_id)
    if send and send.status == "sent":
        send.status = "opened"
        from datetime import datetime, timezone
        send.opened_at = datetime.now(timezone.utc)
        await db.commit()

    # Return 1x1 transparent GIF
    from fastapi.responses import Response
    gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    return Response(content=gif, media_type="image/gif")
