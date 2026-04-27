import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(min_length=1, max_length=500)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    status: str = "draft"
    is_free: bool = False
    certificate_enabled: bool = False
    instructor_id: Optional[uuid.UUID] = None


class CourseUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None
    is_free: Optional[bool] = None
    certificate_enabled: Optional[bool] = None
    instructor_id: Optional[uuid.UUID] = None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    slug: str
    description: Optional[str]
    thumbnail_url: Optional[str]
    status: str
    is_free: bool
    certificate_enabled: bool
    instructor_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime


class ModuleCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(min_length=1, max_length=500)
    order_index: int = 0
    is_hidden: bool = False


class ModuleUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    order_index: Optional[int] = None
    is_hidden: Optional[bool] = None


class ModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    course_id: uuid.UUID
    title: str
    order_index: int
    is_hidden: bool
    created_at: datetime


class LessonCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(min_length=1, max_length=500)
    lesson_type: str = "video"
    order_index: int = 0
    is_hidden: bool = False
    is_free_preview: bool = False
    duration_seconds: Optional[int] = None
    video_provider: Optional[str] = None
    video_external_id: Optional[str] = Field(None, max_length=255)
    video_metadata: Optional[dict[str, Any]] = None
    content_url: Optional[str] = Field(None, max_length=500)
    embed_url: Optional[str] = Field(None, max_length=500)
    drip_type: str = "immediate"
    drip_value: Optional[dict[str, Any]] = None


class LessonUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    lesson_type: Optional[str] = None
    order_index: Optional[int] = None
    is_hidden: Optional[bool] = None
    is_free_preview: Optional[bool] = None
    duration_seconds: Optional[int] = None
    video_provider: Optional[str] = None
    video_external_id: Optional[str] = Field(None, max_length=255)
    video_metadata: Optional[dict[str, Any]] = None
    content_url: Optional[str] = Field(None, max_length=500)
    embed_url: Optional[str] = Field(None, max_length=500)
    drip_type: Optional[str] = None
    drip_value: Optional[dict[str, Any]] = None


class LessonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    module_id: uuid.UUID
    title: str
    order_index: int
    lesson_type: str
    is_hidden: bool
    is_free_preview: bool
    duration_seconds: Optional[int]
    video_provider: Optional[str]
    video_external_id: Optional[str]
    video_metadata: Optional[dict[str, Any]]
    content_url: Optional[str]
    embed_url: Optional[str]
    drip_type: str
    drip_value: Optional[dict[str, Any]]
    ai_summary: Optional[str]
    created_at: datetime
    updated_at: datetime


class ReorderRequest(BaseModel):
    lesson_ids: list[uuid.UUID]


class BulkImportRequest(BaseModel):
    folder: str
