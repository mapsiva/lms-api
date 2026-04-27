import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_magic_link_token,
    create_refresh_token,
    get_user_id_from_refresh_token,
    hash_password,
    revoke_refresh_token,
    verify_magic_link_token,
    verify_password,
)
from app.models.enrollment import Enrollment
from app.models.product import Product
from app.models.user import User


async def register_user(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    email: str,
    name: str,
    password: str,
    role: str = "student",
    company_id: Optional[uuid.UUID] = None,
) -> User:
    existing = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == email)
    )
    if existing.scalar_one_or_none():
        raise AppError(ErrorCode.USER_ALREADY_EXISTS)

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=email,
        name=name,
        password_hash=hash_password(password),
        role=role,
        company_id=company_id,
        is_active=True,
        is_suspended=False,
    )
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise AppError(ErrorCode.USER_ALREADY_EXISTS)
    return user


async def login_user(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    email: str,
    password: str,
) -> dict:
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == email, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise AppError(ErrorCode.INVALID_CREDENTIALS)

    if user.is_suspended:
        raise AppError(ErrorCode.ACCOUNT_SUSPENDED)

    access_token = create_access_token(
        str(user.id), str(tenant_id), user.role,
        company_id=str(user.company_id) if user.company_id else None,
    )
    refresh_token = await create_refresh_token(str(user.id))
    return {"user": user, "access_token": access_token, "refresh_token": refresh_token}


async def logout_user(refresh_token: str) -> None:
    await revoke_refresh_token(refresh_token)


async def refresh_access_token(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    refresh_token: str,
) -> dict:
    user_id_str = await get_user_id_from_refresh_token(refresh_token)
    if not user_id_str:
        raise AppError(ErrorCode.REFRESH_TOKEN_INVALID)

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AppError(ErrorCode.REFRESH_TOKEN_INVALID)

    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user or user.is_suspended:
        raise AppError(ErrorCode.USER_NOT_FOUND)

    # Rotate: revoke old, issue new
    await revoke_refresh_token(refresh_token)
    new_refresh_token = await create_refresh_token(str(user.id))
    access_token = create_access_token(
        str(user.id), str(tenant_id), user.role,
        company_id=str(user.company_id) if user.company_id else None,
    )
    return {"access_token": access_token, "refresh_token": new_refresh_token}


async def send_magic_link(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    email: str,
) -> str:
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == email)
    )
    user = result.scalar_one_or_none()
    # Don't reveal whether user exists — always return success
    if not user:
        return ""

    token = await create_magic_link_token(email)

    # Dispatch email task (imported here to avoid circular; tasks registered later)
    try:
        from app.tasks.email import send_magic_link_email
        send_magic_link_email.delay(email=email, token=token, tenant_id=str(tenant_id))
    except ImportError:
        pass  # Email tasks not yet configured — token stored in Redis, test can verify directly

    return token


async def verify_magic_link(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    token: str,
) -> dict:
    email = await verify_magic_link_token(token)

    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == email, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise AppError(ErrorCode.USER_NOT_FOUND)

    access_token = create_access_token(
        str(user.id), str(tenant_id), user.role,
        company_id=str(user.company_id) if user.company_id else None,
    )
    refresh_token = await create_refresh_token(str(user.id))
    return {"user": user, "access_token": access_token, "refresh_token": refresh_token}


async def send_password_reset(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    email: str,
) -> str:
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == email)
    )
    user = result.scalar_one_or_none()
    if not user:
        return ""  # Don't reveal non-existence

    token = await create_magic_link_token(email)  # Reuse same Redis TTL mechanism

    try:
        from app.tasks.email import send_password_reset_email
        send_password_reset_email.delay(email=email, token=token, tenant_id=str(tenant_id))
    except ImportError:
        pass

    return token


async def reset_password(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    token: str,
    new_password: str,
) -> None:
    email = await verify_magic_link_token(token)

    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == email)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise AppError(ErrorCode.USER_NOT_FOUND)

    user.password_hash = hash_password(new_password)
    await db.commit()


async def update_user(
    db: AsyncSession,
    user: User,
    name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    bio: Optional[str] = None,
) -> User:
    if name is not None:
        user.name = name
    if avatar_url is not None:
        user.avatar_url = avatar_url
    if bio is not None:
        user.bio = bio
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_enrollments(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[dict]:
    result = await db.execute(
        select(Enrollment, Product)
        .join(Product, Enrollment.product_id == Product.id)
        .where(Enrollment.user_id == user_id)
        .where(Enrollment.status == "active")
    )
    rows = result.all()
    return [
        {
            "id": str(e.id),
            "product_id": str(p.id),
            "product_title": p.title,
            "product_type": p.type,
            "status": e.status,
            "expires_at": e.expires_at.isoformat() if e.expires_at else None,
        }
        for e, p in rows
    ]
