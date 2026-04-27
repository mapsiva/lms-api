import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.course import Course, Lesson, Module
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(
        id=uuid.uuid4(),
        slug=f"ac-{uuid.uuid4().hex[:8]}",
        name="AdminCoursesTest",
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
    u = await register_user(db_session, tenant.id, "admin@courses.com", "Admin", "password123", role="admin")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def student_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "student@courses.com", "Student", "password123", role="student")
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


@pytest.fixture
async def course(db_session, tenant):
    c = Course(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Test Course",
        slug=f"test-course-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    yield c
    obj = await db_session.get(Course, c.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def module(db_session, tenant, course):
    m = Module(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        course_id=course.id,
        title="Test Module",
        order_index=0,
    )
    db_session.add(m)
    await db_session.commit()
    await db_session.refresh(m)
    yield m
    obj = await db_session.get(Module, m.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


# ── POST /admin/courses ───────────────────────────────────────────────────────

async def test_create_course_returns_201(admin_client, tenant):
    resp = await admin_client.post("/admin/courses", json={"title": "My First Course"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My First Course"
    assert data["slug"] == "my-first-course"
    assert data["tenant_id"] == str(tenant.id)
    assert data["status"] == "draft"


async def test_create_course_custom_slug(admin_client, tenant):
    resp = await admin_client.post("/admin/courses", json={"title": "Test", "slug": "custom-slug"})
    assert resp.status_code == 201
    assert resp.json()["slug"] == "custom-slug"


async def test_create_course_slug_auto_deduplicates(admin_client, tenant, course):
    resp = await admin_client.post("/admin/courses", json={"title": course.title, "slug": course.slug})
    assert resp.status_code == 201
    assert resp.json()["slug"] != course.slug


async def test_create_course_student_forbidden(student_client):
    resp = await student_client.post("/admin/courses", json={"title": "Should fail"})
    assert resp.status_code == 403


async def test_create_course_no_auth(db_session, redis_client, tenant):
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant.custom_domain}",
        headers={"host": tenant.custom_domain},
    ) as c:
        resp = await c.post("/admin/courses", json={"title": "No auth"})
    app.dependency_overrides.clear()
    assert resp.status_code == 401


# ── GET /admin/courses ────────────────────────────────────────────────────────

async def test_list_courses_returns_only_tenant_courses(admin_client, tenant, course, db_session):
    other_tenant = Tenant(
        id=uuid.uuid4(),
        slug=f"other-{uuid.uuid4().hex[:6]}",
        name="OtherTenant",
        custom_domain=f"{uuid.uuid4().hex[:8]}.example.com",
    )
    db_session.add(other_tenant)
    await db_session.flush()
    other_course = Course(
        id=uuid.uuid4(),
        tenant_id=other_tenant.id,
        title="Other Course",
        slug="other-course",
    )
    db_session.add(other_course)
    await db_session.commit()

    resp = await admin_client.get("/admin/courses")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert str(course.id) in ids
    assert str(other_course.id) not in ids

    await db_session.delete(other_course)
    await db_session.delete(other_tenant)
    await db_session.commit()


# ── PATCH /admin/courses/{id} ─────────────────────────────────────────────────

async def test_update_course(admin_client, course):
    resp = await admin_client.patch(f"/admin/courses/{course.id}", json={
        "title": "Updated Title",
        "status": "published",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "published"


async def test_update_course_wrong_tenant_returns_404(db_session, redis_client, course):
    other_tenant = Tenant(
        id=uuid.uuid4(),
        slug=f"ot-{uuid.uuid4().hex[:6]}",
        name="OT",
        custom_domain=f"{uuid.uuid4().hex[:8]}.example.com",
    )
    db_session.add(other_tenant)
    other_admin = await register_user(db_session, other_tenant.id, "adm@ot.com", "Adm", "pass1234", role="admin")
    await db_session.commit()

    token = create_access_token(str(other_admin.id), str(other_tenant.id), "admin")

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{other_tenant.custom_domain}",
        headers={"host": other_tenant.custom_domain, "Authorization": f"Bearer {token}"},
    ) as c:
        resp = await c.patch(f"/admin/courses/{course.id}", json={"title": "Hacked"})
    app.dependency_overrides.clear()

    assert resp.status_code == 404

    await db_session.delete(other_admin)
    await db_session.delete(other_tenant)
    await db_session.commit()


# ── POST /admin/courses/{id}/modules ─────────────────────────────────────────

async def test_create_module(admin_client, course, tenant):
    resp = await admin_client.post(f"/admin/courses/{course.id}/modules", json={
        "title": "Module 1",
        "order_index": 0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Module 1"
    assert data["course_id"] == str(course.id)
    assert data["tenant_id"] == str(tenant.id)


async def test_create_module_wrong_course_returns_404(admin_client):
    resp = await admin_client.post(f"/admin/courses/{uuid.uuid4()}/modules", json={"title": "M"})
    assert resp.status_code == 404


# ── PATCH /admin/modules/{id} ─────────────────────────────────────────────────

async def test_update_module(admin_client, module):
    resp = await admin_client.patch(f"/admin/modules/{module.id}", json={"title": "Updated Module"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Module"


# ── POST /admin/modules/{id}/lessons ─────────────────────────────────────────

async def test_create_lesson(admin_client, module, tenant):
    resp = await admin_client.post(f"/admin/modules/{module.id}/lessons", json={
        "title": "Lesson 1",
        "lesson_type": "video",
        "video_provider": "bunny",
        "video_external_id": "abc-123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Lesson 1"
    assert data["video_provider"] == "bunny"
    assert data["video_external_id"] == "abc-123"
    assert data["module_id"] == str(module.id)


# ── PATCH /admin/lessons/{id} ─────────────────────────────────────────────────

async def test_update_lesson(admin_client, db_session, module, tenant):
    lesson = Lesson(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        module_id=module.id,
        title="Original",
        lesson_type="video",
        order_index=0,
    )
    db_session.add(lesson)
    await db_session.commit()

    resp = await admin_client.patch(f"/admin/lessons/{lesson.id}", json={"title": "Updated Lesson"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Lesson"

    await db_session.delete(lesson)
    await db_session.commit()


# ── DELETE /admin/lessons/{id} ────────────────────────────────────────────────

async def test_delete_lesson(admin_client, db_session, module, tenant):
    lesson = Lesson(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        module_id=module.id,
        title="To Delete",
        lesson_type="text",
        order_index=0,
    )
    db_session.add(lesson)
    await db_session.commit()

    resp = await admin_client.delete(f"/admin/lessons/{lesson.id}")
    assert resp.status_code == 204

    deleted = await db_session.get(Lesson, lesson.id)
    assert deleted is None


async def test_delete_lesson_wrong_tenant_returns_404(admin_client):
    resp = await admin_client.delete(f"/admin/lessons/{uuid.uuid4()}")
    assert resp.status_code == 404


# ── PATCH /admin/modules/{id}/reorder ────────────────────────────────────────

async def test_reorder_lessons(admin_client, db_session, module, tenant):
    lessons = []
    for i in range(3):
        l = Lesson(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            module_id=module.id,
            title=f"Lesson {i}",
            lesson_type="text",
            order_index=i,
        )
        db_session.add(l)
        lessons.append(l)
    await db_session.commit()

    reversed_ids = [str(l.id) for l in reversed(lessons)]
    resp = await admin_client.patch(f"/admin/modules/{module.id}/reorder", json={"lesson_ids": reversed_ids})
    assert resp.status_code == 200
    assert resp.json()["reordered"] == 3

    for i, lesson in enumerate(reversed(lessons)):
        await db_session.refresh(lesson)
        assert lesson.order_index == i

    for l in lessons:
        await db_session.delete(l)
    await db_session.commit()


# ── POST /admin/modules/{id}/lessons/bulk-import ─────────────────────────────

async def test_bulk_import_lessons(admin_client, module, tenant):
    mock_videos = [
        MagicMock(video_id="v1", title="Intro", duration_seconds=60, thumbnail_url=None),
        MagicMock(video_id="v2", title="Main", duration_seconds=300, thumbnail_url="thumb.jpg"),
    ]

    with patch(
        "app.routers.admin.courses.BunnyVideoProvider.list_library_folder",
        new_callable=AsyncMock,
        return_value=mock_videos,
    ):
        resp = await admin_client.post(
            f"/admin/modules/{module.id}/lessons/bulk-import",
            json={"folder": "my-folder"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2
    assert data[0]["video_external_id"] == "v1"
    assert data[0]["video_provider"] == "bunny"
    assert data[1]["video_external_id"] == "v2"
    assert data[1]["duration_seconds"] == 300
