import asyncio
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import get_db, init_db, close_db
from app.core.redis_client import init_redis, close_redis, get_redis
from app.core.sync_database import init_sync_db, close_sync_db
from app.main import app


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def redis_client():
    settings = get_settings()
    await init_redis(settings.redis_url)
    yield
    await close_redis()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_engine(redis_client):
    settings = get_settings()
    await init_db(settings.database_url)
    init_sync_db(settings.database_url)
    engine = create_async_engine(settings.database_url, echo=False)
    yield engine
    try:
        await engine.dispose()
        await close_db()
        close_sync_db()
    except Exception:
        pass


@pytest_asyncio.fixture(autouse=True)
async def flush_redis(redis_client):
    """Flush Redis between tests to prevent rate-limit and cache bleed."""
    redis = get_redis()
    if redis:
        await redis.flushdb()
    yield


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(db_engine):
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session, redis_client):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
