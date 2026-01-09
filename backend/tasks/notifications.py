"""
GrantRadar Notification Tasks
Celery tasks for sending notifications via WebSocket, email, and SMS.

This module handles:
- Deadline reminders for upcoming grant deadlines
- Grant update notifications when saved grants change
- Stats updates for dashboard counters
- Multi-channel notification delivery via Redis pub/sub
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.delivery.channels import (
    get_sendgrid_channel,
    get_slack_channel,
    get_twilio_channel,
)
from backend.celery_app import celery_app, critical_task
from backend.core.config import settings
from backend.database import get_async_session
from backend.models import Grant, Match, User
from backend.notifications import get_sync_notification_service

logger = logging.getLogger(__name__)


# =============================================================================
# Deadline Reminder Tasks
# =============================================================================


@celery_app.task(queue="critical")
def send_deadline_reminders() -> dict:
    """
    Send deadline reminders for grants with upcoming deadlines.

    Runs periodically (every hour via Celery Beat).
    Sends reminders for grants with deadlines in:
    - 7 days
    - 3 days
    - 1 day

    Returns:
        Dictionary with reminder statistics.
    """
    import asyncio

    return asyncio.run(_send_deadline_reminders_async())


async def _send_deadline_reminders_async() -> dict:
    """
    Async implementation of deadline reminder sending.

    Returns:
        Dictionary with reminder counts.
    """
    async for session in get_async_session():
        try:
            now = datetime.utcnow()
            reminders_sent = 0

            # Define reminder thresholds (in days)
            reminder_days = [7, 3, 1]

            for days in reminder_days:
                deadline_date = now + timedelta(days=days)

                # Find matches with upcoming deadlines
                # (grants with deadlines on the target date)
                result = await session.execute(
                    select(Match, Grant, User)
                    .join(Grant, Match.grant_id == Grant.id)
                    .join(User, Match.user_id == User.id)
                    .where(
                        and_(
                            Grant.deadline.isnot(None),
                            Grant.deadline >= deadline_date,
                            Grant.deadline < deadline_date + timedelta(days=1),
                            # Only remind for saved or unactioned matches
                            or_(
                                Match.user_action == "saved",
                                Match.user_action.is_(None),
                            ),
                        )
                    )
                )

                matches = result.all()

                for match, grant, user in matches:
                    await _send_deadline_reminder(
                        user_id=user.id,
                        grant_id=grant.id,
                        title=grant.title,
                        days_remaining=days,
                        deadline=grant.deadline,
                        url=grant.url,
                        session=session,
                    )
                    reminders_sent += 1

                logger.info(f"Sent {len(matches)} reminders for {days}-day deadline")

            logger.info(f"Deadline reminders completed: {reminders_sent} sent")

            return {
                "reminders_sent": reminders_sent,
                "checked_thresholds": reminder_days,
            }

        except Exception as e:
            logger.error(f"Error sending deadline reminders: {e}", exc_info=True)
            raise


async def _send_deadline_reminder(
    user_id: UUID,
    grant_id: UUID,
    title: str,
    days_remaining: int,
    deadline: datetime,
    url: Optional[str],
    session: AsyncSession,
) -> None:
    """
    Send a deadline reminder notification to a user.

    Args:
        user_id: Target user ID.
        grant_id: ID of the grant with upcoming deadline.
        title: Grant title.
        days_remaining: Number of days until deadline.
        deadline: Actual deadline datetime.
        url: Grant URL.
        session: Database session.
    """
    try:
        # Fetch user for notification preferences
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.error(f"User {user_id} not found for deadline reminder")
            return

        # Get notification service
        notif_service = get_sync_notification_service()

        # Send via WebSocket (Redis pub/sub)
        notif_service.notify_deadline_reminder(
            user_id=user_id,
            grant_id=grant_id,
            title=title,
            days_remaining=days_remaining,
            deadline=deadline,
            url=url,
        )

        logger.info(
            f"Sent deadline reminder: user={user_id}, grant={grant_id}, "
            f"days={days_remaining}"
        )

        # Send email reminder if user has email notifications enabled
        if user.email_notifications:
            await _send_deadline_email(
                user=user,
                grant_id=grant_id,
                title=title,
                days_remaining=days_remaining,
                deadline=deadline,
                url=url,
            )

        # Send SMS reminder if enabled and user has phone number
        if user.sms_notifications and user.phone:
            await _send_deadline_sms(
                user=user,
                grant_id=grant_id,
                title=title,
                days_remaining=days_remaining,
                deadline=deadline,
            )

    except Exception as e:
        logger.error(
            f"Failed to send deadline reminder for grant {grant_id}: {e}",
            exc_info=True,
        )


async def _send_deadline_email(
    user: User,
    grant_id: UUID,
    title: str,
    days_remaining: int,
    deadline: datetime,
    url: Optional[str],
) -> None:
    """
    Send deadline reminder email via SendGrid.

    Args:
        user: Target user object.
        grant_id: ID of the grant with upcoming deadline.
        title: Grant title.
        days_remaining: Number of days until deadline.
        deadline: Actual deadline datetime.
        url: Grant URL.
    """
    email_channel = get_sendgrid_channel()

    if not email_channel.is_configured():
        logger.warning("SendGrid not configured - skipping deadline email")
        return

    # Format deadline for display
    deadline_str = deadline.strftime("%B %d, %Y at %I:%M %p UTC")
    days_text = (
        "tomorrow" if days_remaining == 1 else f"in {days_remaining} days"
    )

    # Build email content
    subject = f"Deadline Reminder: {title} - Due {days_text}"

    grant_link = url or f"{settings.frontend_url}/grants/{grant_id}"

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
            <h2 style="color: #333; margin-top: 0;">Deadline Reminder</h2>
            <p>Hi {user.name or 'Researcher'},</p>
            <p>This is a reminder that the deadline for the following grant is coming up <strong>{days_text}</strong>:</p>
            <div style="background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0; color: #333;">{title}</h3>
                <p style="margin: 0; color: #666;">Deadline: {deadline_str}</p>
            </div>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{grant_link}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">View Grant Details</a>
            </div>
            <p style="color: #666; font-size: 14px;">Don't miss this opportunity! Make sure to submit your application before the deadline.</p>
            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
            <p style="color: #999; font-size: 12px; text-align: center;">
                You're receiving this because you saved this grant or it matched your research profile.<br>
                <a href="{settings.frontend_url}/settings/notifications" style="color: #667eea;">Manage notification preferences</a>
            </p>
        </div>
    </body>
    </html>
    """

    body_text = f"""
    Deadline Reminder

    Hi {user.name or 'Researcher'},

    This is a reminder that the deadline for the following grant is coming up {days_text}:

    {title}
    Deadline: {deadline_str}

    View grant details: {grant_link}

    Don't miss this opportunity! Make sure to submit your application before the deadline.

    - The {settings.app_name} Team

    Manage notification preferences: {settings.frontend_url}/settings/notifications
    """

    try:
        status = email_channel.send_email_sync(
            to_email=user.email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            to_name=user.name,
            tracking_id=str(grant_id),
        )

        if status.status == "sent":
            logger.info(
                f"Deadline email sent: user={user.id}, grant={grant_id}, "
                f"days={days_remaining}"
            )
        else:
            logger.warning(
                f"Deadline email failed: user={user.id}, grant={grant_id}, "
                f"error={status.error_message}"
            )

    except Exception as e:
        logger.error(
            f"Error sending deadline email for grant {grant_id}: {e}",
            exc_info=True,
        )


async def _send_deadline_sms(
    user: User,
    grant_id: UUID,
    title: str,
    days_remaining: int,
    deadline: datetime,
) -> None:
    """
    Send deadline reminder SMS via Twilio.

    Args:
        user: Target user object with phone number.
        grant_id: ID of the grant with upcoming deadline.
        title: Grant title.
        days_remaining: Number of days until deadline.
        deadline: Actual deadline datetime.
    """
    sms_channel = get_twilio_channel()

    if not sms_channel.is_configured():
        logger.warning("Twilio not configured - skipping deadline SMS")
        return

    if not user.phone:
        logger.warning(f"User {user.id} has no phone number - skipping SMS")
        return

    # Build concise SMS message (160 char limit)
    days_text = "tomorrow" if days_remaining == 1 else f"in {days_remaining} days"
    truncated_title = title[:60] + "..." if len(title) > 60 else title
    message = f"{settings.app_name}: Grant deadline {days_text}! '{truncated_title}' is due {deadline.strftime('%m/%d')}."

    try:
        status = sms_channel.send_sms(
            phone_number=user.phone,
            message=message,
            match_id=grant_id,
        )

        if status.status == "sent":
            logger.info(
                f"Deadline SMS sent: user={user.id}, grant={grant_id}, "
                f"days={days_remaining}"
            )
        else:
            logger.warning(
                f"Deadline SMS failed: user={user.id}, grant={grant_id}, "
                f"error={status.error_message}"
            )

    except Exception as e:
        logger.error(
            f"Error sending deadline SMS for grant {grant_id}: {e}",
            exc_info=True,
        )


@critical_task
def send_deadline_urgent_alert(grant_id: str, user_id: str) -> None:
    """
    Send urgent deadline alert (deadline within 24 hours).

    Args:
        grant_id: UUID of the grant.
        user_id: UUID of the user to notify.
    """
    import asyncio

    asyncio.run(_send_deadline_urgent_alert_async(UUID(grant_id), UUID(user_id)))


async def _send_deadline_urgent_alert_async(
    grant_id: UUID,
    user_id: UUID,
) -> None:
    """
    Async implementation of urgent deadline alert.

    Args:
        grant_id: UUID of the grant.
        user_id: UUID of the user to notify.
    """
    async for session in get_async_session():
        try:
            # Fetch grant
            result = await session.execute(select(Grant).where(Grant.id == grant_id))
            grant = result.scalar_one_or_none()

            if not grant:
                logger.error(f"Grant {grant_id} not found for urgent alert")
                return

            if not grant.deadline:
                return

            hours_remaining = (grant.deadline - datetime.utcnow()).total_seconds() / 3600

            if hours_remaining > 24:
                logger.warning(
                    f"Urgent alert called but deadline is {hours_remaining:.1f} hours away"
                )
                return

            # Send notification
            await _send_deadline_reminder(
                user_id=user_id,
                grant_id=grant_id,
                title=grant.title,
                days_remaining=0,
                deadline=grant.deadline,
                url=grant.url,
                session=session,
            )

            logger.info(f"Sent urgent deadline alert for grant {grant_id}")

        except Exception as e:
            logger.error(
                f"Error sending urgent deadline alert: {e}",
                exc_info=True,
            )
            raise


# =============================================================================
# Grant Update Notifications
# =============================================================================


async def notify_grant_update(
    grant_id: UUID,
    update_type: str,
    changes: Optional[dict] = None,
    message: Optional[str] = None,
) -> int:
    """
    Notify all users who have saved/matched a grant about an update.

    Args:
        grant_id: UUID of the updated grant.
        update_type: Type of update (e.g., 'deadline_changed', 'amount_updated').
        changes: Dictionary of changed fields.
        message: Human-readable update message.

    Returns:
        Number of users notified.
    """
    async for session in get_async_session():
        try:
            # Fetch grant
            result = await session.execute(select(Grant).where(Grant.id == grant_id))
            grant = result.scalar_one_or_none()

            if not grant:
                logger.error(f"Grant {grant_id} not found for update notification")
                return 0

            # Find all users who have saved or matched this grant
            result = await session.execute(
                select(User.id)
                .select_from(Match)
                .join(User, Match.user_id == User.id)
                .where(
                    and_(
                        Match.grant_id == grant_id,
                        or_(
                            Match.user_action == "saved",
                            Match.match_score >= 0.7,  # High matches get updates
                        ),
                    )
                )
                .distinct()
            )

            user_ids = [row[0] for row in result.all()]

            if not user_ids:
                logger.info(f"No users to notify for grant {grant_id} update")
                return 0

            # Get notification service
            notif_service = get_sync_notification_service()

            # Send notifications
            for user_id in user_ids:
                notif_service.notify_grant_update(
                    user_id=user_id,
                    grant_id=grant_id,
                    title=grant.title,
                    update_type=update_type,
                    changes=changes,
                    message=message,
                )

            logger.info(
                f"Sent grant update notifications: grant={grant_id}, "
                f"users={len(user_ids)}, type={update_type}"
            )

            return len(user_ids)

        except Exception as e:
            logger.error(
                f"Error sending grant update notifications: {e}",
                exc_info=True,
            )
            return 0


# =============================================================================
# High Match Alert
# =============================================================================


@critical_task
def send_high_match_alert(user_id: str, grant_id: str, match_score: float) -> None:
    """
    Send high-priority alert for exceptional matches (>90% score).

    Routed to critical queue for immediate delivery.

    Args:
        user_id: UUID of the user.
        grant_id: UUID of the matched grant.
        match_score: Match score (0.0 to 1.0).
    """
    import asyncio

    asyncio.run(
        _send_high_match_alert_async(
            UUID(user_id),
            UUID(grant_id),
            match_score,
        )
    )


async def _send_high_match_alert_async(
    user_id: UUID,
    grant_id: UUID,
    match_score: float,
) -> None:
    """
    Async implementation of high match alert.

    Args:
        user_id: UUID of the user.
        grant_id: UUID of the matched grant.
        match_score: Match score (0.0 to 1.0).
    """
    async for session in get_async_session():
        try:
            # Fetch grant
            result = await session.execute(select(Grant).where(Grant.id == grant_id))
            grant = result.scalar_one_or_none()

            if not grant:
                logger.error(f"Grant {grant_id} not found for high match alert")
                return

            # Fetch user for notification preferences
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {user_id} not found for high match alert")
                return

            # Get notification service
            notif_service = get_sync_notification_service()

            # Format amount range
            amount_range = None
            if grant.amount_min or grant.amount_max:
                if grant.amount_min and grant.amount_max:
                    amount_range = f"${grant.amount_min:,} - ${grant.amount_max:,}"
                elif grant.amount_min:
                    amount_range = f"${grant.amount_min:,}+"
                elif grant.amount_max:
                    amount_range = f"Up to ${grant.amount_max:,}"

            # Send WebSocket notification
            notif_service.notify_new_match(
                user_id=user_id,
                grant_id=grant_id,
                title=grant.title,
                match_score=match_score,
                deadline=grant.deadline,
                agency=grant.agency,
                amount_range=amount_range,
            )

            logger.info(
                f"Sent high match alert: user={user_id}, grant={grant_id}, "
                f"score={match_score:.2f}"
            )

            # Send email alert if user has email notifications enabled
            if user.email_notifications:
                await _send_high_match_email(
                    user=user,
                    grant=grant,
                    match_score=match_score,
                    amount_range=amount_range,
                )

            # Send SMS alert if enabled and user has phone number
            if user.sms_notifications and user.phone:
                await _send_high_match_sms(
                    user=user,
                    grant=grant,
                    match_score=match_score,
                    amount_range=amount_range,
                )

        except Exception as e:
            logger.error(
                f"Error sending high match alert: {e}",
                exc_info=True,
            )
            raise


async def _send_high_match_email(
    user: User,
    grant: Grant,
    match_score: float,
    amount_range: Optional[str],
) -> None:
    """
    Send high match alert email via SendGrid.

    Args:
        user: Target user object.
        grant: Matched grant object.
        match_score: Match score (0.0 to 1.0).
        amount_range: Formatted funding amount string.
    """
    email_channel = get_sendgrid_channel()

    if not email_channel.is_configured():
        logger.warning("SendGrid not configured - skipping high match email")
        return

    # Format match score as percentage
    match_pct = int(match_score * 100)

    # Format deadline if available
    deadline_str = ""
    if grant.deadline:
        deadline_str = grant.deadline.strftime("%B %d, %Y")

    # Build email content
    subject = f"Excellent Match ({match_pct}%): {grant.title}"

    grant_link = grant.url or f"{settings.frontend_url}/grants/{grant.id}"

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
            <div style="background: #e8f5e9; color: #2e7d32; padding: 15px; border-radius: 5px; text-align: center; margin-bottom: 20px;">
                <strong style="font-size: 24px;">{match_pct}% Match</strong>
                <p style="margin: 5px 0 0 0; font-size: 14px;">Exceptional match for your research profile!</p>
            </div>
            <h2 style="color: #333; margin-top: 0;">New High-Priority Grant Match</h2>
            <p>Hi {user.name or 'Researcher'},</p>
            <p>We've found a grant opportunity that's an excellent match for your research profile:</p>
            <div style="background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0; color: #333;">{grant.title}</h3>
                {f'<p style="margin: 5px 0; color: #666;"><strong>Agency:</strong> {grant.agency}</p>' if grant.agency else ''}
                {f'<p style="margin: 5px 0; color: #666;"><strong>Funding:</strong> {amount_range}</p>' if amount_range else ''}
                {f'<p style="margin: 5px 0; color: #666;"><strong>Deadline:</strong> {deadline_str}</p>' if deadline_str else ''}
            </div>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{grant_link}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">View Grant Details</a>
            </div>
            <p style="color: #666; font-size: 14px;">High-match grants are opportunities where your research expertise aligns strongly with the funding criteria. Don't miss this one!</p>
            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
            <p style="color: #999; font-size: 12px; text-align: center;">
                <a href="{settings.frontend_url}/settings/notifications" style="color: #667eea;">Manage notification preferences</a>
            </p>
        </div>
    </body>
    </html>
    """

    body_text = f"""
    {match_pct}% Match - Exceptional match for your research profile!

    New High-Priority Grant Match

    Hi {user.name or 'Researcher'},

    We've found a grant opportunity that's an excellent match for your research profile:

    {grant.title}
    {'Agency: ' + grant.agency if grant.agency else ''}
    {'Funding: ' + amount_range if amount_range else ''}
    {'Deadline: ' + deadline_str if deadline_str else ''}

    View grant details: {grant_link}

    High-match grants are opportunities where your research expertise aligns strongly with the funding criteria. Don't miss this one!

    - The {settings.app_name} Team

    Manage notification preferences: {settings.frontend_url}/settings/notifications
    """

    try:
        status = email_channel.send_email_sync(
            to_email=user.email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            to_name=user.name,
            tracking_id=str(grant.id),
        )

        if status.status == "sent":
            logger.info(
                f"High match email sent: user={user.id}, grant={grant.id}, "
                f"score={match_score:.2f}"
            )
        else:
            logger.warning(
                f"High match email failed: user={user.id}, grant={grant.id}, "
                f"error={status.error_message}"
            )

    except Exception as e:
        logger.error(
            f"Error sending high match email for grant {grant.id}: {e}",
            exc_info=True,
        )


async def _send_high_match_sms(
    user: User,
    grant: Grant,
    match_score: float,
    amount_range: Optional[str],
) -> None:
    """
    Send high match alert SMS via Twilio.

    Args:
        user: Target user object with phone number.
        grant: Matched grant object.
        match_score: Match score (0.0 to 1.0).
        amount_range: Formatted funding amount string.
    """
    sms_channel = get_twilio_channel()

    if not sms_channel.is_configured():
        logger.warning("Twilio not configured - skipping high match SMS")
        return

    if not user.phone:
        logger.warning(f"User {user.id} has no phone number - skipping SMS")
        return

    # Build concise SMS message (160 char limit)
    match_pct = int(match_score * 100)
    truncated_title = grant.title[:50] + "..." if len(grant.title) > 50 else grant.title
    message = f"{settings.app_name}: {match_pct}% match! '{truncated_title}'"
    if amount_range:
        # Add amount if there's room
        if len(message) + len(amount_range) + 3 <= 160:
            message += f" - {amount_range}"

    try:
        status = sms_channel.send_sms(
            phone_number=user.phone,
            message=message,
            match_id=grant.id,
        )

        if status.status == "sent":
            logger.info(
                f"High match SMS sent: user={user.id}, grant={grant.id}, "
                f"score={match_score:.2f}"
            )
        else:
            logger.warning(
                f"High match SMS failed: user={user.id}, grant={grant.id}, "
                f"error={status.error_message}"
            )

    except Exception as e:
        logger.error(
            f"Error sending high match SMS for grant {grant.id}: {e}",
            exc_info=True,
        )


# =============================================================================
# Stats Update Notifications
# =============================================================================


async def send_stats_update(user_id: UUID) -> None:
    """
    Send dashboard stats update to a user.

    Computes current stats and emits real-time update.

    Args:
        user_id: UUID of the user.
    """
    async for session in get_async_session():
        try:
            # Count new grants (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            result = await session.execute(
                select(Grant)
                .where(Grant.created_at >= yesterday)
            )
            new_grants_count = len(result.all())

            # Count high matches for this user
            result = await session.execute(
                select(Match)
                .where(
                    and_(
                        Match.user_id == user_id,
                        Match.match_score >= 0.8,
                        or_(
                            Match.user_action.is_(None),
                            Match.user_action != "dismissed",
                        ),
                    )
                )
            )
            high_matches_count = len(result.all())

            # Count pending deadlines (next 30 days)
            deadline_threshold = datetime.utcnow() + timedelta(days=30)
            result = await session.execute(
                select(Match)
                .join(Grant, Match.grant_id == Grant.id)
                .where(
                    and_(
                        Match.user_id == user_id,
                        Grant.deadline.isnot(None),
                        Grant.deadline <= deadline_threshold,
                        or_(
                            Match.user_action == "saved",
                            Match.user_action.is_(None),
                        ),
                    )
                )
            )
            pending_deadlines_count = len(result.all())

            # Count total saved grants
            result = await session.execute(
                select(Match)
                .where(
                    and_(
                        Match.user_id == user_id,
                        Match.user_action == "saved",
                    )
                )
            )
            total_saved_count = len(result.all())

            # Get notification service
            notif_service = get_sync_notification_service()

            # Send stats update
            notif_service.notify_stats_update(
                user_id=user_id,
                new_grants_count=new_grants_count,
                high_matches_count=high_matches_count,
                pending_deadlines_count=pending_deadlines_count,
                total_saved_count=total_saved_count,
            )

            logger.debug(f"Sent stats update to user {user_id}")

        except Exception as e:
            logger.error(
                f"Error sending stats update to user {user_id}: {e}",
                exc_info=True,
            )


# =============================================================================
# Password Reset Email
# =============================================================================


@celery_app.task(queue="critical")
def send_password_reset_email(email: str, name: str, reset_url: str) -> dict:
    """
    Send a password reset email to a user.

    Args:
        email: User's email address.
        name: User's name for personalization.
        reset_url: Password reset URL with token.

    Returns:
        Dictionary with send status.
    """
    try:
        from backend.core.config import settings

        # Check if SendGrid is configured
        if not settings.sendgrid_api_key:
            logger.warning(
                f"SendGrid not configured - would send password reset to {email}"
            )
            return {
                "status": "skipped",
                "reason": "SendGrid not configured",
                "email": email,
            }

        import sendgrid
        from sendgrid.helpers.mail import Content, Email, Mail, To

        sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)

        from_email = Email(settings.from_email, settings.from_name)
        to_email = To(email)
        subject = f"Reset Your {settings.app_name} Password"

        # HTML content for the email
        html_content = f"""
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
                <h2 style="color: #333; margin-top: 0;">Password Reset Request</h2>
                <p>Hi {name},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Reset Password</a>
                </div>
                <p style="color: #666; font-size: 14px;">This link will expire in 1 hour for security reasons.</p>
                <p style="color: #666; font-size: 14px;">If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{reset_url}" style="color: #667eea; word-break: break-all;">{reset_url}</a>
                </p>
            </div>
            <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                <p>&copy; {settings.app_name}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        # Plain text fallback
        plain_content = f"""
        Password Reset Request

        Hi {name},

        We received a request to reset your password. Click the link below to create a new password:

        {reset_url}

        This link will expire in 1 hour for security reasons.

        If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.

        - The {settings.app_name} Team
        """

        mail = Mail(from_email, to_email, subject, Content("text/plain", plain_content))
        mail.add_content(Content("text/html", html_content))

        response = sg.send(mail)

        logger.info(
            f"Password reset email sent to {email}, status_code={response.status_code}"
        )

        return {
            "status": "sent",
            "email": email,
            "status_code": response.status_code,
        }

    except Exception as e:
        logger.error(
            f"Failed to send password reset email to {email}: {e}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "email": email,
            "error": str(e),
        }


# =============================================================================
# Email Verification
# =============================================================================


@celery_app.task(queue="critical")
def send_verification_email(email: str, name: str, verification_url: str) -> dict:
    """
    Send an email verification email to a user.

    Args:
        email: User's email address.
        name: User's name for personalization.
        verification_url: Email verification URL with token.

    Returns:
        Dictionary with send status.
    """
    try:
        from backend.core.config import settings

        # Check if SendGrid is configured
        if not settings.sendgrid_api_key:
            logger.warning(
                f"SendGrid not configured - would send verification email to {email}"
            )
            return {
                "status": "skipped",
                "reason": "SendGrid not configured",
                "email": email,
            }

        import sendgrid
        from sendgrid.helpers.mail import Content, Email, Mail, To

        sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)

        from_email = Email(settings.from_email, settings.from_name)
        to_email = To(email)
        subject = f"Verify Your {settings.app_name} Email Address"

        # HTML content for the email
        html_content = f"""
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
                <h2 style="color: #333; margin-top: 0;">Verify Your Email Address</h2>
                <p>Hi {name},</p>
                <p>Thank you for creating an account with {settings.app_name}! Please verify your email address by clicking the button below:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Verify Email Address</a>
                </div>
                <p style="color: #666; font-size: 14px;">This link will expire in 24 hours for security reasons.</p>
                <p style="color: #666; font-size: 14px;">If you didn't create an account with {settings.app_name}, you can safely ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{verification_url}" style="color: #667eea; word-break: break-all;">{verification_url}</a>
                </p>
            </div>
            <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                <p>&copy; {settings.app_name}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        # Plain text fallback
        plain_content = f"""
        Verify Your Email Address

        Hi {name},

        Thank you for creating an account with {settings.app_name}! Please verify your email address by clicking the link below:

        {verification_url}

        This link will expire in 24 hours for security reasons.

        If you didn't create an account with {settings.app_name}, you can safely ignore this email.

        - The {settings.app_name} Team
        """

        mail = Mail(from_email, to_email, subject, Content("text/plain", plain_content))
        mail.add_content(Content("text/html", html_content))

        response = sg.send(mail)

        logger.info(
            f"Verification email sent to {email}, status_code={response.status_code}"
        )

        return {
            "status": "sent",
            "email": email,
            "status_code": response.status_code,
        }

    except Exception as e:
        logger.error(
            f"Failed to send verification email to {email}: {e}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "email": email,
            "error": str(e),
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "send_deadline_reminders",
    "send_deadline_urgent_alert",
    "send_high_match_alert",
    "notify_grant_update",
    "send_stats_update",
    "send_password_reset_email",
    "send_verification_email",
]
