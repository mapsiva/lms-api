"""Menu schemas."""
from typing import Any

from pydantic import BaseModel, ConfigDict


class MenuUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[dict[str, Any]] = []


class MenuResponse(BaseModel):
    role: str
    items: list[dict[str, Any]]
