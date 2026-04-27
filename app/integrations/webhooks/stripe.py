
from app.integrations.webhooks.base import WebhookEvent


STRIPE_EVENT_MAP = {
    "checkout.session.completed": "active",
    "charge.refunded": "refunded",
    "customer.subscription.deleted": "cancelled",
}


def parse_stripe_webhook(
    raw_body: bytes, headers: dict[str, str], secret: str
) -> tuple[WebhookEvent | None, bool]:
    try:
        import stripe
    except ImportError:  # pragma: no cover
        return None, False

    sig_header = headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(raw_body, sig_header, secret)
    except Exception:
        return None, False

    event_type = event.get("type", "")
    data_object = event.get("data", {}).get("object", {}) or {}

    product_id = None
    buyer_email = None
    buyer_name = None

    if data_object.get("metadata"):
        product_id = data_object["metadata"].get("product_id")

    if event_type == "checkout.session.completed":
        buyer_email = data_object.get("customer_details", {}).get("email")
        buyer_name = data_object.get("customer_details", {}).get("name")
    elif event_type.startswith("customer.subscription"):
        buyer_email = data_object.get("customer_email")

    return (
        WebhookEvent(
            provider="stripe",
            event_type=event_type,
            product_id=str(product_id) if product_id else None,
            buyer_email=buyer_email,
            buyer_name=buyer_name,
            status=STRIPE_EVENT_MAP.get(event_type),
            raw_payload=dict(event),
        ),
        True,
    )
