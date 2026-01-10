"""Funding alerts API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models import User
from backend.schemas.alerts import (
    FundingAlertPreferencesCreate,
    FundingAlertPreferencesResponse,
    FundingAlertPreview,
)
from backend.services.funding_alerts import FundingAlertsService

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

alerts_service = FundingAlertsService()


@router.get("/preferences", response_model=FundingAlertPreferencesResponse)
async def get_alert_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FundingAlertPreferencesResponse:
    """Get user's funding alert preferences."""
    prefs = await alerts_service.get_or_create_preferences(db, current_user.id)
    return FundingAlertPreferencesResponse.model_validate(prefs)


@router.put("/preferences", response_model=FundingAlertPreferencesResponse)
async def update_alert_preferences(
    request: FundingAlertPreferencesCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FundingAlertPreferencesResponse:
    """Update user's funding alert preferences."""
    prefs = await alerts_service.update_preferences(
        db=db,
        user_id=current_user.id,
        enabled=request.enabled,
        frequency=request.frequency,
        min_match_score=request.min_match_score,
        include_deadlines=request.include_deadlines,
        include_new_grants=request.include_new_grants,
        include_insights=request.include_insights,
        preferred_funders=request.preferred_funders,
    )
    return FundingAlertPreferencesResponse.model_validate(prefs)


@router.get("/preview", response_model=FundingAlertPreview)
async def preview_alert(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FundingAlertPreview:
    """
    Preview what the next funding alert email would contain.

    Useful for testing alert configuration before waiting for scheduled delivery.
    """
    return await alerts_service.preview_alert(db, current_user)


@router.post("/send-now")
async def send_alert_now(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger immediate delivery of funding alert (for testing)."""
    from backend.tasks.funding_alerts import send_funding_alert

    # Queue the Celery task
    send_funding_alert.delay(str(current_user.id))

    return {"message": "Alert email queued for delivery", "user_id": str(current_user.id)}
