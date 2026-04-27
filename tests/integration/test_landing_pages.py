"""Integration tests for landing pages."""
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(
        id=uuid.uuid4(),
        slug=f"lp-{uuid.uuid4().hex[:8]}",
        name="LandingTest",
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
    u = await register_user(
        db_session, tenant.id, "admin@lp.com", "Admin", "password123", role="admin"
    )
    yield u
    result = await db_session.get(User, u.id)
    if result:
        await db_session.delete(result)
        await db_session.commit()


@pytest.fixture
async def client_with_tenant(db_session, tenant):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant.custom_domain}",
        headers={"host": tenant.custom_domain},
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_and_get_landing_page(
    client_with_tenant, tenant, admin_user, db_session
):
    token = create_access_token(
        str(admin_user.id),
        str(tenant.id),
        admin_user.role,
        str(admin_user.company_id) if admin_user.company_id else None,
    )
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client_with_tenant.post(
        "/admin/landing-pages",
        json={"slug": "launch", "title": "Product Launch", "status": "published"},
        headers=headers,
    )
    assert resp.status_code == 201
    page_id = resp.json()["id"]

    resp = await client_with_tenant.get(f"/admin/landing-pages/{page_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "launch"
    assert data["title"] == "Product Launch"

    # Public get
    resp = await client_with_tenant.get("/p/launch")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Product Launch"

    # Capture lead (with utm_campaign matching slug for analytics)
    resp = await client_with_tenant.post(
        "/p/launch/lead?utm_campaign=launch",
        json={"email": "lead@example.com", "name": "Lead"},
    )
    assert resp.status_code == 201

    # Analytics
    resp = await client_with_tenant.get("/p/launch/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["views"] >= 1
    assert data["leads"] >= 1


@pytest.mark.asyncio
async def test_public_page_not_found_for_draft(
    client_with_tenant, tenant, admin_user, db_session
):
    token = create_access_token(
        str(admin_user.id),
        str(tenant.id),
        admin_user.role,
        str(admin_user.company_id) if admin_user.company_id else None,
    )
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client_with_tenant.post(
        "/admin/landing-pages",
        json={"slug": "secret", "title": "Secret", "status": "draft"},
        headers=headers,
    )
    assert resp.status_code == 201

    resp = await client_with_tenant.get("/p/secret")
    assert resp.status_code == 404
