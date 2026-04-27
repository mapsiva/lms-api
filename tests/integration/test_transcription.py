"""Integration tests for transcription workflow."""
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
        slug=f"tr-{uuid.uuid4().hex[:8]}",
        name="TranscriptionTest",
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
    u = await register_user(db_session, tenant.id, "admin@trans.com", "Admin", "password123", role="admin")
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
async def sample_lesson(db_session, tenant):
    course = Course(tenant_id=tenant.id, title="Course", slug="course")
    db_session.add(course)
    await db_session.commit()
    await db_session.refresh(course)
    module = Module(tenant_id=tenant.id, course_id=course.id, title="Module")
    db_session.add(module)
    await db_session.commit()
    await db_session.refresh(module)
    lesson = Lesson(
        tenant_id=tenant.id,
        module_id=module.id,
        title="Lesson",
        video_provider="bunny",
        video_external_id="vid-123",
    )
    db_session.add(lesson)
    await db_session.commit()
    await db_session.refresh(lesson)
    yield lesson
    await db_session.delete(lesson)
    await db_session.delete(module)
    await db_session.delete(course)
    await db_session.commit()


@pytest.mark.asyncio
async def test_trigger_transcription(admin_client, sample_lesson):
    with patch("app.routers.admin.courses.celery_app.send_task") as mock_send:
        resp = await admin_client.post(f"/admin/lessons/{sample_lesson.id}/transcribe")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_get_transcript_not_ready(admin_client, sample_lesson):
    resp = await admin_client.get(f"/admin/lessons/{sample_lesson.id}/transcript")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "not_ready"


@pytest.mark.asyncio
async def test_get_transcript_ready(admin_client, sample_lesson, db_session):
    sample_lesson.transcript_text = {"full_text": "hello", "words": []}
    await db_session.commit()
    resp = await admin_client.get(f"/admin/lessons/{sample_lesson.id}/transcript")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["transcript"]["full_text"] == "hello"


@pytest.mark.asyncio
async def test_trigger_summary_no_transcript(admin_client, sample_lesson):
    resp = await admin_client.post(f"/admin/lessons/{sample_lesson.id}/summarize")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_trigger_summary(admin_client, sample_lesson, db_session):
    sample_lesson.transcript_text = {"full_text": "hello world", "words": []}
    await db_session.commit()
    with patch("app.routers.admin.courses.celery_app.send_task") as mock_send:
        resp = await admin_client.post(f"/admin/lessons/{sample_lesson.id}/summarize")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_transcription_callback(admin_client, sample_lesson, db_session):
    sample_lesson.transcript_text = None
    await db_session.commit()

    from app.core.redis_client import get_redis
    redis = get_redis()
    if redis:
        await redis.hset("transcription:pending", str(sample_lesson.id), "t-123")

    with patch("app.integrations.assemblyai.AssemblyAIClient.get_full_transcript", new_callable=AsyncMock) as mock_full:
        mock_full.return_value = {"full_text": "callback text", "words": [{"text": "hi", "start_ms": 0, "end_ms": 100}]}
        resp = await admin_client.post("/internal/transcription-callback", json={"transcript_id": "t-123"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["lesson_id"] == str(sample_lesson.id)

    # Verify DB state
    await db_session.refresh(sample_lesson)
    assert sample_lesson.transcript_text is not None
    assert sample_lesson.transcript_text["full_text"] == "callback text"
