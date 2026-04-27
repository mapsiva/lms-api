import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.core.security import create_access_token
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.models.webhook import WebhookLog
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"wha-{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(
        id=uuid.uuid4(),
        slug=f"wha-{uuid.uuid4().hex[:8]}",
        name="WebhookAdminTest",
        custom_domain=domain,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def admin_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "admin@wha.com", "Admin", "password123", role="admin")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def admin_client(db_session, redis_client, tenant, admin_user):
    token = create_access_token(str(admin_user.id), str(tenant.id), "admin")

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant.custom_domain}",
        headers={"host": tenant.custom_domain, "Authorization": f"Bearer {token}"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def webhook_logs(db_session, tenant):
    logs = []
    for i in range(3):
        log = WebhookLog(
            tenant_id=tenant.id,
            provider="hotmart",
            event_type="PURCHASE_APPROVED",
            payload={"idx": i},
            signature_valid=True,
            processed=(i == 0),
        )
        db_session.add(log)
        logs.append(log)
    await db_session.commit()
    for log in logs:
        await db_session.refresh(log)
    yield logs
    for log in logs:
        await db_session.delete(log)
    await db_session.commit()


# ── List logs ────────────────────────────────────────────────────────────────


async def test_list_logs_paginated(admin_client, webhook_logs):
    resp = await admin_client.get("/admin/webhooks/logs?limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert "next_cursor" in data


async def test_list_logs_filter_by_processed(admin_client, webhook_logs):
    resp = await admin_client.get("/admin/webhooks/logs?processed=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["processed"] is True


async def test_list_logs_filter_by_provider(admin_client, webhook_logs):
    resp = await admin_client.get("/admin/webhooks/logs?provider=hotmart")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3


async def test_list_logs_cursor_pagination(admin_client, webhook_logs):
    resp1 = await admin_client.get("/admin/webhooks/logs?limit=1")
    data1 = resp1.json()
    cursor = data1["next_cursor"]
    assert cursor is not None

    resp2 = await admin_client.get(f"/admin/webhooks/logs?limit=1&cursor={cursor}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["items"][0]["id"] != data1["items"][0]["id"]


# ── Replay ───────────────────────────────────────────────────────────────────


async def test_replay_log_dispatches_task(admin_client, webhook_logs, db_session):
    log = webhook_logs[0]
    resp = await admin_client.post(f"/admin/webhooks/{log.id}/replay")
    assert resp.status_code == 200
    assert resp.json()["status"] == "dispatched"

    # Verify attempts incremented
    await db_session.refresh(log)


async def test_replay_nonexistent_log_returns_404(admin_client):
    fake_id = uuid.uuid4()
    resp = await admin_client.post(f"/admin/webhooks/{fake_id}/replay")
    assert resp.status_code == 404


# ── Test mode ────────────────────────────────────────────────────────────────


async def test_set_test_mode(admin_client, tenant):
    resp = await admin_client.post("/admin/webhooks/test?duration_seconds=60")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "test_mode_enabled"
    assert data["duration_seconds"] == 60

    redis = get_redis()
    if redis:
        val = await redis.get(f"webhook:test_mode:{tenant.id}")
        assert val == "1"
