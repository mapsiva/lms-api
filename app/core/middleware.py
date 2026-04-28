import json
import uuid
from types import SimpleNamespace

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
import app.core.database as _db
from app.core.redis_client import get_redis
from app.models.tenant import Tenant

_TENANT_CACHE_TTL = 300


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        host = request.headers.get("host", "").split(":")[0]

        _BYPASS_PREFIXES = ("/health", "/superadmin", "/docs", "/redoc", "/openapi.json")
        if any(request.url.path == p or request.url.path.startswith(p) for p in _BYPASS_PREFIXES):
            return await call_next(request)

        tenant = await self._resolve_tenant(host)
        if tenant is None:
            return JSONResponse({"detail": "Tenant not found"}, status_code=404)

        request.state.tenant = tenant

        settings = get_settings()
        response = await call_next(request)
        if settings.webhook_test_mode:
            response.headers["X-Tenant-Slug"] = tenant.slug
        return response

    async def _resolve_tenant(self, host: str) -> Tenant | None:
        redis = get_redis()
        if redis:
            cache_key = f"tenant:host:{host}"
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                data["id"] = uuid.UUID(data["id"])
                return SimpleNamespace(**data)  # type: ignore[return-value]

        session_factory = _db.AsyncSessionLocal
        if session_factory is None:
            return None
        tenant: Tenant | None = None
        async with session_factory() as db:
            result = await db.execute(
                select(Tenant).where(
                    (Tenant.custom_domain == host) | (Tenant.subdomain == host)
                )
            )
            tenant = result.scalar_one_or_none()

        if tenant and redis:
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
