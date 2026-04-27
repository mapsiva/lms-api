"""Community admin router."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.community import Channel, Comment, Post, Report, Space
from app.models.user import User

router = APIRouter(prefix="/admin/community", tags=["admin:community"])


@router.get("/reports")
async def list_reports(
    status: str = "pending",
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report)
        .where(Report.tenant_id == tenant.id, Report.status == status)
        .order_by(Report.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/reports/{report_id}")
async def resolve_report(
    report_id: uuid.UUID,
    status: str,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(Report, report_id)
    if report is None or report.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = status
    import datetime
    report.resolved_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    return report


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None or user.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_suspended = True
    await db.commit()

    # Notify WebSocket layer via Redis
    from app.core.redis_client import get_redis
    redis = get_redis()
    if redis:
        await redis.publish(f"user:suspend:{tenant.id}", str(user_id))

    return {"suspended": True}


@router.post("/spaces", status_code=201)
async def create_space(
    name: str,
    description: str | None = None,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    space = Space(tenant_id=tenant.id, name=name, description=description)
    db.add(space)
    await db.commit()
    await db.refresh(space)
    return space


@router.post("/spaces/{space_id}/channels", status_code=201)
async def create_channel(
    space_id: uuid.UUID,
    name: str,
    channel_type: str = "discussion",
    post_policy: str = "open",
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    space = await db.get(Space, space_id)
    if space is None or space.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Space not found")
    channel = Channel(
        space_id=space_id,
        tenant_id=tenant.id,
        name=name,
        channel_type=channel_type,
        post_policy=post_policy,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.patch("/posts/{post_id}/hide")
async def hide_post(
    post_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Post not found")
    post.is_hidden = True
    await db.commit()
    return {"hidden": True}


@router.patch("/comments/{comment_id}/hide")
async def hide_comment(
    comment_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    comment = await db.get(Comment, comment_id)
    if comment is None or comment.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.is_hidden = True
    await db.commit()
    return {"hidden": True}
