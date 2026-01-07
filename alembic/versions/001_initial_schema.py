"""Initial schema with pgvector support

Revision ID: 001
Revises:
Create Date: 2025-01-06

Creates all tables for the GrantRadar grant intelligence platform:
- grants: Grant opportunities with vector embeddings
- users: User accounts and authentication
- lab_profiles: Research profiles for matching
- matches: Grant-to-user match results
- alerts_sent: Notification delivery tracking
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ==========================================================================
    # Create grants table
    # ==========================================================================
    op.create_table(
        "grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("agency", sa.Text(), nullable=True),
        sa.Column("amount_min", sa.Integer(), nullable=True),
        sa.Column("amount_max", sa.Integer(), nullable=True),
        sa.Column("deadline", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("posted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("eligibility", postgresql.JSONB(), nullable=True),
        sa.Column("categories", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Grants indexes
    op.create_index(
        "ix_grants_posted_at_desc",
        "grants",
        [sa.text("posted_at DESC")],
    )
    op.create_index(
        "ix_grants_deadline_asc",
        "grants",
        [sa.text("deadline ASC")],
    )
    op.create_index(
        "ix_grants_source",
        "grants",
        ["source"],
    )

    # Vector similarity index for grants (IVFFlat)
    op.execute(
        """
        CREATE INDEX ix_grants_embedding
        ON grants
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    # ==========================================================================
    # Create users table
    # ==========================================================================
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("institution", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True),
    )

    op.create_index("ix_users_email", "users", ["email"])

    # ==========================================================================
    # Create lab_profiles table
    # ==========================================================================
    op.create_table(
        "lab_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("research_areas", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("methods", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("career_stage", sa.Text(), nullable=True),
        sa.Column("past_grants", postgresql.JSONB(), nullable=True),
        sa.Column("publications", postgresql.JSONB(), nullable=True),
        sa.Column("orcid", sa.Text(), nullable=True),
        sa.Column("profile_embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Lab profiles indexes
    op.create_index("ix_lab_profiles_user_id", "lab_profiles", ["user_id"])

    # Vector similarity index for lab profiles (IVFFlat)
    op.execute(
        """
        CREATE INDEX ix_lab_profiles_embedding
        ON lab_profiles
        USING ivfflat (profile_embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    # ==========================================================================
    # Create matches table
    # ==========================================================================
    op.create_table(
        "matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "grant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("grants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("predicted_success", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("user_action", sa.Text(), nullable=True),
        sa.Column("user_feedback", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("grant_id", "user_id", name="uq_matches_grant_user"),
    )

    # Matches indexes
    op.create_index("ix_matches_grant_id", "matches", ["grant_id"])
    op.create_index("ix_matches_user_id", "matches", ["user_id"])
    op.create_index(
        "ix_matches_score_desc",
        "matches",
        [sa.text("match_score DESC")],
    )

    # ==========================================================================
    # Create alerts_sent table
    # ==========================================================================
    op.create_table(
        "alerts_sent",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "match_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("matches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column(
            "sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("opened_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("clicked_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Alerts indexes
    op.create_index("ix_alerts_sent_match_id", "alerts_sent", ["match_id"])
    op.create_index("ix_alerts_sent_channel", "alerts_sent", ["channel"])
    op.create_index(
        "ix_alerts_sent_sent_at_desc",
        "alerts_sent",
        [sa.text("sent_at DESC")],
    )


def downgrade() -> None:
    """Drop all tables and extensions."""

    # Drop tables in reverse order of creation (due to foreign keys)
    op.drop_table("alerts_sent")
    op.drop_table("matches")
    op.drop_table("lab_profiles")
    op.drop_table("users")
    op.drop_table("grants")

    # Drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector")
