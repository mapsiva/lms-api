"""Community router (student-facing)."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.community import (
    ChannelResponse,
    CommentResponse,
    PostResponse,
    SpaceResponse,
)
from app.services import community as community_service

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/spaces", response_model=list[SpaceResponse])
async def list_spaces(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await community_service.list_spaces(db, tenant.id, user)


@router.get("/spaces/{space_id}/channels", response_model=list[ChannelResponse])
async def list_channels(
    space_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await community_service.list_channels(db, tenant.id, user, space_id)


@router.get("/channels/{channel_id}/posts", response_model=list[PostResponse])
async def list_posts(
    channel_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await community_service.list_posts(db, tenant.id, user, channel_id)


@router.post("/channels/{channel_id}/posts", status_code=201, response_model=PostResponse)
async def create_post(
    channel_id: uuid.UUID,
    body: str,
    title: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await community_service.create_post(db, tenant.id, user, channel_id, body, title)


@router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await community_service.get_post(db, tenant.id, user, post_id)


@router.patch("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: uuid.UUID,
    body: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await community_service.update_post(db, tenant.id, user, post_id, body)


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await community_service.delete_post(db, tenant.id, user, post_id)


@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await community_service.like_post(db, tenant.id, user, post_id)


@router.delete("/posts/{post_id}/like")
async def unlike_post(
    post_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await community_service.unlike_post(db, tenant.id, user, post_id)


@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    post_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await community_service.list_comments(db, tenant.id, user, post_id)


@router.post("/posts/{post_id}/comments", status_code=201, response_model=CommentResponse)
async def create_comment(
    post_id: uuid.UUID,
    body: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await community_service.create_comment(db, tenant.id, user, post_id, body)


@router.post("/posts/{post_id}/report")
async def report_post(
    post_id: uuid.UUID,
    reason: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await community_service.report_post(db, tenant.id, user, post_id, reason)
