import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.course import Course
from app.models.product import Product, ProductCourse
from app.models.tenant import Tenant


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(
        id=uuid.uuid4(),
        slug=f"cat-{uuid.uuid4().hex[:8]}",
        name="CatalogTest",
        custom_domain=domain,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def catalog_client(db_session, tenant):
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


async def test_list_catalog_returns_published_public(db_session, tenant, catalog_client):
    p1 = Product(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        type="course",
        title="Public Course",
        slug="public-course",
        status="published",
        visibility="public",
    )
    p2 = Product(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        type="course",
        title="Unlisted Course",
        slug="unlisted-course",
        status="published",
        visibility="unlisted",
    )
    p3 = Product(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        type="course",
        title="Draft Course",
        slug="draft-course",
        status="draft",
        visibility="public",
    )
    db_session.add_all([p1, p2, p3])
    await db_session.commit()

    resp = await catalog_client.get("/catalog")
    assert resp.status_code == 200
    data = resp.json()
    slugs = {item["slug"] for item in data}
    assert "public-course" in slugs
    assert "unlisted-course" not in slugs
    assert "draft-course" not in slugs


async def test_list_catalog_no_products_returns_empty(db_session, tenant, catalog_client):
    resp = await catalog_client.get("/catalog")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_catalog_product_by_slug(db_session, tenant, catalog_client):
    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        type="course",
        title="Amazing Course",
        slug="amazing-course",
        status="published",
        visibility="public",
    )
    db_session.add(p)
    await db_session.commit()

    resp = await catalog_client.get("/catalog/amazing-course")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "amazing-course"
    assert data["title"] == "Amazing Course"
    assert data["courses"] == []


async def test_get_catalog_bundle_includes_courses(db_session, tenant, catalog_client):
    c1 = Course(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Course 1",
        slug="course-1",
        thumbnail_url="https://example.com/1.jpg",
    )
    c2 = Course(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Course 2",
        slug="course-2",
    )
    db_session.add_all([c1, c2])
    await db_session.commit()

    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        type="bundle",
        title="Best Bundle",
        slug="best-bundle",
        status="published",
        visibility="public",
    )
    db_session.add(p)
    await db_session.commit()

    pc1 = ProductCourse(product_id=p.id, course_id=c1.id, order_index=0)
    pc2 = ProductCourse(product_id=p.id, course_id=c2.id, order_index=1)
    db_session.add_all([pc1, pc2])
    await db_session.commit()

    resp = await catalog_client.get("/catalog/best-bundle")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "bundle"
    assert len(data["courses"]) == 2
    assert data["courses"][0]["title"] == "Course 1"
    assert data["courses"][0]["thumbnail_url"] == "https://example.com/1.jpg"
    assert data["courses"][1]["title"] == "Course 2"


async def test_get_catalog_not_found(db_session, tenant, catalog_client):
    resp = await catalog_client.get("/catalog/nonexistent")
    assert resp.status_code == 404
