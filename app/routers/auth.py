from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.rate_limit import forgot_password_limit, login_limit, magic_link_limit
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserMeResponse,
    UserUpdateRequest,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])

_REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=30 * 24 * 3600,
        path="/auth/refresh",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.register_user(
        db, tenant.id, body.email, body.name, body.password
    )
    return {"id": str(user.id), "email": user.email, "name": user.name}


@router.post("/login", response_model=TokenResponse)
@login_limit
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await auth_service.login_user(db, tenant.id, body.email, body.password)
    _set_refresh_cookie(response, result["refresh_token"])
    from app.core.config import get_settings
    settings = get_settings()
    return TokenResponse(
        access_token=result["access_token"],
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str = Cookie(None, alias=_REFRESH_COOKIE),
    body: RefreshRequest | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    token = refresh_token or (body.refresh_token if body else None)
    if not token:
        raise AppError(ErrorCode.REFRESH_TOKEN_INVALID)

    result = await auth_service.refresh_access_token(db, tenant.id, token)
    _set_refresh_cookie(response, result["refresh_token"])
    from app.core.config import get_settings
    settings = get_settings()
    return TokenResponse(
        access_token=result["access_token"],
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str = Cookie(None, alias=_REFRESH_COOKIE),
    body: RefreshRequest | None = None,
):
    token = refresh_token or (body.refresh_token if body else None)
    if token:
        await auth_service.logout_user(token)
    response.delete_cookie(_REFRESH_COOKIE, path="/auth/refresh")


@router.post("/magic-link", status_code=status.HTTP_204_NO_CONTENT)
@magic_link_limit
async def magic_link(
    request: Request,
    body: MagicLinkRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.send_magic_link(db, tenant.id, body.email)


@router.post("/magic-link/verify", response_model=TokenResponse)
async def magic_link_verify(
    response: Response,
    body: MagicLinkVerifyRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await auth_service.verify_magic_link(db, tenant.id, body.token)
    _set_refresh_cookie(response, result["refresh_token"])
    from app.core.config import get_settings
    settings = get_settings()
    return TokenResponse(
        access_token=result["access_token"],
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
@forgot_password_limit
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.send_password_reset(db, tenant.id, body.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    body: ResetPasswordRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.reset_password(db, tenant.id, body.token, body.new_password)


@users_router.get("/me", response_model=UserMeResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@users_router.patch("/me", response_model=UserMeResponse)
async def update_me(
    body: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await auth_service.update_user(
        db, user, name=body.name, avatar_url=body.avatar_url, bio=body.bio
    )
    return updated


@users_router.get("/me/enrollments")
async def get_my_enrollments(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await auth_service.get_user_enrollments(db, user.id)
    return {"items": items}
