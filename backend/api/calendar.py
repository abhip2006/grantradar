"""
Calendar API Endpoints
Export grant deadlines to ICS format, generate calendar links,
and provide calendar view data for deadline tracking.
"""

from calendar import monthrange
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import and_, select
from sqlalchemy.orm import joinedload

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import Grant, GrantApplication, Match
from backend.schemas.calendar import (
    CalendarDay,
    CalendarDeadlinesResponse,
    CalendarEvent,
    CalendarEventType,
    CalendarMonthResponse,
    UpcomingDeadline,
    UpcomingDeadlinesResponse,
    UrgencyLevel,
)

router = APIRouter(prefix="/api/calendar", tags=["Calendar"])


def generate_ics_event(
    uid: str,
    title: str,
    description: str,
    deadline: datetime,
    url: Optional[str] = None,
    agency: Optional[str] = None,
    amount_max: Optional[int] = None,
) -> str:
    """
    Generate a single ICS VEVENT block.

    Args:
        uid: Unique identifier for the event
        title: Event title (grant title)
        description: Event description
        deadline: Grant deadline datetime
        url: Grant URL
        agency: Funding agency
        amount_max: Maximum funding amount

    Returns:
        ICS formatted VEVENT string
    """
    # Format datetime for ICS (YYYYMMDDTHHMMSSZ)
    dtstart = deadline.strftime("%Y%m%dT%H%M%SZ")
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Build description with grant details
    desc_parts = []
    if agency:
        desc_parts.append(f"Agency: {agency}")
    if amount_max:
        desc_parts.append(f"Funding: ${amount_max:,}")
    if description:
        # Truncate long descriptions
        truncated = description[:500] + "..." if len(description) > 500 else description
        desc_parts.append(f"\n{truncated}")
    if url:
        desc_parts.append(f"\nMore info: {url}")

    full_description = "\\n".join(desc_parts).replace("\n", "\\n").replace(",", "\\,")

    # Escape special characters in title
    safe_title = title.replace(",", "\\,").replace("\n", " ")

    event = f"""BEGIN:VEVENT
UID:{uid}@grantradar.com
DTSTAMP:{dtstamp}
DTSTART:{dtstart}
DTEND:{dtstart}
SUMMARY:DEADLINE: {safe_title}
DESCRIPTION:{full_description}
STATUS:CONFIRMED
TRANSP:TRANSPARENT
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Grant deadline in 1 week
TRIGGER:-P7D
END:VALARM
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Grant deadline in 1 day
TRIGGER:-P1D
END:VALARM
END:VEVENT"""

    return event


def generate_ics_calendar(events: list[str], calendar_name: str = "GrantRadar Deadlines") -> str:
    """
    Generate a complete ICS calendar file.

    Args:
        events: List of VEVENT strings
        calendar_name: Name of the calendar

    Returns:
        Complete ICS file content
    """
    events_str = "\n".join(events)

    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//GrantRadar//Grant Deadlines//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:{calendar_name}
X-WR-TIMEZONE:UTC
{events_str}
END:VCALENDAR"""


def generate_google_calendar_url(
    title: str,
    deadline: datetime,
    description: str = "",
    url: Optional[str] = None,
) -> str:
    """
    Generate a Google Calendar add event URL.

    Args:
        title: Event title
        deadline: Event datetime
        description: Event description
        url: Link to include

    Returns:
        Google Calendar URL
    """
    import urllib.parse

    # Format dates for Google Calendar (YYYYMMDDTHHMMSSZ)
    date_str = deadline.strftime("%Y%m%dT%H%M%SZ")

    # Build description
    desc = description[:500] if description else ""
    if url:
        desc = f"{desc}\n\nMore info: {url}" if desc else f"More info: {url}"

    params = {
        "action": "TEMPLATE",
        "text": f"DEADLINE: {title}",
        "dates": f"{date_str}/{date_str}",
        "details": desc,
        "sf": "true",
    }

    base_url = "https://calendar.google.com/calendar/render"
    return f"{base_url}?{urllib.parse.urlencode(params)}"


def generate_outlook_calendar_url(
    title: str,
    deadline: datetime,
    description: str = "",
    url: Optional[str] = None,
) -> str:
    """
    Generate an Outlook calendar add event URL.

    Args:
        title: Event title
        deadline: Event datetime
        description: Event description
        url: Link to include

    Returns:
        Outlook calendar URL
    """
    import urllib.parse

    # Format dates for Outlook (ISO 8601)
    date_str = deadline.strftime("%Y-%m-%dT%H:%M:%SZ")

    desc = description[:500] if description else ""
    if url:
        desc = f"{desc}\n\nMore info: {url}" if desc else f"More info: {url}"

    params = {
        "rru": "addevent",
        "subject": f"DEADLINE: {title}",
        "startdt": date_str,
        "enddt": date_str,
        "body": desc,
        "allday": "false",
    }

    base_url = "https://outlook.live.com/calendar/0/deeplink/compose"
    return f"{base_url}?{urllib.parse.urlencode(params)}"


@router.get(
    "/export", summary="Export deadlines to ICS", description="Export saved grant deadlines as an ICS calendar file."
)
async def export_calendar(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    saved_only: bool = Query(default=True, description="Only export saved grants"),
    days_ahead: int = Query(default=365, ge=1, le=730, description="Include deadlines within N days"),
) -> Response:
    """
    Export grant deadlines as an ICS calendar file.

    Generates an ICS file that can be imported into any calendar app.
    Includes alarms for 1 week and 1 day before each deadline.
    """
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days_ahead)

    # Build query based on saved_only flag
    if saved_only:
        # Get grants that user has saved (match with user_action='saved')
        query = (
            select(Grant)
            .join(Match, Match.grant_id == Grant.id)
            .where(
                and_(
                    Match.user_id == current_user.id,
                    Match.user_action == "saved",
                    Grant.deadline.isnot(None),
                    Grant.deadline > now,
                    Grant.deadline <= cutoff,
                )
            )
            .order_by(Grant.deadline.asc())
        )
    else:
        # Get all matched grants with deadlines
        query = (
            select(Grant)
            .join(Match, Match.grant_id == Grant.id)
            .where(
                and_(
                    Match.user_id == current_user.id,
                    Grant.deadline.isnot(None),
                    Grant.deadline > now,
                    Grant.deadline <= cutoff,
                )
            )
            .order_by(Grant.deadline.asc())
        )

    result = await db.execute(query)
    grants = result.scalars().all()

    # Generate ICS events
    events = []
    for grant in grants:
        event = generate_ics_event(
            uid=str(grant.id),
            title=grant.title,
            description=grant.description or "",
            deadline=grant.deadline,
            url=grant.url,
            agency=grant.agency,
            amount_max=grant.amount_max,
        )
        events.append(event)

    # Generate calendar
    ics_content = generate_ics_calendar(events)

    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=grantradar-deadlines.ics"},
    )


@router.get(
    "/grant/{grant_id}/links",
    summary="Get calendar links for a grant",
    description="Get Google Calendar and Outlook links for a specific grant deadline.",
)
async def get_calendar_links(
    grant_id: UUID,
    db: AsyncSessionDep,
) -> dict:
    """
    Get calendar links for adding a specific grant deadline.

    Returns URLs for:
    - Google Calendar
    - Outlook Calendar
    - ICS download (single event)
    """
    # Fetch grant
    result = await db.execute(select(Grant).where(Grant.id == grant_id))
    grant = result.scalar_one_or_none()

    if not grant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")

    if not grant.deadline:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grant has no deadline")

    # Generate links
    google_url = generate_google_calendar_url(
        title=grant.title,
        deadline=grant.deadline,
        description=grant.description or "",
        url=grant.url,
    )

    outlook_url = generate_outlook_calendar_url(
        title=grant.title,
        deadline=grant.deadline,
        description=grant.description or "",
        url=grant.url,
    )

    return {
        "grant_id": str(grant_id),
        "grant_title": grant.title,
        "deadline": grant.deadline.isoformat(),
        "google_calendar_url": google_url,
        "outlook_calendar_url": outlook_url,
        "ics_download_url": f"/api/calendar/grant/{grant_id}/ics",
    }


@router.get(
    "/grant/{grant_id}/ics",
    summary="Download ICS for a single grant",
    description="Download an ICS file for a single grant deadline.",
)
async def download_grant_ics(
    grant_id: UUID,
    db: AsyncSessionDep,
) -> Response:
    """
    Download an ICS file for a single grant deadline.
    """
    # Fetch grant
    result = await db.execute(select(Grant).where(Grant.id == grant_id))
    grant = result.scalar_one_or_none()

    if not grant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")

    if not grant.deadline:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grant has no deadline")

    # Generate single event ICS
    event = generate_ics_event(
        uid=str(grant.id),
        title=grant.title,
        description=grant.description or "",
        deadline=grant.deadline,
        url=grant.url,
        agency=grant.agency,
        amount_max=grant.amount_max,
    )

    ics_content = generate_ics_calendar([event], f"GrantRadar: {grant.title[:30]}")

    # Create safe filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in grant.title[:30])

    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="grant-deadline-{safe_title}.ics"'},
    )


# =============================================================================
# Calendar View Endpoints
# =============================================================================


def compute_urgency(deadline: datetime) -> UrgencyLevel:
    """Compute urgency level based on days until deadline."""
    now = datetime.now(timezone.utc)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    days = (deadline - now).days

    if days < 7:
        return UrgencyLevel.CRITICAL
    elif days < 14:
        return UrgencyLevel.WARNING
    else:
        return UrgencyLevel.NORMAL


def compute_days_until(deadline: datetime) -> int:
    """Compute days until deadline (negative if past)."""
    now = datetime.now(timezone.utc)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return (deadline - now).days


@router.get(
    "/deadlines",
    response_model=CalendarDeadlinesResponse,
    summary="Get deadlines for date range",
    description="Get all grant deadlines for a specified date range from saved matches and pipeline items.",
)
async def get_calendar_deadlines(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    start_date: datetime = Query(..., description="Start of date range"),
    end_date: datetime = Query(..., description="End of date range"),
    include_saved: bool = Query(default=True, description="Include saved matches"),
    include_pipeline: bool = Query(default=True, description="Include pipeline items"),
) -> CalendarDeadlinesResponse:
    """
    Get all grant deadlines within a date range.

    Combines grants from:
    - Saved matches (user_action='saved')
    - Pipeline items (grants in application pipeline)
    """
    events: list[CalendarEvent] = []
    seen_grant_ids: set[UUID] = set()

    # Ensure dates are timezone-aware
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    # Get saved matches with deadlines
    if include_saved:
        saved_query = (
            select(Match)
            .options(joinedload(Match.grant))
            .where(
                and_(
                    Match.user_id == current_user.id,
                    Match.user_action == "saved",
                )
            )
        )
        result = await db.execute(saved_query)
        saved_matches = result.unique().scalars().all()

        for match in saved_matches:
            grant = match.grant
            if grant.deadline is None:
                continue

            deadline = grant.deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)

            if not (start_date <= deadline <= end_date):
                continue

            seen_grant_ids.add(grant.id)
            events.append(
                CalendarEvent(
                    grant_id=grant.id,
                    title=grant.title,
                    deadline=deadline,
                    event_type=CalendarEventType.SAVED,
                    stage=None,
                    urgency=compute_urgency(deadline),
                    days_until_deadline=compute_days_until(deadline),
                    agency=grant.agency,
                    amount_max=grant.amount_max,
                    url=grant.url,
                    match_id=match.id,
                    pipeline_item_id=None,
                )
            )

    # Get pipeline items with deadlines
    if include_pipeline:
        pipeline_query = (
            select(GrantApplication)
            .options(joinedload(GrantApplication.grant))
            .where(GrantApplication.user_id == current_user.id)
        )
        result = await db.execute(pipeline_query)
        pipeline_items = result.unique().scalars().all()

        for item in pipeline_items:
            grant = item.grant
            if grant.deadline is None:
                continue

            # Skip if already added from saved matches
            if grant.id in seen_grant_ids:
                continue

            deadline = grant.deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)

            if not (start_date <= deadline <= end_date):
                continue

            seen_grant_ids.add(grant.id)
            events.append(
                CalendarEvent(
                    grant_id=grant.id,
                    title=grant.title,
                    deadline=deadline,
                    event_type=CalendarEventType.PIPELINE,
                    stage=item.stage.value,
                    urgency=compute_urgency(deadline),
                    days_until_deadline=compute_days_until(deadline),
                    agency=grant.agency,
                    amount_max=grant.amount_max,
                    url=grant.url,
                    match_id=None,
                    pipeline_item_id=item.id,
                )
            )

    # Sort by deadline
    events.sort(key=lambda e: e.deadline)

    return CalendarDeadlinesResponse(
        events=events,
        total=len(events),
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/month/{year}/{month}",
    response_model=CalendarMonthResponse,
    summary="Get deadlines for a month",
    description="Get all grant deadlines for a specific month, grouped by day.",
)
async def get_calendar_month(
    year: int,
    month: int,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    include_saved: bool = Query(default=True, description="Include saved matches"),
    include_pipeline: bool = Query(default=True, description="Include pipeline items"),
) -> CalendarMonthResponse:
    """
    Get deadlines for a specific month, organized by day.
    """
    if not (1 <= month <= 12):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Month must be between 1 and 12")

    # Calculate month boundaries
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    _, last_day = monthrange(year, month)
    end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    # Get all deadlines for the month
    deadlines_response = await get_calendar_deadlines(
        db=db,
        current_user=current_user,
        start_date=start_date,
        end_date=end_date,
        include_saved=include_saved,
        include_pipeline=include_pipeline,
    )

    # Group events by day
    events_by_day: dict[int, list[CalendarEvent]] = defaultdict(list)
    for event in deadlines_response.events:
        day = event.deadline.day
        events_by_day[day].append(event)

    # Build days list
    days: list[CalendarDay] = []
    for day in range(1, last_day + 1):
        day_events = events_by_day.get(day, [])
        if day_events:  # Only include days with events
            days.append(
                CalendarDay(
                    date=datetime(year, month, day, tzinfo=timezone.utc),
                    events=day_events,
                    count=len(day_events),
                )
            )

    return CalendarMonthResponse(
        year=year,
        month=month,
        days=days,
        total_events=len(deadlines_response.events),
    )


@router.get(
    "/upcoming",
    response_model=UpcomingDeadlinesResponse,
    summary="Get upcoming deadlines",
    description="Get the next 30 days of deadlines with urgency levels.",
)
async def get_upcoming_deadlines(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    days: int = Query(default=30, ge=1, le=90, description="Number of days to look ahead"),
    include_saved: bool = Query(default=True, description="Include saved matches"),
    include_pipeline: bool = Query(default=True, description="Include pipeline items"),
) -> UpcomingDeadlinesResponse:
    """
    Get upcoming deadlines within the specified number of days.

    Returns deadlines sorted by date with urgency indicators:
    - Critical: < 7 days
    - Warning: < 14 days
    - Normal: >= 14 days
    """
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=days)

    # Get all deadlines
    deadlines_response = await get_calendar_deadlines(
        db=db,
        current_user=current_user,
        start_date=now,
        end_date=end_date,
        include_saved=include_saved,
        include_pipeline=include_pipeline,
    )

    # Convert to UpcomingDeadline format
    deadlines: list[UpcomingDeadline] = []
    critical_count = 0
    warning_count = 0

    for event in deadlines_response.events:
        deadline = UpcomingDeadline(
            grant_id=event.grant_id,
            title=event.title,
            deadline=event.deadline,
            days_until_deadline=event.days_until_deadline,
            urgency=event.urgency,
            event_type=event.event_type,
            stage=event.stage,
            agency=event.agency,
            amount_max=event.amount_max,
        )
        deadlines.append(deadline)

        if event.urgency == UrgencyLevel.CRITICAL:
            critical_count += 1
        elif event.urgency == UrgencyLevel.WARNING:
            warning_count += 1

    return UpcomingDeadlinesResponse(
        deadlines=deadlines,
        total=len(deadlines),
        critical_count=critical_count,
        warning_count=warning_count,
    )
