"""Integration tests for gamification router."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.company import Company
from app.models.gamification import Badge, UserBadge, UserLevel, UserStreak
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"gm-{uuid.uuid4().hex[:8]}", name="GamifyTest", custom_domain=domain)
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
    u = await register_user(db_session, tenant.id, "student@gamify.com", "Student", "password123", role="student")
    u.company_id = company.id
    await db_session.commit()
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


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
async def test_leaderboard_empty(student_client, company):
    resp = await student_client.get(f"/gamification/leaderboard?company_id={company.id}")
    assert resp.status_code == 200
    data = resp.json()
    # student_user is in company but has no XP yet
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_my_stats(student_client, student_user, tenant, db_session):
    ul = UserLevel(tenant_id=tenant.id, user_id=student_user.id, total_xp=150, level=2)
    db_session.add(ul)
    await db_session.commit()

    streak = UserStreak(user_id=student_user.id, current_streak=5, longest_streak=10)
    db_session.add(streak)
    await db_session.commit()

    resp = await student_client.get("/gamification/my-stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_xp"] == 150
    assert data["level"] == 2
    assert data["current_streak"] == 5
    assert data["top_badges"] == []


@pytest.mark.asyncio
async def test_list_badges(student_client, tenant, db_session):
    b = Badge(
        tenant_id=tenant.id,
        name="Welcome",
        category="completion",
        rarity="common",
        is_active=True,
    )
    db_session.add(b)
    await db_session.commit()

    resp = await student_client.get("/gamification/badges")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Welcome"
    assert data[0]["earned"] is False


@pytest.mark.asyncio
async def test_list_badges_with_earned(student_client, tenant, student_user, db_session):
    b = Badge(
        tenant_id=tenant.id,
        name="Welcome",
        category="completion",
        rarity="common",
        is_active=True,
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)

    ub = UserBadge(user_id=student_user.id, badge_id=b.id)
    db_session.add(ub)
    await db_session.commit()

    resp = await student_client.get("/gamification/badges")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["earned"] is True


@pytest.mark.asyncio
async def test_leaderboard_isolation(student_client, tenant, db_session):
    other_company = Company(tenant_id=tenant.id, cnpj="00000000000000", legal_name="Other")
    db_session.add(other_company)
    await db_session.commit()

    resp = await student_client.get(f"/gamification/leaderboard?company_id={other_company.id}")
    assert resp.status_code == 200
    # No users in OtherCo yet
