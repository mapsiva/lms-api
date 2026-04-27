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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

DripType = Enum(
    "immediate", "fixed_date", "days_after_enrollment", "prerequisite",
    name="drip_type",
)
VideoProvider = Enum(
    "bunny", "mux", "vimeo", "youtube", "panda", "custom",
    name="video_provider",
)
LessonType = Enum(
    "video", "text", "pdf", "live", "quiz", "embed", "download",
    name="lesson_type",
)
CourseStatus = Enum("draft", "published", "archived", name="course_status")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_courses_tenant_slug"),
        Index("ix_courses_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(CourseStatus, nullable=False, server_default="draft")
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    certificate_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    instructor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (
        Index("ix_modules_course_order", "course_id", "order_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        Index("ix_lessons_module_order", "module_id", "order_index"),
        Index("ix_lessons_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lesson_type: Mapped[str] = mapped_column(LessonType, nullable=False, server_default="video")
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_free_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Video fields
    video_provider: Mapped[str | None] = mapped_column(VideoProvider, nullable=True)
    video_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    video_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Content
    content_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embed_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Drip
    drip_type: Mapped[str] = mapped_column(DripType, nullable=False, server_default="immediate")
    drip_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Transcript / AI
    transcript_text: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
