import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from typing import Any, Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.errors import AppError, build_error_response
from app.core.middleware import TenantMiddleware
from app.core.rate_limit import limiter
from app.core.redis_client import close_redis, init_redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db(settings.database_url)
    await init_redis(settings.redis_url)
    yield
    await close_db()
    await close_redis()


app = FastAPI(
    title="LMS API",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# CORS — origins come from settings (not wildcard in prod)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantMiddleware)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_errors(errors: Sequence[Any]) -> list:
    """Pydantic v2 error ctx may contain non-JSON-serializable exception objects."""
    result = []
    for err in errors:
        e = dict(err)
        if "ctx" in e:
            e["ctx"] = {k: str(v) for k, v in e["ctx"].items()}
        result.append(e)
    return result


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return build_error_response(
        error_def=exc.error_def,
        request=request,
        details=exc.details,
        override_message=exc.override_message,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": 422,
            "detail": _sanitize_errors(exc.errors()),
            "instance": request.url.path,
            "timestamp": _now_iso(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error at %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "status": 500,
            "detail": "An unexpected error occurred",
            "instance": request.url.path,
            "timestamp": _now_iso(),
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


from app.routers import auth as _auth_module  # noqa: E402
from app.routers.admin import tenant as _admin_tenant_module  # noqa: E402
from app.routers.admin import courses as _admin_courses_module  # noqa: E402
from app.routers.admin import webhooks as _admin_webhooks_module  # noqa: E402
from app.routers.admin import companies as _admin_companies_module  # noqa: E402
from app.routers.admin import email as _admin_email_module  # noqa: E402
from app.routers.admin import enrollments as _admin_enrollments_module  # noqa: E402
from app.routers.admin import dashboard as _admin_dashboard_module  # noqa: E402
from app.routers.admin import menu as _admin_menu_module  # noqa: E402
from app.routers.manager import dashboard as _manager_module  # noqa: E402
from app.routers import courses as _courses_module  # noqa: E402
from app.routers import quiz as _quiz_module  # noqa: E402
from app.routers import notes as _notes_module  # noqa: E402
from app.routers import menu as _menu_module  # noqa: E402
from app.routers import webhooks as _webhooks_module  # noqa: E402
from app.routers import gamification as _gamification_module  # noqa: E402
from app.routers import community as _community_module  # noqa: E402
from app.routers import internal as _internal_module  # noqa: E402
from app.routers.admin import community as _admin_community_module  # noqa: E402
from app.routers.admin import landing_pages as _admin_landing_module  # noqa: E402
from app.routers.admin import audit as _admin_audit_module  # noqa: E402
from app.routers.admin import gamification as _admin_gamification_module  # noqa: E402
from app.routers import catalog as _catalog_module  # noqa: E402
from app.routers import public as _public_module  # noqa: E402
from app.routers import superadmin as _superadmin_module  # noqa: E402
from app.websockets import presence as _presence_module  # noqa: E402
from app.routers import messages as _messages_module  # noqa: E402
from app.routers import uploads as _uploads_module  # noqa: E402
from app.routers import notifications as _notifications_module  # noqa: E402
from app.websockets import messages as _ws_messages_module  # noqa: E402
from app.websockets import notifications as _notifications_ws_module  # noqa: E402
app.include_router(_auth_module.router)
app.include_router(_auth_module.users_router)
app.include_router(_admin_tenant_module.router)
app.include_router(_admin_courses_module.router)
app.include_router(_admin_webhooks_module.router)
app.include_router(_admin_companies_module.router)
app.include_router(_admin_enrollments_module.router)
app.include_router(_admin_dashboard_module.router)
app.include_router(_admin_menu_module.router)
app.include_router(_admin_email_module.router)
app.include_router(_manager_module.router)
app.include_router(_courses_module.router)
app.include_router(_quiz_module.router)
app.include_router(_notes_module.router)
app.include_router(_menu_module.router)
app.include_router(_webhooks_module.router)
app.include_router(_gamification_module.router)
app.include_router(_community_module.router)
app.include_router(_admin_community_module.router)
app.include_router(_admin_landing_module.router)
app.include_router(_admin_audit_module.router)
app.include_router(_admin_gamification_module.router)
app.include_router(_catalog_module.router)
app.include_router(_public_module.router)
app.include_router(_superadmin_module.router)
app.include_router(_presence_module.router)
app.include_router(_presence_module.admin_router)
app.include_router(_messages_module.router)
app.include_router(_notifications_module.router)
app.include_router(_ws_messages_module.router)
app.include_router(_notifications_ws_module.router)
app.include_router(_uploads_module.router)
app.include_router(_internal_module.router)
