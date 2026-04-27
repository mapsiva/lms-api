from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_sync_engine = None
_SyncSessionLocal = None


def init_sync_db(database_url: str) -> None:
    global _sync_engine, _SyncSessionLocal
    # Convert asyncpg URL to psycopg2 URL for sync access
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    _sync_engine = create_engine(sync_url, echo=False, pool_pre_ping=True)
    _SyncSessionLocal = sessionmaker(bind=_sync_engine)


def get_sync_db() -> Session:
    if _SyncSessionLocal is None:
        raise RuntimeError("Sync DB not initialised")
    return _SyncSessionLocal()


def close_sync_db() -> None:
    global _sync_engine
    if _sync_engine:
        _sync_engine.dispose()
