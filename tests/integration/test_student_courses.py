import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.course import Course, Lesson, Module
from app.models.enrollment import Enrollment
from app.models.product import Product, ProductCourse
from app.models.progress import LessonProgress
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(
        id=uuid.uuid4(),
        slug=f"sc-{uuid.uuid4().hex[:8]}",
        name="StudentCoursesTest",
        custom_domain=domain,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def student_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "student@sc.com", "Student", "password123", role="student")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def other_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "other@sc.com", "Other", "password123", role="student")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def course(db_session, tenant):
    c = Course(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        title="Test Course",
        slug=f"test-course-{uuid.uuid4().hex[:6]}",
        status="published",
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
async def product(db_session, tenant, course):
    p = Product(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        type="course",
        title="Test Product",
        slug=f"test-product-{uuid.uuid4().hex[:6]}",
        status="published",
    )
    db_session.add(p)
    await db_session.flush()
    pc = ProductCourse(product_id=p.id, course_id=course.id, order_index=0)
    db_session.add(pc)
    await db_session.commit()
    yield p
    obj = await db_session.get(Product, p.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def enrollment(db_session, tenant, student_user, product):
    e = Enrollment(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        user_id=student_user.id,
        product_id=product.id,
        status="active",
    )
    db_session.add(e)
    await db_session.commit()
    await db_session.refresh(e)
    yield e
    obj = await db_session.get(Enrollment, e.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def module(db_session, tenant, course):
    m = Module(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        course_id=course.id,
        title="Module 1",
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


@pytest.fixture
async def lesson(db_session, tenant, module):
    l = Lesson(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        module_id=module.id,
        title="Lesson 1",
        lesson_type="video",
        order_index=0,
        video_provider="bunny",
        video_external_id="vid-abc",
        drip_type="immediate",
    )
    db_session.add(l)
    await db_session.commit()
    await db_session.refresh(l)
    yield l
    obj = await db_session.get(Lesson, l.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


def _make_client(db_session, tenant, user, role):
    token = create_access_token(str(user.id), str(tenant.id), role)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant.custom_domain}",
        headers={"host": tenant.custom_domain, "Authorization": f"Bearer {token}"},
    )


# ── GET /courses ───────────────────────────────────────────────────────────────

async def test_list_courses_enrolled_user(db_session, redis_client, tenant, student_user, course, enrollment):
    async with _make_client(db_session, tenant, student_user, "student") as c:
        resp = await c.get("/courses")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()]
    assert str(course.id) in ids


async def test_list_courses_not_enrolled_returns_empty(db_session, redis_client, tenant, other_user):
    async with _make_client(db_session, tenant, other_user, "student") as c:
        resp = await c.get("/courses")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_courses_no_auth(db_session, redis_client, tenant):
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant.custom_domain}",
        headers={"host": tenant.custom_domain},
    ) as c:
        resp = await c.get("/courses")
    app.dependency_overrides.clear()
    assert resp.status_code == 401


# ── GET /courses/{slug} ────────────────────────────────────────────────────────

async def test_get_course_detail_enrolled(db_session, redis_client, tenant, student_user, course, module, lesson, enrollment):
    async with _make_client(db_session, tenant, student_user, "student") as c:
        resp = await c.get(f"/courses/{course.slug}")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == course.slug
    assert len(data["modules"]) == 1
    assert data["modules"][0]["lessons"][0]["id"] == str(lesson.id)


async def test_get_course_not_enrolled_returns_403(db_session, redis_client, tenant, other_user, course, module, lesson):
    async with _make_client(db_session, tenant, other_user, "student") as c:
        resp = await c.get(f"/courses/{course.slug}")
    app.dependency_overrides.clear()
    assert resp.status_code == 403


async def test_get_free_course_no_enrollment(db_session, redis_client, tenant, other_user, course):
    course.is_free = True
    await db_session.commit()
    async with _make_client(db_session, tenant, other_user, "student") as c:
        resp = await c.get(f"/courses/{course.slug}")
    app.dependency_overrides.clear()
    course.is_free = False
    await db_session.commit()
    assert resp.status_code == 200


# ── GET /lessons/{id} ─────────────────────────────────────────────────────────

async def test_get_lesson_enrolled_bunny_signed_url(db_session, redis_client, tenant, student_user, lesson, enrollment):
    with patch(
        "app.routers.courses.BunnyVideoProvider.get_playback_url",
        new_callable=AsyncMock,
        return_value="https://cdn.example.com/vid-abc/playlist.m3u8?token=abc&expires=999",
    ):
        async with _make_client(db_session, tenant, student_user, "student") as c:
            resp = await c.get(f"/lessons/{lesson.id}")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert data["drip_accessible"] is True
    assert "token=" in data["playback_url"]
    assert data["video_external_id"] == "vid-abc"


async def test_get_lesson_not_enrolled_returns_403(db_session, redis_client, tenant, other_user, lesson):
    async with _make_client(db_session, tenant, other_user, "student") as c:
        resp = await c.get(f"/lessons/{lesson.id}")
    app.dependency_overrides.clear()
    assert resp.status_code == 403


async def test_get_free_preview_lesson_no_enrollment(db_session, redis_client, tenant, other_user, lesson):
    lesson.is_free_preview = True
    await db_session.commit()
    with patch(
        "app.routers.courses.BunnyVideoProvider.get_playback_url",
        new_callable=AsyncMock,
        return_value="https://cdn.example.com/signed",
    ):
        async with _make_client(db_session, tenant, other_user, "student") as c:
            resp = await c.get(f"/lessons/{lesson.id}")
    app.dependency_overrides.clear()
    lesson.is_free_preview = False
    await db_session.commit()
    assert resp.status_code == 200


async def test_drip_fixed_date_future_not_accessible(db_session, redis_client, tenant, student_user, lesson, enrollment):
    lesson.drip_type = "fixed_date"
    lesson.drip_value = {"date": "2099-01-01T00:00:00"}
    await db_session.commit()
    async with _make_client(db_session, tenant, student_user, "student") as c:
        resp = await c.get(f"/lessons/{lesson.id}")
    app.dependency_overrides.clear()
    lesson.drip_type = "immediate"
    lesson.drip_value = None
    await db_session.commit()
    assert resp.status_code == 200
    assert resp.json()["drip_accessible"] is False


async def test_drip_days_after_enrollment_not_accessible(db_session, redis_client, tenant, student_user, lesson, enrollment):
    lesson.drip_type = "days_after_enrollment"
    lesson.drip_value = {"days": 999}
    await db_session.commit()
    async with _make_client(db_session, tenant, student_user, "student") as c:
        resp = await c.get(f"/lessons/{lesson.id}")
    app.dependency_overrides.clear()
    lesson.drip_type = "immediate"
    lesson.drip_value = None
    await db_session.commit()
    assert resp.status_code == 200
    assert resp.json()["drip_accessible"] is False


# ── POST /lessons/{id}/progress ────────────────────────────────────────────────

async def test_update_progress_creates_record(db_session, redis_client, tenant, student_user, lesson, enrollment):
    async with _make_client(db_session, tenant, student_user, "student") as c:
        resp = await c.post(f"/lessons/{lesson.id}/progress", json={"watch_seconds": 120, "completed": False})
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert data["watch_seconds"] == 120
    assert data["completed_at"] is None


async def test_update_progress_mark_complete(db_session, redis_client, tenant, student_user, lesson, enrollment):
    async with _make_client(db_session, tenant, student_user, "student") as c:
        resp = await c.post(f"/lessons/{lesson.id}/progress", json={"watch_seconds": 300, "completed": True})
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is not None


async def test_update_progress_upserts(db_session, redis_client, tenant, student_user, lesson, enrollment):
    async with _make_client(db_session, tenant, student_user, "student") as c:
        await c.post(f"/lessons/{lesson.id}/progress", json={"watch_seconds": 60})
        resp = await c.post(f"/lessons/{lesson.id}/progress", json={"watch_seconds": 200})
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["watch_seconds"] == 200


# ── GET /courses/{id}/continue ─────────────────────────────────────────────────

async def test_continue_course_no_progress(db_session, redis_client, tenant, student_user, course, enrollment):
    async with _make_client(db_session, tenant, student_user, "student") as c:
        resp = await c.get(f"/courses/{course.id}/continue")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["lesson_id"] is None


async def test_continue_course_returns_last_lesson(db_session, redis_client, tenant, student_user, course, module, lesson, enrollment):
    lp = LessonProgress(
        user_id=student_user.id,
        lesson_id=lesson.id,
        watch_seconds=60,
        last_watched_at=datetime.now(timezone.utc),
    )
    db_session.add(lp)
    await db_session.commit()

    async with _make_client(db_session, tenant, student_user, "student") as c:
        resp = await c.get(f"/courses/{course.id}/continue")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["lesson_id"] == str(lesson.id)

    await db_session.delete(lp)
    await db_session.commit()
