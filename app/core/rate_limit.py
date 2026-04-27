from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def _get_redis_url() -> str:
    return get_settings().redis_url


limiter = Limiter(key_func=get_remote_address, storage_uri=_get_redis_url())

# Decorator helpers — apply in auth router
login_limit = limiter.limit("10/15minutes")
magic_link_limit = limiter.limit("10/15minutes")
forgot_password_limit = limiter.limit("5/minute")
