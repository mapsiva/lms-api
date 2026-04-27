"""Unit tests for community models."""
import uuid

import pytest

from app.models.community import Channel, Comment, Post, PostLike, Report, Space


def test_space_fields():
    s = Space(tenant_id=uuid.uuid4(), name="General", is_active=True)
    assert s.name == "General"
    assert s.is_active is True


def test_channel_fields():
    c = Channel(
        space_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name="Q&A",
        post_policy="open",
        channel_type="discussion",
    )
    assert c.post_policy == "open"
    assert c.channel_type == "discussion"


def test_post_fields():
    p = Post(
        channel_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        body="Hello",
        likes_count=0,
        comments_count=0,
        is_hidden=False,
    )
    assert p.likes_count == 0
    assert p.comments_count == 0
    assert p.is_hidden is False


def test_comment_fields():
    c = Comment(
        post_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        body="Reply",
        is_hidden=False,
    )
    assert c.is_hidden is False


def test_post_like_init():
    pl = PostLike(user_id=uuid.uuid4(), post_id=uuid.uuid4())
    assert pl.user_id is not None
    assert pl.post_id is not None


def test_report_fields():
    r = Report(
        tenant_id=uuid.uuid4(),
        post_id=uuid.uuid4(),
        reporter_id=uuid.uuid4(),
        reason="spam",
        ai_flagged=False,
        status="pending",
    )
    assert r.ai_flagged is False
    assert r.status == "pending"
