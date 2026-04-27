import pytest
from pydantic import SecretStr

from app.core.config import Settings


def test_settings_loads_defaults():
    s = Settings()
    assert s.jwt_algorithm == "HS256"
    assert s.access_token_expire_minutes == 15
    assert s.refresh_token_expire_days == 30
    assert s.magic_link_expire_minutes == 15
    assert s.webhook_test_mode is False


def test_sensitive_fields_are_secretstr():
    s = Settings()
    assert isinstance(s.jwt_secret_key, SecretStr)
    assert isinstance(s.bunny_api_key, SecretStr)
    assert isinstance(s.assemblyai_api_key, SecretStr)
    assert isinstance(s.resend_api_key, SecretStr)
    assert isinstance(s.r2_access_key_id, SecretStr)
    assert isinstance(s.r2_secret_access_key, SecretStr)
    assert isinstance(s.hotmart_webhook_secret, SecretStr)
    assert isinstance(s.kiwify_webhook_secret, SecretStr)
    assert isinstance(s.greenn_webhook_secret, SecretStr)
    assert isinstance(s.monetizze_webhook_secret, SecretStr)
    assert isinstance(s.stripe_webhook_secret, SecretStr)
    assert isinstance(s.anthropic_api_key, SecretStr)


def test_secretstr_not_leaked_in_repr():
    s = Settings(jwt_secret_key="super-secret")
    assert "super-secret" not in repr(s)
    assert "super-secret" not in str(s.jwt_secret_key)


def test_settings_overridden_from_env(monkeypatch):
    monkeypatch.setenv("JWT_ALGORITHM", "RS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    s = Settings()
    assert s.jwt_algorithm == "RS256"
    assert s.access_token_expire_minutes == 30


def test_get_settings_cached():
    from app.core.config import get_settings
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
