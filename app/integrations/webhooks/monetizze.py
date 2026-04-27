import hmac
from typing import Any

from app.integrations.webhooks.base import WebhookEvent


MONETIZZE_EVENT_MAP = {
    "APPROVED": "active",
    "REFUNDED": "refunded",
    "CANCELED": "cancelled",
}


def parse_monetizze_webhook(
    raw_body: bytes, headers: dict[str, str], token: str
) -> tuple[WebhookEvent | None, bool]:
    auth = headers.get("x-monetizze-token", "")
    valid = hmac.compare_digest(auth, token)
    if not valid:
        return None, False

    payload: dict[str, Any]
    try:
        import json

        payload = json.loads(raw_body)
    except Exception:
        return None, False

    event_type = payload.get("evento", "")
    venda = payload.get("venda", {}) or {}
    produto = venda.get("produto", {}) or {}
    comprador = venda.get("comprador", {}) or {}

    return (
        WebhookEvent(
            provider="monetizze",
            event_type=event_type,
            product_id=str(produto.get("codigo")) if produto.get("codigo") else None,
            buyer_email=comprador.get("email"),
            buyer_name=comprador.get("nome"),
            status=MONETIZZE_EVENT_MAP.get(event_type),
            raw_payload=payload,
        ),
        True,
    )
