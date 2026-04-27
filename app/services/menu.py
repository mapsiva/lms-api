"""Menu service."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.menu import MenuConfig


async def get_menu_config(db: AsyncSession, tenant_id: uuid.UUID, role: str) -> MenuConfig:
    result = await db.execute(
        select(MenuConfig).where(
            MenuConfig.tenant_id == tenant_id,
            MenuConfig.role == role,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise AppError(ErrorCode.MENU_CONFIG_NOT_FOUND)
    return config


async def update_menu_config(db: AsyncSession, tenant_id: uuid.UUID, role: str, items: list[dict]) -> MenuConfig:
    result = await db.execute(
        select(MenuConfig).where(
            MenuConfig.tenant_id == tenant_id,
            MenuConfig.role == role,
        )
    )
    config = result.scalar_one_or_none()
    if config:
        config.items = items
    else:
        config = MenuConfig(tenant_id=tenant_id, role=role, items=items)
        db.add(config)
    await db.commit()
    await db.refresh(config)
    return config
