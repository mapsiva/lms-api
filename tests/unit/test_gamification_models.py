"""Unit tests for gamification models."""
import uuid

from app.models.gamification import (
    Badge,
    League,
    LeagueCompany,
    SpecialEvent,
    UserBadge,
    UserLevel,
    UserStreak,
    XPEvent,
)


def test_xp_event_fields():
    e = XPEvent(
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        action="lesson_completed",
        amount=10,
    )
    assert e.amount == 10
    assert e.action == "lesson_completed"


def test_user_level_init():
    ul = UserLevel(tenant_id=uuid.uuid4(), user_id=uuid.uuid4(), total_xp=0, level=1)
    assert ul.total_xp == 0
    assert ul.level == 1


def test_badge_fields():
    b = Badge(
        tenant_id=uuid.uuid4(),
        name="First Step",
        category="completion",
        rarity="common",
        xp_reward=0,
        is_active=True,
    )
    assert b.category == "completion"
    assert b.rarity == "common"
    assert b.xp_reward == 0
    assert b.is_active is True


def test_user_badge_init():
    ub = UserBadge(user_id=uuid.uuid4(), badge_id=uuid.uuid4())
    assert ub.user_id is not None
    assert ub.badge_id is not None


def test_user_streak_init():
    us = UserStreak(
        user_id=uuid.uuid4(),
        current_streak=0,
        longest_streak=0,
        shields_available=0,
    )
    assert us.current_streak == 0
    assert us.shields_available == 0
    assert us.longest_streak == 0


def test_special_event_multiplier():
    from datetime import datetime, timezone

    se = SpecialEvent(
        tenant_id=uuid.uuid4(),
        name="Double XP Weekend",
        event_type="xp_multiplier",
        xp_multiplier=2,
        starts_at=datetime.now(timezone.utc),
        ends_at=datetime.now(timezone.utc),
        is_active=True,
    )
    assert se.xp_multiplier == 2
    assert se.is_active is True


def test_league_and_company():
    from datetime import datetime, timezone

    l = League(
        tenant_id=uuid.uuid4(),
        name="Gold League",
        tier="gold",
        season_start=datetime.now(timezone.utc),
        season_end=datetime.now(timezone.utc),
    )
    assert l.tier == "gold"
    lc = LeagueCompany(league_id=l.id, company_id=uuid.uuid4(), score=100)
    assert lc.score == 100
