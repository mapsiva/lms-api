"""Upload business logic."""

import uuid

from fastapi import HTTPException

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.integrations.r2 import upload_file
from app.models.tenant import Tenant

_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


def _build_key(prefix: str, tenant_id: uuid.UUID, ext: str) -> str:
    return f"{prefix}/{tenant_id}/{uuid.uuid4()}.{ext}"


async def handle_upload(
    *, file_content: bytes, content_type: str | None, prefix: str, tenant: Tenant
) -> str:
    """Validate, upload to R2 and return the public URL."""
    if len(file_content) > _MAX_SIZE_BYTES:
        raise AppError(ErrorCode.FILE_TOO_LARGE)

    ct = content_type or ""
    ext = _ALLOWED_TYPES.get(ct)
    if not ext:
        raise AppError(ErrorCode.UNSUPPORTED_FILE_TYPE)

    key = _build_key(prefix, tenant.id, ext)
    try:
        url = await upload_file(file_content, key, ct)
    except (RuntimeError, NotImplementedError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return url
