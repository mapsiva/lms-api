import asyncio

from celery.signals import worker_init  # type: ignore[import-untyped]

from app.core.celery_app import celery_app


@worker_init.connect
def _init_worker(**kwargs) -> None:  # type: ignore[no-untyped-def]
    from app.core.config import get_settings
    from app.core.database import init_db
    from app.core.sync_database import init_sync_db

    settings = get_settings()
    asyncio.run(init_db(settings.database_url))
    init_sync_db(settings.database_url)


__all__ = ["celery_app"]
