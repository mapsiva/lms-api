from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.menu import MenuConfig
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/admin/menu", tags=["admin:menu"])


@router.get("")
async def get_admin_menu(
    role: str,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MenuConfig).where(
            MenuConfig.tenant_id == tenant.id,
            MenuConfig.role == role,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Menu config not found")
    return {"role": config.role, "items": config.items}


@router.put("")
async def update_menu(
    role: str,
    body: dict,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    items = body.get("items", [])
    result = await db.execute(
        select(MenuConfig).where(
            MenuConfig.tenant_id == tenant.id,
            MenuConfig.role == role,
        )
    )
    config = result.scalar_one_or_none()
    if config:
        config.items = items
    else:
        config = MenuConfig(tenant_id=tenant.id, role=role, items=items)
        db.add(config)
    await db.commit()
    await db.refresh(config)
    return {"role": config.role, "items": config.items}
