"""Enrollment business logic."""
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.enrollment import Enrollment
from app.models.product import Product
from app.models.user import User


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
    if not result.scalar_one_or_none():
        raise AppError(ErrorCode.USER_NOT_FOUND)

    result = await db.execute(
        select(Product).where(Product.id == uuid.UUID(str(product_id)), Product.tenant_id == tenant_id)
    )
    if not result.scalar_one_or_none():
        raise AppError(ErrorCode.PRODUCT_NOT_FOUND)

    enrollment = Enrollment(
        tenant_id=tenant_id,
        user_id=uuid.UUID(str(user_id)),
        product_id=uuid.UUID(str(product_id)),
        status=body.get("status", "active"),
        enrolled_by="admin",
        expires_at=body.get("expires_at"),
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
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

    if "status" in body:
        enrollment.status = body["status"]
    if "expires_at" in body:
        enrollment.expires_at = body["expires_at"]
    await db.commit()
    await db.refresh(enrollment)
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
        created = 0
        for uid in user_ids:
            enrollment = Enrollment(
                tenant_id=tenant_id,
                user_id=uuid.UUID(str(uid)),
                product_id=uuid.UUID(str(product_id)),
                status="active",
                enrolled_by="admin",
            )
            db.add(enrollment)
            created += 1
        await db.commit()
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
