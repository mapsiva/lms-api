"""Integration tests for messaging REST router."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.messaging import Conversation, ConversationParticipant, Message
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import register_user


@pytest.fixture
async def tenant(db_session):
    domain = f"{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(id=uuid.uuid4(), slug=f"ms-{uuid.uuid4().hex[:8]}", name="MsgTest", custom_domain=domain)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def user_a(db_session, tenant):
    u = await register_user(db_session, tenant.id, "a@msg.com", "UserA", "password123", role="student")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def user_b(db_session, tenant):
    u = await register_user(db_session, tenant.id, "b@msg.com", "UserB", "password123", role="student")
    yield u
    obj = await db_session.get(User, u.id)
    if obj:
        await db_session.delete(obj)
        await db_session.commit()


@pytest.fixture
async def client_a(db_session, redis_client, tenant, user_a):
    token = create_access_token(str(user_a.id), str(tenant.id), "student")

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
async def client_b(db_session, redis_client, tenant, user_b):
    token = create_access_token(str(user_b.id), str(tenant.id), "student")

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
async def test_create_conversation(client_a, user_a, user_b):
    resp = await client_a.post("/messages/conversations", json={"title": "Test Conv", "participant_ids": [str(user_b.id)]})
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_list_conversations(client_a, user_a, user_b, db_session, tenant):
    conv = Conversation(tenant_id=tenant.id, title="Conv")
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)
    cp_a = ConversationParticipant(conversation_id=conv.id, user_id=user_a.id)
    cp_b = ConversationParticipant(conversation_id=conv.id, user_id=user_b.id)
    db_session.add_all([cp_a, cp_b])
    await db_session.commit()

    resp = await client_a.get("/messages/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_send_and_list_messages(client_a, user_a, user_b, db_session, tenant):
    conv = Conversation(tenant_id=tenant.id, title="Conv2")
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)
    cp_a = ConversationParticipant(conversation_id=conv.id, user_id=user_a.id)
    cp_b = ConversationParticipant(conversation_id=conv.id, user_id=user_b.id)
    db_session.add_all([cp_a, cp_b])
    await db_session.commit()

    resp = await client_a.post(f"/messages/conversations/{conv.id}/messages", json={"content": "Hello!"})
    assert resp.status_code == 201
    assert resp.json()["id"]

    resp = await client_a.get(f"/messages/conversations/{conv.id}/messages")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_message_isolation(client_a, user_a, db_session, tenant):
    conv = Conversation(tenant_id=tenant.id, title="Isolated")
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)

    resp = await client_a.get(f"/messages/conversations/{conv.id}/messages")
    assert resp.status_code == 404
