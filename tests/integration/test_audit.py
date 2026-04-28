"""Integration tests for audit logging."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.audit import AuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"au-{uuid.uuid4().hex[:8]}", name="AuditTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def admin_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "admin@audit.com", "Admin", "password123", role="admin")
    yield u
    from sqlalchemy import delete
    await db_session.execute(delete(AuditLog).where(AuditLog.user_id == u.id))
    await db_session.commit()
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


@pytest.mark.asyncio
async def test_audit_log_list(admin_client, tenant, admin_user, db_session):
    log = AuditLog(
        tenant_id=tenant.id,
        user_id=admin_user.id,
        action="test_action",
        resource_type="test",
        resource_id=str(uuid.uuid4()),
        details={"key": "value"},
    )
    db_session.add(log)
    await db_session.commit()

    resp = await admin_client.get("/admin/audit-log")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_audit_log_filter_by_action(admin_client, tenant, admin_user, db_session):
    log = AuditLog(
        tenant_id=tenant.id,
        user_id=admin_user.id,
        action="specific_action",
        resource_type="test",
        resource_id=str(uuid.uuid4()),
    )
    db_session.add(log)
    await db_session.commit()

    resp = await admin_client.get("/admin/audit-log?action=specific_action")
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["action"] == "specific_action" for item in data["items"])


@pytest.mark.asyncio
async def test_audit_log_service(tenant, admin_user, db_session):
    from app.services.audit import log_admin_action

    await log_admin_action(
        db_session, tenant.id, admin_user.id,
        "delete_company", "company", str(uuid.uuid4()),
        {"reason": "test"},
    )

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "delete_company")
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.user_id == admin_user.id
    assert log.details == {"reason": "test"}
