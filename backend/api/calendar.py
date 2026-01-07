"""
Calendar API Endpoints
Export grant deadlines to ICS format and generate calendar links.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import and_, select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import Grant, Match

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
    "/export",
    summary="Export deadlines to ICS",
    description="Export saved grant deadlines as an ICS calendar file."
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
        headers={
            "Content-Disposition": "attachment; filename=grantradar-deadlines.ics"
        }
    )


@router.get(
    "/grant/{grant_id}/links",
    summary="Get calendar links for a grant",
    description="Get Google Calendar and Outlook links for a specific grant deadline."
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
    result = await db.execute(
        select(Grant).where(Grant.id == grant_id)
    )
    grant = result.scalar_one_or_none()

    if not grant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grant not found"
        )

    if not grant.deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grant has no deadline"
        )

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
    description="Download an ICS file for a single grant deadline."
)
async def download_grant_ics(
    grant_id: UUID,
    db: AsyncSessionDep,
) -> Response:
    """
    Download an ICS file for a single grant deadline.
    """
    # Fetch grant
    result = await db.execute(
        select(Grant).where(Grant.id == grant_id)
    )
    grant = result.scalar_one_or_none()

    if not grant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grant not found"
        )

    if not grant.deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grant has no deadline"
        )

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
        headers={
            "Content-Disposition": f'attachment; filename="grant-deadline-{safe_title}.ics"'
        }
    )
