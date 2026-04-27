import hashlib
import hmac
import json

import pytest

from app.integrations.webhooks.hotmart import parse_hotmart_webhook
from app.integrations.webhooks.kiwify import parse_kiwify_webhook
from app.integrations.webhooks.greenn import parse_greenn_webhook
from app.integrations.webhooks.monetizze import parse_monetizze_webhook

SECRET = "super-secret"


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ── Hotmart ──────────────────────────────────────────────────────────────────

def test_hotmart_valid_signature():
    payload = {
        "event": "PURCHASE_APPROVED",
        "data": {
            "product": {"id": 123},
            "buyer": {"email": "a@b.com", "name": "Alice"},
        },
    }
    body = json.dumps(payload).encode()
    headers = {"x-hotmart-signature": _sign(body, SECRET)}
    event, valid = parse_hotmart_webhook(body, headers, SECRET)
    assert valid is True
    assert event is not None
    assert event.provider == "hotmart"
    assert event.status == "active"
    assert event.buyer_email == "a@b.com"


def test_hotmart_invalid_signature():
    body = b'{}'
    headers = {"x-hotmart-signature": "bad"}
    event, valid = parse_hotmart_webhook(body, headers, SECRET)
    assert valid is False
    assert event is None


def test_hotmart_event_mapping():
    for ev, expected in (
        ("PURCHASE_REFUNDED", "refunded"),
        ("PURCHASE_CANCELED", "cancelled"),
        ("SUBSCRIPTION_CANCELLATION", "cancelled"),
    ):
        payload = {"event": ev, "data": {"product": {"id": 1}, "buyer": {}}}
        body = json.dumps(payload).encode()
        headers = {"x-hotmart-signature": _sign(body, SECRET)}
        event, _ = parse_hotmart_webhook(body, headers, SECRET)
        assert event.status == expected


# ── Kiwify ───────────────────────────────────────────────────────────────────

def test_kiwify_valid_signature():
    payload = {
        "event": "order.approved",
        "data": {
            "product": {"id": 456},
            "customer": {"email": "b@c.com", "name": "Bob"},
        },
    }
    body = json.dumps(payload).encode()
    headers = {"x-kiwify-signature": _sign(body, SECRET)}
    event, valid = parse_kiwify_webhook(body, headers, SECRET)
    assert valid is True
    assert event.provider == "kiwify"
    assert event.status == "active"


def test_kiwify_invalid_signature():
    body = b'{}'
    headers = {"x-kiwify-signature": "bad"}
    event, valid = parse_kiwify_webhook(body, headers, SECRET)
    assert valid is False


def test_kiwify_event_mapping():
    for ev, expected in (("order.refunded", "refunded"), ("order.chargeback", "refunded")):
        payload = {"event": ev, "data": {"product": {"id": 1}, "customer": {}}}
        body = json.dumps(payload).encode()
        headers = {"x-kiwify-signature": _sign(body, SECRET)}
        event, _ = parse_kiwify_webhook(body, headers, SECRET)
        assert event.status == expected


# ── Greenn ───────────────────────────────────────────────────────────────────

def test_greenn_valid_signature():
    payload = {
        "event": "purchase.approved",
        "data": {
            "product": {"id": 789},
            "customer": {"email": "c@d.com", "name": "Carol"},
        },
    }
    body = json.dumps(payload).encode()
    headers = {"x-greenn-signature": _sign(body, SECRET)}
    event, valid = parse_greenn_webhook(body, headers, SECRET)
    assert valid is True
    assert event.provider == "greenn"
    assert event.status == "active"


def test_greenn_invalid_signature():
    body = b'{}'
    headers = {"x-greenn-signature": "bad"}
    event, valid = parse_greenn_webhook(body, headers, SECRET)
    assert valid is False


# ── Monetizze ────────────────────────────────────────────────────────────────

def test_monetizze_valid_token():
    payload = {
        "evento": "APPROVED",
        "venda": {
            "produto": {"codigo": 999},
            "comprador": {"email": "d@e.com", "nome": "Dan"},
        },
    }
    body = json.dumps(payload).encode()
    headers = {"x-monetizze-token": SECRET}
    event, valid = parse_monetizze_webhook(body, headers, SECRET)
    assert valid is True
    assert event.provider == "monetizze"
    assert event.status == "active"
    assert event.product_id == "999"


def test_monetizze_invalid_token():
    body = b'{}'
    headers = {"x-monetizze-token": "bad"}
    event, valid = parse_monetizze_webhook(body, headers, SECRET)
    assert valid is False


# ── Stripe ───────────────────────────────────────────────────────────────────

def _make_module(name: str):
    import types
    mod = types.ModuleType(name)
    mod.Webhook = types.SimpleNamespace()
    return mod


def test_stripe_valid_signature(monkeypatch):
    mock_stripe = _make_module("stripe")
    mock_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"product_id": "prod_123"},
                "customer_details": {"email": "e@f.com", "name": "Eve"},
            }
        },
    }
    mock_stripe.Webhook.construct_event = lambda *a, **k: mock_event
    monkeypatch.setitem(__import__("sys").modules, "stripe", mock_stripe)

    body = b'{}'
    headers = {"stripe-signature": "sig"}
    from app.integrations.webhooks.stripe import parse_stripe_webhook

    event, valid = parse_stripe_webhook(body, headers, SECRET)
    assert valid is True
    assert event.provider == "stripe"
    assert event.status == "active"
    assert event.product_id == "prod_123"


def test_stripe_invalid_signature(monkeypatch):
    mock_stripe = _make_module("stripe")
    mock_stripe.Webhook.construct_event = lambda *a, **k: (_ for _ in ()).throw(ValueError("bad"))
    monkeypatch.setitem(__import__("sys").modules, "stripe", mock_stripe)

    body = b'{}'
    headers = {"stripe-signature": "sig"}
    from app.integrations.webhooks.stripe import parse_stripe_webhook

    event, valid = parse_stripe_webhook(body, headers, SECRET)
    assert valid is False
    assert event is None
