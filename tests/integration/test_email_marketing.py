"""Integration tests for email marketing."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.email import EmailAudience, EmailCampaign, EmailAutomation, EmailSend, EmailTemplate
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(
        id=uuid.uuid4(),
        slug=f"em-{uuid.uuid4().hex[:8]}",
        name="EmailTest",
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
    u = await register_user(db_session, tenant.id, "admin@email.com", "Admin", "password123", role="admin")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def student_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "student@email.com", "Student", "password123", role="student")
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
async def test_create_audience(admin_client, tenant):
    resp = await admin_client.post(
        "/admin/email/audiences",
        json={"name": "All Students", "filter_json": {"role": "student"}},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "All Students"
    assert data["tenant_id"] == str(tenant.id)


@pytest.mark.asyncio
async def test_list_audiences(admin_client, tenant, db_session):
    a = EmailAudience(tenant_id=tenant.id, name="A1")
    db_session.add(a)
    await db_session.commit()
    resp = await admin_client.get("/admin/email/audiences")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_create_template(admin_client, tenant):
    resp = await admin_client.post(
        "/admin/email/templates",
        json={"name": "Welcome", "subject": "Bem-vindo", "html_body": "<p>Ola</p>"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Welcome"
    assert data["subject"] == "Bem-vindo"


@pytest.mark.asyncio
async def test_create_campaign(admin_client, tenant, db_session):
    tmpl = EmailTemplate(tenant_id=tenant.id, name="T1", subject="S", html_body="<p>B</p>")
    aud = EmailAudience(tenant_id=tenant.id, name="A1")
    db_session.add_all([tmpl, aud])
    await db_session.commit()
    await db_session.refresh(tmpl)
    await db_session.refresh(aud)

    resp = await admin_client.post(
        "/admin/email/campaigns",
        json={"name": "C1", "template_id": str(tmpl.id), "audience_id": str(aud.id)},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "C1"


@pytest.mark.asyncio
async def test_send_campaign(admin_client, tenant, db_session, student_user):
    tmpl = EmailTemplate(tenant_id=tenant.id, name="T1", subject="S", html_body="<p>B</p>")
    aud = EmailAudience(tenant_id=tenant.id, name="A1", filter_json={"role": "student"})
    db_session.add_all([tmpl, aud])
    await db_session.commit()
    await db_session.refresh(tmpl)
    await db_session.refresh(aud)

    camp = EmailCampaign(tenant_id=tenant.id, name="C1", template_id=tmpl.id, audience_id=aud.id)
    db_session.add(camp)
    await db_session.commit()
    await db_session.refresh(camp)

    from unittest.mock import patch
    with patch("app.services.email.celery_app.send_task") as mock_send:
        resp = await admin_client.post(f"/admin/email/campaigns/{camp.id}/send")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent"
    assert data["recipients"] == 1  # student_user matches role filter
    mock_send.assert_called()


@pytest.mark.asyncio
async def test_create_automation(admin_client, tenant):
    resp = await admin_client.post(
        "/admin/email/automations",
        json={"name": "Welcome Flow", "trigger_event": "enrollment.created", "steps": [{"subject": "Hi", "template_html": "<p>Hi</p>"}]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Welcome Flow"


@pytest.mark.asyncio
async def test_open_tracking_pixel(admin_client, tenant, db_session, student_user):
    send = EmailSend(campaign_id=None, user_id=student_user.id, email=student_user.email, status="sent")
    db_session.add(send)
    await db_session.commit()
    await db_session.refresh(send)

    resp = await admin_client.get(f"/admin/email/track/{send.id}/open.gif")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/gif"

    await db_session.refresh(send)
    assert send.status == "opened"
    assert send.opened_at is not None
