"""Enrollment business logic."""
import logging
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.enrollment import Enrollment
from app.models.product import Product
from app.models.user import User

logger = logging.getLogger(__name__)


def _frontend_url(path: str) -> str:
    from app.core.config import get_settings

    base_url = get_settings().frontend_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{base_url}{normalized_path}" if base_url else normalized_path


def _template_for_status(status: str) -> str | None:
    return {
        "active": "enrollment.access_granted",
        "reactivated": "enrollment.access_reactivated",
        "suspended": "enrollment.access_suspended",
        "cancelled": "enrollment.access_cancelled",
        "refunded": "enrollment.access_refunded",
    }.get(status)


def _queue_enrollment_email(user: User, product: Product, status: str) -> None:
    template_key = _template_for_status(status)
    if template_key is None:
        return

    try:
        from app.tasks.email import send_system_email_task

        send_system_email_task.delay(
            user.email,
            template_key,
            {
                "user_name": user.name,
                "product_title": product.title,
                "product_url": _frontend_url("/courses"),
            },
        )
    except Exception:
        logger.exception(
            "Failed to queue enrollment email to=%s template=%s",
            user.email,
            template_key,
        )


async def list_enrollments(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    status: str | None,
    user_id: uuid.UUID | None,
    product_id: uuid.UUID | None,
    limit: int,
    offset: int,
):
    query = select(Enrollment).where(Enrollment.tenant_id == tenant_id)
    if status:
        query = query.where(Enrollment.status == status)
    if user_id:
        query = query.where(Enrollment.user_id == user_id)
    if product_id:
        query = query.where(Enrollment.product_id == product_id)

    result = await db.execute(query.limit(limit).offset(offset))
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(e.id),
                "user_id": str(e.user_id),
                "product_id": str(e.product_id),
                "status": e.status,
                "enrolled_by": e.enrolled_by,
                "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            }
            for e in rows
        ]
    }


async def create_enrollment(db: AsyncSession, tenant_id: uuid.UUID, body: dict[str, Any]):
    user_id = body.get("user_id")
    product_id = body.get("product_id")
    if not user_id or not product_id:
        raise AppError(ErrorCode.MISSING_REQUIRED_FIELDS)

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(str(user_id)), User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise AppError(ErrorCode.USER_NOT_FOUND)

    result = await db.execute(
        select(Product).where(Product.id == uuid.UUID(str(product_id)), Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise AppError(ErrorCode.PRODUCT_NOT_FOUND)

    status = body.get("status", "active")
    enrollment = Enrollment(
        tenant_id=tenant_id,
        user_id=uuid.UUID(str(user_id)),
        product_id=uuid.UUID(str(product_id)),
        status=status,
        enrolled_by="admin",
        expires_at=body.get("expires_at"),
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    _queue_enrollment_email(user, product, status)
    return {"id": str(enrollment.id)}


async def update_enrollment(db: AsyncSession, tenant_id: uuid.UUID, enrollment_id: uuid.UUID, body: dict[str, Any]):
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.id == enrollment_id,
            Enrollment.tenant_id == tenant_id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise AppError(ErrorCode.ENROLLMENT_NOT_FOUND)

    old_status = enrollment.status
    if "status" in body:
        enrollment.status = body["status"]
    if "expires_at" in body:
        enrollment.expires_at = body["expires_at"]
    await db.commit()
    await db.refresh(enrollment)
    if "status" in body and body["status"] != old_status:
        user = await db.get(User, enrollment.user_id)
        product = await db.get(Product, enrollment.product_id)
        if user and product:
            template_status = (
                "reactivated"
                if body["status"] == "active" and old_status != "active"
                else body["status"]
            )
            _queue_enrollment_email(user, product, template_status)
    return {"id": str(enrollment.id), "status": enrollment.status}


async def delete_enrollment(db: AsyncSession, tenant_id: uuid.UUID, enrollment_id: uuid.UUID):
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.id == enrollment_id,
            Enrollment.tenant_id == tenant_id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise AppError(ErrorCode.ENROLLMENT_NOT_FOUND)
    await db.delete(enrollment)
    await db.commit()


async def bulk_enrollments(db: AsyncSession, tenant_id: uuid.UUID, body: dict[str, Any]):
    action = body.get("action")
    user_ids = body.get("user_ids", [])
    product_id = body.get("product_id")

    if not action or not user_ids or not product_id:
        raise AppError(ErrorCode.MISSING_REQUIRED_FIELDS)

    if len(user_ids) > 50:
        raise AppError(ErrorCode.BULK_LIMIT_EXCEEDED)

    if action == "enroll":
        product = await db.get(Product, uuid.UUID(str(product_id)))
        if product is None or product.tenant_id != tenant_id:
            raise AppError(ErrorCode.PRODUCT_NOT_FOUND)

        users_by_id = {}
        users_result = await db.execute(
            select(User).where(
                User.tenant_id == tenant_id,
                User.id.in_([uuid.UUID(str(uid)) for uid in user_ids]),
            )
        )
        for user in users_result.scalars().all():
            users_by_id[user.id] = user

        created = 0
        for uid in user_ids:
            parsed_user_id = uuid.UUID(str(uid))
            enrollment = Enrollment(
                tenant_id=tenant_id,
                user_id=parsed_user_id,
                product_id=uuid.UUID(str(product_id)),
                status="active",
                enrolled_by="admin",
            )
            db.add(enrollment)
            created += 1
        await db.commit()
        for user in users_by_id.values():
            _queue_enrollment_email(user, product, "active")
        return {"created": created}

    if action in ("suspend", "cancel"):
        parsed_user_ids = [uuid.UUID(str(u)) for u in user_ids]
        stmt = (
            update(Enrollment)
            .where(Enrollment.tenant_id == tenant_id)
            .where(Enrollment.user_id.in_(parsed_user_ids))
            .where(Enrollment.product_id == uuid.UUID(str(product_id)))
            .values(status=action)
        )
        await db.execute(stmt)
        await db.commit()
        return {"updated": len(parsed_user_ids)}

    raise AppError(ErrorCode.UNKNOWN_ACTION)
