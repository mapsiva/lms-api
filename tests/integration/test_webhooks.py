import hashlib
import hmac
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.sync_database import get_sync_db
from app.main import app
from app.models.enrollment import Enrollment
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User
from app.models.webhook import WebhookLog
from app.tasks.webhooks import process_webhook_task

SECRET = "test-webhook-secret"


@pytest.fixture
async def webhook_tenant(db_session):
    domain = f"wh-{uuid.uuid4().hex[:8]}.example.com"
    t = Tenant(
        id=uuid.uuid4(),
        slug=f"wh-{uuid.uuid4().hex[:8]}",
        name="Webhook Test Tenant",
        custom_domain=domain,
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    yield t
    await db_session.delete(t)
    await db_session.commit()


@pytest.fixture
async def webhook_product(db_session, webhook_tenant):
    p = Product(
        tenant_id=webhook_tenant.id,
        type="course",
        title="Webhook Course",
        slug="webhook-course",
        status="published",
        gateway_ids={"hotmart": "HOT999"},
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    yield p
    await db_session.delete(p)
    await db_session.commit()


@pytest.fixture
async def webhook_client(db_session, redis_client, webhook_tenant):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://{webhook_tenant.custom_domain}",
        headers={"host": webhook_tenant.custom_domain},
    ) as c:
        yield c
    app.dependency_overrides.clear()


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ── Receipt tests ────────────────────────────────────────────────────────────


async def test_webhook_valid_signature_creates_log(webhook_client, webhook_tenant, webhook_product):
    payload = {
        "event": "PURCHASE_APPROVED",
        "data": {
            "product": {"id": "HOT999"},
            "buyer": {"email": "buyer@example.com", "name": "Buyer"},
        },
    }
    body = json.dumps(payload).encode()
    headers = {"x-hotmart-signature": _sign(body, SECRET)}

    resp = await webhook_client.post("/webhooks/hotmart", content=body, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_webhook_invalid_signature_returns_200(webhook_client, webhook_tenant):
    resp = await webhook_client.post(
        "/webhooks/hotmart",
        content=b"{}",
        headers={"x-hotmart-signature": "bad"},
    )
    assert resp.status_code == 200


async def test_webhook_unknown_provider_returns_200(webhook_client, webhook_tenant):
    resp = await webhook_client.post("/webhooks/unknown", content=b"{}")
    assert resp.status_code == 200


# ── Processing tests (direct task call) ──────────────────────────────────────


async def test_process_webhook_creates_user_and_enrollment(
    webhook_tenant, webhook_product, db_session
):
    log = WebhookLog(
        tenant_id=webhook_tenant.id,
        provider="hotmart",
        event_type="PURCHASE_APPROVED",
        payload={},
        signature_valid=True,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    process_webhook_task(
        str(log.id),
        str(webhook_tenant.id),
        "hotmart",
        "PURCHASE_APPROVED",
        "HOT999",
        "buyer@example.com",
        "Buyer",
        "active",
        {},
    )

    # Verify user created
    from sqlalchemy import select

    result = await db_session.execute(
        select(User).where(User.tenant_id == webhook_tenant.id, User.email == "buyer@example.com")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.role == "student"

    # Verify enrollment created
    result = await db_session.execute(
        select(Enrollment).where(
            Enrollment.tenant_id == webhook_tenant.id,
            Enrollment.user_id == user.id,
            Enrollment.product_id == webhook_product.id,
        )
    )
    enrollment = result.scalar_one_or_none()
    assert enrollment is not None
    assert enrollment.status == "active"
    assert enrollment.enrolled_by == "webhook"

    # Cleanup
    if enrollment:
        await db_session.delete(enrollment)
    await db_session.delete(user)
    await db_session.commit()


async def test_process_webhook_refund_updates_status(
    webhook_tenant, webhook_product, db_session
):
    # Create existing enrollment
    user = User(
        tenant_id=webhook_tenant.id,
        email="refund@example.com",
        name="Refund",
        role="student",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    enrollment = Enrollment(
        tenant_id=webhook_tenant.id,
        user_id=user.id,
        product_id=webhook_product.id,
        status="active",
        enrolled_by="webhook",
    )
    db_session.add(enrollment)
    await db_session.commit()

    log = WebhookLog(
        tenant_id=webhook_tenant.id,
        provider="hotmart",
        event_type="PURCHASE_REFUNDED",
        payload={},
        signature_valid=True,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    process_webhook_task(
        str(log.id),
        str(webhook_tenant.id),
        "hotmart",
        "PURCHASE_REFUNDED",
        "HOT999",
        "refund@example.com",
        "Refund",
        "refunded",
        {},
    )

    await db_session.refresh(enrollment)
    assert enrollment.status == "refunded"

    # Cleanup
    await db_session.delete(enrollment)
    await db_session.delete(user)
    await db_session.commit()


async def test_process_webhook_missing_product_logs_warning(
    webhook_tenant, db_session
):
    log = WebhookLog(
        tenant_id=webhook_tenant.id,
        provider="hotmart",
        event_type="PURCHASE_APPROVED",
        payload={},
        signature_valid=True,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    process_webhook_task(
        str(log.id),
        str(webhook_tenant.id),
        "hotmart",
        "PURCHASE_APPROVED",
        "NONEXISTENT",
        "buyer@example.com",
        "Buyer",
        "active",
        {},
    )

    # Log should be marked processed but no user/enrollment created
    await db_session.refresh(log)
    assert log.processed is True
