from celery import Celery  # type: ignore[import-untyped]

from app.core.config import get_settings


def create_celery() -> Celery:
    settings = get_settings()
    app = Celery(
        "lms",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["app.tasks"],
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
    )
    return app


celery_app = create_celery()
