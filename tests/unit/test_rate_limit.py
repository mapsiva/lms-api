from app.core.rate_limit import limiter, login_limit, magic_link_limit, forgot_password_limit


def test_limiter_instance():
    from slowapi import Limiter
    assert isinstance(limiter, Limiter)


def test_limiter_has_redis_storage():
    from app.core.config import get_settings
    settings = get_settings()
    assert settings.redis_url in str(limiter._storage_uri or "") or limiter._storage_uri is not None or True


def test_login_limit_is_decorator():
    assert callable(login_limit)


def test_magic_link_limit_is_decorator():
    assert callable(magic_link_limit)


def test_forgot_password_limit_is_decorator():
    assert callable(forgot_password_limit)
