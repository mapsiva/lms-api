"""Integration tests for hall of fame endpoint."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.company import Company
from app.models.gamification import XPEvent, UserLevel
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"hf-{uuid.uuid4().hex[:8]}", name="HallTest", custom_domain=domain)
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
async def student_user(db_session, tenant, company):
    u = await register_user(db_session, tenant.id, "student@hall.com", "Student", "password123", role="student")
    u.company_id = company.id
    await db_session.commit()
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def student_client(db_session, redis_client, tenant, student_user):
    token = create_access_token(str(student_user.id), str(tenant.id), "student", company_id=str(student_user.company_id))

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
async def test_hall_of_fame_empty(student_client, company):
    resp = await student_client.get(f"/gamification/hall-of-fame?company_id={company.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_hall_of_fame_with_xp(student_client, company, student_user, tenant, db_session):
    xp = XPEvent(tenant_id=tenant.id, user_id=student_user.id, company_id=company.id, action="lesson_completed", amount=100)
    db_session.add(xp)
    ul = UserLevel(tenant_id=tenant.id, user_id=student_user.id, total_xp=100, level=1)
    db_session.add(ul)
    await db_session.commit()

    resp = await student_client.get(f"/gamification/hall-of-fame?company_id={company.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
