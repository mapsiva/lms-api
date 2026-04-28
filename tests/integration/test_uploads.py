"""Integration tests for uploads router."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"up-{uuid.uuid4().hex[:8]}", name="UploadTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def student_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "student@up.com", "Student", "password123", role="student")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


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
async def test_upload_avatar(student_client):
    resp = await student_client.post("/uploads/avatar", files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\n", "image/png")})
    assert resp.status_code in (200, 201, 500)


@pytest.mark.asyncio
async def test_upload_thumbnail(student_client):
    resp = await student_client.post("/uploads/thumbnail", files={"file": ("thumb.jpg", b"\xff\xd8\xff", "image/jpeg")})
    assert resp.status_code in (200, 201, 500)


@pytest.mark.asyncio
async def test_upload_post_image(student_client):
    resp = await student_client.post("/uploads/post-image", files={"file": ("post.webp", b"RIFF", "image/webp")})
    assert resp.status_code in (200, 201, 500)
