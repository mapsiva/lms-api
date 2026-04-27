"""Email marketing admin router."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.email import EmailAudience, EmailAutomation, EmailCampaign, EmailSend, EmailTemplate
from app.models.user import User

router = APIRouter(prefix="/admin/email", tags=["admin:email"])


# --- Audiences ---

@router.get("/audiences")
async def list_audiences(
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmailAudience).where(EmailAudience.tenant_id == tenant.id)
    )
    return result.scalars().all()


@router.post("/audiences", status_code=201)
async def create_audience(
    name: str,
    filter_json: dict | None = None,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    audience = EmailAudience(tenant_id=tenant.id, name=name, filter_json=filter_json)
    db.add(audience)
    await db.commit()
    await db.refresh(audience)
    return audience


# --- Templates ---

@router.get("/templates")
async def list_templates(
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.tenant_id == tenant.id)
    )
    return result.scalars().all()


@router.post("/templates", status_code=201)
async def create_template(
    name: str,
    subject: str,
    html_body: str,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    template = EmailTemplate(tenant_id=tenant.id, name=name, subject=subject, html_body=html_body)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


# --- Campaigns ---

@router.get("/campaigns")
async def list_campaigns(
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmailCampaign).where(EmailCampaign.tenant_id == tenant.id)
    )
    return result.scalars().all()


@router.post("/campaigns", status_code=201)
async def create_campaign(
    name: str,
    template_id: uuid.UUID,
    audience_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    campaign = EmailCampaign(
        tenant_id=tenant.id,
        name=name,
        template_id=template_id,
        audience_id=audience_id,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User as UserModel
    from app.models.enrollment import Enrollment

    campaign = await db.get(EmailCampaign, campaign_id)
    if campaign is None or campaign.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Campaign not found")

    template = await db.get(EmailTemplate, campaign.template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    audience = await db.get(EmailAudience, campaign.audience_id)
    if audience is None:
        raise HTTPException(status_code=404, detail="Audience not found")

    # Resolve audience
    query = select(UserModel).where(UserModel.tenant_id == tenant.id, UserModel.is_active == True)  # noqa: E712
    filters = audience.filter_json or {}

    if "role" in filters:
        query = query.where(UserModel.role == filters["role"])
    if "company_id" in filters:
        query = query.where(UserModel.company_id == uuid.UUID(filters["company_id"]))
    if "enrolled_in" in filters:
        query = query.join(
            Enrollment, Enrollment.user_id == UserModel.id
        ).where(
            Enrollment.product_id == uuid.UUID(filters["enrolled_in"]),
            Enrollment.status == "active",
        )

    result = await db.execute(query)
    users = result.scalars().all()

    # Create sends, dispatch batches
    batch = []
    for user in users:
        send = EmailSend(
            campaign_id=campaign.id,
            user_id=user.id,
            email=user.email,
        )
        db.add(send)
        batch.append(send)
        if len(batch) >= 100:
            await db.commit()
            _dispatch_batch(batch, campaign.id, template.subject, template.html_body)
            batch = []

    if batch:
        await db.commit()
        _dispatch_batch(batch, campaign.id, template.subject, template.html_body)

    campaign.status = "sent"
    campaign.sent_count = len(users)
    await db.commit()

    return {"status": "sent", "recipients": len(users)}


def _dispatch_batch(sends: list, campaign_id: uuid.UUID, subject: str, html_body: str) -> None:
    items = [{"email": s.email, "send_id": str(s.id)} for s in sends]
    celery_app.send_task(
        "app.tasks.email.send_campaign_batch_task",
        args=[items, str(campaign_id), subject, html_body],
    )


# --- Automations ---

@router.get("/automations")
async def list_automations(
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmailAutomation).where(EmailAutomation.tenant_id == tenant.id)
    )
    return result.scalars().all()


@router.post("/automations", status_code=201)
async def create_automation(
    name: str,
    trigger_event: str | None = None,
    steps: list | None = None,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    automation = EmailAutomation(
        tenant_id=tenant.id,
        name=name,
        trigger_event=trigger_event,
        steps=steps,
    )
    db.add(automation)
    await db.commit()
    await db.refresh(automation)
    return automation


# --- Open tracking ---

@router.get("/track/{send_id}/open.gif")
async def track_open(send_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    send = await db.get(EmailSend, send_id)
    if send and send.status == "sent":
        send.status = "opened"
        from datetime import datetime, timezone
        send.opened_at = datetime.now(timezone.utc)
        await db.commit()

    # Return 1x1 transparent GIF
    from fastapi.responses import Response
    gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    return Response(content=gif, media_type="image/gif")
