"""Add profile analysis fields for researcher onboarding

Revision ID: 039
Revises: 038
Create Date: 2026-01-10

Adds fields to users table:
- lab_name: Specific lab or research group name
- cv_path: Path to uploaded CV file

Adds fields to lab_profiles table:
- analysis_status: Status of profile analysis (pending, in_progress, completed, failed)
- analysis_started_at: When analysis started
- analysis_completed_at: When analysis completed
- lab_details: Scraped lab info (website, members count, etc.)
- current_funding: Current active funding/grants
- past_work: Past research work
- current_work: Current research projects
- cv_analysis: Extracted info from CV
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '039'
down_revision = '038'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add profile analysis fields to users and lab_profiles tables."""
    # Add lab_name to users table
    op.add_column(
        'users',
        sa.Column(
            'lab_name',
            sa.Text(),
            nullable=True,
        )
    )

    # Add cv_path to users table
    op.add_column(
        'users',
        sa.Column(
            'cv_path',
            sa.Text(),
            nullable=True,
        )
    )

    # Add analysis_status to lab_profiles table
    op.add_column(
        'lab_profiles',
        sa.Column(
            'analysis_status',
            sa.String(20),
            nullable=True,
        )
    )

    # Add analysis_started_at to lab_profiles table
    op.add_column(
        'lab_profiles',
        sa.Column(
            'analysis_started_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        )
    )

    # Add analysis_completed_at to lab_profiles table
    op.add_column(
        'lab_profiles',
        sa.Column(
            'analysis_completed_at',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        )
    )

    # Add lab_details JSONB to lab_profiles table
    op.add_column(
        'lab_profiles',
        sa.Column(
            'lab_details',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        )
    )

    # Add current_funding JSONB to lab_profiles table
    op.add_column(
        'lab_profiles',
        sa.Column(
            'current_funding',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        )
    )

    # Add past_work JSONB to lab_profiles table
    op.add_column(
        'lab_profiles',
        sa.Column(
            'past_work',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        )
    )

    # Add current_work JSONB to lab_profiles table
    op.add_column(
        'lab_profiles',
        sa.Column(
            'current_work',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        )
    )

    # Add cv_analysis JSONB to lab_profiles table
    op.add_column(
        'lab_profiles',
        sa.Column(
            'cv_analysis',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        )
    )

    # Create index on analysis_status for filtering
    op.create_index(
        'ix_lab_profiles_analysis_status',
        'lab_profiles',
        ['analysis_status'],
        unique=False,
    )


def downgrade() -> None:
    """Remove profile analysis fields from users and lab_profiles tables."""
    # Drop index
    op.drop_index('ix_lab_profiles_analysis_status', table_name='lab_profiles')

    # Drop columns from lab_profiles
    op.drop_column('lab_profiles', 'cv_analysis')
    op.drop_column('lab_profiles', 'current_work')
    op.drop_column('lab_profiles', 'past_work')
    op.drop_column('lab_profiles', 'current_funding')
    op.drop_column('lab_profiles', 'lab_details')
    op.drop_column('lab_profiles', 'analysis_completed_at')
    op.drop_column('lab_profiles', 'analysis_started_at')
    op.drop_column('lab_profiles', 'analysis_status')

    # Drop columns from users
    op.drop_column('users', 'cv_path')
    op.drop_column('users', 'lab_name')
