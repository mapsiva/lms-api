from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.menu import MenuConfig
from app.models.tenant import Tenant
from app.models.user import User
from app.routers.menu import _DEFAULT_ADMIN_MENU, _DEFAULT_MANAGER_MENU, _DEFAULT_STUDENT_MENU
from app.schemas.menu import MenuResponse, MenuUpdate
from app.services import menu as menu_service

router = APIRouter(prefix="/admin/menu", tags=["admin:menu"])

_ROLE_DEFAULTS: dict[str, list] = {
    "student": _DEFAULT_STUDENT_MENU,
    "manager": _DEFAULT_MANAGER_MENU,
    "admin": _DEFAULT_ADMIN_MENU,
    "super_admin": _DEFAULT_ADMIN_MENU,
}


@router.get("", response_model=MenuResponse)
async def get_admin_menu(
    role: str,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MenuConfig).where(MenuConfig.tenant_id == tenant.id, MenuConfig.role == role)
    )
    config = result.scalar_one_or_none()
    if config:
        return {"role": config.role, "items": config.items}
    return {"role": role, "items": _ROLE_DEFAULTS.get(role, _DEFAULT_STUDENT_MENU)}


@router.put("", response_model=MenuResponse)
async def update_menu(
    role: str,
    body: MenuUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    config = await menu_service.update_menu_config(db, tenant.id, role, body.items)
    return {"role": config.role, "items": config.items}
