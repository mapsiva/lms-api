"""add is_pinned to posts

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default="false"))
    op.create_index("ix_posts_channel_pinned", "posts", ["channel_id", "is_pinned"])


def downgrade() -> None:
    op.drop_index("ix_posts_channel_pinned", table_name="posts")
    op.drop_column("posts", "is_pinned")
