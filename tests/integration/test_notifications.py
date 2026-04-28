"""Integration tests for notifications router."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.notification import Notification
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"nt-{uuid.uuid4().hex[:8]}", name="NotifTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def admin_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "admin@notif.com", "Admin", "password123", role="admin")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def student_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "student@notif.com", "Student", "password123", role="student")
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
async def student_client(db_session, redis_client, tenant, student_user):
    token = create_access_token(str(student_user.id), str(tenant.id), "student")

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


@pytest.mark.asyncio
async def test_list_notifications(student_client, tenant, student_user, db_session):
    n = Notification(tenant_id=tenant.id, user_id=student_user.id, type="test", title="Hello", body="World")
    db_session.add(n)
    await db_session.commit()

    resp = await student_client.get("/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_mark_notification_read(student_client, tenant, student_user, db_session):
    n = Notification(tenant_id=tenant.id, user_id=student_user.id, type="test", title="Read", body="Me")
    db_session.add(n)
    await db_session.commit()
    await db_session.refresh(n)

    resp = await student_client.patch(f"/notifications/{n.id}/read")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_mark_all_read(student_client, tenant, student_user, db_session):
    n = Notification(tenant_id=tenant.id, user_id=student_user.id, type="test", title="All", body="Read")
    db_session.add(n)
    await db_session.commit()

    resp = await student_client.post("/notifications/read-all")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_broadcast_notification(admin_client, tenant, student_user, db_session):
    resp = await admin_client.post("/admin/notifications/broadcast", json={"title": "Broadcast", "body": "Hello all", "type": "broadcast"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["created_count"] >= 1


@pytest.mark.asyncio
async def test_push_subscribe(student_client):
    resp = await student_client.post("/push/subscribe", json={"endpoint": "https://fcm.googleapis.com/fcm/send/test", "p256dh": "abc", "auth": "def"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_push_unsubscribe(student_client):
    resp = await student_client.request("DELETE", "/push/subscribe", json={"endpoint": "https://fcm.googleapis.com/fcm/send/test", "p256dh": "abc", "auth": "def"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
