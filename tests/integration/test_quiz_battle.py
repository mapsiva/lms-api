"""Integration tests for quiz battle router."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.course import Course
from app.models.quiz import QuizBattle
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"qb-{uuid.uuid4().hex[:8]}", name="QuizTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def user_a(db_session, tenant):
    u = await register_user(db_session, tenant.id, "a@quiz.com", "UserA", "password123", role="student")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def user_b(db_session, tenant):
    u = await register_user(db_session, tenant.id, "b@quiz.com", "UserB", "password123", role="student")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def client_a(db_session, redis_client, tenant, user_a):
    token = create_access_token(str(user_a.id), str(tenant.id), "student")

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
async def client_b(db_session, redis_client, tenant, user_b):
    token = create_access_token(str(user_b.id), str(tenant.id), "student")

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
async def test_create_battle(client_a, user_a, user_b, tenant, db_session):
    c = Course(tenant_id=tenant.id, title="Course", slug=f"c-{uuid.uuid4().hex[:8]}")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    resp = await client_a.post("/quiz/battles", json={
        "opponent_id": str(user_b.id),
        "course_id": str(c.id),
        "question_count": 3,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["challenger_id"] == str(user_a.id)


@pytest.mark.asyncio
async def test_list_battles(client_a, user_a, user_b, tenant, db_session):
    c = Course(tenant_id=tenant.id, title="Course2", slug=f"c2-{uuid.uuid4().hex[:8]}")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    b = QuizBattle(tenant_id=tenant.id, challenger_id=user_a.id, opponent_id=user_b.id, course_id=c.id, status="pending")
    db_session.add(b)
    await db_session.commit()

    resp = await client_a.get("/quiz/battles")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_battle(client_a, user_a, user_b, tenant, db_session):
    c = Course(tenant_id=tenant.id, title="Course3", slug=f"c3-{uuid.uuid4().hex[:8]}")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    b = QuizBattle(tenant_id=tenant.id, challenger_id=user_a.id, opponent_id=user_b.id, course_id=c.id, status="pending")
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)

    resp = await client_a.get(f"/quiz/battles/{b.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(b.id)


@pytest.mark.asyncio
async def test_submit_answer(client_a, client_b, user_a, user_b, tenant, db_session):
    c = Course(tenant_id=tenant.id, title="Course4", slug=f"c4-{uuid.uuid4().hex[:8]}")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    b = QuizBattle(tenant_id=tenant.id, challenger_id=user_a.id, opponent_id=user_b.id, course_id=c.id, status="active")
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)

    resp = await client_a.post(f"/quiz/battles/{b.id}/answer", json={"answers": {}})
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data

    resp = await client_b.post(f"/quiz/battles/{b.id}/answer", json={"answers": {}})
    assert resp.status_code == 200
