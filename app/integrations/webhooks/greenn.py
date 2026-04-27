import hashlib
import hmac
from typing import Any

from app.integrations.webhooks.base import WebhookEvent


GREENN_EVENT_MAP = {
    "purchase.approved": "active",
    "purchase.refunded": "refunded",
    "purchase.cancelled": "cancelled",
}


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_greenn_webhook(
    raw_body: bytes, headers: dict[str, str], secret: str
) -> tuple[WebhookEvent | None, bool]:
    signature = headers.get("x-greenn-signature", "")
    valid = _verify_signature(raw_body, signature, secret)
    if not valid:
        return None, False

    payload: dict[str, Any]
    try:
        import json

        payload = json.loads(raw_body)
    except Exception:
        return None, False

    event_type = payload.get("event", "")
    data = payload.get("data", {}) or {}
    product = data.get("product", {}) or {}
    customer = data.get("customer", {}) or {}

    return (
        WebhookEvent(
            provider="greenn",
            event_type=event_type,
            product_id=str(product.get("id")) if product.get("id") else None,
            buyer_email=customer.get("email"),
            buyer_name=customer.get("name"),
            status=GREENN_EVENT_MAP.get(event_type),
            raw_payload=payload,
        ),
        True,
    )
