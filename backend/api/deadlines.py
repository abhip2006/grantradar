"""
Deadline management API endpoints.
CRUD operations for user deadlines with filtering, sorting, and iCal export.
"""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import and_, select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import Deadline, Grant
from backend.schemas.deadlines import (
    DeadlineCreate,
    DeadlineList,
    DeadlinePriority,
    DeadlineResponse,
    DeadlineStatus,
    DeadlineUpdate,
    LinkGrantRequest,
)

router = APIRouter(prefix="/api/deadlines", tags=["Deadlines"])


@router.get(
    "",
    response_model=DeadlineList,
    summary="List user deadlines",
    description="Get all deadlines for the current user with optional filters.",
)
async def list_deadlines(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    status: Optional[DeadlineStatus] = Query(None, description="Filter by status"),
    from_date: Optional[datetime] = Query(None, description="Filter deadlines from this date"),
    to_date: Optional[datetime] = Query(None, description="Filter deadlines until this date"),
    funder: Optional[str] = Query(None, description="Filter by funder name"),
    search: Optional[str] = Query(None, description="Search in title"),
    sort: str = Query(
        "deadline_asc",
        pattern="^(deadline_asc|deadline_desc|created_desc)$",
        description="Sort order",
    ),
) -> DeadlineList:
    """
    Get all deadlines for the current user with optional filters.

    Filters:
    - status: Filter by deadline status (active, completed, archived)
    - from_date: Only include deadlines on or after this date
    - to_date: Only include deadlines on or before this date
    - funder: Filter by funder name (partial match)
    - search: Search in title (partial match)

    Sorting:
    - deadline_asc: Sort by sponsor_deadline ascending (default)
    - deadline_desc: Sort by sponsor_deadline descending
    - created_desc: Sort by created_at descending
    """
    query = select(Deadline).where(Deadline.user_id == current_user.id)

    # Apply filters
    if status:
        query = query.where(Deadline.status == status.value)
    if from_date:
        query = query.where(Deadline.sponsor_deadline >= from_date)
    if to_date:
        query = query.where(Deadline.sponsor_deadline <= to_date)
    if funder:
        query = query.where(Deadline.funder.ilike(f"%{funder}%"))
    if search:
        query = query.where(Deadline.title.ilike(f"%{search}%"))

    # Apply sorting
    if sort == "deadline_asc":
        query = query.order_by(Deadline.sponsor_deadline.asc())
    elif sort == "deadline_desc":
        query = query.order_by(Deadline.sponsor_deadline.desc())
    else:
        query = query.order_by(Deadline.created_at.desc())

    result = await db.execute(query)
    deadlines = result.scalars().all()

    return DeadlineList(items=deadlines, total=len(deadlines))


@router.post(
    "",
    response_model=DeadlineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create deadline",
    description="Create a new deadline.",
)
async def create_deadline(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    data: DeadlineCreate,
) -> DeadlineResponse:
    """
    Create a new deadline.

    Optionally link to an existing grant by providing grant_id.
    """
    deadline = Deadline(
        user_id=current_user.id,
        grant_id=data.grant_id,
        title=data.title,
        description=data.description,
        funder=data.funder,
        mechanism=data.mechanism,
        sponsor_deadline=data.sponsor_deadline,
        internal_deadline=data.internal_deadline,
        priority=data.priority.value,
        url=data.url,
        notes=data.notes,
        color=data.color,
    )
    db.add(deadline)
    await db.commit()
    await db.refresh(deadline)
    return deadline


@router.get(
    "/export.ics",
    summary="Export deadlines as iCal",
    description="Export active deadlines as an iCal file.",
)
async def export_ics(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> Response:
    """
    Export active deadlines as iCal file.

    Includes alarms for 1 week and 1 day before each deadline.
    Can be imported into any calendar application.
    """
    from icalendar import Alarm, Calendar, Event

    result = await db.execute(
        select(Deadline).where(
            and_(
                Deadline.user_id == current_user.id,
                Deadline.status == "active",
            )
        )
    )
    deadlines = result.scalars().all()

    cal = Calendar()
    cal.add("prodid", "-//GrantRadar//Deadlines//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "GrantRadar Deadlines")

    for d in deadlines:
        event = Event()
        event.add("uid", str(d.id))
        event.add("summary", d.title)
        event.add("dtstart", d.sponsor_deadline.date())
        event.add("dtend", d.sponsor_deadline.date())
        if d.description:
            event.add("description", d.description)
        if d.url:
            event.add("url", d.url)

        # Add 1-week reminder
        alarm_week = Alarm()
        alarm_week.add("action", "DISPLAY")
        alarm_week.add("trigger", timedelta(days=-7))
        alarm_week.add("description", f"1 week until: {d.title}")
        event.add_component(alarm_week)

        # Add 1-day reminder
        alarm_day = Alarm()
        alarm_day.add("action", "DISPLAY")
        alarm_day.add("trigger", timedelta(days=-1))
        alarm_day.add("description", f"Tomorrow: {d.title}")
        event.add_component(alarm_day)

        cal.add_component(event)

    return Response(
        content=cal.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=grantradar-deadlines.ics"},
    )


@router.get(
    "/{deadline_id}",
    response_model=DeadlineResponse,
    summary="Get deadline",
    description="Get a specific deadline by ID.",
)
async def get_deadline(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    deadline_id: UUID,
) -> DeadlineResponse:
    """Get a specific deadline by ID."""
    result = await db.execute(
        select(Deadline).where(
            and_(Deadline.id == deadline_id, Deadline.user_id == current_user.id)
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )
    return deadline


@router.patch(
    "/{deadline_id}",
    response_model=DeadlineResponse,
    summary="Update deadline",
    description="Update an existing deadline.",
)
async def update_deadline(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    deadline_id: UUID,
    data: DeadlineUpdate,
) -> DeadlineResponse:
    """
    Update an existing deadline.

    Only provided fields are updated; others remain unchanged.
    """
    result = await db.execute(
        select(Deadline).where(
            and_(Deadline.id == deadline_id, Deadline.user_id == current_user.id)
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            # Handle enum values
            if isinstance(value, Enum):
                setattr(deadline, field, value.value)
            else:
                setattr(deadline, field, value)

    deadline.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(deadline)
    return deadline


@router.delete(
    "/{deadline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete deadline",
    description="Delete a deadline.",
)
async def delete_deadline(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    deadline_id: UUID,
) -> None:
    """Delete a deadline."""
    result = await db.execute(
        select(Deadline).where(
            and_(Deadline.id == deadline_id, Deadline.user_id == current_user.id)
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )

    await db.delete(deadline)
    await db.commit()


@router.post(
    "/link-grant",
    response_model=DeadlineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create deadline from grant",
    description="Create a deadline from an existing grant.",
)
async def link_grant_to_deadline(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    data: LinkGrantRequest,
) -> DeadlineResponse:
    """
    Create a deadline from an existing grant.

    Copies grant title, agency, deadline, and URL to create a new deadline.
    """
    result = await db.execute(select(Grant).where(Grant.id == data.grant_id))
    grant = result.scalar_one_or_none()
    if not grant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grant not found",
        )

    if not grant.deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grant has no deadline",
        )

    deadline = Deadline(
        user_id=current_user.id,
        grant_id=grant.id,
        title=grant.title,
        funder=grant.agency,
        sponsor_deadline=grant.deadline,
        url=grant.url,
    )
    db.add(deadline)
    await db.commit()
    await db.refresh(deadline)
    return deadline
