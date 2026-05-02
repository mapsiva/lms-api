import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt  # type: ignore[import-untyped]

from app.core.config import get_settings
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.redis_client import get_redis

_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    company_id: Optional[str] = None,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "company_id": company_id,
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def create_invite_token(user_id: str, tenant_id: str, company_id: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    payload: dict[str, Any] = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "company_id": company_id,
        "type": "company_invite",
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_invite_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("type") != "company_invite":
        raise AppError(ErrorCode.INVALID_TOKEN)
    return payload


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise AppError(ErrorCode.INVALID_TOKEN)


async def create_refresh_token(user_id: str) -> str:
    settings = get_settings()
    token = str(uuid.uuid4())
    redis = get_redis()
    if redis is None:
        raise RuntimeError("Redis not configured")
    ttl = settings.refresh_token_expire_days * 86400
    await redis.setex(f"refresh:{token}", ttl, user_id)
    return token


async def revoke_refresh_token(token: str) -> None:
    redis = get_redis()
    if redis is None:
        return
    await redis.delete(f"refresh:{token}")


async def get_user_id_from_refresh_token(token: str) -> Optional[str]:
    redis = get_redis()
    if redis is None:
        return None
    return await redis.get(f"refresh:{token}")


async def create_magic_link_token(email: str) -> str:
    settings = get_settings()
    token = str(uuid.uuid4())
    redis = get_redis()
    if redis is None:
        raise RuntimeError("Redis not configured")
    ttl = settings.magic_link_expire_minutes * 60
    await redis.setex(f"magic_link:{token}", ttl, email)
    return token


async def verify_magic_link_token(token: str) -> str:
    redis = get_redis()
    if redis is None:
        raise AppError(ErrorCode.INVALID_REQUEST, message="Redis not configured")
    key = f"magic_link:{token}"
    email = await redis.get(key)
    if not email:
        raise AppError(ErrorCode.INVALID_MAGIC_LINK)
    await redis.delete(key)
    return email
