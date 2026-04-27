from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WebhookEvent:
    provider: str
    event_type: str
    product_id: str | None
    buyer_email: str | None
    buyer_name: str | None
    status: str | None
    raw_payload: dict[str, Any]
