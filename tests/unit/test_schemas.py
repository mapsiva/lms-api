import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserMeResponse,
    UserUpdateRequest,
)
from app.schemas.tenant import (
    TenantBrandingResponse,
    TenantBrandingUpdate,
    TenantSettingsResponse,
    TenantSettingsUpdate,
)


# ── T10: Auth schemas ────────────────────────────────────────────────────────


def test_auth_register_valid():
    r = RegisterRequest(name="Alice", email="alice@example.com", password="password123")
    assert r.email == "alice@example.com"
    assert r.name == "Alice"


def test_auth_register_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(name="Alice", email="not-an-email", password="password123")


def test_auth_register_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(name="Alice", email="alice@example.com", password="short")


def test_auth_login_password_hidden_in_serialization():
    r = LoginRequest(email="alice@example.com", password="secret")
    data = r.model_dump()
    assert data["password"] == "***"


def test_auth_token_response():
    t = TokenResponse(access_token="tok", expires_in=900)
    assert t.token_type == "bearer"
    assert t.expires_in == 900


def test_auth_refresh_request():
    r = RefreshRequest(refresh_token="some-opaque-token")
    assert r.refresh_token == "some-opaque-token"


def test_auth_magic_link_request():
    r = MagicLinkRequest(email="user@example.com")
    assert r.email == "user@example.com"


def test_auth_magic_link_verify_request():
    r = MagicLinkVerifyRequest(token="uuid-token")
    assert r.token == "uuid-token"


def test_auth_forgot_password():
    r = ForgotPasswordRequest(email="user@example.com")
    assert r.email == "user@example.com"


def test_auth_reset_password_hidden():
    r = ResetPasswordRequest(token="tok", new_password="newpassword1")
    data = r.model_dump()
    assert data["new_password"] == "***"


def test_auth_reset_password_too_short():
    with pytest.raises(ValidationError):
        ResetPasswordRequest(token="tok", new_password="short")


def test_auth_user_me_response_from_attributes():
    now = datetime.now(timezone.utc)
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    r = UserMeResponse(
        id=user_id,
        tenant_id=tenant_id,
        email="alice@example.com",
        name="Alice",
        avatar_url=None,
        bio=None,
        role="student",
        company_id=None,
        is_active=True,
        is_suspended=False,
        last_seen_at=None,
        created_at=now,
    )
    assert r.id == user_id
    assert r.role == "student"


def test_auth_user_update_optional_fields():
    r = UserUpdateRequest()
    assert r.name is None
    r2 = UserUpdateRequest(name="Bob")
    assert r2.name == "Bob"


# ── T11: Tenant schemas ──────────────────────────────────────────────────────


def test_tenant_branding_update_valid_color():
    r = TenantBrandingUpdate(primary_color="#FF5733", secondary_color="#FFFFFF")
    assert r.primary_color == "#FF5733"


def test_tenant_branding_update_invalid_color():
    with pytest.raises(ValidationError):
        TenantBrandingUpdate(primary_color="red")


def test_tenant_branding_update_invalid_short_hex():
    with pytest.raises(ValidationError):
        TenantBrandingUpdate(primary_color="#FFF")


def test_tenant_branding_update_none_color():
    r = TenantBrandingUpdate(primary_color=None)
    assert r.primary_color is None


def test_tenant_branding_response():
    r = TenantBrandingResponse(
        id=uuid.uuid4(),
        slug="acme",
        name="Acme",
        logo_url=None,
        favicon_url=None,
        primary_color="#123456",
        secondary_color=None,
        font_family=None,
        app_name=None,
    )
    assert r.slug == "acme"


def test_tenant_settings_response():
    r = TenantSettingsResponse(
        id=uuid.uuid4(),
        slug="acme",
        name="Acme",
        custom_domain=None,
        subdomain="acme",
        plan="pro",
        features={"gamification": True},
        created_at=datetime.now(timezone.utc),
    )
    assert r.plan == "pro"


def test_tenant_settings_update_optional():
    r = TenantSettingsUpdate()
    assert r.name is None
    assert r.features is None
