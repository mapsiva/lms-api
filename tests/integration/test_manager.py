"""Integration tests for manager router."""
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
    t = Tenant(id=uuid.uuid4(), slug=f"mg-{uuid.uuid4().hex[:8]}", name="ManagerTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def company(db_session, tenant):
    c = Company(tenant_id=tenant.id, cnpj="12345678000195", legal_name="TestCo")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    yield c
    await db_session.delete(c)
    await db_session.commit()


@pytest.fixture
async def manager_user(db_session, tenant, company):
    u = await register_user(db_session, tenant.id, "manager@test.com", "Manager", "password123", role="manager", company_id=company.id)
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def manager_client(db_session, redis_client, tenant, manager_user):
    token = create_access_token(str(manager_user.id), str(tenant.id), "manager", company_id=str(manager_user.company_id))

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
async def test_manager_dashboard(manager_client):
    resp = await manager_client.get("/manager/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "member_count" in data


@pytest.mark.asyncio
async def test_manager_members(manager_client, company, db_session):
    s = await register_user(db_session, company.tenant_id, "student@test.com", "Student", "password123", role="student")
    cm = CompanyMember(company_id=company.id, user_id=s.id)
    db_session.add(cm)
    await db_session.commit()

    resp = await manager_client.get("/manager/members")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_manager_create_goal(manager_client):
    resp = await manager_client.post("/manager/goals", json={"title": "Complete Course", "target_metric": "courses_completed", "target_value": 5})
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_manager_list_goals(manager_client, company, db_session):
    from app.models.company import CompanyGoal
    g = CompanyGoal(company_id=company.id, title="Goal 1", target_metric="courses_completed", target_value=3)
    db_session.add(g)
    await db_session.commit()

    resp = await manager_client.get("/manager/goals")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_manager_report(manager_client):
    resp = await manager_client.get("/manager/report")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_manager_isolation_student_blocked(db_session, redis_client, tenant, company):
    s = await register_user(db_session, tenant.id, "student2@test.com", "Student2", "password123", role="student", company_id=company.id)
    token = create_access_token(str(s.id), str(tenant.id), "student", company_id=str(company.id))

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant.custom_domain}",
        headers={"host": tenant.custom_domain, "Authorization": f"Bearer {token}"},
    ) as c:
        resp = await c.get("/manager/dashboard")
        assert resp.status_code == 403

    app.dependency_overrides.clear()
