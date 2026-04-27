import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer


class RegisterRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    password: str

    @field_serializer("password")
    def _hide_password(self, _: str) -> str:
        return "***"


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    refresh_token: str


class MagicLinkRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr


class MagicLinkVerifyRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    token: str


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_serializer("new_password")
    def _hide_password(self, _: str) -> str:
        return "***"


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    name: str
    avatar_url: Optional[str]
    bio: Optional[str]
    role: str
    company_id: Optional[uuid.UUID]
    is_active: bool
    is_suspended: bool
    last_seen_at: Optional[datetime]
    created_at: datetime


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=1000)
