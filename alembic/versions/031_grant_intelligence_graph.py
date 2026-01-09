"""Add Grant Intelligence Graph tables

Revision ID: 031
Revises: 030
Create Date: 2026-01-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = '031'
down_revision: Union[str, None] = '030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
        sa.Column('award_date', sa.Date()),
        sa.Column('project_start', sa.Date()),
        sa.Column('project_end', sa.Date()),
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

    # Grant Mechanisms table - stores success rates and metadata per mechanism
    op.create_table(
        'grant_mechanisms',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.Text(), nullable=False, unique=True),  # R01, R21, K01
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('funding_agency', sa.Text()),  # NIH, NSF
        sa.Column('category', sa.Text()),  # research, career, training, center
        sa.Column('typical_duration_months', sa.Integer()),
        sa.Column('typical_budget_min', sa.Integer()),
        sa.Column('typical_budget_max', sa.Integer()),
        sa.Column('success_rate_overall', sa.Float()),
        sa.Column('success_rate_new', sa.Float()),  # New applications
        sa.Column('success_rate_renewal', sa.Float()),  # Renewals
        sa.Column('success_rate_resubmission', sa.Float()),
        sa.Column('avg_review_score_funded', sa.Float()),
        sa.Column('competition_level', sa.Text()),  # low, medium, high, very_high
        sa.Column('estimated_applicants_per_cycle', sa.Integer()),
        sa.Column('review_criteria', JSONB()),  # Structured review criteria
        sa.Column('eligibility_notes', sa.Text()),
        sa.Column('tips', JSONB()),  # Array of tips for applicants
        sa.Column('last_updated', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # Competition Snapshots - periodic snapshots of competition data
    op.create_table(
        'competition_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('grant_id', UUID(as_uuid=True), sa.ForeignKey('grants.id', ondelete='CASCADE')),
        sa.Column('mechanism_id', UUID(as_uuid=True), sa.ForeignKey('grant_mechanisms.id', ondelete='SET NULL')),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('estimated_applicants', sa.Integer()),
        sa.Column('similar_grants_count', sa.Integer()),  # How many similar grants open
        sa.Column('competition_score', sa.Float()),  # 0-1, higher = more competitive
        sa.Column('factors', JSONB()),  # Explanation of competition factors
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_competition_snapshots_grant_id', 'competition_snapshots', ['grant_id'])


def downgrade() -> None:
    op.drop_table('competition_snapshots')
    op.drop_table('grant_mechanisms')
    op.drop_table('funded_projects')
