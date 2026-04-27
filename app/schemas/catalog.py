import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CatalogCourseItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    thumbnail_url: Optional[str]


class CatalogProductListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    price: Optional[float]
    type: str
    status: str


class CatalogProductDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    price: Optional[float]
    type: str
    status: str
    courses: list[CatalogCourseItem] = []
