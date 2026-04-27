import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.drip import DripResult, is_lesson_accessible


def _make_lesson(drip_type="immediate", drip_value=None):
    l = MagicMock()
    l.drip_type = drip_type
    l.drip_value = drip_value
    return l


def _make_enrollment(created_at=None):
    e = MagicMock()
    e.created_at = created_at or datetime.now(timezone.utc) - timedelta(days=1)
    return e


def _make_db(progress=None):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = progress
    db.execute = AsyncMock(return_value=result)
    return db


# ── immediate ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_immediate_always_accessible():
    result = await is_lesson_accessible(_make_db(), uuid.uuid4(), _make_lesson(), _make_enrollment())
    assert result.accessible is True
    assert result.unlocks_at is None


# ── fixed_date ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fixed_date_past_accessible():
    past = "2020-01-01T00:00:00"
    lesson = _make_lesson("fixed_date", {"date": past})
    result = await is_lesson_accessible(_make_db(), uuid.uuid4(), lesson, _make_enrollment())
    assert result.accessible is True


@pytest.mark.asyncio
async def test_fixed_date_future_not_accessible():
    future = "2099-01-01T00:00:00"
    lesson = _make_lesson("fixed_date", {"date": future})
    result = await is_lesson_accessible(_make_db(), uuid.uuid4(), lesson, _make_enrollment())
    assert result.accessible is False
    assert result.unlocks_at is not None
    assert "2099" in result.reason


@pytest.mark.asyncio
async def test_fixed_date_no_date_defaults_accessible():
    lesson = _make_lesson("fixed_date", {})
    result = await is_lesson_accessible(_make_db(), uuid.uuid4(), lesson, _make_enrollment())
    assert result.accessible is True


@pytest.mark.asyncio
async def test_fixed_date_tz_aware_comparison():
    future = "2099-06-15T12:00:00+00:00"
    lesson = _make_lesson("fixed_date", {"date": future})
    result = await is_lesson_accessible(_make_db(), uuid.uuid4(), lesson, _make_enrollment())
    assert result.accessible is False


# ── days_after_enrollment ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_days_after_enrollment_elapsed_accessible():
    enrollment = _make_enrollment(created_at=datetime.now(timezone.utc) - timedelta(days=10))
    lesson = _make_lesson("days_after_enrollment", {"days": 7})
    result = await is_lesson_accessible(_make_db(), uuid.uuid4(), lesson, enrollment)
    assert result.accessible is True


@pytest.mark.asyncio
async def test_days_after_enrollment_not_elapsed():
    enrollment = _make_enrollment(created_at=datetime.now(timezone.utc) - timedelta(days=2))
    lesson = _make_lesson("days_after_enrollment", {"days": 30})
    result = await is_lesson_accessible(_make_db(), uuid.uuid4(), lesson, enrollment)
    assert result.accessible is False
    assert result.unlocks_at is not None
    assert "30 days" in result.reason


@pytest.mark.asyncio
async def test_days_after_enrollment_zero_days_accessible():
    enrollment = _make_enrollment(created_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    lesson = _make_lesson("days_after_enrollment", {"days": 0})
    result = await is_lesson_accessible(_make_db(), uuid.uuid4(), lesson, enrollment)
    assert result.accessible is True


@pytest.mark.asyncio
async def test_days_after_enrollment_naive_datetime():
    enrollment = _make_enrollment(created_at=datetime.utcnow() - timedelta(days=10))
    enrollment.created_at = enrollment.created_at.replace(tzinfo=None)
    lesson = _make_lesson("days_after_enrollment", {"days": 7})
    result = await is_lesson_accessible(_make_db(), uuid.uuid4(), lesson, enrollment)
    assert result.accessible is True


# ── prerequisite ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_prerequisite_completed_accessible():
    prereq_id = str(uuid.uuid4())
    lesson = _make_lesson("prerequisite", {"lesson_id": prereq_id})
    db = _make_db(progress=MagicMock())
    result = await is_lesson_accessible(db, uuid.uuid4(), lesson, _make_enrollment())
    assert result.accessible is True


@pytest.mark.asyncio
async def test_prerequisite_not_completed():
    prereq_id = str(uuid.uuid4())
    lesson = _make_lesson("prerequisite", {"lesson_id": prereq_id})
    db = _make_db(progress=None)
    result = await is_lesson_accessible(db, uuid.uuid4(), lesson, _make_enrollment())
    assert result.accessible is False
    assert "prerequisite" in result.reason


@pytest.mark.asyncio
async def test_prerequisite_no_lesson_id_defaults_accessible():
    lesson = _make_lesson("prerequisite", {})
    result = await is_lesson_accessible(_make_db(), uuid.uuid4(), lesson, _make_enrollment())
    assert result.accessible is True


# ── DripResult dataclass ──────────────────────────────────────────────────────

def test_drip_result_fields():
    r = DripResult(accessible=True, reason="ok")
    assert r.accessible is True
    assert r.unlocks_at is None

    future = datetime(2099, 1, 1, tzinfo=timezone.utc)
    r2 = DripResult(accessible=False, reason="locked", unlocks_at=future)
    assert r2.unlocks_at == future
