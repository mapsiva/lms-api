from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.community import Post
from app.models.company import Company
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/admin/dashboard", tags=["admin:dashboard"])
analytics_router = APIRouter(prefix="/admin/analytics", tags=["admin:analytics"])


@router.get("")
async def dashboard(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user_count = await db.scalar(
        select(func.count(User.id)).where(User.tenant_id == tenant.id)
    )
    active_enrollments = await db.scalar(
        select(func.count(Enrollment.id)).where(
            Enrollment.tenant_id == tenant.id,
            Enrollment.status == "active",
        )
    )
    course_count = await db.scalar(
        select(func.count(Course.id)).where(Course.tenant_id == tenant.id)
    )
    company_count = await db.scalar(
        select(func.count(Company.id)).where(Company.tenant_id == tenant.id)
    )

    return {
        "total_users": user_count or 0,
        "active_enrollments": active_enrollments or 0,
        "total_courses": course_count or 0,
        "total_companies": company_count or 0,
    }


@router.get("/analytics/engagement")
async def engagement_analytics(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.progress import LessonProgress

    total_completions = await db.scalar(
        select(func.count(LessonProgress.id)).where(
            LessonProgress.completed_at.isnot(None)
        )
    )
    return {"total_completions": total_completions or 0}


@router.get("/analytics/courses")
async def course_analytics(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Course.status, func.count(Course.id))
        .where(Course.tenant_id == tenant.id)
        .group_by(Course.status)
    )
    rows = result.all()
    return {"by_status": {status: count for status, count in rows}}


@router.get("/analytics/revenue")
async def revenue_analytics(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.product import Product

    result = await db.execute(
        select(func.sum(Product.price))
        .select_from(Enrollment)
        .join(Product, Enrollment.product_id == Product.id)
        .where(Enrollment.tenant_id == tenant.id)
        .where(Enrollment.status == "active")
    )
    total = result.scalar_one_or_none()
    return {"total_revenue": float(total) if total else 0.0}


@router.get("/analytics/community")
async def community_analytics(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_posts = await db.scalar(
        select(func.count(Post.id)).where(Post.tenant_id == tenant.id)
    )
    visible_posts = await db.scalar(
        select(func.count(Post.id)).where(
            Post.tenant_id == tenant.id,
            Post.is_hidden.is_(False),
        )
    )
    return {"total_posts": total_posts or 0, "visible_posts": visible_posts or 0}


@analytics_router.get("/engagement")
async def engagement_analytics_alias(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await engagement_analytics(tenant, _admin, db)


@analytics_router.get("/courses")
async def course_analytics_alias(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await course_analytics(tenant, _admin, db)


@analytics_router.get("/community")
async def community_analytics_alias(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await community_analytics(tenant, _admin, db)


@analytics_router.get("/revenue")
async def revenue_analytics_alias(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await revenue_analytics(tenant, _admin, db)
