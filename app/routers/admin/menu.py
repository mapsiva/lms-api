from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.menu import MenuResponse, MenuUpdate
from app.services import menu as menu_service

router = APIRouter(prefix="/admin/menu", tags=["admin:menu"])


@router.get("", response_model=MenuResponse)
async def get_admin_menu(
    role: str,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    config = await menu_service.get_menu_config(db, tenant.id, role)
    return {"role": config.role, "items": config.items}


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
