"""
GrantRadar Admin Seed Endpoint
One-time endpoint for seeding demo/test data into the database.
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class SeedResponse(BaseModel):
    """Response model for seed operation."""

    success: bool
    message: str
    users_created: int = 0
    grants_created: int = 0
    applications_created: int = 0
    details: dict[str, Any] | None = None


router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.post(
    "/seed-users",
    response_model=SeedResponse,
    summary="Seed demo users",
    description="One-time endpoint to seed demo/test users into the database.",
)
async def seed_demo_users_endpoint(secret: str | None = None) -> SeedResponse:
    """
    Seed demo users into the database.

    This endpoint is protected by requiring a secret key that matches
    the ADMIN_SEED_SECRET environment variable.
    """
    # Get the seed secret from environment
    expected_secret = os.getenv("ADMIN_SEED_SECRET", "")

    # If no secret is configured, allow seeding (useful for initial setup)
    # In production, you should set ADMIN_SEED_SECRET
    if expected_secret and secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing seed secret",
        )

    try:
        # Import the seed function
        from backend.scripts.seed_data import seed_demo_users as do_seed

        # Run the seed operation
        async with AsyncSessionLocal() as session:
            created_users = await do_seed(session)
            await session.commit()

        return SeedResponse(
            success=True,
            message=f"Successfully seeded {len(created_users)} demo users",
            users_created=len(created_users),
            details={"users": [u.email for u in created_users]},
        )

    except Exception as e:
        logger.exception(f"Failed to seed users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed users: {str(e)}",
        )


@router.post(
    "/seed-all",
    response_model=SeedResponse,
    summary="Seed all demo data",
    description="Seed all demo data including users, grants, applications, and teams.",
)
async def seed_all_demo_data(secret: str | None = None) -> SeedResponse:
    """
    Seed all demo data into the database.

    This endpoint seeds users, grants, applications, teams, and notifications.
    """
    # Get the seed secret from environment
    expected_secret = os.getenv("ADMIN_SEED_SECRET", "")

    if expected_secret and secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing seed secret",
        )

    try:
        from backend.scripts.seed_data import (
            seed_demo_users,
            seed_demo_grants,
            seed_demo_applications,
            seed_demo_team,
            seed_demo_notifications,
        )

        async with AsyncSessionLocal() as session:
            # Seed users
            users = await seed_demo_users(session)
            await session.commit()

            # Seed grants
            grants = await seed_demo_grants(session)
            await session.commit()

            # Seed applications (requires users and grants)
            apps = await seed_demo_applications(session, users, grants)

            # Seed team
            await seed_demo_team(session, users)

            # Seed notifications
            await seed_demo_notifications(session, users)

        return SeedResponse(
            success=True,
            message=f"Successfully seeded {len(users)} users, {len(grants)} grants, {len(apps)} applications",
            users_created=len(users),
            grants_created=len(grants),
            applications_created=len(apps),
            details={
                "users": [u.email for u in users if hasattr(u, 'email')],
                "grants": len(grants),
                "applications": len(apps),
            },
        )

    except Exception as e:
        logger.exception(f"Failed to seed data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed data: {str(e)}",
        )


@router.post(
    "/seed-grants",
    response_model=SeedResponse,
    summary="Seed demo grants only",
    description="Seed demo grants into the database.",
)
async def seed_grants_only(secret: str | None = None) -> SeedResponse:
    """
    Seed demo grants into the database.

    This endpoint only seeds grants, not users or applications.
    """
    expected_secret = os.getenv("ADMIN_SEED_SECRET", "")

    if expected_secret and secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing seed secret",
        )

    try:
        from backend.scripts.seed_data import seed_demo_grants

        async with AsyncSessionLocal() as session:
            grants = await seed_demo_grants(session)
            await session.commit()

        return SeedResponse(
            success=True,
            message=f"Successfully seeded {len(grants)} demo grants",
            grants_created=len(grants),
            details={"grants": [g.title[:50] for g in grants if hasattr(g, 'title')]},
        )

    except Exception as e:
        logger.exception(f"Failed to seed grants: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed grants: {str(e)}",
        )


@router.get(
    "/seed-status",
    summary="Check seed status",
    description="Check if demo data has already been seeded.",
)
async def check_seed_status() -> dict[str, Any]:
    """Check if demo data exist in the database."""
    from sqlalchemy import select, func

    from backend.models import User, Grant

    demo_emails = [
        "admin@grantradar.com",
        "test.user1@grantradar.com",
        "test.user2@grantradar.com",
    ]

    try:
        async with AsyncSessionLocal() as session:
            # Check users
            result = await session.execute(
                select(User.email).where(User.email.in_(demo_emails))
            )
            existing_emails = [row[0] for row in result.fetchall()]

            # Check grants (count demo grants)
            result = await session.execute(
                select(func.count(Grant.id)).where(Grant.external_id.startswith("DEMO-GRANT-"))
            )
            demo_grant_count = result.scalar() or 0

            # Count total grants
            result = await session.execute(select(func.count(Grant.id)))
            total_grant_count = result.scalar() or 0

        return {
            "seeded": len(existing_emails) > 0 and demo_grant_count > 0,
            "users": {
                "seeded": len(existing_emails) > 0,
                "existing": existing_emails,
                "expected": demo_emails,
            },
            "grants": {
                "seeded": demo_grant_count > 0,
                "demo_grants": demo_grant_count,
                "total_grants": total_grant_count,
            },
        }
    except Exception as e:
        logger.exception(f"Failed to check seed status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check seed status: {str(e)}",
        )
