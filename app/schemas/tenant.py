import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _validate_hex_color(v: Optional[str]) -> Optional[str]:
    if v is not None and not _HEX_COLOR_RE.match(v):
        raise ValueError("Color must be in #RRGGBB format")
    return v


class TenantFeatures(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gamification: bool = False
    community: bool = False
    live_classes: bool = False
    certificates: bool = False
    custom_domain: bool = False


class TenantBrandingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    logo_url: Optional[str]
    favicon_url: Optional[str]
    primary_color: Optional[str]
    secondary_color: Optional[str]
    font_family: Optional[str]
    app_name: Optional[str]


class TenantBrandingUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    logo_url: Optional[str] = Field(None, max_length=500)
    favicon_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, max_length=7)
    secondary_color: Optional[str] = Field(None, max_length=7)
    font_family: Optional[str] = Field(None, max_length=100)
    app_name: Optional[str] = Field(None, max_length=255)

    @field_validator("primary_color", "secondary_color", mode="before")
    @classmethod
    def validate_colors(cls, v: Optional[str]) -> Optional[str]:
        return _validate_hex_color(v)


class TenantSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    custom_domain: Optional[str]
    subdomain: Optional[str]
    plan: str
    features: Optional[dict]
    created_at: datetime


class TenantSettingsUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    features: Optional[TenantFeatures] = None


class TenantCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    custom_domain: Optional[str] = Field(None, max_length=255)
    subdomain: Optional[str] = Field(None, max_length=100)
    plan: str = "free"


class TenantUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    custom_domain: Optional[str] = Field(None, max_length=255)
    subdomain: Optional[str] = Field(None, max_length=100)
    plan: Optional[str] = None
    logo_url: Optional[str] = Field(None, max_length=500)
    favicon_url: Optional[str] = Field(None, max_length=500)
    primary_color: Optional[str] = Field(None, max_length=7)
    secondary_color: Optional[str] = Field(None, max_length=7)
    font_family: Optional[str] = Field(None, max_length=100)
    app_name: Optional[str] = Field(None, max_length=255)
