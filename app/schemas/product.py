import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductCourseInput(BaseModel):
    course_id: uuid.UUID
    order_index: int = 0


class ProductSpaceInput(BaseModel):
    space_id: uuid.UUID


class ProductCreate(BaseModel):
    type: str = Field(pattern="^(course|trail|mentorship|bundle)$")
    title: str = Field(min_length=1, max_length=500)
    slug: str = Field(min_length=1, max_length=255)
    status: str = Field(default="draft", pattern="^(draft|published|archived)$")
    visibility: str = Field(default="public", pattern="^(public|unlisted|private)$")
    price: float | None = None
    gateway_ids: dict[str, Any] | None = None
    access_days: int | None = None
    is_free: bool = False
    courses: list[ProductCourseInput] = Field(default_factory=list)
    spaces: list[ProductSpaceInput] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    type: str | None = Field(default=None, pattern="^(course|trail|mentorship|bundle)$")
    visibility: str | None = Field(default=None, pattern="^(public|unlisted|private)$")
    price: float | None = None
    gateway_ids: dict[str, Any] | None = None
    access_days: int | None = None
    is_free: bool | None = None
    courses: list[ProductCourseInput] | None = None
    spaces: list[ProductSpaceInput] | None = None


class ProductStatusUpdate(BaseModel):
    status: str = Field(pattern="^(draft|published|archived)$")


class ProductCourseItem(BaseModel):
    course_id: uuid.UUID
    order_index: int


class ProductSpaceItem(BaseModel):
    space_id: uuid.UUID


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    slug: str
    status: str
    visibility: str
    price: float | None = None
    gateway_ids: dict[str, Any] | None = None
    access_days: int | None = None
    is_free: bool
    courses: list[ProductCourseItem] = Field(default_factory=list)
    spaces: list[ProductSpaceItem] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
