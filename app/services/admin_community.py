"""Admin community service."""
import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.redis_client import get_redis
from app.models.community import Channel, Comment, Post, Report, Space
from app.models.user import User


async def list_reports(db: AsyncSession, tenant_id: uuid.UUID, status: str) -> list[Report]:
    result = await db.execute(
        select(Report)
        .where(Report.tenant_id == tenant_id, Report.status == status)
        .order_by(Report.created_at.desc())
    )
    return list(result.scalars().all())


async def resolve_report(db: AsyncSession, tenant_id: uuid.UUID, report_id: uuid.UUID, status: str) -> Report:
    report = await db.get(Report, report_id)
    if report is None or report.tenant_id != tenant_id:
        raise AppError(ErrorCode.REPORT_NOT_FOUND)
    report.status = status
    report.resolved_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    return report


async def suspend_user(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    user = await db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        raise AppError(ErrorCode.USER_NOT_FOUND)
    user.is_suspended = True
    await db.commit()

    redis = get_redis()
    if redis:
        await redis.publish(f"user:suspend:{tenant_id}", str(user_id))


async def create_space(db: AsyncSession, tenant_id: uuid.UUID, name: str, description: str | None) -> Space:
    space = Space(tenant_id=tenant_id, name=name, description=description)
    db.add(space)
    await db.commit()
    await db.refresh(space)
    return space


async def create_channel(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    space_id: uuid.UUID,
    name: str,
    channel_type: str,
    post_policy: str,
) -> Channel:
    space = await db.get(Space, space_id)
    if space is None or space.tenant_id != tenant_id:
        raise AppError(ErrorCode.SPACE_NOT_FOUND)
    channel = Channel(
        space_id=space_id,
        tenant_id=tenant_id,
        name=name,
        channel_type=channel_type,
        post_policy=post_policy,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


async def hide_post(db: AsyncSession, tenant_id: uuid.UUID, post_id: uuid.UUID) -> None:
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    post.is_hidden = True
    await db.commit()


async def hide_comment(db: AsyncSession, tenant_id: uuid.UUID, comment_id: uuid.UUID) -> None:
    comment = await db.get(Comment, comment_id)
    if comment is None or comment.tenant_id != tenant_id:
        raise AppError(ErrorCode.COMMENT_NOT_FOUND)
    comment.is_hidden = True
    await db.commit()
