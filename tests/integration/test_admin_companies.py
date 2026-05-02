"""Integration tests for admin companies router."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.company import Company, CompanyMember
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"ac-{uuid.uuid4().hex[:8]}", name="AdminCoTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def admin_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "admin@co.com", "Admin", "password123", role="admin")
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
async def test_create_company(admin_client):
    resp = await admin_client.post("/admin/companies", json={"legal_name": "Test Corp", "cnpj": "12345678000195"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["legal_name"] == "Test Corp"


@pytest.mark.asyncio
async def test_list_companies(admin_client, tenant, db_session):
    c = Company(tenant_id=tenant.id, legal_name="Existing Co", cnpj="00000000000000")
    db_session.add(c)
    await db_session.commit()

    resp = await admin_client.get("/admin/companies")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_company(admin_client, tenant, db_session):
    c = Company(tenant_id=tenant.id, legal_name="Get Co", cnpj="11111111000111")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    resp = await admin_client.get(f"/admin/companies/{c.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["legal_name"] == "Get Co"


@pytest.mark.asyncio
async def test_update_company(admin_client, tenant, db_session):
    c = Company(tenant_id=tenant.id, legal_name="Old Name", cnpj="22222222000122")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    resp = await admin_client.patch(f"/admin/companies/{c.id}", json={"legal_name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["legal_name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_company(admin_client, tenant, db_session):
    c = Company(tenant_id=tenant.id, legal_name="Delete Co", cnpj="33333333000133")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    resp = await admin_client.delete(f"/admin/companies/{c.id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_company_isolation_wrong_tenant(admin_client, tenant, db_session):
    other_tenant = Tenant(id=uuid.uuid4(), slug="other", name="Other", custom_domain="other.example.com")
    db_session.add(other_tenant)
    await db_session.commit()

    c = Company(tenant_id=other_tenant.id, legal_name="Other Co", cnpj="44444444000144")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    resp = await admin_client.get(f"/admin/companies/{c.id}")
    assert resp.status_code == 404

    await db_session.delete(c)
    await db_session.delete(other_tenant)
    await db_session.commit()


@pytest.mark.asyncio
async def test_invite_member(admin_client, tenant, db_session):
    c = Company(tenant_id=tenant.id, legal_name="Invite Co", cnpj="55555555000155")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    resp = await admin_client.post(f"/admin/companies/{c.id}/members/invite", json={"email": "new@member.com", "name": "Member"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "new@member.com"
    assert data["invite_token"]
    assert data["invite_url"].startswith("/invites/")

    accept_resp = await admin_client.post(
        f"/invites/{data['invite_token']}/accept",
        json={"password": "new-password123", "name": "Accepted Member"},
    )
    assert accept_resp.status_code == 200
    accept_data = accept_resp.json()
    assert accept_data["access_token"]
    assert accept_data["company_id"] == str(c.id)


@pytest.mark.asyncio
async def test_update_member(admin_client, tenant, db_session):
    c = Company(tenant_id=tenant.id, legal_name="Update Member Co", cnpj="77777777000177")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    u = await register_user(db_session, tenant.id, "update@member.com", "Update", "password123", role="student")
    cm = CompanyMember(company_id=c.id, user_id=u.id, team="Old", job_role="Analyst")
    db_session.add(cm)
    await db_session.commit()

    resp = await admin_client.patch(
        f"/admin/companies/{c.id}/members/{u.id}",
        json={"team": "New", "job_role": "Lead", "is_active": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["team"] == "New"
    assert data["job_role"] == "Lead"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_company_dashboard(admin_client, tenant, db_session):
    c = Company(tenant_id=tenant.id, legal_name="Dashboard Co", cnpj="88888888000188")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    u = await register_user(db_session, tenant.id, "dash@member.com", "Dash", "password123", role="student", company_id=c.id)
    cm = CompanyMember(company_id=c.id, user_id=u.id)
    db_session.add(cm)
    await db_session.commit()

    resp = await admin_client.get(f"/admin/companies/{c.id}/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["company_id"] == str(c.id)
    assert data["member_count"] >= 1


@pytest.mark.asyncio
async def test_remove_member(admin_client, tenant, db_session):
    c = Company(tenant_id=tenant.id, legal_name="Remove Co", cnpj="66666666000166")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    u = await register_user(db_session, tenant.id, "remove@member.com", "Remove", "password123", role="student")
    cm = CompanyMember(company_id=c.id, user_id=u.id)
    db_session.add(cm)
    await db_session.commit()

    resp = await admin_client.delete(f"/admin/companies/{c.id}/members/{u.id}")
    assert resp.status_code == 204
