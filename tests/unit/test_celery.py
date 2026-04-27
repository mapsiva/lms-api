from app.core.celery_app import celery_app


def test_celery_app_created():
    assert celery_app is not None
    assert celery_app.main == "lms"


def test_celery_broker_from_settings():
    from app.core.config import get_settings
    settings = get_settings()
    assert celery_app.conf.broker_url == settings.redis_url


def test_celery_backend_from_settings():
    from app.core.config import get_settings
    settings = get_settings()
    assert celery_app.conf.result_backend == settings.redis_url


def test_celery_serialization_config():
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert "json" in celery_app.conf.accept_content


def test_celery_utc_enabled():
    assert celery_app.conf.enable_utc is True
    assert celery_app.conf.timezone == "UTC"
