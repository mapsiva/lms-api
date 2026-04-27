import json
import uuid
from types import SimpleNamespace
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.redis_client import get_redis
from app.core.security import decode_token
from app.models.tenant import Tenant
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)

_TENANT_CACHE_TTL = 300  # 5 min


async def get_current_tenant(request: Request, db: AsyncSession = Depends(get_db)) -> Tenant:
    # First check if middleware already resolved the tenant
    if hasattr(request.state, "tenant"):
        return request.state.tenant

    host = request.headers.get("host", "").split(":")[0]
    redis = get_redis()

    cache_key = f"tenant:host:{host}"
    if redis:
        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            data["id"] = uuid.UUID(data["id"])
            return SimpleNamespace(**data)  # type: ignore[return-value]

    result = await db.execute(
        select(Tenant).where(
            (Tenant.custom_domain == host) | (Tenant.subdomain == host)
        )
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise AppError(ErrorCode.TENANT_NOT_FOUND)

    if redis:
        payload = {
            "id": str(tenant.id),
            "slug": tenant.slug,
            "name": tenant.name,
            "custom_domain": tenant.custom_domain,
            "subdomain": tenant.subdomain,
            "plan": tenant.plan,
            "features": tenant.features,
        }
        await redis.setex(cache_key, _TENANT_CACHE_TTL, json.dumps(payload))

    return tenant


async def get_current_user(
    tenant: Tenant = Depends(get_current_tenant),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise AppError(ErrorCode.NOT_AUTHENTICATED)

    payload = decode_token(credentials.credentials)
    user_id_str = payload.get("sub")
    token_tenant_id = payload.get("tenant_id")

    if not user_id_str or str(tenant.id) != token_tenant_id:
        raise AppError(ErrorCode.INVALID_TOKEN)

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AppError(ErrorCode.INVALID_TOKEN)

    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise AppError(ErrorCode.USER_NOT_FOUND)

    if user.is_suspended:
        raise AppError(ErrorCode.ACCOUNT_SUSPENDED)

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "super_admin"):
        raise AppError(ErrorCode.ADMIN_REQUIRED)
    return user


async def require_company_access(
    company_id: uuid.UUID,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    from app.models.company import Company  # imported here to avoid circular at module level

    if user.role == "manager":
        if not user.company_id:
            raise AppError(ErrorCode.NO_COMPANY_CONTEXT)
        effective_company_id = user.company_id
    else:
        effective_company_id = company_id

    result = await db.execute(
        select(Company).where(
            Company.id == effective_company_id,
            Company.tenant_id == tenant.id,
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)

    return effective_company_id
