import uuid
import pytest
from fastapi import HTTPException

from app.core.redis_client import get_redis
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import (
    login_user,
    logout_user,
    refresh_access_token,
    register_user,
    reset_password,
    send_magic_link,
    send_password_reset,
    verify_magic_link,
)


@pytest.fixture
async def tenant(db_session):
    t = Tenant(id=uuid.uuid4(), slug=f"t-{uuid.uuid4().hex[:8]}", name="Test Tenant",
                custom_domain=f"{uuid.uuid4().hex[:8]}.example.com")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def registered_user(db_session, tenant):
    user = await register_user(
        db_session, tenant.id, "alice@example.com", "Alice", "password123"
    )
    yield user
    result = await db_session.get(User, user.id)
    if result:
        await db_session.delete(result)
        await db_session.commit()


# ── register ─────────────────────────────────────────────────────────────────

async def test_register_user_success(db_session, tenant, redis_client):
    user = await register_user(db_session, tenant.id, "bob@example.com", "Bob", "password123")
    assert user.id is not None
    assert user.email == "bob@example.com"
    assert user.role == "student"
    assert user.password_hash is not None
    assert user.password_hash != "password123"
    # Cleanup
    await db_session.delete(user)
    await db_session.commit()


async def test_register_duplicate_email_raises_409(db_session, tenant, registered_user, redis_client):
    with pytest.raises(HTTPException) as exc_info:
        await register_user(db_session, tenant.id, "alice@example.com", "Alice2", "password456")
    assert exc_info.value.status_code == 409


async def test_register_same_email_different_tenants(db_session, redis_client):
    t1 = Tenant(id=uuid.uuid4(), slug=f"t1-{uuid.uuid4().hex[:8]}", name="T1",
                 custom_domain=f"{uuid.uuid4().hex[:8]}.example.com")
    t2 = Tenant(id=uuid.uuid4(), slug=f"t2-{uuid.uuid4().hex[:8]}", name="T2",
                 custom_domain=f"{uuid.uuid4().hex[:8]}.example.com")
    db_session.add(t1)
    db_session.add(t2)
    await db_session.commit()

    u1 = await register_user(db_session, t1.id, "shared@example.com", "U1", "pass123456")
    u2 = await register_user(db_session, t2.id, "shared@example.com", "U2", "pass123456")
    assert u1.id != u2.id

    for u in [u1, u2]:
        await db_session.delete(u)
    for t in [t1, t2]:
        await db_session.delete(t)
    await db_session.commit()


# ── login ─────────────────────────────────────────────────────────────────────

async def test_login_user_success(db_session, tenant, registered_user, redis_client):
    result = await login_user(db_session, tenant.id, "alice@example.com", "password123")
    assert "access_token" in result
    assert "refresh_token" in result
    assert result["user"].id == registered_user.id
    # Cleanup Redis refresh token
    await get_redis().delete(f"refresh:{result['refresh_token']}")


async def test_login_wrong_password_raises_401(db_session, tenant, registered_user, redis_client):
    with pytest.raises(HTTPException) as exc_info:
        await login_user(db_session, tenant.id, "alice@example.com", "wrongpassword")
    assert exc_info.value.status_code == 401


async def test_login_nonexistent_user_raises_401(db_session, tenant, redis_client):
    with pytest.raises(HTTPException) as exc_info:
        await login_user(db_session, tenant.id, "nobody@example.com", "password")
    assert exc_info.value.status_code == 401


# ── logout + refresh ──────────────────────────────────────────────────────────

async def test_logout_revokes_refresh_token(db_session, tenant, registered_user, redis_client):
    result = await login_user(db_session, tenant.id, "alice@example.com", "password123")
    refresh_token = result["refresh_token"]
    assert await get_redis().get(f"refresh:{refresh_token}") is not None
    await logout_user(refresh_token)
    assert await get_redis().get(f"refresh:{refresh_token}") is None


async def test_refresh_access_token_rotates(db_session, tenant, registered_user, redis_client):
    result = await login_user(db_session, tenant.id, "alice@example.com", "password123")
    old_refresh = result["refresh_token"]

    new_result = await refresh_access_token(db_session, tenant.id, old_refresh)
    # New refresh token is different (rotated)
    assert new_result["refresh_token"] != old_refresh
    # Old refresh token is revoked
    assert await get_redis().get(f"refresh:{old_refresh}") is None
    # New access token is present and valid
    assert new_result["access_token"]
    # Cleanup new refresh token
    await get_redis().delete(f"refresh:{new_result['refresh_token']}")


async def test_refresh_invalid_token_raises_401(db_session, tenant, redis_client):
    with pytest.raises(HTTPException) as exc_info:
        await refresh_access_token(db_session, tenant.id, "invalid-token")
    assert exc_info.value.status_code == 401


# ── magic link ───────────────────────────────────────────────────────────────

async def test_send_magic_link_stores_in_redis(db_session, tenant, registered_user, redis_client):
    token = await send_magic_link(db_session, tenant.id, "alice@example.com")
    assert token != ""
    value = await get_redis().get(f"magic_link:{token}")
    assert value == "alice@example.com"
    await get_redis().delete(f"magic_link:{token}")


async def test_send_magic_link_unknown_email_returns_empty(db_session, tenant, redis_client):
    token = await send_magic_link(db_session, tenant.id, "nobody@example.com")
    assert token == ""


async def test_verify_magic_link_success(db_session, tenant, registered_user, redis_client):
    token = await send_magic_link(db_session, tenant.id, "alice@example.com")
    result = await verify_magic_link(db_session, tenant.id, token)
    assert result["user"].id == registered_user.id
    assert "access_token" in result
    assert "refresh_token" in result
    await get_redis().delete(f"refresh:{result['refresh_token']}")


# ── password reset ────────────────────────────────────────────────────────────

async def test_password_reset_flow(db_session, tenant, registered_user, redis_client):
    token = await send_password_reset(db_session, tenant.id, "alice@example.com")
    assert token != ""

    await reset_password(db_session, tenant.id, token, "newpassword456")

    result = await login_user(db_session, tenant.id, "alice@example.com", "newpassword456")
    assert "access_token" in result
    await get_redis().delete(f"refresh:{result['refresh_token']}")


async def test_password_reset_old_password_fails(db_session, tenant, registered_user, redis_client):
    token = await send_password_reset(db_session, tenant.id, "alice@example.com")
    await reset_password(db_session, tenant.id, token, "newpassword456")

    with pytest.raises(HTTPException) as exc_info:
        await login_user(db_session, tenant.id, "alice@example.com", "password123")
    assert exc_info.value.status_code == 401
