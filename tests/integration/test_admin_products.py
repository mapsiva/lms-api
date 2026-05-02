import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.course import Course
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(
        id=uuid.uuid4(),
        slug=f"prod-{uuid.uuid4().hex[:8]}",
        name="ProductsTest",
        custom_domain=domain,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def admin_user(db_session, tenant):
    u = await register_user(
        db_session, tenant.id, "admin@products.com", "Admin", "password123", role="admin"
    )
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


@pytest.mark.asyncio
async def test_admin_products_crud_and_gateway_ids(admin_client, tenant, db_session):
    course = Course(
        tenant_id=tenant.id,
        title="Admin Course",
        slug=f"admin-course-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)

    resp = await admin_client.post(
        "/admin/products",
        json={
            "type": "bundle",
            "title": "Bundle",
            "slug": "bundle",
            "gateway_ids": {"stripe": "price_123"},
            "courses": [{"course_id": str(course.id), "order_index": 0}],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["gateway_ids"]["stripe"] == "price_123"
    assert data["courses"][0]["course_id"] == str(course.id)

    product_id = data["id"]
    resp = await admin_client.patch(
        f"/admin/products/{product_id}",
        json={"title": "Bundle Pro", "gateway_ids": {"hotmart": "product_abc"}},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Bundle Pro"
    assert resp.json()["gateway_ids"]["hotmart"] == "product_abc"

    resp = await admin_client.patch(
        f"/admin/products/{product_id}/status",
        json={"status": "published"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"

    resp = await admin_client.get("/admin/products?status=published")
    assert resp.status_code == 200
    assert any(item["id"] == product_id for item in resp.json()["items"])
