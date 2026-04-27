"""Community business logic."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.community import Channel, Comment, Post, PostLike, Report, Space
from app.models.user import User


async def list_spaces(db: AsyncSession, tenant_id: uuid.UUID):
    result = await db.execute(
        select(Space)
        .where(Space.tenant_id == tenant_id, Space.is_active == True)  # noqa: E712
        .order_by(Space.created_at.desc())
    )
    return result.scalars().all()


async def list_channels(db: AsyncSession, tenant_id: uuid.UUID, space_id: uuid.UUID):
    space = await db.get(Space, space_id)
    if space is None or space.tenant_id != tenant_id:
        raise AppError(ErrorCode.SPACE_NOT_FOUND)
    result = await db.execute(
        select(Channel)
        .where(Channel.space_id == space_id, Channel.is_active == True)  # noqa: E712
        .order_by(Channel.created_at.desc())
    )
    return result.scalars().all()


async def list_posts(db: AsyncSession, tenant_id: uuid.UUID, channel_id: uuid.UUID):
    channel = await db.get(Channel, channel_id)
    if channel is None or channel.tenant_id != tenant_id:
        raise AppError(ErrorCode.CHANNEL_NOT_FOUND)
    result = await db.execute(
        select(Post)
        .where(Post.channel_id == channel_id, Post.is_hidden == False)  # noqa: E712
        .order_by(Post.created_at.desc())
    )
    return result.scalars().all()


async def create_post(db: AsyncSession, tenant_id: uuid.UUID, user: User, channel_id: uuid.UUID, body: str, title: str | None):
    channel = await db.get(Channel, channel_id)
    if channel is None or channel.tenant_id != tenant_id:
        raise AppError(ErrorCode.CHANNEL_NOT_FOUND)

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


async def get_post(db: AsyncSession, tenant_id: uuid.UUID, post_id: uuid.UUID):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id or post.is_hidden:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    return post


async def update_post(db: AsyncSession, tenant_id: uuid.UUID, user: User, post_id: uuid.UUID, body: str):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    if post.user_id != user.id:
        raise AppError(ErrorCode.CANNOT_EDIT_OTHERS_POST)
    post.body = body
    await db.commit()
    await db.refresh(post)
    return post


async def delete_post(db: AsyncSession, tenant_id: uuid.UUID, user: User, post_id: uuid.UUID):
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


async def list_comments(db: AsyncSession, tenant_id: uuid.UUID, post_id: uuid.UUID):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
    result = await db.execute(
        select(Comment)
        .where(Comment.post_id == post_id, Comment.is_hidden == False)  # noqa: E712
        .order_by(Comment.created_at.asc())
    )
    return result.scalars().all()


async def create_comment(db: AsyncSession, tenant_id: uuid.UUID, user: User, post_id: uuid.UUID, body: str):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant_id:
        raise AppError(ErrorCode.POST_NOT_FOUND)
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


async def report_post(db: AsyncSession, tenant_id: uuid.UUID, user: User, post_id: uuid.UUID, reason: str):
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
