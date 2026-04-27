"""Uploads router for R2-backed file storage."""
from fastapi import APIRouter, Depends, UploadFile

from app.core.dependencies import get_current_tenant, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.upload import UploadResponse
from app.services.upload import handle_upload

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/avatar", response_model=UploadResponse)
async def upload_avatar(
    file: UploadFile,
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    url = await handle_upload(
        file_content=content,
        content_type=file.content_type,
        prefix="avatars",
        tenant=tenant,
    )
    return UploadResponse(url=url)


@router.post("/thumbnail", response_model=UploadResponse)
async def upload_thumbnail(
    file: UploadFile,
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    url = await handle_upload(
        file_content=content,
        content_type=file.content_type,
        prefix="thumbnails",
        tenant=tenant,
    )
    return UploadResponse(url=url)


@router.post("/post-image", response_model=UploadResponse)
async def upload_post_image(
    file: UploadFile,
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    url = await handle_upload(
        file_content=content,
        content_type=file.content_type,
        prefix="posts",
        tenant=tenant,
    )
    return UploadResponse(url=url)
