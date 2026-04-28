"""Integration tests for admin dashboard router."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.company import Company
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"db-{uuid.uuid4().hex[:8]}", name="DashTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def admin_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "admin@dash.com", "Admin", "password123", role="admin")
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
async def test_dashboard_summary(admin_client, tenant, db_session):
    c = Course(tenant_id=tenant.id, title="Test Course", slug=f"course-{uuid.uuid4().hex[:8]}")
    db_session.add(c)
    await db_session.commit()

    resp = await admin_client.get("/admin/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "active_enrollments" in data
    assert "total_courses" in data
    assert "total_companies" in data


@pytest.mark.asyncio
async def test_dashboard_engagement(admin_client, tenant, db_session):
    resp = await admin_client.get("/admin/dashboard/analytics/engagement")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_completions" in data


@pytest.mark.asyncio
async def test_dashboard_courses(admin_client, tenant, db_session):
    resp = await admin_client.get("/admin/dashboard/analytics/courses")
    assert resp.status_code == 200
    data = resp.json()
    assert "by_status" in data


@pytest.mark.asyncio
async def test_dashboard_revenue(admin_client, tenant, db_session):
    resp = await admin_client.get("/admin/dashboard/analytics/revenue")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_revenue" in data
    assert isinstance(data["total_revenue"], float)
