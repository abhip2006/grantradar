"""Add advanced filter fields to grants table.

Add new columns to support advanced filtering capabilities:
- Career stage eligibility
- Citizenship requirements
- Institution type eligibility
- Award type and duration
- Geographic scope and regions
- Limited submission flag
- Submission types
- Indirect cost policy

Revision ID: 028
Revises: 027
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(index_name: str, table_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx["name"] == index_name for idx in indexes)


def upgrade() -> None:
    """Add advanced filter fields (idempotent)."""
    # Add array columns for eligibility criteria
    if not column_exists("grants", "eligible_career_stages"):
        op.add_column(
            "grants",
            sa.Column(
                "eligible_career_stages",
                postgresql.ARRAY(sa.Text()),
                nullable=True,
                comment="Array of eligible career stages: postdoc, early_career, graduate, etc."
            )
        )
    if not column_exists("grants", "citizenship_requirements"):
        op.add_column(
            "grants",
            sa.Column(
                "citizenship_requirements",
                postgresql.ARRAY(sa.Text()),
                nullable=True,
                comment="Array of citizenship requirements: us_citizen, permanent_resident, any_visa, etc."
            )
        )
    if not column_exists("grants", "eligible_institution_types"):
        op.add_column(
            "grants",
            sa.Column(
                "eligible_institution_types",
                postgresql.ARRAY(sa.Text()),
                nullable=True,
                comment="Array of eligible institution types: r1_university, nonprofit, hbcu, etc."
            )
        )

    # Add award type and duration columns
    if not column_exists("grants", "award_type"):
        op.add_column(
            "grants",
            sa.Column(
                "award_type",
                sa.String(50),
                nullable=True,
                comment="Type of award: research, training, fellowship, career_development, equipment, conference, seed"
            )
        )
    if not column_exists("grants", "award_duration_min_months"):
        op.add_column(
            "grants",
            sa.Column(
                "award_duration_min_months",
                sa.Integer(),
                nullable=True,
                comment="Minimum award duration in months"
            )
        )
    if not column_exists("grants", "award_duration_max_months"):
        op.add_column(
            "grants",
            sa.Column(
                "award_duration_max_months",
                sa.Integer(),
                nullable=True,
                comment="Maximum award duration in months"
            )
        )

    # Add geographic scope columns
    if not column_exists("grants", "geographic_scope"):
        op.add_column(
            "grants",
            sa.Column(
                "geographic_scope",
                sa.String(50),
                nullable=True,
                comment="Geographic scope: national, regional, state, international"
            )
        )
    if not column_exists("grants", "geographic_regions"):
        op.add_column(
            "grants",
            sa.Column(
                "geographic_regions",
                postgresql.ARRAY(sa.Text()),
                nullable=True,
                comment="Array of geographic regions where the grant applies"
            )
        )

    # Add submission-related columns
    if not column_exists("grants", "is_limited_submission"):
        op.add_column(
            "grants",
            sa.Column(
                "is_limited_submission",
                sa.Boolean(),
                server_default="false",
                nullable=False,
                comment="Whether this grant has limited submission restrictions"
            )
        )
    if not column_exists("grants", "submission_types"):
        op.add_column(
            "grants",
            sa.Column(
                "submission_types",
                postgresql.ARRAY(sa.Text()),
                nullable=True,
                comment="Array of submission types: new, resubmission, renewal, supplement"
            )
        )

    # Add indirect cost policy column
    if not column_exists("grants", "indirect_cost_policy"):
        op.add_column(
            "grants",
            sa.Column(
                "indirect_cost_policy",
                sa.String(50),
                nullable=True,
                comment="Indirect cost policy: full, capped, none, training_rate"
            )
        )

    # Create GIN indexes for array columns to enable efficient containment queries
    if not index_exists("ix_grants_eligible_career_stages_gin", "grants"):
        op.create_index(
            "ix_grants_eligible_career_stages_gin",
            "grants",
            ["eligible_career_stages"],
            postgresql_using="gin"
        )
    if not index_exists("ix_grants_citizenship_requirements_gin", "grants"):
        op.create_index(
            "ix_grants_citizenship_requirements_gin",
            "grants",
            ["citizenship_requirements"],
            postgresql_using="gin"
        )
    if not index_exists("ix_grants_eligible_institution_types_gin", "grants"):
        op.create_index(
            "ix_grants_eligible_institution_types_gin",
            "grants",
            ["eligible_institution_types"],
            postgresql_using="gin"
        )
    if not index_exists("ix_grants_geographic_regions_gin", "grants"):
        op.create_index(
            "ix_grants_geographic_regions_gin",
            "grants",
            ["geographic_regions"],
            postgresql_using="gin"
        )
    if not index_exists("ix_grants_submission_types_gin", "grants"):
        op.create_index(
            "ix_grants_submission_types_gin",
            "grants",
            ["submission_types"],
            postgresql_using="gin"
        )

    # Create standard indexes for non-array filter columns
    if not index_exists("ix_grants_award_type", "grants"):
        op.create_index(
            "ix_grants_award_type",
            "grants",
            ["award_type"]
        )
    if not index_exists("ix_grants_geographic_scope", "grants"):
        op.create_index(
            "ix_grants_geographic_scope",
            "grants",
            ["geographic_scope"]
        )
    if not index_exists("ix_grants_is_limited_submission", "grants"):
        op.create_index(
            "ix_grants_is_limited_submission",
            "grants",
            ["is_limited_submission"]
        )
    if not index_exists("ix_grants_indirect_cost_policy", "grants"):
        op.create_index(
            "ix_grants_indirect_cost_policy",
            "grants",
            ["indirect_cost_policy"]
        )


def downgrade() -> None:
    # Drop standard indexes
    op.drop_index("ix_grants_indirect_cost_policy", table_name="grants")
    op.drop_index("ix_grants_is_limited_submission", table_name="grants")
    op.drop_index("ix_grants_geographic_scope", table_name="grants")
    op.drop_index("ix_grants_award_type", table_name="grants")

    # Drop GIN indexes for array columns
    op.drop_index("ix_grants_submission_types_gin", table_name="grants")
    op.drop_index("ix_grants_geographic_regions_gin", table_name="grants")
    op.drop_index("ix_grants_eligible_institution_types_gin", table_name="grants")
    op.drop_index("ix_grants_citizenship_requirements_gin", table_name="grants")
    op.drop_index("ix_grants_eligible_career_stages_gin", table_name="grants")

    # Drop columns in reverse order of addition
    op.drop_column("grants", "indirect_cost_policy")
    op.drop_column("grants", "submission_types")
    op.drop_column("grants", "is_limited_submission")
    op.drop_column("grants", "geographic_regions")
    op.drop_column("grants", "geographic_scope")
    op.drop_column("grants", "award_duration_max_months")
    op.drop_column("grants", "award_duration_min_months")
    op.drop_column("grants", "award_type")
    op.drop_column("grants", "eligible_institution_types")
    op.drop_column("grants", "citizenship_requirements")
    op.drop_column("grants", "eligible_career_stages")
