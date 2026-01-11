"""Add missing columns for matching system

Revision ID: 006
Revises: 005
Create Date: 2025-01-07

Adds columns needed by the grant matching engine:
- lab_profiles: institution, department, keywords, source_text_hash
- matches: vector_similarity, llm_match_score, key_strengths, concerns
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    # Check all tables for the index
    for table_name in inspector.get_table_names():
        indexes = inspector.get_indexes(table_name)
        if any(idx["name"] == index_name for idx in indexes):
            return True
    return False


def upgrade() -> None:
    """Add matching-related columns."""

    # ==========================================================================
    # Add columns to lab_profiles (idempotent)
    # ==========================================================================

    # Institution name (from User, but cached here for faster matching queries)
    if not column_exists("lab_profiles", "institution"):
        op.add_column(
            "lab_profiles",
            sa.Column("institution", sa.Text(), nullable=True),
        )

    # Department within institution
    if not column_exists("lab_profiles", "department"):
        op.add_column(
            "lab_profiles",
            sa.Column("department", sa.Text(), nullable=True),
        )

    # Keywords for matching
    if not column_exists("lab_profiles", "keywords"):
        op.add_column(
            "lab_profiles",
            sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=True),
        )

    # Hash of the text used to generate embedding (for cache invalidation)
    if not column_exists("lab_profiles", "source_text_hash"):
        op.add_column(
            "lab_profiles",
            sa.Column("source_text_hash", sa.String(64), nullable=True),
        )

    # Index on source_text_hash for quick lookups
    if not index_exists("ix_lab_profiles_source_text_hash"):
        op.create_index(
            "ix_lab_profiles_source_text_hash",
            "lab_profiles",
            ["source_text_hash"],
        )

    # ==========================================================================
    # Add columns to matches (idempotent)
    # ==========================================================================

    # Vector similarity score (0-1)
    if not column_exists("matches", "vector_similarity"):
        op.add_column(
            "matches",
            sa.Column("vector_similarity", sa.Float(), nullable=True),
        )

    # LLM match score (0-100)
    if not column_exists("matches", "llm_match_score"):
        op.add_column(
            "matches",
            sa.Column("llm_match_score", sa.Float(), nullable=True),
        )

    # Key strengths identified by LLM
    if not column_exists("matches", "key_strengths"):
        op.add_column(
            "matches",
            sa.Column("key_strengths", postgresql.ARRAY(sa.Text()), nullable=True),
        )

    # Concerns identified by LLM
    if not column_exists("matches", "concerns"):
        op.add_column(
            "matches",
            sa.Column("concerns", postgresql.ARRAY(sa.Text()), nullable=True),
        )


def downgrade() -> None:
    """Remove matching-related columns."""

    # Remove matches columns
    op.drop_column("matches", "concerns")
    op.drop_column("matches", "key_strengths")
    op.drop_column("matches", "llm_match_score")
    op.drop_column("matches", "vector_similarity")

    # Remove lab_profiles columns
    op.drop_index("ix_lab_profiles_source_text_hash", table_name="lab_profiles")
    op.drop_column("lab_profiles", "source_text_hash")
    op.drop_column("lab_profiles", "keywords")
    op.drop_column("lab_profiles", "department")
    op.drop_column("lab_profiles", "institution")
