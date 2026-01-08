"""
Deadline Reminder API Endpoints
Manage reminder schedules for user deadlines.
"""
import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, delete, select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import Deadline, ReminderSchedule
from backend.schemas.reminders import (
    BulkReminderCreate,
    ReminderScheduleResponse,
    ReminderSettingsResponse,
    ReminderSettingsUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reminders", tags=["Reminders"])

# Default reminder times (in minutes before deadline)
DEFAULT_REMINDERS = [
    10080,  # 1 week
    1440,  # 1 day
    60,  # 1 hour
]


@router.get("/settings", response_model=ReminderSettingsResponse)
async def get_reminder_settings(
    current_user: CurrentUser,
) -> ReminderSettingsResponse:
    """Get user's reminder notification settings."""
    return ReminderSettingsResponse(
        email_enabled=current_user.email_notifications,
        sms_enabled=current_user.sms_notifications,
        default_reminders=DEFAULT_REMINDERS,
    )


@router.put("/settings", response_model=ReminderSettingsResponse)
async def update_reminder_settings(
    settings: ReminderSettingsUpdate,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> ReminderSettingsResponse:
    """Update user's reminder notification settings."""
    if settings.email_enabled is not None:
        current_user.email_notifications = settings.email_enabled
    if settings.sms_enabled is not None:
        current_user.sms_notifications = settings.sms_enabled

    await db.commit()
    await db.refresh(current_user)

    return ReminderSettingsResponse(
        email_enabled=current_user.email_notifications,
        sms_enabled=current_user.sms_notifications,
        default_reminders=DEFAULT_REMINDERS,
    )


@router.get("/deadline/{deadline_id}", response_model=List[ReminderScheduleResponse])
async def get_deadline_reminders(
    deadline_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> List[ReminderScheduleResponse]:
    """Get all reminders for a specific deadline."""
    # Verify deadline belongs to user
    result = await db.execute(
        select(Deadline).where(
            and_(
                Deadline.id == deadline_id,
                Deadline.user_id == current_user.id,
            )
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    # Get reminders
    result = await db.execute(
        select(ReminderSchedule).where(ReminderSchedule.deadline_id == deadline_id)
    )
    reminders = result.scalars().all()

    return [ReminderScheduleResponse.model_validate(r) for r in reminders]


@router.post("/deadline/{deadline_id}", response_model=List[ReminderScheduleResponse])
async def create_deadline_reminders(
    deadline_id: UUID,
    reminders: BulkReminderCreate,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> List[ReminderScheduleResponse]:
    """Create or replace reminders for a deadline."""
    # Verify deadline belongs to user
    result = await db.execute(
        select(Deadline).where(
            and_(
                Deadline.id == deadline_id,
                Deadline.user_id == current_user.id,
            )
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    # Delete existing reminders
    await db.execute(
        delete(ReminderSchedule).where(ReminderSchedule.deadline_id == deadline_id)
    )

    # Create new reminders
    created = []
    for reminder in reminders.reminders:
        schedule = ReminderSchedule(
            deadline_id=deadline_id,
            reminder_type=reminder.reminder_type,
            remind_before_minutes=reminder.remind_before_minutes,
        )
        db.add(schedule)
        created.append(schedule)

    await db.commit()

    # Refresh all created reminders
    for schedule in created:
        await db.refresh(schedule)

    return [ReminderScheduleResponse.model_validate(r) for r in created]


@router.delete("/deadline/{deadline_id}")
async def delete_deadline_reminders(
    deadline_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> dict:
    """Delete all reminders for a deadline."""
    # Verify deadline belongs to user
    result = await db.execute(
        select(Deadline).where(
            and_(
                Deadline.id == deadline_id,
                Deadline.user_id == current_user.id,
            )
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    await db.execute(
        delete(ReminderSchedule).where(ReminderSchedule.deadline_id == deadline_id)
    )
    await db.commit()

    return {"message": "Reminders deleted"}


@router.post(
    "/deadline/{deadline_id}/default", response_model=List[ReminderScheduleResponse]
)
async def create_default_reminders(
    deadline_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> List[ReminderScheduleResponse]:
    """Create default reminders for a deadline (1 week, 1 day, 1 hour before)."""
    # Verify deadline belongs to user
    result = await db.execute(
        select(Deadline).where(
            and_(
                Deadline.id == deadline_id,
                Deadline.user_id == current_user.id,
            )
        )
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    # Delete existing reminders
    await db.execute(
        delete(ReminderSchedule).where(ReminderSchedule.deadline_id == deadline_id)
    )

    # Create default reminders for each type user has enabled
    created = []
    reminder_types = ["email"]  # Always include email
    if current_user.sms_notifications and current_user.phone:
        reminder_types.append("sms")

    for remind_before in DEFAULT_REMINDERS:
        for reminder_type in reminder_types:
            schedule = ReminderSchedule(
                deadline_id=deadline_id,
                reminder_type=reminder_type,
                remind_before_minutes=remind_before,
            )
            db.add(schedule)
            created.append(schedule)

    await db.commit()

    for schedule in created:
        await db.refresh(schedule)

    return [ReminderScheduleResponse.model_validate(r) for r in created]
