"""WebSocket notification handler."""
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.dependencies import get_current_tenant
from app.core.redis_client import get_redis
from app.core.security import decode_token
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("/notifications")
async def ws_notifications(
    websocket: WebSocket, tenant: Tenant = Depends(get_current_tenant)
):
    await websocket.accept()
    redis = get_redis()
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

        if redis is None:
            await websocket.close(code=4001, reason="Redis not available")
            return

        channel = f"notifications:{tenant.id}:{user_id}"
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        async def redis_listener():
            try:
                async for msg in pubsub.listen():
                    if msg["type"] == "message":
                        await websocket.send_text(msg["data"])
            except asyncio.CancelledError:
                return
            except Exception:
                logger.exception("Redis listener error")

        listener_task = asyncio.create_task(redis_listener())

        try:
            while True:
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                    # Client can send heartbeats; no action needed
                except asyncio.TimeoutError:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except WebSocketDisconnect:
                    break
        finally:
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
            await pubsub.unsubscribe(channel)
    finally:
        pass
