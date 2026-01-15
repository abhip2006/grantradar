"""
GrantRadar Admin Seed Endpoint
One-time endpoint for seeding demo/test users into the database.
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


@router.get(
    "/seed-status",
    summary="Check seed status",
    description="Check if demo users have already been seeded.",
)
async def check_seed_status() -> dict[str, Any]:
    """Check if demo users exist in the database."""
    from sqlalchemy import select

    from backend.models import User

    demo_emails = [
        "admin@grantradar.com",
        "test.user1@grantradar.com",
        "test.user2@grantradar.com",
    ]

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User.email).where(User.email.in_(demo_emails))
            )
            existing_emails = [row[0] for row in result.fetchall()]

        return {
            "seeded": len(existing_emails) > 0,
            "existing_users": existing_emails,
            "expected_users": demo_emails,
        }
    except Exception as e:
        logger.exception(f"Failed to check seed status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check seed status: {str(e)}",
        )
