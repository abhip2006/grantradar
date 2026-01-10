"""
Notification Preferences API Endpoints
Manage user notification settings.
"""

from fastapi import APIRouter

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.schemas.preferences import (
    DigestFrequency,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
)

router = APIRouter(prefix="/api/preferences", tags=["Preferences"])


@router.get(
    "",
    response_model=NotificationPreferencesResponse,
    summary="Get notification preferences",
    description="Get the current user's notification preferences.",
)
async def get_preferences(
    current_user: CurrentUser,
) -> NotificationPreferencesResponse:
    """
    Get the notification preferences for the authenticated user.

    Returns:
        NotificationPreferencesResponse: Current notification settings including
        email/SMS/Slack toggles, digest frequency, and minimum match score threshold.
    """
    return NotificationPreferencesResponse(
        email_notifications=current_user.email_notifications,
        sms_notifications=current_user.sms_notifications,
        slack_notifications=current_user.slack_notifications,
        digest_frequency=DigestFrequency(current_user.digest_frequency),
        minimum_match_score=current_user.minimum_match_score,
    )


@router.put(
    "",
    response_model=NotificationPreferencesResponse,
    summary="Update notification preferences",
    description="Update the current user's notification preferences.",
)
async def update_preferences(
    preferences: NotificationPreferencesUpdate,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> NotificationPreferencesResponse:
    """
    Update notification preferences for the authenticated user.

    Only fields included in the request will be updated.
    Omitted fields will retain their current values.

    Args:
        preferences: Partial update containing fields to modify.

    Returns:
        NotificationPreferencesResponse: Updated notification settings.
    """
    # Update only provided fields
    update_data = preferences.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(current_user, field):
            # Convert enum to string for digest_frequency
            if field == "digest_frequency" and value is not None:
                value = value.value if isinstance(value, DigestFrequency) else value
            setattr(current_user, field, value)

    await db.flush()
    await db.refresh(current_user)

    return NotificationPreferencesResponse(
        email_notifications=current_user.email_notifications,
        sms_notifications=current_user.sms_notifications,
        slack_notifications=current_user.slack_notifications,
        digest_frequency=DigestFrequency(current_user.digest_frequency),
        minimum_match_score=current_user.minimum_match_score,
    )
