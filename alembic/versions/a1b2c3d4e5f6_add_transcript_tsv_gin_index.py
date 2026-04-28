"""add transcript_tsv column and GIN index on lessons

Revision ID: a1b2c3d4e5f6
Revises: f0cbf12d8626
Create Date: 2026-04-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TSVECTOR

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "dd72c941244c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column("transcript_tsv", TSVECTOR(), nullable=True),
    )
    # GIN index for fast full-text search on transcript
    op.create_index(
        "ix_lessons_transcript_tsv",
        "lessons",
        ["transcript_tsv"],
        postgresql_using="gin",
    )
    # Backfill existing transcripts
    op.execute(
        """
        UPDATE lessons
        SET transcript_tsv = to_tsvector('portuguese', COALESCE(transcript_text->>'full_text', ''))
        WHERE transcript_text IS NOT NULL
          AND transcript_text->>'full_text' IS NOT NULL
          AND transcript_text->>'full_text' <> ''
        """
    )


def downgrade() -> None:
    op.drop_index("ix_lessons_transcript_tsv", table_name="lessons")
    op.drop_column("lessons", "transcript_tsv")
