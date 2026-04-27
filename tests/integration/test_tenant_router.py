import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.redis_client import get_redis
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
        slug=f"tr-{uuid.uuid4().hex[:8]}",
        name="TenantRouterTest",
        custom_domain=domain,
        subdomain=None,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def admin_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "admin@example.com", "Admin", "password123", role="admin")
    yield u
    result = await db_session.get(User, u.id)
    if result:
        await db_session.delete(result)
        await db_session.commit()


@pytest.fixture
async def student_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "student@example.com", "Student", "password123", role="student")
    yield u
    result = await db_session.get(User, u.id)
    if result:
        await db_session.delete(result)
        await db_session.commit()


@pytest.fixture
async def admin_client(db_session, redis_client, tenant, admin_user):
    access_token = create_access_token(str(admin_user.id), str(tenant.id), "admin")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant.custom_domain}",
        headers={"host": tenant.custom_domain, "Authorization": f"Bearer {access_token}"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def student_client(db_session, redis_client, tenant, student_user):
    access_token = create_access_token(str(student_user.id), str(tenant.id), "student")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant.custom_domain}",
        headers={"host": tenant.custom_domain, "Authorization": f"Bearer {access_token}"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


# ── GET branding ──────────────────────────────────────────────────────────────

async def test_get_branding_returns_200(admin_client, tenant):
    resp = await admin_client.get("/admin/tenant/branding")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == tenant.slug
    assert data["name"] == tenant.name


async def test_get_branding_student_forbidden(student_client, tenant):
    resp = await student_client.get("/admin/tenant/branding")
    assert resp.status_code == 403


async def test_get_branding_no_auth(db_session, redis_client, tenant):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant.custom_domain}",
        headers={"host": tenant.custom_domain},
    ) as c:
        resp = await c.get("/admin/tenant/branding")
    assert resp.status_code == 401
    app.dependency_overrides.clear()


# ── PATCH branding ────────────────────────────────────────────────────────────

async def test_patch_branding_updates_fields(admin_client, tenant, db_session):
    resp = await admin_client.patch("/admin/tenant/branding", json={
        "primary_color": "#123456",
        "app_name": "My LMS",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["primary_color"] == "#123456"
    assert data["app_name"] == "My LMS"


async def test_patch_branding_partial_update(admin_client, tenant, db_session):
    await admin_client.patch("/admin/tenant/branding", json={"app_name": "First"})
    resp = await admin_client.patch("/admin/tenant/branding", json={"primary_color": "#AABBCC"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["primary_color"] == "#AABBCC"
    assert data["app_name"] == "First"


async def test_patch_branding_invalid_color_returns_422(admin_client, tenant):
    resp = await admin_client.patch("/admin/tenant/branding", json={"primary_color": "red"})
    assert resp.status_code == 422


async def test_patch_branding_invalidates_redis_cache(admin_client, tenant):
    redis = get_redis()
    import json
    cached_payload = json.dumps({"id": str(tenant.id), "slug": tenant.slug, "name": tenant.name,
                                  "custom_domain": tenant.custom_domain, "subdomain": None,
                                  "plan": "free", "features": None})
    await redis.set(f"tenant:host:{tenant.custom_domain}", cached_payload)
    resp = await admin_client.patch("/admin/tenant/branding", json={"app_name": "Updated"})
    assert resp.status_code == 200
    cached = await redis.get(f"tenant:host:{tenant.custom_domain}")
    assert cached is None


# ── GET settings ──────────────────────────────────────────────────────────────

async def test_get_settings_returns_plan(admin_client, tenant):
    resp = await admin_client.get("/admin/tenant/settings")
    assert resp.status_code == 200
    assert "plan" in resp.json()


# ── PATCH settings ────────────────────────────────────────────────────────────

async def test_patch_settings_updates_name(admin_client, tenant):
    resp = await admin_client.patch("/admin/tenant/settings", json={"name": "Renamed Corp"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Corp"


async def test_patch_settings_updates_features(admin_client, tenant):
    resp = await admin_client.patch("/admin/tenant/settings", json={
        "features": {"gamification": True, "community": False, "live_classes": False,
                     "certificates": True, "custom_domain": False}
    })
    assert resp.status_code == 200
    assert resp.json()["features"]["gamification"] is True


# ── Tenant isolation ──────────────────────────────────────────────────────────

async def test_tenant_isolation_admin_cannot_see_other_tenant(db_session, redis_client, admin_user, tenant):
    other_domain = f"{uuid.uuid4().hex[:8]}.example.com"
    other_tenant = Tenant(
        id=uuid.uuid4(),
        slug=f"other-{uuid.uuid4().hex[:8]}",
        name="OtherTenant",
        custom_domain=other_domain,
    )
    db_session.add(other_tenant)
    await db_session.commit()

    access_token = create_access_token(str(admin_user.id), str(tenant.id), "admin")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Admin from tenant A hitting other tenant's domain
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{other_domain}",
        headers={"host": other_domain, "Authorization": f"Bearer {access_token}"},
    ) as c:
        resp = await c.get("/admin/tenant/branding")
    app.dependency_overrides.clear()

    # Token tenant_id != other_tenant.id → 401
    assert resp.status_code == 401

    await db_session.delete(other_tenant)
    await db_session.commit()
