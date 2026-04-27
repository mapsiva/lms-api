"""Presence WebSocket handler."""
import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.core.redis_client import get_redis
from app.core.security import decode_token
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger(__name__)

PRESENCE_TTL = 60  # seconds
BEAT_INTERVAL = 30  # seconds


async def presence_websocket(
    websocket: WebSocket,
    tenant: Tenant = Depends(get_current_tenant),
):
    """WebSocket endpoint for presence. Receives JWT in first message."""
    await websocket.accept()
    try:
        # First message must contain JWT
        first = await websocket.receive_text()
        data = json.loads(first)
        token = data.get("token", "")
        if not token:
            await websocket.close(code=4001, reason="Token required")
            return

        try:
            payload = decode_token(token)
        except Exception:
            await websocket.close(code=4001, reason="Invalid token")
            return

        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        if str(tenant.id) != tenant_id or not user_id:
            await websocket.close(code=4001, reason="Tenant mismatch")
            return

        redis = get_redis()
        key = f"presence:{tenant.id}:{user_id}"

        # Initial presence set
        if redis:
            await redis.setex(
                key,
                PRESENCE_TTL,
                json.dumps(
                    {
                        "page": data.get("page", "/"),
                        "last_seen": datetime.now(timezone.utc).isoformat(),
                    }
                ),
            )

        # Heartbeat loop
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=BEAT_INTERVAL)
                beat = json.loads(msg)
                page = beat.get("page", "/")
                if redis:
                    await redis.setex(
                        key,
                        PRESENCE_TTL,
                        json.dumps(
                            {
                                "page": page,
                                "last_seen": datetime.now(timezone.utc).isoformat(),
                            }
                        ),
                    )
            except asyncio.TimeoutError:
                # Heartbeat refresh only — no message from client
                if redis:
                    await redis.expire(key, PRESENCE_TTL)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                continue
    finally:
        # Connection drop: key expires naturally via TTL
        pass


router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("/presence")
async def ws_presence(websocket: WebSocket, tenant: Tenant = Depends(get_current_tenant)):
    await presence_websocket(websocket, tenant)


# Admin endpoint for online users
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/users/online")
async def list_online_users(
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    redis = get_redis()
    if not redis:
        return {"items": []}

    pattern = f"presence:{tenant.id}:*"
    keys = []
    async for key in redis.scan_iter(match=pattern):
        keys.append(key)

    items = []
    if keys:
        values = await redis.mget(keys)
        for key, val in zip(keys, values):
            if not val:
                continue
            parts = key.split(":")
            user_id = parts[-1] if len(parts) >= 3 else None
            data = json.loads(val)
            user = await db.get(User, user_id)
            items.append(
                {
                    "user_id": user_id,
                    "name": user.name if user else None,
                    "page": data.get("page"),
                    "last_seen": data.get("last_seen"),
                }
            )

    return {"items": items}
