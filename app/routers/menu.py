from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.menu import MenuConfig
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/menu", tags=["menu"])

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


@router.get("")
async def get_menu(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MenuConfig).where(
            MenuConfig.tenant_id == tenant.id,
            MenuConfig.role == user.role,
        )
    )
    config = result.scalar_one_or_none()

    if config and config.items:
        return {"items": config.items}

    # Return defaults
    defaults = {
        "student": _DEFAULT_STUDENT_MENU,
        "manager": _DEFAULT_MANAGER_MENU,
        "admin": _DEFAULT_ADMIN_MENU,
        "super_admin": _DEFAULT_ADMIN_MENU,
    }
    return {"items": defaults.get(user.role, _DEFAULT_STUDENT_MENU)}
