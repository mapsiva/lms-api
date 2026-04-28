"""Admin audit log router."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.audit import AuditLog
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/admin/audit-log", tags=["admin:audit"])


@router.get("")
async def list_audit_logs(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    action: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    resource_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(AuditLog).where(AuditLog.tenant_id == tenant.id)
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    query = query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "user_id": str(r.user_id),
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "details": r.details,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }
