"""Business logic for public routes."""
import hashlib
import uuid
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_invite_token,
    hash_password,
)
from app.models.company import Company, CompanyMember
from app.models.landing_page import LandingPage, PageView
from app.models.user import User
from app.models.webhook import Lead


async def get_published_landing_page(
    db: AsyncSession, tenant_id: Any, slug: str
) -> LandingPage:
    result = await db.execute(
        select(LandingPage).where(
            LandingPage.tenant_id == tenant_id,
            LandingPage.slug == slug,
            LandingPage.status == "published",
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise AppError(ErrorCode.LANDING_PAGE_NOT_FOUND)
    return page


async def track_page_view(
    db: AsyncSession, page: LandingPage, request: Request
) -> None:
    ip = request.client.host if request.client else ""
    ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else None
    view = PageView(
        page_id=page.id,
        ip_hash=ip_hash,
        user_agent=request.headers.get("user-agent"),
        utm_source=request.query_params.get("utm_source"),
        utm_medium=request.query_params.get("utm_medium"),
        utm_campaign=request.query_params.get("utm_campaign"),
        utm_term=request.query_params.get("utm_term"),
        utm_content=request.query_params.get("utm_content"),
    )
    db.add(view)
    await db.commit()


async def capture_lead(
    db: AsyncSession,
    tenant_id: Any,
    page: LandingPage,
    body: dict[str, Any],
    request: Request,
) -> Lead:
    email = body.get("email", "").strip()
    if not email:
        raise AppError(ErrorCode.EMAIL_REQUIRED)

    lead = Lead(
        tenant_id=tenant_id,
        email=email,
        name=body.get("name"),
        source="landing_page",
        utm_source=request.query_params.get("utm_source"),
        utm_medium=request.query_params.get("utm_medium"),
        utm_campaign=request.query_params.get("utm_campaign"),
        utm_term=request.query_params.get("utm_term"),
        utm_content=request.query_params.get("utm_content"),
        product_id=page.product_id,
    )
    db.add(lead)
    await db.commit()
    return lead


async def get_landing_page_analytics(
    db: AsyncSession, tenant_id: Any, slug: str
) -> tuple[int, int]:
    result = await db.execute(
        select(LandingPage).where(
            LandingPage.tenant_id == tenant_id,
            LandingPage.slug == slug,
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise AppError(ErrorCode.LANDING_PAGE_NOT_FOUND)

    views_result = await db.execute(
        select(func.count(PageView.id)).where(PageView.page_id == page.id)
    )
    total_views = views_result.scalar() or 0

    leads_result = await db.execute(
        select(func.count(Lead.id)).where(
            Lead.tenant_id == tenant_id,
            Lead.utm_campaign == slug,
        )
    )
    total_leads = leads_result.scalar() or 0

    return total_views, total_leads


async def accept_company_invite(
    db: AsyncSession,
    tenant_id: Any,
    token: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    payload = decode_invite_token(token)
    if str(tenant_id) != payload.get("tenant_id"):
        raise AppError(ErrorCode.INVALID_TOKEN)

    try:
        user_id = uuid.UUID(payload.get("sub", ""))
        company_id = uuid.UUID(payload.get("company_id", ""))
    except ValueError:
        raise AppError(ErrorCode.INVALID_TOKEN)
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise AppError(ErrorCode.USER_NOT_FOUND)

    company_result = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    if not company_result.scalar_one_or_none():
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)

    member_result = await db.execute(
        select(CompanyMember).where(
            CompanyMember.company_id == company_id,
            CompanyMember.user_id == user.id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        db.add(CompanyMember(company_id=company_id, user_id=user.id))

    if body.get("name"):
        user.name = body["name"]
    if body.get("password"):
        user.password_hash = hash_password(body["password"])
    user.company_id = company_id

    await db.commit()
    access_token = create_access_token(
        str(user.id),
        str(tenant_id),
        user.role,
        company_id=str(company_id),
    )
    refresh_token = await create_refresh_token(str(user.id))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": str(user.id),
        "company_id": str(company_id),
    }
