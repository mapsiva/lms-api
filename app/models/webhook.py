import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

WebhookProvider = Enum(
    "hotmart",
    "kiwify",
    "greenn",
    "monetizze",
    "stripe",
    "custom",
    name="webhook_provider",
)

LeadSource = Enum(
    "hotmart_checkout",
    "kiwify_checkout",
    "greenn_checkout",
    "landing_page",
    name="lead_source",
)


class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    __table_args__ = (
        Index("ix_webhook_logs_tenant_processed", "tenant_id", "processed"),
        Index(
            "ix_webhook_logs_tenant_provider_received",
            "tenant_id",
            "provider",
            "received_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(WebhookProvider, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    signature_valid: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    processed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_tenant_email", "tenant_id", "email"),
        Index("ix_leads_tenant_source", "tenant_id", "source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(LeadSource, nullable=False)
    utm_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
