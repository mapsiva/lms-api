"""Integration tests for community router."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.community import Channel, Comment, Post, PostLike, Space
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"cm-{uuid.uuid4().hex[:8]}", name="CommunityTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def student_user(db_session, tenant):
    u = await register_user(db_session, tenant.id, "student@community.com", "Student", "password123", role="student")
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


@pytest.fixture
async def sample_space(db_session, tenant):
    s = Space(tenant_id=tenant.id, name="General")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    yield s


@pytest.fixture
async def sample_channel(db_session, tenant, sample_space):
    c = Channel(space_id=sample_space.id, tenant_id=tenant.id, name="Discussion", post_policy="open")
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    yield c


@pytest.mark.asyncio
async def test_list_spaces(student_client, sample_space):
    resp = await student_client.get("/community/spaces")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "General"


@pytest.mark.asyncio
async def test_list_channels(student_client, sample_space, sample_channel):
    resp = await student_client.get(f"/community/spaces/{sample_space.id}/channels")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_create_post(student_client, sample_channel, student_user):
    resp = await student_client.post(
        f"/community/channels/{sample_channel.id}/posts",
        params={"body": "Hello community!", "title": "Hi"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["body"] == "Hello community!"
    assert data["user_id"] == str(student_user.id)


@pytest.mark.asyncio
async def test_create_post_restricted_policy(student_client, sample_space, db_session, tenant):
    channel = Channel(space_id=sample_space.id, tenant_id=tenant.id, name="Announcements", post_policy="admins")
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)

    resp = await student_client.post(
        f"/community/channels/{channel.id}/posts",
        params={"body": "Should fail"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_like_unlike_post(student_client, sample_channel, student_user, db_session):
    post = Post(channel_id=sample_channel.id, tenant_id=sample_channel.tenant_id, user_id=student_user.id, body="Test")
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)

    resp = await student_client.post(f"/community/posts/{post.id}/like")
    assert resp.status_code == 200
    assert resp.json()["liked"] is True

    resp = await student_client.post(f"/community/posts/{post.id}/like")
    assert resp.status_code == 409

    resp = await student_client.delete(f"/community/posts/{post.id}/like")
    assert resp.status_code == 200
    assert resp.json()["liked"] is False


@pytest.mark.asyncio
async def test_create_comment(student_client, sample_channel, student_user, db_session):
    post = Post(channel_id=sample_channel.id, tenant_id=sample_channel.tenant_id, user_id=student_user.id, body="Parent")
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)

    resp = await student_client.post(
        f"/community/posts/{post.id}/comments",
        params={"body": "Nice post!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["body"] == "Nice post!"
    assert post.comments_count == 1


@pytest.mark.asyncio
async def test_report_post(student_client, sample_channel, student_user, db_session):
    post = Post(channel_id=sample_channel.id, tenant_id=sample_channel.tenant_id, user_id=student_user.id, body="Spam")
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)

    resp = await student_client.post(
        f"/community/posts/{post.id}/report",
        params={"reason": "spam"},
    )
    assert resp.status_code == 200
    assert resp.json()["reported"] is True
