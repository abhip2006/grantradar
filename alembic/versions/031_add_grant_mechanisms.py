"""Add grant_mechanisms table for NIH and NSF mechanism data

Revision ID: 031_grant_mechanisms
Revises: 030_outcome_tracking
Create Date: 2026-01-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '031'
down_revision: Union[str, None] = '030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create grant_mechanisms table
    op.create_table(
        'grant_mechanisms',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('funding_agency', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('typical_duration_months', sa.Integer(), nullable=True),
        sa.Column('typical_budget_min', sa.Integer(), nullable=True),
        sa.Column('typical_budget_max', sa.Integer(), nullable=True),
        sa.Column('success_rate_overall', sa.Float(), nullable=True),
        sa.Column('success_rate_new', sa.Float(), nullable=True),
        sa.Column('success_rate_renewal', sa.Float(), nullable=True),
        sa.Column('success_rate_resubmission', sa.Float(), nullable=True),
        sa.Column('competition_level', sa.String(length=30), nullable=True),
        sa.Column('estimated_applicants_per_cycle', sa.Integer(), nullable=True),
        sa.Column('review_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tips', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_updated', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_grant_mechanisms_code'),
    )

    # Create indexes
    op.create_index('ix_grant_mechanisms_code', 'grant_mechanisms', ['code'])
    op.create_index('ix_grant_mechanisms_funding_agency', 'grant_mechanisms', ['funding_agency'])
    op.create_index('ix_grant_mechanisms_category', 'grant_mechanisms', ['category'])
    op.create_index('ix_grant_mechanisms_competition_level', 'grant_mechanisms', ['competition_level'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_grant_mechanisms_competition_level', table_name='grant_mechanisms')
    op.drop_index('ix_grant_mechanisms_category', table_name='grant_mechanisms')
    op.drop_index('ix_grant_mechanisms_funding_agency', table_name='grant_mechanisms')
    op.drop_index('ix_grant_mechanisms_code', table_name='grant_mechanisms')

    # Drop table
    op.drop_table('grant_mechanisms')
