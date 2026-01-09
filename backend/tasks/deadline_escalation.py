"""
Deadline Escalation Tasks
Celery tasks for checking and sending escalation alerts for stale deadlines.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select

from backend.celery_app import celery_app
from backend.database import get_sync_session
from backend.models import Deadline, User
from backend.schemas.deadlines import DeadlineStatus

logger = logging.getLogger(__name__)


# Statuses that indicate work has started (don't escalate these)
ACTIVE_STATUSES = {
    DeadlineStatus.DRAFTING.value,
    DeadlineStatus.INTERNAL_REVIEW.value,
    DeadlineStatus.SUBMITTED.value,
    DeadlineStatus.UNDER_REVIEW.value,
    DeadlineStatus.AWARDED.value,
    DeadlineStatus.REJECTED.value,
}

# Days before deadline to trigger escalation for NOT_STARTED deadlines
ESCALATION_THRESHOLD_DAYS = 14


@celery_app.task(queue="normal")
def check_deadline_escalations() -> dict:
    """
    Check for stale deadlines and send escalation alerts.

    Runs daily via Celery Beat.
    Flags deadlines that are:
    - Still in NOT_STARTED status
    - Due within ESCALATION_THRESHOLD_DAYS days
    - Haven't had an escalation alert sent yet

    Returns:
        Dictionary with escalation statistics.
    """
    now = datetime.now(timezone.utc)
    threshold_date = now + timedelta(days=ESCALATION_THRESHOLD_DAYS)
    escalations_sent = 0
    errors = 0

    with get_sync_session() as session:
        # Find deadlines that need escalation
        result = session.execute(
            select(Deadline, User)
            .join(User, Deadline.user_id == User.id)
            .where(
                and_(
                    Deadline.status == DeadlineStatus.NOT_STARTED.value,
                    Deadline.escalation_sent == False,
                    Deadline.sponsor_deadline <= threshold_date,
                    Deadline.sponsor_deadline > now,  # Not already past
                )
            )
        )

        stale_deadlines = result.all()

        for deadline, user in stale_deadlines:
            try:
                # Calculate days until deadline
                days_until = (deadline.sponsor_deadline - now).days

                # Send escalation alert
                _send_escalation_alert(deadline, user, days_until)

                # Mark as escalated
                deadline.escalation_sent = True
                escalations_sent += 1

                logger.info(
                    f"Sent escalation for deadline {deadline.id} "
                    f"('{deadline.title}') - {days_until} days remaining"
                )

            except Exception as e:
                logger.error(f"Failed to send escalation for deadline {deadline.id}: {e}")
                errors += 1

        session.commit()

    logger.info(f"Deadline escalations: sent={escalations_sent}, errors={errors}")
    return {"escalations_sent": escalations_sent, "errors": errors}


def _send_escalation_alert(deadline: Deadline, user: User, days_until: int) -> None:
    """
    Send an escalation alert for a stale deadline.

    Args:
        deadline: The deadline that needs attention
        user: The user who owns the deadline
        days_until: Days remaining until the deadline
    """
    from agents.delivery.channels import get_sendgrid_channel
    from backend.core.config import settings

    if not user.email_notifications:
        logger.debug(f"User {user.id} has email notifications disabled, skipping escalation")
        return

    # Format urgency message
    if days_until <= 3:
        urgency = "CRITICAL"
        urgency_color = "#DC2626"  # Red
    elif days_until <= 7:
        urgency = "URGENT"
        urgency_color = "#F59E0B"  # Amber
    else:
        urgency = "IMPORTANT"
        urgency_color = "#3B82F6"  # Blue

    # Build email content
    subject = f"[{urgency}] Grant deadline requires attention: {deadline.title}"

    html_content = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, {urgency_color} 0%, #1E40AF 100%); padding: 30px; border-radius: 12px; color: white; text-align: center; margin-bottom: 24px;">
            <h1 style="margin: 0; font-size: 24px;">⚠️ {urgency} - Action Required</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Grant deadline needs your attention</p>
        </div>

        <div style="background: #F9FAFB; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
            <h2 style="color: #111827; margin: 0 0 16px 0; font-size: 18px;">{deadline.title}</h2>

            <div style="display: flex; gap: 16px; flex-wrap: wrap;">
                <div style="background: white; padding: 12px 16px; border-radius: 6px; flex: 1; min-width: 120px;">
                    <div style="color: #6B7280; font-size: 12px; text-transform: uppercase;">Days Remaining</div>
                    <div style="color: {urgency_color}; font-size: 24px; font-weight: bold;">{days_until}</div>
                </div>

                <div style="background: white; padding: 12px 16px; border-radius: 6px; flex: 1; min-width: 120px;">
                    <div style="color: #6B7280; font-size: 12px; text-transform: uppercase;">Status</div>
                    <div style="color: #6B7280; font-size: 14px; font-weight: 500;">Not Started</div>
                </div>

                <div style="background: white; padding: 12px 16px; border-radius: 6px; flex: 1; min-width: 120px;">
                    <div style="color: #6B7280; font-size: 12px; text-transform: uppercase;">Deadline</div>
                    <div style="color: #111827; font-size: 14px; font-weight: 500;">{deadline.sponsor_deadline.strftime('%B %d, %Y')}</div>
                </div>
            </div>

            {f'<p style="color: #6B7280; margin: 16px 0 0 0;"><strong>Funder:</strong> {deadline.funder}</p>' if deadline.funder else ''}
        </div>

        <div style="background: #FEF3C7; border: 1px solid #F59E0B; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
            <p style="color: #92400E; margin: 0;">
                <strong>This deadline has not been started yet.</strong><br>
                We recommend beginning your application soon to allow adequate time for drafting, review, and submission.
            </p>
        </div>

        <div style="text-align: center; margin-top: 24px;">
            <a href="{settings.FRONTEND_URL or 'http://localhost:5173'}/deadlines"
               style="display: inline-block; background: #3B82F6; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 500;">
                View Deadline Details
            </a>
        </div>

        <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 32px 0;">

        <p style="color: #9CA3AF; font-size: 12px; text-align: center;">
            You're receiving this because you have a grant deadline that needs attention.<br>
            <a href="{settings.FRONTEND_URL or 'http://localhost:5173'}/settings" style="color: #6B7280;">Manage notification preferences</a>
        </p>
    </body>
    </html>
    """

    # Send via SendGrid
    try:
        channel = get_sendgrid_channel()
        if channel:
            channel.send(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
            )
    except Exception as e:
        logger.error(f"Failed to send escalation email: {e}")
        raise


@celery_app.task(queue="normal")
def reset_escalation_flags() -> dict:
    """
    Reset escalation flags for deadlines that have moved past NOT_STARTED status.

    This allows re-escalation if a deadline is moved back to NOT_STARTED.
    Runs daily via Celery Beat.

    Returns:
        Dictionary with reset statistics.
    """
    reset_count = 0

    with get_sync_session() as session:
        # Find deadlines with escalation_sent=True but status is now active
        result = session.execute(
            select(Deadline).where(
                and_(
                    Deadline.escalation_sent == True,
                    Deadline.status.in_(ACTIVE_STATUSES),
                )
            )
        )

        deadlines = result.scalars().all()

        for deadline in deadlines:
            deadline.escalation_sent = False
            reset_count += 1

        session.commit()

    logger.info(f"Reset escalation flags for {reset_count} deadlines")
    return {"reset_count": reset_count}
