"""Integration tests for community admin router."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.community import Channel, Comment, Post, Report, Space
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"ca-{uuid.uuid4().hex[:8]}", name="CommAdminTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def admin_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "admin@ca.com", "Admin", "password123", role="admin")
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


@pytest.mark.asyncio
async def test_list_reports(admin_client, tenant, db_session):
    s = Space(tenant_id=tenant.id, name="General")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    ch = Channel(space_id=s.id, tenant_id=tenant.id, name="Discussion", post_policy="open")
    db_session.add(ch)
    await db_session.commit()
    await db_session.refresh(ch)

    u = await register_user(db_session, tenant.id, "reporter@ca.com", "Reporter", "password123", role="student")
    p = Post(channel_id=ch.id, tenant_id=tenant.id, user_id=u.id, body="Spam post")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    r = Report(post_id=p.id, tenant_id=tenant.id, reporter_id=u.id, reason="spam", status="pending")
    db_session.add(r)
    await db_session.commit()

    resp = await admin_client.get("/admin/community/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_resolve_report(admin_client, tenant, db_session):
    s = Space(tenant_id=tenant.id, name="General")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    ch = Channel(space_id=s.id, tenant_id=tenant.id, name="Discussion", post_policy="open")
    db_session.add(ch)
    await db_session.commit()
    await db_session.refresh(ch)

    u = await register_user(db_session, tenant.id, "r2@ca.com", "R2", "password123", role="student")
    p = Post(channel_id=ch.id, tenant_id=tenant.id, user_id=u.id, body="Spam")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    r = Report(post_id=p.id, tenant_id=tenant.id, reporter_id=u.id, reason="spam", status="pending")
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)

    resp = await admin_client.patch(f"/admin/community/reports/{r.id}?status=resolved")
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_suspend_user(admin_client, tenant, db_session):
    u = await register_user(db_session, tenant.id, "suspend@ca.com", "Suspend", "password123", role="student")
    resp = await admin_client.post(f"/admin/community/users/{u.id}/suspend")
    assert resp.status_code == 200
    assert resp.json()["suspended"] is True


@pytest.mark.asyncio
async def test_create_space(admin_client):
    resp = await admin_client.post("/admin/community/spaces", json={"name": "New Space", "description": "Desc"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "New Space"


@pytest.mark.asyncio
async def test_create_channel(admin_client, tenant, db_session):
    s = Space(tenant_id=tenant.id, name="Space")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)

    resp = await admin_client.post(f"/admin/community/spaces/{s.id}/channels", json={"name": "Channel", "channel_type": "discussion", "post_policy": "open"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Channel"


@pytest.mark.asyncio
async def test_hide_post(admin_client, tenant, db_session):
    s = Space(tenant_id=tenant.id, name="General")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    ch = Channel(space_id=s.id, tenant_id=tenant.id, name="Discussion", post_policy="open")
    db_session.add(ch)
    await db_session.commit()
    await db_session.refresh(ch)

    u = await register_user(db_session, tenant.id, "poster@ca.com", "Poster", "password123", role="student")
    p = Post(channel_id=ch.id, tenant_id=tenant.id, user_id=u.id, body="Bad post")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    resp = await admin_client.patch(f"/admin/community/posts/{p.id}/hide")
    assert resp.status_code == 200
    assert resp.json()["hidden"] is True
