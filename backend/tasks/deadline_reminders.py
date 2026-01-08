"""
Deadline Reminder Tasks
Celery tasks for sending reminders for user-created deadlines.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select

from agents.delivery.channels import get_sendgrid_channel, get_twilio_channel
from backend.celery_app import celery_app
from backend.core.config import settings
from backend.database import get_sync_session
from backend.models import Deadline, ReminderSchedule, User

logger = logging.getLogger(__name__)


@celery_app.task(queue="default")
def check_and_send_deadline_reminders() -> dict:
    """
    Check for pending deadline reminders and send them.

    Runs every 5 minutes via Celery Beat.

    Returns:
        Dictionary with reminder statistics.
    """
    now = datetime.now(timezone.utc)
    reminders_sent = 0
    errors = 0

    with get_sync_session() as session:
        # Find unsent reminders where it's time to send
        # reminder_time = deadline.sponsor_deadline - remind_before_minutes
        result = session.execute(
            select(ReminderSchedule, Deadline, User)
            .join(Deadline, ReminderSchedule.deadline_id == Deadline.id)
            .join(User, Deadline.user_id == User.id)
            .where(
                and_(
                    ReminderSchedule.is_sent == False,
                    Deadline.status == "active",
                )
            )
        )

        pending = result.all()

        for schedule, deadline, user in pending:
            # Calculate when reminder should be sent
            reminder_time = deadline.sponsor_deadline - timedelta(
                minutes=schedule.remind_before_minutes
            )

            if now >= reminder_time:
                try:
                    # Send the reminder
                    _send_reminder(schedule, deadline, user)

                    # Mark as sent
                    schedule.is_sent = True
                    schedule.sent_at = now
                    reminders_sent += 1

                except Exception as e:
                    logger.error(f"Failed to send reminder {schedule.id}: {e}")
                    errors += 1

        session.commit()

    logger.info(f"Deadline reminders: sent={reminders_sent}, errors={errors}")
    return {"sent": reminders_sent, "errors": errors}


def _send_reminder(
    schedule: ReminderSchedule, deadline: Deadline, user: User
) -> None:
    """Send a single reminder notification."""
    # Calculate time remaining
    now = datetime.now(timezone.utc)
    time_remaining = deadline.sponsor_deadline - now

    if time_remaining.days > 0:
        time_str = f"{time_remaining.days} day{'s' if time_remaining.days > 1 else ''}"
    elif time_remaining.seconds >= 3600:
        hours = time_remaining.seconds // 3600
        time_str = f"{hours} hour{'s' if hours > 1 else ''}"
    else:
        minutes = time_remaining.seconds // 60
        time_str = f"{minutes} minute{'s' if minutes > 1 else ''}"

    if schedule.reminder_type == "email":
        _send_email_reminder(user, deadline, time_str)
    elif schedule.reminder_type == "sms":
        _send_sms_reminder(user, deadline, time_str)


def _send_email_reminder(user: User, deadline: Deadline, time_str: str) -> None:
    """Send email reminder via SendGrid."""
    email_channel = get_sendgrid_channel()

    if not email_channel.is_configured():
        logger.warning("SendGrid not configured - skipping email reminder")
        return

    deadline_str = deadline.sponsor_deadline.strftime("%B %d, %Y at %I:%M %p UTC")

    subject = f"Deadline Reminder: {deadline.title} - Due in {time_str}"

    # Build funder line if present
    funder_line = ""
    if deadline.funder:
        funder_line = f'<p style="margin: 5px 0; color: #666;"><strong>Funder:</strong> {deadline.funder}</p>'

    # Build mechanism line if present
    mechanism_line = ""
    if deadline.mechanism:
        mechanism_line = f'<p style="margin: 5px 0; color: #666;"><strong>Mechanism:</strong> {deadline.mechanism}</p>'

    # Build notes line if present
    notes_line = ""
    if deadline.notes:
        notes_line = f'<p style="color: #666; font-size: 14px;"><strong>Notes:</strong> {deadline.notes}</p>'

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 28px;">{settings.app_name}</h1>
        </div>
        <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
            <div style="background: #fef3c7; color: #92400e; padding: 15px; border-radius: 5px; text-align: center; margin-bottom: 20px;">
                <strong style="font-size: 18px;">Due in {time_str}</strong>
            </div>
            <h2 style="color: #333; margin-top: 0;">Deadline Reminder</h2>
            <p>Hi {user.name or 'Researcher'},</p>
            <p>This is a reminder for your upcoming deadline:</p>
            <div style="background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0; color: #333;">{deadline.title}</h3>
                {funder_line}
                {mechanism_line}
                <p style="margin: 5px 0; color: #666;"><strong>Deadline:</strong> {deadline_str}</p>
                <p style="margin: 5px 0; color: #666;"><strong>Priority:</strong> {deadline.priority.upper()}</p>
            </div>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{settings.frontend_url}/deadlines" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">View Deadlines</a>
            </div>
            {notes_line}
            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
            <p style="color: #999; font-size: 12px; text-align: center;">
                <a href="{settings.frontend_url}/settings/notifications" style="color: #667eea;">Manage reminder preferences</a>
            </p>
        </div>
    </body>
    </html>
    """

    # Build funder line for text version
    funder_text = f"Funder: {deadline.funder}\n" if deadline.funder else ""
    mechanism_text = f"Mechanism: {deadline.mechanism}\n" if deadline.mechanism else ""

    body_text = f"""
    Deadline Reminder - Due in {time_str}

    Hi {user.name or 'Researcher'},

    This is a reminder for your upcoming deadline:

    {deadline.title}
    {funder_text}{mechanism_text}Deadline: {deadline_str}
    Priority: {deadline.priority.upper()}

    View deadlines: {settings.frontend_url}/deadlines

    - The {settings.app_name} Team
    """

    try:
        status = email_channel.send_email_sync(
            to_email=user.email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            to_name=user.name,
            tracking_id=str(deadline.id),
        )

        if status.status == "sent":
            logger.info(f"Email reminder sent for deadline {deadline.id}")
        else:
            logger.warning(f"Email reminder failed: {status.error_message}")

    except Exception as e:
        logger.error(f"Error sending email reminder: {e}")
        raise


def _send_sms_reminder(user: User, deadline: Deadline, time_str: str) -> None:
    """Send SMS reminder via Twilio."""
    sms_channel = get_twilio_channel()

    if not sms_channel.is_configured():
        logger.warning("Twilio not configured - skipping SMS reminder")
        return

    if not user.phone:
        logger.warning(f"User {user.id} has no phone number")
        return

    # Truncate title for SMS (160 char limit)
    title = deadline.title[:50] + "..." if len(deadline.title) > 50 else deadline.title
    message = f"{settings.app_name}: '{title}' due in {time_str}!"

    try:
        status = sms_channel.send_sms(
            phone_number=user.phone,
            message=message,
            match_id=deadline.id,
        )

        if status.status == "sent":
            logger.info(f"SMS reminder sent for deadline {deadline.id}")
        else:
            logger.warning(f"SMS reminder failed: {status.error_message}")

    except Exception as e:
        logger.error(f"Error sending SMS reminder: {e}")
        raise


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "check_and_send_deadline_reminders",
]
