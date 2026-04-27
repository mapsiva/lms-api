import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import app.core.database as db_module


@pytest.fixture(autouse=True)
def reset_db():
    """Restore global state after each test."""
    original_engine = db_module.engine
    original_session = db_module.AsyncSessionLocal
    yield
    db_module.engine = original_engine
    db_module.AsyncSessionLocal = original_session


@pytest.mark.asyncio
async def test_init_db_creates_engine():
    await db_module.init_db("postgresql+asyncpg://user:pass@localhost/test")
    assert db_module.engine is not None
    assert db_module.AsyncSessionLocal is not None
    await db_module.close_db()


@pytest.mark.asyncio
async def test_close_db_disposes_engine():
    mock_engine = AsyncMock()
    db_module.engine = mock_engine
    await db_module.close_db()
    mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_close_db_noop_when_not_initialised():
    db_module.engine = None
    # Should not raise
    await db_module.close_db()


@pytest.mark.asyncio
async def test_get_db_raises_when_not_initialised():
    db_module.AsyncSessionLocal = None
    with pytest.raises(RuntimeError, match="not initialised"):
        async for _ in db_module.get_db():
            pass


@pytest.mark.asyncio
async def test_get_db_commits_on_success():
    mock_session = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_ctx)
    db_module.AsyncSessionLocal = mock_factory

    async for session in db_module.get_db():
        assert session is mock_session

    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_db_rolls_back_on_exception():
    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("boom")
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_ctx)
    db_module.AsyncSessionLocal = mock_factory

    with pytest.raises(Exception, match="boom"):
        async for _ in db_module.get_db():
            pass

    mock_session.rollback.assert_called_once()
