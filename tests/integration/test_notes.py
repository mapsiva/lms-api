import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.course import Course, Lesson, Module
from app.models.progress import Note
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(
        id=uuid.uuid4(),
        slug=f"nt-{uuid.uuid4().hex[:8]}",
        name="NotesTest",
        custom_domain=domain,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def user_a(db_session, tenant):
    u = await register_user(db_session, tenant.id, "usera@notes.com", "UserA", "password123")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def user_b(db_session, tenant):
    u = await register_user(db_session, tenant.id, "userb@notes.com", "UserB", "password123")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def lesson(db_session, tenant):
    c = Course(
        id=uuid.uuid4(), tenant_id=tenant.id,
        title="C", slug=f"c-{uuid.uuid4().hex[:6]}", status="published",
    )
    db_session.add(c)
    await db_session.flush()
    m = Module(id=uuid.uuid4(), tenant_id=tenant.id, course_id=c.id, title="M", order_index=0)
    db_session.add(m)
    await db_session.flush()
    l = Lesson(
        id=uuid.uuid4(), tenant_id=tenant.id, module_id=m.id,
        title="L", lesson_type="video", order_index=0,
    )
    db_session.add(l)
    await db_session.commit()
    await db_session.refresh(l)
    yield l
    await db_session.delete(l)
    await db_session.delete(m)
    await db_session.delete(c)
    await db_session.commit()


def _client(db_session, tenant, user, role="student"):
    token = create_access_token(str(user.id), str(tenant.id), role)

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{tenant.custom_domain}",
        headers={"host": tenant.custom_domain, "Authorization": f"Bearer {token}"},
    )


# ── POST /lessons/{id}/notes ──────────────────────────────────────────────────

async def test_create_note(db_session, redis_client, tenant, user_a, lesson):
    async with _client(db_session, tenant, user_a) as c:
        resp = await c.post(f"/lessons/{lesson.id}/notes", json={
            "content": "My note",
            "video_timestamp_seconds": 42,
        })
    app.dependency_overrides.clear()
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "My note"
    assert data["video_timestamp_seconds"] == 42
    assert data["user_id"] == str(user_a.id)
    assert data["lesson_id"] == str(lesson.id)


async def test_create_note_unknown_lesson_returns_404(db_session, redis_client, tenant, user_a):
    async with _client(db_session, tenant, user_a) as c:
        resp = await c.post(f"/lessons/{uuid.uuid4()}/notes", json={"content": "x"})
    app.dependency_overrides.clear()
    assert resp.status_code == 404


# ── GET /lessons/{id}/notes ────────────────────────────────────────────────────

async def test_list_notes_only_own(db_session, redis_client, tenant, user_a, user_b, lesson):
    note_a = Note(user_id=user_a.id, lesson_id=lesson.id, content="A note")
    note_b = Note(user_id=user_b.id, lesson_id=lesson.id, content="B note")
    db_session.add(note_a)
    db_session.add(note_b)
    await db_session.commit()

    async with _client(db_session, tenant, user_a) as c:
        resp = await c.get(f"/lessons/{lesson.id}/notes")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    contents = [n["content"] for n in resp.json()]
    assert "A note" in contents
    assert "B note" not in contents

    await db_session.delete(note_a)
    await db_session.delete(note_b)
    await db_session.commit()


# ── PATCH /notes/{id} ─────────────────────────────────────────────────────────

async def test_update_own_note(db_session, redis_client, tenant, user_a, lesson):
    note = Note(user_id=user_a.id, lesson_id=lesson.id, content="Original")
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)

    async with _client(db_session, tenant, user_a) as c:
        resp = await c.patch(f"/notes/{note.id}", json={"content": "Updated"})
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["content"] == "Updated"

    await db_session.delete(note)
    await db_session.commit()


async def test_update_other_user_note_returns_404(db_session, redis_client, tenant, user_a, user_b, lesson):
    note = Note(user_id=user_b.id, lesson_id=lesson.id, content="B's note")
    db_session.add(note)
    await db_session.commit()

    async with _client(db_session, tenant, user_a) as c:
        resp = await c.patch(f"/notes/{note.id}", json={"content": "Hijacked"})
    app.dependency_overrides.clear()
    assert resp.status_code == 404

    await db_session.delete(note)
    await db_session.commit()


# ── DELETE /notes/{id} ────────────────────────────────────────────────────────

async def test_delete_own_note(db_session, redis_client, tenant, user_a, lesson):
    note = Note(user_id=user_a.id, lesson_id=lesson.id, content="To delete")
    db_session.add(note)
    await db_session.commit()
    note_id = note.id

    async with _client(db_session, tenant, user_a) as c:
        resp = await c.delete(f"/notes/{note_id}")
    app.dependency_overrides.clear()
    assert resp.status_code == 204

    deleted = await db_session.get(Note, note_id)
    assert deleted is None


async def test_delete_other_user_note_returns_404(db_session, redis_client, tenant, user_a, user_b, lesson):
    note = Note(user_id=user_b.id, lesson_id=lesson.id, content="B's")
    db_session.add(note)
    await db_session.commit()

    async with _client(db_session, tenant, user_a) as c:
        resp = await c.delete(f"/notes/{note.id}")
    app.dependency_overrides.clear()
    assert resp.status_code == 404

    await db_session.delete(note)
    await db_session.commit()
