"""Email marketing business logic."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.email import EmailAudience, EmailAutomation, EmailCampaign, EmailSend, EmailTemplate
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.email import (
    AudienceCreate,
    AudienceResponse,
    AutomationCreate,
    AutomationResponse,
    CampaignCreate,
    CampaignResponse,
    CampaignSendResponse,
    TemplateCreate,
    TemplateResponse,
)


async def list_audiences(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[AudienceResponse]:
    result = await db.execute(
        select(EmailAudience).where(EmailAudience.tenant_id == tenant_id)
    )
    rows = result.scalars().all()
    return [AudienceResponse.model_validate(r) for r in rows]


async def create_audience(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: AudienceCreate,
) -> AudienceResponse:
    audience = EmailAudience(
        tenant_id=tenant_id,
        name=data.name,
        filter_json=data.filter_json,
    )
    db.add(audience)
    await db.commit()
    await db.refresh(audience)
    return AudienceResponse.model_validate(audience)


async def list_templates(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[TemplateResponse]:
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.tenant_id == tenant_id)
    )
    rows = result.scalars().all()
    return [TemplateResponse.model_validate(r) for r in rows]


async def create_template(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: TemplateCreate,
) -> TemplateResponse:
    template = EmailTemplate(
        tenant_id=tenant_id,
        name=data.name,
        subject=data.subject,
        html_body=data.html_body,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return TemplateResponse.model_validate(template)


async def list_campaigns(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[CampaignResponse]:
    result = await db.execute(
        select(EmailCampaign).where(EmailCampaign.tenant_id == tenant_id)
    )
    rows = result.scalars().all()
    return [CampaignResponse.model_validate(r) for r in rows]


async def create_campaign(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: CampaignCreate,
) -> CampaignResponse:
    campaign = EmailCampaign(
        tenant_id=tenant_id,
        name=data.name,
        template_id=data.template_id,
        audience_id=data.audience_id,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return CampaignResponse.model_validate(campaign)


async def send_campaign(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> CampaignSendResponse:
    campaign = await db.get(EmailCampaign, campaign_id)
    if campaign is None or campaign.tenant_id != tenant_id:
        raise AppError(ErrorCode.CAMPAIGN_NOT_FOUND)

    template = await db.get(EmailTemplate, campaign.template_id)
    if template is None:
        raise AppError(ErrorCode.TEMPLATE_NOT_FOUND)

    audience = await db.get(EmailAudience, campaign.audience_id)
    if audience is None:
        raise AppError(ErrorCode.AUDIENCE_NOT_FOUND)

    # Resolve audience
    query = select(User).where(
        User.tenant_id == tenant_id,
        User.is_active.is_(True),  # type: ignore[attr-defined]
    )
    filters = audience.filter_json or {}

    if "role" in filters:
        query = query.where(User.role == filters["role"])
    if "company_id" in filters:
        query = query.where(User.company_id == uuid.UUID(filters["company_id"]))
    if "enrolled_in" in filters:
        query = query.join(
            Enrollment, Enrollment.user_id == User.id
        ).where(
            Enrollment.product_id == uuid.UUID(filters["enrolled_in"]),
            Enrollment.status == "active",
        )

    result = await db.execute(query)
    users = result.scalars().all()

    # Create sends, dispatch batches
    batch: list[EmailSend] = []
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
            _dispatch_batch(batch, str(campaign.id), template.subject, template.html_body)
            batch = []

    if batch:
        await db.commit()
        _dispatch_batch(batch, str(campaign.id), template.subject, template.html_body)

    campaign.status = "sent"
    campaign.sent_count = len(users)
    await db.commit()

    return CampaignSendResponse(status="sent", recipients=len(users))


def _dispatch_batch(
    sends: list[EmailSend],
    campaign_id: str,
    subject: str,
    html_body: str,
) -> None:
    items = [{"email": s.email, "send_id": str(s.id)} for s in sends]
    celery_app.send_task(
        "app.tasks.email.send_campaign_batch_task",
        args=[items, campaign_id, subject, html_body],
    )


async def list_automations(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> list[AutomationResponse]:
    result = await db.execute(
        select(EmailAutomation).where(EmailAutomation.tenant_id == tenant_id)
    )
    rows = result.scalars().all()
    return [AutomationResponse.model_validate(r) for r in rows]


async def create_automation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: AutomationCreate,
) -> AutomationResponse:
    automation = EmailAutomation(
        tenant_id=tenant_id,
        name=data.name,
        trigger_event=data.trigger_event,
        steps=data.steps,
    )
    db.add(automation)
    await db.commit()
    await db.refresh(automation)
    return AutomationResponse.model_validate(automation)
