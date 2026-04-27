"""Uploads router for R2-backed file storage."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.dependencies import get_current_tenant, get_current_user
from app.integrations.r2 import upload_file
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/uploads", tags=["uploads"])

_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


def _build_key(prefix: str, tenant_id: uuid.UUID, ext: str) -> str:
    return f"{prefix}/{tenant_id}/{uuid.uuid4()}.{ext}"


async def _handle_upload(file: UploadFile, prefix: str, tenant: Tenant) -> dict:
    content = await file.read()
    if len(content) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 10MB)",
        )

    content_type = file.content_type or ""
    ext = _ALLOWED_TYPES.get(content_type)
    if not ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {content_type}",
        )

    key = _build_key(prefix, tenant.id, ext)
    url = await upload_file(content, key, content_type)
    return {"url": url}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile,
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    return await _handle_upload(file, "avatars", tenant)


@router.post("/thumbnail")
async def upload_thumbnail(
    file: UploadFile,
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    return await _handle_upload(file, "thumbnails", tenant)


@router.post("/post-image")
async def upload_post_image(
    file: UploadFile,
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    return await _handle_upload(file, "posts", tenant)
