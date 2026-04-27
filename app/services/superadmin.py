"""Superadmin business logic."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.menu import MenuConfig
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantUpdate

_DEFAULT_STUDENT_MENU = [
    {"id": "courses", "label": "Cursos", "icon": "book", "url": "/courses", "order": 1, "group": "principal", "visible": True},
    {"id": "community", "label": "Comunidade", "icon": "message-circle", "url": "/community", "order": 2, "group": "principal", "visible": True},
    {"id": "profile", "label": "Perfil", "icon": "user", "url": "/profile", "order": 3, "group": "principal", "visible": True},
]

_DEFAULT_MANAGER_MENU = _DEFAULT_STUDENT_MENU + [
    {"id": "dashboard", "label": "Dashboard", "icon": "bar-chart", "url": "/manager", "order": 0, "group": "principal", "visible": True},
]

_DEFAULT_ADMIN_MENU = _DEFAULT_MANAGER_MENU + [
    {"id": "admin", "label": "Admin", "icon": "settings", "url": "/admin", "order": 10, "group": "admin", "visible": True},
]


async def list_tenants(db: AsyncSession, page: int, per_page: int):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Tenant).order_by(Tenant.created_at.desc()).offset(offset).limit(per_page)
    )
    tenants = result.scalars().all()

    count_result = await db.execute(select(func.count(Tenant.id)))
    total = count_result.scalar() or 0

    return {
        "items": [
            {
                "id": str(t.id),
                "slug": t.slug,
                "name": t.name,
                "custom_domain": t.custom_domain,
                "subdomain": t.subdomain,
                "plan": t.plan,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tenants
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


async def create_tenant(db: AsyncSession, body: TenantCreate):
    from uuid import uuid4

    tenant = Tenant(
        id=uuid4(),
        slug=body.slug,
        name=body.name,
        custom_domain=body.custom_domain,
        subdomain=body.subdomain,
        plan=body.plan,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    for role, items in [
        ("student", _DEFAULT_STUDENT_MENU),
        ("manager", _DEFAULT_MANAGER_MENU),
        ("admin", _DEFAULT_ADMIN_MENU),
    ]:
        db.add(MenuConfig(tenant_id=tenant.id, role=role, items=items))
    await db.commit()

    return {
        "id": str(tenant.id),
        "slug": tenant.slug,
        "name": tenant.name,
        "custom_domain": tenant.custom_domain,
        "subdomain": tenant.subdomain,
        "plan": tenant.plan,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
    }


async def update_tenant(db: AsyncSession, tenant_id: UUID, body: TenantUpdate):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise AppError(ErrorCode.TENANT_NOT_FOUND)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)

    return {
        "id": str(tenant.id),
        "slug": tenant.slug,
        "name": tenant.name,
        "custom_domain": tenant.custom_domain,
        "subdomain": tenant.subdomain,
        "plan": tenant.plan,
        "logo_url": tenant.logo_url,
        "favicon_url": tenant.favicon_url,
        "primary_color": tenant.primary_color,
        "secondary_color": tenant.secondary_color,
        "font_family": tenant.font_family,
        "app_name": tenant.app_name,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
    }


async def get_tenant_stats(db: AsyncSession, tenant_id: UUID):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise AppError(ErrorCode.TENANT_NOT_FOUND)

    users_result = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id)
    )
    total_users = users_result.scalar() or 0

    enrollments_result = await db.execute(
        select(func.count(Enrollment.id)).where(
            Enrollment.tenant_id == tenant_id,
            Enrollment.status == "active",
        )
    )
    active_enrollments = enrollments_result.scalar() or 0

    courses_result = await db.execute(
        select(func.count(Course.id)).where(Course.tenant_id == tenant_id)
    )
    total_courses = courses_result.scalar() or 0

    return {
        "total_users": total_users,
        "active_enrollments": active_enrollments,
        "total_courses": total_courses,
    }
