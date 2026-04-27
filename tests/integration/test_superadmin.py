import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.menu import MenuConfig
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def super_admin(db_session):
    # Create a placeholder tenant to satisfy the NOT NULL FK constraint on users.tenant_id
    slug = f"system-{uuid.uuid4().hex[:8]}"
    placeholder = Tenant(
        id=uuid.uuid4(),
        slug=slug,
        name="System",
    )
    db_session.add(placeholder)
    await db_session.commit()

    u = User(
        id=uuid.uuid4(),
        tenant_id=placeholder.id,
        email="super@example.com",
        name="Super Admin",
        password_hash="",
        role="super_admin",
        is_active=True,
        is_suspended=False,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    yield u
    await db_session.delete(u)
    await db_session.delete(placeholder)
    await db_session.commit()


@pytest.fixture
async def superadmin_client(db_session, super_admin):
    access_token = create_access_token(
        str(super_admin.id),
        str(super_admin.tenant_id),
        super_admin.role,
    )

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {access_token}"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


async def test_list_tenants_paginated(superadmin_client):
    resp = await superadmin_client.get("/superadmin/tenants")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data


async def test_create_tenant(superadmin_client, db_session):
    slug = f"new-tenant-{uuid.uuid4().hex[:8]}"
    resp = await superadmin_client.post("/superadmin/tenants", json={
        "slug": slug,
        "name": "New Tenant",
        "custom_domain": f"{slug}.example.com",
        "subdomain": slug,
        "plan": "pro",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == slug
    assert data["name"] == "New Tenant"
    assert data["plan"] == "pro"

    # Verify default menus seeded
    result = await db_session.execute(
        select(MenuConfig).where(MenuConfig.tenant_id == uuid.UUID(data["id"]))
    )
    menus = result.scalars().all()
    roles = {m.role for m in menus}
    assert roles == {"student", "manager", "admin"}

    # Cleanup
    t = await db_session.get(Tenant, uuid.UUID(data["id"]))
    if t:
        await db_session.delete(t)
        await db_session.commit()


async def test_update_tenant(superadmin_client, db_session):
    t = Tenant(
        id=uuid.uuid4(),
        slug=f"upd-{uuid.uuid4().hex[:8]}",
        name="Update Me",
    )
    db_session.add(t)
    await db_session.commit()

    resp = await superadmin_client.patch(f"/superadmin/tenants/{t.id}", json={
        "name": "Updated Name",
        "primary_color": "#123456",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"
    assert resp.json()["primary_color"] == "#123456"

    await db_session.delete(t)
    await db_session.commit()


async def test_update_tenant_not_found(superadmin_client):
    resp = await superadmin_client.patch(
        f"/superadmin/tenants/{uuid.uuid4()}", json={"name": "X"}
    )
    assert resp.status_code == 404


async def test_get_tenant_stats(superadmin_client, db_session):
    from app.models.product import Product

    t = Tenant(
        id=uuid.uuid4(),
        slug=f"stats-{uuid.uuid4().hex[:8]}",
        name="Stats Tenant",
    )
    db_session.add(t)
    await db_session.commit()

    u = await register_user(db_session, t.id, "user@stats.com", "User", "pw123")
    c = Course(id=uuid.uuid4(), tenant_id=t.id, title="Stats Course", slug="stats-course")
    p = Product(
        id=uuid.uuid4(),
        tenant_id=t.id,
        type="course",
        title="Stats Product",
        slug="stats-product",
    )
    db_session.add_all([c, p])
    await db_session.commit()

    e = Enrollment(
        id=uuid.uuid4(),
        tenant_id=t.id,
        user_id=u.id,
        product_id=p.id,
        status="active",
    )
    db_session.add(e)
    await db_session.commit()

    resp = await superadmin_client.get(f"/superadmin/tenants/{t.id}/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_users"] >= 1
    assert data["active_enrollments"] >= 1
    assert data["total_courses"] >= 1

    await db_session.delete(e)
    await db_session.delete(c)
    await db_session.delete(p)
    await db_session.delete(u)
    await db_session.delete(t)
    await db_session.commit()


async def test_unauthenticated_rejected(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
    ) as c:
        resp = await c.get("/superadmin/tenants")
    assert resp.status_code == 401
    app.dependency_overrides.clear()


async def test_non_super_admin_rejected(db_session):
    slug = f"foo-{uuid.uuid4().hex[:8]}"
    t = Tenant(id=uuid.uuid4(), slug=slug, name="Foo")
    db_session.add(t)
    await db_session.commit()
    u = await register_user(db_session, t.id, "admin@test.com", "Admin", "pw123", role="admin")

    access_token = create_access_token(str(u.id), str(t.id), "admin")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {access_token}"},
    ) as c:
        resp = await c.get("/superadmin/tenants")
    assert resp.status_code == 403
    app.dependency_overrides.clear()
