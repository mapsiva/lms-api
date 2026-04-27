import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import get_current_user, get_current_tenant, require_admin
from app.core.security import create_access_token
from app.models.tenant import Tenant
from app.models.user import User


def _make_tenant(**kwargs) -> MagicMock:
    defaults = dict(id=uuid.uuid4(), slug="acme", name="Acme", custom_domain="acme.com", subdomain=None, plan="pro", features=None)
    defaults.update(kwargs)
    m = MagicMock(spec=Tenant)
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


def _make_user(**kwargs) -> MagicMock:
    tenant_id = kwargs.pop("tenant_id", uuid.uuid4())
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="alice@example.com",
        name="Alice",
        role="student",
        company_id=None,
        is_active=True,
        is_suspended=False,
        password_hash=None,
        avatar_url=None,
        bio=None,
        last_seen_at=None,
    )
    defaults.update(kwargs)
    m = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


# ── get_current_tenant ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_current_tenant_found_by_custom_domain():
    tenant = _make_tenant()
    request = MagicMock()
    request.headers = {"host": "acme.com"}
    # Ensure state.tenant is not set so middleware path isn't triggered
    del request.state.tenant

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    result = MagicMock()
    result.scalar_one_or_none.return_value = tenant
    db = AsyncMock()
    db.execute.return_value = result

    with patch("app.core.dependencies.get_redis", return_value=mock_redis):
        found = await get_current_tenant(request, db)
    assert found.slug == "acme"


@pytest.mark.asyncio
async def test_get_current_tenant_not_found():
    request = MagicMock()
    request.headers = {"host": "unknown.com"}
    del request.state.tenant

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute.return_value = result

    with patch("app.core.dependencies.get_redis", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_tenant(request, db)
    assert exc_info.value.status_code == 404


# ── get_current_user ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_current_user_valid():
    tenant = _make_tenant()
    user = _make_user(tenant_id=tenant.id)
    token = create_access_token(str(user.id), str(tenant.id), "student")
    credentials = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = AsyncMock()
    db.execute.return_value = result

    found = await get_current_user(tenant=tenant, credentials=credentials, db=db)
    assert found.id == user.id


@pytest.mark.asyncio
async def test_get_current_user_no_credentials():
    tenant = _make_tenant()
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(tenant=tenant, credentials=None, db=db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_wrong_tenant():
    tenant = _make_tenant()
    other_tenant_id = str(uuid.uuid4())
    token = create_access_token("user-id", other_tenant_id, "student")
    credentials = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(tenant=tenant, credentials=credentials, db=db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_suspended():
    tenant = _make_tenant()
    user = _make_user(tenant_id=tenant.id, is_suspended=True)
    token = create_access_token(str(user.id), str(tenant.id), "student")
    credentials = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = AsyncMock()
    db.execute.return_value = result

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(tenant=tenant, credentials=credentials, db=db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_not_found_in_db():
    tenant = _make_tenant()
    user_id = uuid.uuid4()
    token = create_access_token(str(user_id), str(tenant.id), "student")
    credentials = HTTPAuthorizationCredentials(scheme="bearer", credentials=token)

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute.return_value = result

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(tenant=tenant, credentials=credentials, db=db)
    assert exc_info.value.status_code == 401


# ── require_admin ────────────────────────────────────────────────────────────

def test_require_admin_passes_for_admin():
    user = _make_user(role="admin")
    result = require_admin(user=user)
    assert result is user


def test_require_admin_passes_for_super_admin():
    user = _make_user(role="super_admin")
    result = require_admin(user=user)
    assert result is user


def test_require_admin_blocks_student():
    user = _make_user(role="student")
    with pytest.raises(HTTPException) as exc_info:
        require_admin(user=user)
    assert exc_info.value.status_code == 403


def test_require_admin_blocks_manager():
    user = _make_user(role="manager")
    with pytest.raises(HTTPException) as exc_info:
        require_admin(user=user)
    assert exc_info.value.status_code == 403
