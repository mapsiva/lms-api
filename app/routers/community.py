"""Community router (student-facing)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.community import Channel, Comment, Post, PostLike, Report, Space
from app.models.user import User

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/spaces")
async def list_spaces(
    tenant=Depends(get_current_tenant),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Space)
        .where(Space.tenant_id == tenant.id, Space.is_active == True)  # noqa: E712
        .order_by(Space.created_at.desc())
    )
    return result.scalars().all()


@router.get("/spaces/{space_id}/channels")
async def list_channels(
    space_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    space = await db.get(Space, space_id)
    if space is None or space.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Space not found")
    result = await db.execute(
        select(Channel)
        .where(Channel.space_id == space_id, Channel.is_active == True)  # noqa: E712
        .order_by(Channel.created_at.desc())
    )
    return result.scalars().all()


@router.get("/channels/{channel_id}/posts")
async def list_posts(
    channel_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    channel = await db.get(Channel, channel_id)
    if channel is None or channel.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Channel not found")
    result = await db.execute(
        select(Post)
        .where(Post.channel_id == channel_id, Post.is_hidden == False)  # noqa: E712
        .order_by(Post.created_at.desc())
    )
    return result.scalars().all()


@router.post("/channels/{channel_id}/posts", status_code=201)
async def create_post(
    channel_id: uuid.UUID,
    body: str,
    title: str | None = None,
    tenant=Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    channel = await db.get(Channel, channel_id)
    if channel is None or channel.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Post policy check
    if channel.post_policy == "admins" and user.role in ("student", "manager"):
        raise HTTPException(status_code=403, detail="Posting restricted to admins")
    if channel.post_policy == "moderators" and user.role == "student":
        raise HTTPException(status_code=403, detail="Posting restricted")

    post = Post(
        channel_id=channel_id,
        tenant_id=tenant.id,
        user_id=user.id,
        title=title,
        body=body,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.get("/posts/{post_id}")
async def get_post(
    post_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant.id or post.is_hidden:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.patch("/posts/{post_id}")
async def update_post(
    post_id: uuid.UUID,
    body: str,
    tenant=Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot edit others' posts")
    post.body = body
    await db.commit()
    await db.refresh(post)
    return post


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot delete others' posts")
    await db.delete(post)
    await db.commit()


@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Post not found")
    existing = await db.execute(
        select(PostLike).where(PostLike.user_id == user.id, PostLike.post_id == post_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already liked")
    like = PostLike(user_id=user.id, post_id=post_id)
    db.add(like)
    post.likes_count += 1
    await db.commit()
    return {"liked": True}


@router.delete("/posts/{post_id}/like")
async def unlike_post(
    post_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Post not found")
    result = await db.execute(
        select(PostLike).where(PostLike.user_id == user.id, PostLike.post_id == post_id)
    )
    like = result.scalar_one_or_none()
    if like is None:
        raise HTTPException(status_code=404, detail="Like not found")
    await db.delete(like)
    post.likes_count -= 1
    await db.commit()
    return {"liked": False}


@router.get("/posts/{post_id}/comments")
async def list_comments(
    post_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Post not found")
    result = await db.execute(
        select(Comment)
        .where(Comment.post_id == post_id, Comment.is_hidden == False)  # noqa: E712
        .order_by(Comment.created_at.asc())
    )
    return result.scalars().all()


@router.post("/posts/{post_id}/comments", status_code=201)
async def create_comment(
    post_id: uuid.UUID,
    body: str,
    tenant=Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Post not found")
    comment = Comment(
        post_id=post_id,
        tenant_id=tenant.id,
        user_id=user.id,
        body=body,
    )
    db.add(comment)
    post.comments_count += 1
    await db.commit()
    await db.refresh(comment)
    return comment


@router.post("/posts/{post_id}/report")
async def report_post(
    post_id: uuid.UUID,
    reason: str,
    tenant=Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if post is None or post.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Post not found")
    report = Report(
        tenant_id=tenant.id,
        post_id=post_id,
        reporter_id=user.id,
        reason=reason,
    )
    db.add(report)
    await db.commit()
    return {"reported": True}
