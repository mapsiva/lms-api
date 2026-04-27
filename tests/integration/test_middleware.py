import pytest
import pytest_asyncio
import uuid
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.tenant import Tenant
from app.core.database import get_db


@pytest_asyncio.fixture
async def two_tenants(db_session):
    t1 = Tenant(
        id=uuid.uuid4(),
        slug="alpha",
        name="Alpha Corp",
        custom_domain="alpha.example.com",
    )
    t2 = Tenant(
        id=uuid.uuid4(),
        slug="beta",
        name="Beta Corp",
        custom_domain="beta.example.com",
    )
    db_session.add(t1)
    db_session.add(t2)
    await db_session.commit()
    yield t1, t2
    await db_session.delete(t1)
    await db_session.delete(t2)
    await db_session.commit()


async def _client_for_host(db_session, host: str) -> AsyncClient:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{host}",
        headers={"host": host},
    )


@pytest.mark.asyncio
async def test_known_host_resolves_tenant(two_tenants, db_session, redis_client):
    t1, _ = two_tenants
    async with await _client_for_host(db_session, "alpha.example.com") as c:
        resp = await c.get("/health")
    assert resp.status_code == 200
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_unknown_host_returns_404(db_session, redis_client):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://unknown.example.com",
        headers={"host": "unknown.example.com"},
    ) as c:
        resp = await c.get("/some-endpoint")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Tenant not found"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_two_tenants_isolated(two_tenants, db_session, redis_client):
    t1, t2 = two_tenants
    async with await _client_for_host(db_session, "alpha.example.com") as c1:
        r1 = await c1.get("/health")
    async with await _client_for_host(db_session, "beta.example.com") as c2:
        r2 = await c2.get("/health")
    assert r1.status_code == 200
    assert r2.status_code == 200
    app.dependency_overrides.clear()
