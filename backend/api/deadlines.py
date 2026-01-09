"""
Deadline management API endpoints.
CRUD operations for user deadlines with filtering, sorting, status tracking, and iCal export.
"""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import and_, func, select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import Deadline, DeadlineStatusHistory, Grant
from backend.schemas.deadlines import (
    DeadlineCreate,
    DeadlineList,
    DeadlinePriority,
    DeadlineResponse,
    DeadlineStatsResponse,
    DeadlineStatus,
    DeadlineUpdate,
    LinkGrantRequest,
    RecurrencePreset,
    RecurrencePresetsResponse,
    ReminderConfigUpdate,
    RECURRENCE_PRESETS,
    StatusChangeRequest,
    StatusHistoryList,
    StatusHistoryResponse,
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
    Creates initial status history entry.
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
        status=data.status.value,
        priority=data.priority.value,
        url=data.url,
        notes=data.notes,
        color=data.color,
        is_recurring=data.is_recurring,
        recurrence_rule=data.recurrence_rule,
        reminder_config=data.reminder_config,
    )
    db.add(deadline)
    await db.flush()  # Get the deadline ID

    # Create initial status history entry
    history_entry = DeadlineStatusHistory(
        deadline_id=deadline.id,
        previous_status=None,
        new_status=data.status.value,
        changed_by=current_user.id,
        notes="Deadline created",
    )
    db.add(history_entry)

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

    Exports all deadlines that are not in terminal states (awarded/rejected).
    Includes alarms for 1 week and 1 day before each deadline.
    Can be imported into any calendar application.
    """
    from icalendar import Alarm, Calendar, Event

    # Export deadlines that are not in terminal states
    terminal_statuses = [DeadlineStatus.AWARDED.value, DeadlineStatus.REJECTED.value]
    result = await db.execute(
        select(Deadline).where(
            and_(
                Deadline.user_id == current_user.id,
                ~Deadline.status.in_(terminal_statuses),
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
        status=DeadlineStatus.NOT_STARTED.value,
    )
    db.add(deadline)
    await db.flush()

    # Create initial status history entry
    history_entry = DeadlineStatusHistory(
        deadline_id=deadline.id,
        previous_status=None,
        new_status=DeadlineStatus.NOT_STARTED.value,
        changed_by=current_user.id,
        notes=f"Created from grant: {grant.title}",
    )
    db.add(history_entry)

    await db.commit()
    await db.refresh(deadline)
    return deadline


@router.post(
    "/{deadline_id}/status",
    response_model=DeadlineResponse,
    summary="Change deadline status",
    description="Change a deadline's status with history tracking.",
)
async def change_deadline_status(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    deadline_id: UUID,
    data: StatusChangeRequest,
) -> DeadlineResponse:
    """
    Change a deadline's status.

    Records the change in status history for audit purposes.
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

    previous_status = deadline.status

    # Don't create history if status unchanged
    if previous_status == data.status.value:
        return deadline

    # Update status
    deadline.status = data.status.value
    deadline.updated_at = datetime.now(timezone.utc)

    # Reset escalation flag if moving to active status
    if data.status in {DeadlineStatus.DRAFTING, DeadlineStatus.INTERNAL_REVIEW}:
        deadline.escalation_sent = False

    # Create status history entry
    history_entry = DeadlineStatusHistory(
        deadline_id=deadline.id,
        previous_status=previous_status,
        new_status=data.status.value,
        changed_by=current_user.id,
        notes=data.notes,
    )
    db.add(history_entry)

    await db.commit()
    await db.refresh(deadline)
    return deadline


@router.get(
    "/{deadline_id}/history",
    response_model=StatusHistoryList,
    summary="Get status history",
    description="Get the status change history for a deadline.",
)
async def get_deadline_history(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    deadline_id: UUID,
) -> StatusHistoryList:
    """
    Get the status change history for a deadline.

    Returns all status changes in reverse chronological order.
    """
    # Verify deadline exists and belongs to user
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

    # Get history entries
    result = await db.execute(
        select(DeadlineStatusHistory)
        .where(DeadlineStatusHistory.deadline_id == deadline_id)
        .order_by(DeadlineStatusHistory.changed_at.desc())
    )
    history = result.scalars().all()

    return StatusHistoryList(items=history, total=len(history))


@router.put(
    "/{deadline_id}/reminders",
    response_model=DeadlineResponse,
    summary="Update reminder configuration",
    description="Update the reminder configuration for a deadline.",
)
async def update_reminder_config(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    deadline_id: UUID,
    data: ReminderConfigUpdate,
) -> DeadlineResponse:
    """
    Update the reminder configuration for a deadline.

    Specify days before deadline when reminders should be sent.
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

    # Sort and deduplicate reminder config
    deadline.reminder_config = sorted(set(data.reminder_config), reverse=True)
    deadline.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(deadline)
    return deadline


@router.get(
    "/stats",
    response_model=DeadlineStatsResponse,
    summary="Get deadline statistics",
    description="Get aggregated statistics about user's deadlines.",
)
async def get_deadline_stats(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> DeadlineStatsResponse:
    """
    Get aggregated statistics about user's deadlines.

    Returns counts by status, priority, and time-based metrics.
    """
    result = await db.execute(
        select(Deadline).where(Deadline.user_id == current_user.id)
    )
    deadlines = result.scalars().all()

    now = datetime.now(timezone.utc)
    week_from_now = now + timedelta(days=7)
    month_from_now = now + timedelta(days=30)

    by_status = {}
    by_priority = {}
    overdue = 0
    due_this_week = 0
    due_this_month = 0
    recurring_templates = 0

    terminal_statuses = {DeadlineStatus.AWARDED.value, DeadlineStatus.REJECTED.value, DeadlineStatus.SUBMITTED.value}

    for d in deadlines:
        # Count by status
        by_status[d.status] = by_status.get(d.status, 0) + 1

        # Count by priority
        by_priority[d.priority] = by_priority.get(d.priority, 0) + 1

        # Count recurring templates
        if d.is_recurring:
            recurring_templates += 1

        # Skip terminal statuses for time-based metrics
        if d.status in terminal_statuses:
            continue

        deadline_dt = d.sponsor_deadline
        if deadline_dt.tzinfo is None:
            deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)

        if deadline_dt < now:
            overdue += 1
        elif deadline_dt <= week_from_now:
            due_this_week += 1
        elif deadline_dt <= month_from_now:
            due_this_month += 1

    return DeadlineStatsResponse(
        total=len(deadlines),
        by_status=by_status,
        by_priority=by_priority,
        overdue=overdue,
        due_this_week=due_this_week,
        due_this_month=due_this_month,
        recurring_templates=recurring_templates,
    )


@router.get(
    "/recurrence-presets",
    response_model=RecurrencePresetsResponse,
    summary="Get recurrence presets",
    description="Get available recurrence rule presets for common grant cycles.",
)
async def get_recurrence_presets() -> RecurrencePresetsResponse:
    """
    Get available recurrence rule presets.

    Returns pre-built RRULE patterns for common grant cycles
    like NIH standard dates, NSF quarterly, etc.
    """
    presets = [
        RecurrencePreset(key=key, label=value["label"], rule=value["rule"])
        for key, value in RECURRENCE_PRESETS.items()
    ]
    return RecurrencePresetsResponse(presets=presets)
