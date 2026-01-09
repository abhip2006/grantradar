"""Add Grant Intelligence Graph tables (funded_projects, competition_snapshots)
and new columns to grant_mechanisms

Revision ID: 032
Revises: 031
Create Date: 2026-01-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = '032'
down_revision: Union[str, None] = '031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to existing grant_mechanisms table
    op.add_column(
        'grant_mechanisms',
        sa.Column('avg_review_score_funded', sa.Float(), nullable=True)
    )
    op.add_column(
        'grant_mechanisms',
        sa.Column('eligibility_notes', sa.Text(), nullable=True)
    )
    # Make last_updated nullable (it was not nullable in the original migration)
    op.alter_column(
        'grant_mechanisms',
        'last_updated',
        existing_type=sa.TIMESTAMP(timezone=True),
        nullable=True
    )

    # Funded Projects table - stores historical funded grants from NIH Reporter
    op.create_table(
        'funded_projects',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('source', sa.Text(), nullable=False),  # 'nih', 'nsf'
        sa.Column('external_id', sa.Text(), nullable=False, unique=True),  # NIH project number
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('abstract', sa.Text()),
        sa.Column('mechanism', sa.Text()),  # R01, R21, K01, etc.
        sa.Column('activity_code', sa.Text()),
        sa.Column('funding_agency', sa.Text()),
        sa.Column('funding_institute', sa.Text()),  # NCI, NHLBI, etc.
        sa.Column('award_amount', sa.Integer()),
        sa.Column('award_date', sa.TIMESTAMP(timezone=True)),
        sa.Column('project_start', sa.TIMESTAMP(timezone=True)),
        sa.Column('project_end', sa.TIMESTAMP(timezone=True)),
        sa.Column('pi_name', sa.Text()),
        sa.Column('pi_institution', sa.Text()),
        sa.Column('pi_institution_type', sa.Text()),  # university, research_institute, etc.
        sa.Column('fiscal_year', sa.Integer()),
        sa.Column('is_new', sa.Boolean()),  # New vs renewal
        sa.Column('keywords', JSONB()),
        sa.Column('raw_data', JSONB()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_funded_projects_mechanism', 'funded_projects', ['mechanism'])
    op.create_index('ix_funded_projects_fiscal_year', 'funded_projects', ['fiscal_year'])
    op.create_index('ix_funded_projects_funding_institute', 'funded_projects', ['funding_institute'])
    op.create_index('ix_funded_projects_source', 'funded_projects', ['source'])

    # Competition Snapshots - periodic snapshots of competition data
    op.create_table(
        'competition_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('grant_id', UUID(as_uuid=True), sa.ForeignKey('grants.id', ondelete='CASCADE')),
        sa.Column('mechanism_id', UUID(as_uuid=True), sa.ForeignKey('grant_mechanisms.id', ondelete='SET NULL')),
        sa.Column('snapshot_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('estimated_applicants', sa.Integer()),
        sa.Column('similar_grants_count', sa.Integer()),  # How many similar grants open
        sa.Column('competition_score', sa.Float()),  # 0-1, higher = more competitive
        sa.Column('factors', JSONB()),  # Explanation of competition factors
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_competition_snapshots_grant_id', 'competition_snapshots', ['grant_id'])
    op.create_index('ix_competition_snapshots_mechanism_id', 'competition_snapshots', ['mechanism_id'])
    op.create_index('ix_competition_snapshots_snapshot_date', 'competition_snapshots', ['snapshot_date'])


def downgrade() -> None:
    # Drop competition_snapshots table and indexes
    op.drop_index('ix_competition_snapshots_snapshot_date', table_name='competition_snapshots')
    op.drop_index('ix_competition_snapshots_mechanism_id', table_name='competition_snapshots')
    op.drop_index('ix_competition_snapshots_grant_id', table_name='competition_snapshots')
    op.drop_table('competition_snapshots')

    # Drop funded_projects table and indexes
    op.drop_index('ix_funded_projects_source', table_name='funded_projects')
    op.drop_index('ix_funded_projects_funding_institute', table_name='funded_projects')
    op.drop_index('ix_funded_projects_fiscal_year', table_name='funded_projects')
    op.drop_index('ix_funded_projects_mechanism', table_name='funded_projects')
    op.drop_table('funded_projects')

    # Remove new columns from grant_mechanisms
    op.drop_column('grant_mechanisms', 'eligibility_notes')
    op.drop_column('grant_mechanisms', 'avg_review_score_funded')

    # Restore last_updated to not nullable
    op.alter_column(
        'grant_mechanisms',
        'last_updated',
        existing_type=sa.TIMESTAMP(timezone=True),
        nullable=False
    )
