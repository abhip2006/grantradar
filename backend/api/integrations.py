"""
Calendar Integration API Endpoints
Google Calendar OAuth and sync functionality.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import and_, select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.core.config import settings
from backend.models import CalendarIntegration, Deadline
from backend.schemas.integrations import (
    CalendarIntegrationResponse,
    CalendarStatusResponse,
    ProviderStatus,
    SyncResponse,
    UpdateIntegrationRequest,
)
from backend.services.google_calendar import GoogleCalendarService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrations/calendar", tags=["Calendar Integrations"])


@router.get(
    "/status",
    response_model=CalendarStatusResponse,
    summary="Get calendar integration status",
    description="Get calendar integration status for all providers.",
)
async def get_integration_status(
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> CalendarStatusResponse:
    """
    Get calendar integration status for all providers.

    Returns connection status, calendar ID, last sync time,
    and sync enabled state for Google and Outlook.
    """
    result = await db.execute(select(CalendarIntegration).where(CalendarIntegration.user_id == current_user.id))
    integrations = result.scalars().all()

    google_integration = next((i for i in integrations if i.provider == "google"), None)
    outlook_integration = next((i for i in integrations if i.provider == "outlook"), None)

    return CalendarStatusResponse(
        google=ProviderStatus(
            connected=google_integration is not None,
            calendar_id=google_integration.calendar_id if google_integration else None,
            last_synced_at=(
                google_integration.last_synced_at.isoformat()
                if google_integration and google_integration.last_synced_at
                else None
            ),
            sync_enabled=google_integration.sync_enabled if google_integration else False,
        ),
        outlook=ProviderStatus(
            connected=outlook_integration is not None,
            calendar_id=outlook_integration.calendar_id if outlook_integration else None,
            last_synced_at=(
                outlook_integration.last_synced_at.isoformat()
                if outlook_integration and outlook_integration.last_synced_at
                else None
            ),
            sync_enabled=outlook_integration.sync_enabled if outlook_integration else False,
        ),
    )


@router.post(
    "/google/connect",
    summary="Connect Google Calendar",
    description="Initiate Google Calendar OAuth flow.",
)
async def connect_google_calendar(
    current_user: CurrentUser,
) -> dict:
    """
    Initiate Google Calendar OAuth flow.

    Returns the authorization URL to redirect the user to.
    """
    service = GoogleCalendarService()
    auth_url = service.get_authorization_url(user_id=str(current_user.id))
    return {"auth_url": auth_url}


@router.get(
    "/google/callback",
    summary="Google OAuth callback",
    description="Handle Google OAuth callback.",
)
async def google_oauth_callback(
    db: AsyncSessionDep,
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for CSRF protection"),
) -> RedirectResponse:
    """
    Handle Google OAuth callback.

    Exchanges the authorization code for tokens and stores them.
    Redirects to the frontend settings page with success/error status.
    """
    try:
        service = GoogleCalendarService()
        user_id, tokens = service.handle_callback(code=code, state=state)

        # Check for existing integration
        result = await db.execute(
            select(CalendarIntegration).where(
                and_(
                    CalendarIntegration.user_id == UUID(user_id),
                    CalendarIntegration.provider == "google",
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing integration
            existing.access_token = tokens["access_token"]
            existing.refresh_token = tokens.get("refresh_token", existing.refresh_token)
            existing.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])
            existing.updated_at = datetime.now(timezone.utc)
        else:
            # Create new integration
            integration = CalendarIntegration(
                user_id=UUID(user_id),
                provider="google",
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"]),
                calendar_id="primary",  # Default to primary calendar
                sync_enabled=True,
            )
            db.add(integration)

        await db.commit()

        # Redirect to settings page with success
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings/integrations?google=connected",
            status_code=status.HTTP_302_FOUND,
        )

    except Exception as e:
        logger.error(f"Google OAuth callback failed: {e}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings/integrations?google=error&message={str(e)}",
            status_code=status.HTTP_302_FOUND,
        )


@router.delete(
    "/google",
    summary="Disconnect Google Calendar",
    description="Disconnect Google Calendar integration.",
)
async def disconnect_google_calendar(
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> dict:
    """
    Disconnect Google Calendar integration.

    Removes the stored OAuth tokens and integration record.
    """
    result = await db.execute(
        select(CalendarIntegration).where(
            and_(
                CalendarIntegration.user_id == current_user.id,
                CalendarIntegration.provider == "google",
            )
        )
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Calendar not connected",
        )

    await db.delete(integration)
    await db.commit()

    return {"message": "Google Calendar disconnected"}


@router.patch(
    "/google",
    response_model=CalendarIntegrationResponse,
    summary="Update Google Calendar settings",
    description="Update Google Calendar integration settings.",
)
async def update_google_integration(
    data: UpdateIntegrationRequest,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> CalendarIntegrationResponse:
    """
    Update Google Calendar integration settings.

    Currently supports enabling/disabling sync.
    """
    result = await db.execute(
        select(CalendarIntegration).where(
            and_(
                CalendarIntegration.user_id == current_user.id,
                CalendarIntegration.provider == "google",
            )
        )
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Calendar not connected",
        )

    integration.sync_enabled = data.sync_enabled
    integration.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(integration)

    return CalendarIntegrationResponse.model_validate(integration)


@router.post(
    "/google/sync",
    response_model=SyncResponse,
    summary="Sync to Google Calendar",
    description="Manually trigger sync of deadlines to Google Calendar.",
)
async def sync_google_calendar(
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> SyncResponse:
    """
    Manually trigger sync of deadlines to Google Calendar.

    Syncs all active deadlines with future sponsor_deadline dates.
    """
    # Get integration
    result = await db.execute(
        select(CalendarIntegration).where(
            and_(
                CalendarIntegration.user_id == current_user.id,
                CalendarIntegration.provider == "google",
            )
        )
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Calendar not connected",
        )

    if not integration.sync_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Calendar sync is disabled",
        )

    # Get user's active deadlines
    result = await db.execute(
        select(Deadline).where(
            and_(
                Deadline.user_id == current_user.id,
                Deadline.status == "active",
                Deadline.sponsor_deadline >= datetime.now(timezone.utc),
            )
        )
    )
    deadlines = result.scalars().all()

    # Sync to Google Calendar
    service = GoogleCalendarService()
    synced_count = await service.sync_deadlines(
        integration=integration,
        deadlines=deadlines,
        db=db,
    )

    # Update last synced timestamp
    integration.last_synced_at = datetime.now(timezone.utc)
    await db.commit()

    return SyncResponse(
        synced_count=synced_count,
        last_synced_at=integration.last_synced_at,
    )


@router.get(
    "/google",
    response_model=CalendarIntegrationResponse,
    summary="Get Google Calendar integration",
    description="Get Google Calendar integration details.",
)
async def get_google_integration(
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> CalendarIntegrationResponse:
    """
    Get Google Calendar integration details.
    """
    result = await db.execute(
        select(CalendarIntegration).where(
            and_(
                CalendarIntegration.user_id == current_user.id,
                CalendarIntegration.provider == "google",
            )
        )
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Calendar not connected",
        )

    return CalendarIntegrationResponse.model_validate(integration)


@router.get(
    "/google/calendars",
    summary="List Google calendars",
    description="Get list of user's Google calendars for selection.",
)
async def list_google_calendars(
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> dict:
    """
    Get list of user's Google calendars.

    Returns available calendars so user can select which one to sync to.
    """
    result = await db.execute(
        select(CalendarIntegration).where(
            and_(
                CalendarIntegration.user_id == current_user.id,
                CalendarIntegration.provider == "google",
            )
        )
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Calendar not connected",
        )

    service = GoogleCalendarService()

    # Refresh token if needed
    if integration.token_expires_at and integration.token_expires_at < datetime.now(timezone.utc):
        tokens = await service.refresh_token(integration.refresh_token)
        integration.access_token = tokens["access_token"]
        integration.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])
        await db.commit()

    calendars = await service.get_calendars(integration.access_token)

    return {
        "calendars": calendars,
        "current_calendar_id": integration.calendar_id,
    }


@router.patch(
    "/google/calendar",
    response_model=CalendarIntegrationResponse,
    summary="Set target calendar",
    description="Set which Google calendar to sync deadlines to.",
)
async def set_google_calendar(
    calendar_id: str = Query(..., description="Google Calendar ID to sync to"),
    current_user: CurrentUser = None,
    db: AsyncSessionDep = None,
) -> CalendarIntegrationResponse:
    """
    Set which Google calendar to sync deadlines to.
    """
    result = await db.execute(
        select(CalendarIntegration).where(
            and_(
                CalendarIntegration.user_id == current_user.id,
                CalendarIntegration.provider == "google",
            )
        )
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Calendar not connected",
        )

    integration.calendar_id = calendar_id
    integration.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(integration)

    return CalendarIntegrationResponse.model_validate(integration)
