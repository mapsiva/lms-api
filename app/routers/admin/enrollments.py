import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.enrollment import Enrollment
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/admin/enrollments", tags=["admin:enrollments"])


@router.get("")
async def list_enrollments(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    product_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(Enrollment).where(Enrollment.tenant_id == tenant.id)
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


@router.post("", status_code=201)
async def create_enrollment(
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user_id = body.get("user_id")
    product_id = body.get("product_id")
    if not user_id or not product_id:
        raise HTTPException(status_code=400, detail="user_id and product_id required")

    # Verify user belongs to tenant
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(str(user_id)), User.tenant_id == tenant.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    # Verify product belongs to tenant
    result = await db.execute(
        select(Product).where(Product.id == uuid.UUID(str(product_id)), Product.tenant_id == tenant.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    enrollment = Enrollment(
        tenant_id=tenant.id,
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


@router.patch("/{enrollment_id}")
async def update_enrollment(
    enrollment_id: uuid.UUID,
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.id == enrollment_id,
            Enrollment.tenant_id == tenant.id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if "status" in body:
        enrollment.status = body["status"]
    if "expires_at" in body:
        enrollment.expires_at = body["expires_at"]
    await db.commit()
    await db.refresh(enrollment)
    return {"id": str(enrollment.id), "status": enrollment.status}


@router.delete("/{enrollment_id}", status_code=204)
async def delete_enrollment(
    enrollment_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.id == enrollment_id,
            Enrollment.tenant_id == tenant.id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    await db.delete(enrollment)
    await db.commit()
    return


@router.post("/bulk")
async def bulk_enrollments(
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    action = body.get("action")
    user_ids = body.get("user_ids", [])
    product_id = body.get("product_id")

    if not action or not user_ids or not product_id:
        raise HTTPException(status_code=400, detail="action, user_ids, product_id required")

    if len(user_ids) > 50:
        # Dispatch Celery task for large batches
        # Placeholder: actual bulk task would be separate; for now process inline with limit
        raise HTTPException(status_code=400, detail="Max 50 users per bulk request")

    if action == "enroll":
        created = 0
        for uid in user_ids:
            enrollment = Enrollment(
                tenant_id=tenant.id,
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
        from sqlalchemy import update
        parsed_user_ids = [uuid.UUID(str(u)) for u in user_ids]
        stmt = (
            update(Enrollment)
            .where(Enrollment.tenant_id == tenant.id)
            .where(Enrollment.user_id.in_(parsed_user_ids))
            .where(Enrollment.product_id == uuid.UUID(str(product_id)))
            .values(status=action)
        )
        await db.execute(stmt)
        await db.commit()
        return {"updated": len(parsed_user_ids)}

    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
