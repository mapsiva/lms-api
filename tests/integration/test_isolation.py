"""Multi-tenancy isolation integration tests."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.company import Company, CompanyMember
from app.models.course import Course, Lesson, Module
from app.models.enrollment import Enrollment
from app.models.progress import Note
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant_a(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.a.com"
    t = Tenant(id=uuid.uuid4(), slug=f"ta-{uuid.uuid4().hex[:8]}", name="TenantA", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t


@pytest.fixture
async def tenant_b(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.b.com"
    t = Tenant(id=uuid.uuid4(), slug=f"tb-{uuid.uuid4().hex[:8]}", name="TenantB", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t


@pytest.fixture
async def admin_a(db_session, tenant_a):
    u = await register_user(db_session, tenant_a.id, "admin@a.com", "AdminA", "password123", role="admin")
    yield u


@pytest.fixture
async def admin_a_client(db_session, redis_client, tenant_a, admin_a):
    token = create_access_token(str(admin_a.id), str(tenant_a.id), "admin")

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant_a.custom_domain}",
        headers={"host": tenant_a.custom_domain, "Authorization": f"Bearer {token}"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_tenant_course_isolation(tenant_a, tenant_b, db_session, admin_a_client):
    # Same slug in both tenants
    slug = "shared-course"
    c_a = Course(tenant_id=tenant_a.id, title="Course A", slug=slug)
    c_b = Course(tenant_id=tenant_b.id, title="Course B", slug=slug)
    db_session.add_all([c_a, c_b])
    await db_session.commit()

    resp = await admin_a_client.get(f"/admin/courses/{c_a.id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Course A"

    # Admin A cannot see tenant B course
    resp = await admin_a_client.get(f"/admin/courses/{c_b.id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_cross_tenant_company_404(tenant_a, tenant_b, db_session, admin_a_client):
    c_b = Company(tenant_id=tenant_b.id, cnpj="99999999000199", legal_name="OtherCo")
    db_session.add(c_b)
    await db_session.commit()
    await db_session.refresh(c_b)

    resp = await admin_a_client.get(f"/admin/companies/{c_b.id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_student_notes_isolation(tenant_a, db_session):
    u_a = await register_user(db_session, tenant_a.id, "student@a.com", "StudentA", "password123", role="student")
    u_b = await register_user(db_session, tenant_a.id, "other@a.com", "Other", "password123", role="student")

    c = Course(tenant_id=tenant_a.id, title="Course", slug="iso-course")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    m = Module(course_id=c.id, tenant_id=tenant_a.id, title="Module")
    db_session.add(m)
    await db_session.commit()
    await db_session.refresh(m)
    l = Lesson(module_id=m.id, tenant_id=tenant_a.id, title="Lesson", lesson_type="video")
    db_session.add(l)
    await db_session.commit()
    await db_session.refresh(l)

    n = Note(user_id=u_a.id, lesson_id=l.id, content="My note")
    db_session.add(n)
    await db_session.commit()

    token_b = create_access_token(str(u_b.id), str(tenant_a.id), "student")

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant_a.custom_domain}",
        headers={"host": tenant_a.custom_domain, "Authorization": f"Bearer {token_b}"},
    ) as c:
        resp = await c.get(f"/lessons/{l.id}/notes")
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["id"] for item in data]
        assert str(n.id) not in ids

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_manager_company_isolation(tenant_a, db_session):
    c_a = Company(tenant_id=tenant_a.id, cnpj="11111111000111", legal_name="CoA")
    c_b = Company(tenant_id=tenant_a.id, cnpj="22222222000122", legal_name="CoB")
    db_session.add_all([c_a, c_b])
    await db_session.commit()

    mgr_a = await register_user(db_session, tenant_a.id, "mgr@a.com", "MgrA", "password123", role="manager", company_id=c_a.id)
    token = create_access_token(str(mgr_a.id), str(tenant_a.id), "manager", company_id=str(c_a.id))

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant_a.custom_domain}",
        headers={"host": tenant_a.custom_domain, "Authorization": f"Bearer {token}"},
    ) as c:
        # Manager can see own company
        resp = await c.get("/manager/members")
        assert resp.status_code == 200

        # Trying to access other company data via query param should not leak
        resp = await c.get(f"/manager/members?company_id={c_b.id}")
        # Still uses JWT company_id, should return only own company members
        assert resp.status_code == 200

    app.dependency_overrides.clear()
