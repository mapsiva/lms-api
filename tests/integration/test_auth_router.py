import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
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
    t = Tenant(id=uuid.uuid4(), slug=f"rt-{uuid.uuid4().hex[:8]}", name="RouterTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "router@example.com", "Router User", "password123")
    yield u
    result = await db_session.get(User, u.id)
    if result:
        await db_session.delete(result)
        await db_session.commit()


@pytest.fixture
async def auth_client(db_session, redis_client, tenant):
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


# ── register ─────────────────────────────────────────────────────────────────

async def test_register_returns_201(auth_client, tenant):
    resp = await auth_client.post("/auth/register", json={
        "name": "New User", "email": "new@example.com", "password": "password123"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    # Cleanup
    redis = get_redis()


async def test_register_duplicate_email_returns_409(auth_client, user, tenant):
    resp = await auth_client.post("/auth/register", json={
        "name": "Dup", "email": "router@example.com", "password": "password123"
    })
    assert resp.status_code == 409


# ── login ─────────────────────────────────────────────────────────────────────

async def test_login_returns_access_token(auth_client, user, tenant):
    resp = await auth_client.post("/auth/login", json={
        "email": "router@example.com", "password": "password123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert "refresh_token" in resp.cookies


async def test_login_sets_httponly_cookie(auth_client, user, tenant):
    resp = await auth_client.post("/auth/login", json={
        "email": "router@example.com", "password": "password123"
    })
    assert resp.status_code == 200
    # httpx surfaces cookies from response headers
    cookie_header = resp.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie_header or "httponly" in cookie_header.lower()


async def test_login_wrong_password_returns_401(auth_client, user, tenant):
    resp = await auth_client.post("/auth/login", json={
        "email": "router@example.com", "password": "wrongpassword"
    })
    assert resp.status_code == 401


# ── logout ───────────────────────────────────────────────────────────────────

async def test_logout_returns_204(auth_client, user, tenant):
    login_resp = await auth_client.post("/auth/login", json={
        "email": "router@example.com", "password": "password123"
    })
    token_data = login_resp.json()
    resp = await auth_client.post("/auth/logout", json={
        "refresh_token": login_resp.cookies.get("refresh_token", "tok")
    })
    assert resp.status_code == 204


# ── magic link ───────────────────────────────────────────────────────────────

async def test_magic_link_returns_204(auth_client, user, tenant):
    resp = await auth_client.post("/auth/magic-link", json={"email": "router@example.com"})
    assert resp.status_code == 204


async def test_magic_link_verify_returns_token(auth_client, user, tenant, db_session):
    from app.services.auth import send_magic_link
    token = await send_magic_link(db_session, tenant.id, "router@example.com")
    resp = await auth_client.post("/auth/magic-link/verify", json={"token": token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_magic_link_verify_invalid_token_returns_401(auth_client, tenant):
    resp = await auth_client.post("/auth/magic-link/verify", json={"token": "invalid-token"})
    assert resp.status_code == 401


# ── forgot/reset password ─────────────────────────────────────────────────────

async def test_forgot_password_returns_204(auth_client, user, tenant):
    resp = await auth_client.post("/auth/forgot-password", json={"email": "router@example.com"})
    assert resp.status_code == 204


async def test_reset_password_returns_204(auth_client, user, tenant, db_session):
    from app.services.auth import send_password_reset
    token = await send_password_reset(db_session, tenant.id, "router@example.com")
    resp = await auth_client.post("/auth/reset-password", json={
        "token": token, "new_password": "newpassword999"
    })
    assert resp.status_code == 204


# ── /users/me ─────────────────────────────────────────────────────────────────

async def test_get_me_returns_user(auth_client, user, tenant):
    access_token = create_access_token(str(user.id), str(tenant.id), user.role)
    resp = await auth_client.get("/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "router@example.com"


async def test_get_me_no_token_returns_401(auth_client, tenant):
    resp = await auth_client.get("/users/me")
    assert resp.status_code == 401


async def test_patch_me_updates_name(auth_client, user, tenant, db_session):
    access_token = create_access_token(str(user.id), str(tenant.id), user.role)
    resp = await auth_client.patch("/users/me",
        json={"name": "Updated Name"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
