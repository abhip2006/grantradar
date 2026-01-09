"""Add eligibility fields to lab_profiles table.

Add columns to store user eligibility criteria for smart filtering:
- career_stage: Already exists, keeping for reference
- citizenship_status: User's citizenship/visa status
- institution_type: Type of institution user is affiliated with
- is_pi_eligible: Whether user is eligible to be a PI

These fields will be used to pre-populate eligibility filters when
searching for grants, providing personalized grant recommendations.

Revision ID: 029
Revises: 028
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add citizenship_status column
    op.add_column(
        "lab_profiles",
        sa.Column(
            "citizenship_status",
            sa.String(50),
            nullable=True,
            comment="User citizenship/visa status: us_citizen, permanent_resident, visa_holder, international, etc."
        )
    )

    # Add institution_type column
    op.add_column(
        "lab_profiles",
        sa.Column(
            "institution_type",
            sa.String(50),
            nullable=True,
            comment="Type of institution: r1_university, r2_university, liberal_arts, community_college, nonprofit, industry, government, hbcu, msi, etc."
        )
    )

    # Add is_pi_eligible column
    op.add_column(
        "lab_profiles",
        sa.Column(
            "is_pi_eligible",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="Whether user is eligible to be a Principal Investigator"
        )
    )

    # Create indexes for efficient filtering
    op.create_index(
        "ix_lab_profiles_citizenship_status",
        "lab_profiles",
        ["citizenship_status"]
    )
    op.create_index(
        "ix_lab_profiles_institution_type",
        "lab_profiles",
        ["institution_type"]
    )
    op.create_index(
        "ix_lab_profiles_is_pi_eligible",
        "lab_profiles",
        ["is_pi_eligible"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_lab_profiles_is_pi_eligible", table_name="lab_profiles")
    op.drop_index("ix_lab_profiles_institution_type", table_name="lab_profiles")
    op.drop_index("ix_lab_profiles_citizenship_status", table_name="lab_profiles")

    # Drop columns
    op.drop_column("lab_profiles", "is_pi_eligible")
    op.drop_column("lab_profiles", "institution_type")
    op.drop_column("lab_profiles", "citizenship_status")
