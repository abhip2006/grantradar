"""Authorization utilities for API endpoints."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import GrantApplication


async def verify_card_ownership(db: AsyncSession, card_id: UUID, user_id: UUID) -> bool:
    """
    Verify user owns the kanban card.

    Args:
        db: Database session
        card_id: The UUID of the kanban card (grant application)
        user_id: The UUID of the user to check

    Returns:
        True if the user owns the card

    Raises:
        HTTPException 403 if user does not own the card
        HTTPException 404 if card does not exist
    """
    result = await db.execute(select(GrantApplication).where(GrantApplication.id == card_id))
    card = result.scalar_one_or_none()

    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grant application not found",
        )

    if card.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this grant application",
        )

    return True
