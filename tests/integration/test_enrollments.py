"""Integration tests for enrollment admin and student endpoints."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"en-{uuid.uuid4().hex[:8]}", name="EnrollTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def admin_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "admin@enroll.com", "Admin", "password123", role="admin")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def student_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "student@enroll.com", "Student", "password123", role="student")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def admin_client(db_session, redis_client, tenant, admin_user):
    token = create_access_token(str(admin_user.id), str(tenant.id), "admin")

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
async def test_admin_list_enrollments(admin_client, tenant, db_session):
    resp = await admin_client.get("/admin/enrollments")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_admin_create_enrollment(admin_client, tenant, student_user, db_session):
    p = Product(tenant_id=tenant.id, type="course", title="Test Product", slug=f"prod-{uuid.uuid4().hex[:8]}")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    resp = await admin_client.post("/admin/enrollments", json={"user_id": str(student_user.id), "product_id": str(p.id)})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_admin_update_enrollment(admin_client, tenant, student_user, db_session):
    p = Product(tenant_id=tenant.id, type="course", title="Update Prod", slug=f"up-{uuid.uuid4().hex[:8]}")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    e = Enrollment(tenant_id=tenant.id, user_id=student_user.id, product_id=p.id, status="active")
    db_session.add(e)
    await db_session.commit()
    await db_session.refresh(e)

    resp = await admin_client.patch(f"/admin/enrollments/{e.id}", json={"status": "suspended"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "suspended"


@pytest.mark.asyncio
async def test_admin_delete_enrollment(admin_client, tenant, student_user, db_session):
    p = Product(tenant_id=tenant.id, type="course", title="Del Prod", slug=f"dl-{uuid.uuid4().hex[:8]}")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    e = Enrollment(tenant_id=tenant.id, user_id=student_user.id, product_id=p.id, status="active")
    db_session.add(e)
    await db_session.commit()
    await db_session.refresh(e)

    resp = await admin_client.delete(f"/admin/enrollments/{e.id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_student_my_enrollments(student_client, tenant, student_user, db_session):
    p = Product(tenant_id=tenant.id, type="course", title="My Prod", slug=f"my-{uuid.uuid4().hex[:8]}")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    c = Course(tenant_id=tenant.id, title="My Course", slug=f"mc-{uuid.uuid4().hex[:8]}")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    e = Enrollment(tenant_id=tenant.id, user_id=student_user.id, product_id=p.id, status="active")
    db_session.add(e)
    await db_session.commit()

    resp = await student_client.get("/users/me/enrollments")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
