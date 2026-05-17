"""Community business logic."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.community import Channel, Comment, Post, PostLike, Report, Space
from app.models.enrollment import Enrollment
from app.models.product import ProductSpace
from app.models.user import User


async def user_has_space_access(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user_role: str,
    space_id: uuid.UUID,
) -> bool:
    if user_role in ("admin", "super_admin"):
        return True
    count_result = await db.execute(
        select(func.count(ProductSpace.id)).where(ProductSpace.space_id == space_id)
    )
    if count_result.scalar() == 0:
        return True
    result = await db.execute(
        select(ProductSpace)
        .join(Enrollment, Enrollment.product_id == ProductSpace.product_id)
        .where(
            ProductSpace.space_id == space_id,
            Enrollment.user_id == user_id,
            Enrollment.tenant_id == tenant_id,
            Enrollment.status == "active",
        )
    )
    return result.scalar_one_or_none() is not None


async def _require_space_access(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user: User,
    space_id: uuid.UUID,
) -> None:
    if not await user_has_space_access(db, tenant_id, user.id, user.role, space_id):
        raise AppError(ErrorCode.SPACE_ACCESS_REQUIRED)


async def list_spaces(db: AsyncSession, tenant_id: uuid.UUID, user: User):
    result = await db.execute(
        select(Space)
        .where(Space.tenant_id == tenant_id, Space.is_active == True)  # noqa: E712
        .order_by(Space.created_at.desc())
    )
    spaces = result.scalars().all()
    items = []
    for space in spaces:
        has_access = await user_has_space_access(db, tenant_id, user.id, user.role, space.id)
        items.append({
            "id": space.id,
            "name": space.name,
            "description": space.description,
            "is_active": space.is_active,
            "has_access": has_access,
            "created_at": space.created_at,
        })
    return items


async def list_channels(db: AsyncSession, tenant_id: uuid.UUID, user: User, space_id: uuid.UUID):
    space = await db.get(Space, space_id)
    if space is None or space.tenant_id != tenant_id:
        raise AppError(ErrorCode.SPACE_NOT_FOUND)
    has_access = await user_has_space_access(db, tenant_id, user.id, user.role, space_id)
    result = await db.execute(
        select(Channel)
        .where(Channel.space_id == space_id, Channel.is_active == True)  # noqa: E712
        .order_by(Channel.created_at.desc())
    )
    channels = result.scalars().all()
    return [
        {
            "id": ch.id,
            "space_id": ch.space_id,
            "name": ch.name,
            "channel_type": ch.channel_type,
            "post_policy": ch.post_policy,
            "is_active": ch.is_active,
            "has_access": has_access,
            "created_at": ch.created_at,
        }
        for ch in channels
    ]


async def _get_channel_and_check_access(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user: User,
    channel_id: uuid.UUID,
) -> Channel:
    channel = await db.get(Channel, channel_id)
    if channel is None or channel.tenant_id != tenant_id:
        raise AppError(ErrorCode.CHANNEL_NOT_FOUND)
    await _require_space_access(db, tenant_id, user, channel.space_id)
    return channel


async def list_posts(db: AsyncSession, tenant_id: uuid.UUID, user: User, channel_id: uuid.UUID):
    await _get_channel_and_check_access(db, tenant_id, user, channel_id)
    result = await db.execute(
        select(Post)
        .where(Post.channel_id == channel_id, Post.is_hidden == False)  # noqa: E712
        .order_by(Post.is_pinned.desc(), Post.created_at.desc())
    )
    return result.scalars().all()


async def pin_post(db: AsyncSession, tenant_id: uuid.UUID, post_id: uuid.UUID) -> Post:
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    post.is_pinned = True
    await db.commit()
    await db.refresh(post)
    return post


async def unpin_post(db: AsyncSession, tenant_id: uuid.UUID, post_id: uuid.UUID) -> Post:
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    post.is_pinned = False
    await db.commit()
    await db.refresh(post)
    return post


async def create_post(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user: User,
    channel_id: uuid.UUID,
    body: str,
    title: str | None,
):
    channel = await _get_channel_and_check_access(db, tenant_id, user, channel_id)

    if channel.post_policy == "admins" and user.role in ("student", "manager"):
        raise AppError(ErrorCode.POSTING_RESTRICTED_ADMINS)
    if channel.post_policy == "moderators" and user.role == "student":
        raise AppError(ErrorCode.POSTING_RESTRICTED)

    post = Post(
        channel_id=channel_id,
        tenant_id=tenant_id,
        user_id=user.id,
        title=title,
        body=body,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def get_post(db: AsyncSession, tenant_id: uuid.UUID, user: User, post_id: uuid.UUID):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id or post.is_hidden:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    channel = await db.get(Channel, post.channel_id)
    if channel:
        await _require_space_access(db, tenant_id, user, channel.space_id)
    return post


async def update_post(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user: User,
    post_id: uuid.UUID,
    body: str,
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    channel = await db.get(Channel, post.channel_id)
    if channel:
        await _require_space_access(db, tenant_id, user, channel.space_id)
    if post.user_id != user.id:
        raise AppError(ErrorCode.CANNOT_EDIT_OTHERS_POST)
    post.body = body
    await db.commit()
    await db.refresh(post)
    return post


async def delete_post(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user: User,
    post_id: uuid.UUID,
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    if post.user_id != user.id:
        raise AppError(ErrorCode.CANNOT_DELETE_OTHERS_POST)
    await db.delete(post)
    await db.commit()


async def like_post(db: AsyncSession, tenant_id: uuid.UUID, user: User, post_id: uuid.UUID):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    channel = await db.get(Channel, post.channel_id)
    if channel:
        await _require_space_access(db, tenant_id, user, channel.space_id)
    existing = await db.execute(
        select(PostLike).where(PostLike.user_id == user.id, PostLike.post_id == post_id)
    )
    if existing.scalar_one_or_none():
        raise AppError(ErrorCode.ALREADY_LIKED)
    like = PostLike(user_id=user.id, post_id=post_id)
    db.add(like)
    post.likes_count += 1
    await db.commit()
    return {"liked": True}


async def unlike_post(db: AsyncSession, tenant_id: uuid.UUID, user: User, post_id: uuid.UUID):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    channel = await db.get(Channel, post.channel_id)
    if channel:
        await _require_space_access(db, tenant_id, user, channel.space_id)
    result = await db.execute(
        select(PostLike).where(PostLike.user_id == user.id, PostLike.post_id == post_id)
    )
    like = result.scalar_one_or_none()
    if like is None:
        raise AppError(ErrorCode.LIKE_NOT_FOUND)
    await db.delete(like)
    post.likes_count -= 1
    await db.commit()
    return {"liked": False}


async def list_comments(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user: User,
    post_id: uuid.UUID,
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    channel = await db.get(Channel, post.channel_id)
    if channel:
        await _require_space_access(db, tenant_id, user, channel.space_id)
    result = await db.execute(
        select(Comment)
        .where(Comment.post_id == post_id, Comment.is_hidden == False)  # noqa: E712
        .order_by(Comment.created_at.asc())
    )
    return result.scalars().all()


async def create_comment(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user: User,
    post_id: uuid.UUID,
    body: str,
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    channel = await db.get(Channel, post.channel_id)
    if channel:
        await _require_space_access(db, tenant_id, user, channel.space_id)
    comment = Comment(
        post_id=post_id,
        tenant_id=tenant_id,
        user_id=user.id,
        body=body,
    )
    db.add(comment)
    post.comments_count += 1
    await db.commit()
    await db.refresh(comment)
    return comment


async def report_post(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user: User,
    post_id: uuid.UUID,
    reason: str,
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    report = Report(
        tenant_id=tenant_id,
        post_id=post_id,
        reporter_id=user.id,
        reason=reason,
    )
    db.add(report)
    await db.commit()
    return {"reported": True}
