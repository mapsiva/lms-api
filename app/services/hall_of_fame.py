"""Hall of Fame service."""
import datetime
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.company import Company
from app.models.gamification import XPEvent
from app.models.user import User


async def compute_monthly_hall_of_fame(
    db: AsyncSession,
    company_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> list[dict]:
    company = await db.get(Company, company_id)
    if company is None or company.tenant_id != tenant_id:
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)

    now = datetime.datetime.now(datetime.timezone.utc)
    year, month = now.year, now.month

    # Aggregate XP events by user in current month
    stmt = (
        select(
            XPEvent.user_id,
            func.sum(XPEvent.amount).label("month_xp"),
        )
        .where(
            XPEvent.tenant_id == tenant_id,
            XPEvent.company_id == company_id,
            func.extract("year", XPEvent.created_at) == year,
            func.extract("month", XPEvent.created_at) == month,
        )
        .group_by(XPEvent.user_id)
        .order_by(func.sum(XPEvent.amount).desc())
        .limit(3)
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return []

    user_ids = [row.user_id for row in rows]
    names_result = await db.execute(
        select(User.id, User.name).where(User.id.in_(user_ids))
    )
    names = {uid: name for uid, name in names_result.all()}

    return [
        {
            "rank": i + 1,
            "user_id": str(row.user_id),
            "name": names.get(row.user_id, ""),
            "xp": row.month_xp or 0,
        }
        for i, row in enumerate(rows)
    ]
