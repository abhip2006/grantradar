"""
Team collaboration Celery tasks.

Handles background tasks for team invitations including:
- Sending invitation emails
- Sending reminder emails before expiration
- Expiring old invitations
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_

from backend.celery_app import celery_app
from backend.core.config import settings
from backend.database import get_async_session
from backend.models import LabMember, User, InvitationStatus

logger = logging.getLogger(__name__)


# =============================================================================
# Invitation Email Task
# =============================================================================


@celery_app.task(queue="critical")
def send_invitation_email(
    to_email: str,
    inviter_name: str,
    lab_name: str,
    role: str,
    token: str,
    message: Optional[str] = None,
) -> dict:
    """
    Send a team invitation email to a new member.

    Args:
        to_email: Email address of the invitee.
        inviter_name: Name of the person sending the invitation.
        lab_name: Name of the lab/institution.
        role: Role assigned to the new member.
        token: Invitation token for accepting.
        message: Optional personal message from the inviter.

    Returns:
        Dictionary with send status.
    """
    try:
        # Check if SendGrid is configured
        if not settings.sendgrid_api_key:
            logger.warning(
                f"SendGrid not configured - would send invitation email to {to_email}"
            )
            return {
                "status": "skipped",
                "reason": "SendGrid not configured",
                "email": to_email,
            }

        import sendgrid
        from sendgrid.helpers.mail import Content, Email, Mail, To

        sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)

        from_email = Email(settings.from_email, settings.from_name)
        to_email_obj = To(to_email)
        subject = f"{inviter_name} invited you to join {lab_name} on {settings.app_name}"

        # Build accept URL
        accept_url = f"{settings.frontend_url}/team/accept?token={token}"

        # Build personal message section if provided
        message_section = ""
        if message:
            message_section = f"""
            <div style="background: #f9f9f9; padding: 15px; border-left: 4px solid #667eea; margin: 20px 0; border-radius: 0 5px 5px 0;">
                <p style="margin: 0; color: #555; font-style: italic;">"{message}"</p>
                <p style="margin: 10px 0 0 0; color: #888; font-size: 12px;">- {inviter_name}</p>
            </div>
            """

        # Role description
        role_descriptions = {
            "admin": "As an Admin, you'll be able to manage applications, invite other members, and access all team features.",
            "member": "As a Member, you'll be able to create and edit applications, and collaborate with the team.",
            "viewer": "As a Viewer, you'll be able to view applications and track progress.",
        }
        role_description = role_descriptions.get(
            role.lower(), "You'll be able to collaborate on grant applications."
        )

        # HTML content
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
                <h2 style="color: #333; margin-top: 0;">You're Invited!</h2>
                <p>Hi there,</p>
                <p><strong>{inviter_name}</strong> has invited you to join <strong>{lab_name}</strong> on {settings.app_name} as a <strong>{role.title()}</strong>.</p>
                {message_section}
                <p style="color: #666;">{role_description}</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{accept_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Accept Invitation</a>
                </div>
                <p style="color: #666; font-size: 14px;">This invitation will expire in 7 days.</p>
                <p style="color: #666; font-size: 14px;">If you don't want to join, you can simply ignore this email or click below to decline:</p>
                <p style="text-align: center;">
                    <a href="{settings.frontend_url}/team/decline?token={token}" style="color: #667eea; font-size: 14px;">Decline Invitation</a>
                </p>
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{accept_url}" style="color: #667eea; word-break: break-all;">{accept_url}</a>
                </p>
            </div>
            <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
                <p>&copy; {settings.app_name}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        plain_content = f"""
        You're Invited to {lab_name}!

        Hi there,

        {inviter_name} has invited you to join {lab_name} on {settings.app_name} as a {role.title()}.

        {f'Personal message: "{message}"' if message else ''}

        {role_description}

        Accept the invitation: {accept_url}

        This invitation will expire in 7 days.

        If you don't want to join, you can decline here:
        {settings.frontend_url}/team/decline?token={token}

        - The {settings.app_name} Team
        """

        mail = Mail(from_email, to_email_obj, subject, Content("text/plain", plain_content))
        mail.add_content(Content("text/html", html_content))

        response = sg.send(mail)

        logger.info(
            f"Invitation email sent to {to_email}, status_code={response.status_code}"
        )

        return {
            "status": "sent",
            "email": to_email,
            "status_code": response.status_code,
        }

    except Exception as e:
        logger.error(
            f"Failed to send invitation email to {to_email}: {e}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "email": to_email,
            "error": str(e),
        }


# =============================================================================
# Invitation Reminder Task
# =============================================================================


@celery_app.task(queue="normal")
def send_invitation_reminder(member_id: str) -> dict:
    """
    Send a reminder email for a pending invitation.

    Called 2 days before the invitation expires.

    Args:
        member_id: UUID of the lab member record.

    Returns:
        Dictionary with send status.
    """
    import asyncio

    return asyncio.run(_send_invitation_reminder_async(UUID(member_id)))


async def _send_invitation_reminder_async(member_id: UUID) -> dict:
    """
    Async implementation of invitation reminder.

    Args:
        member_id: UUID of the lab member record.

    Returns:
        Dictionary with send status.
    """
    async for session in get_async_session():
        try:
            # Fetch member with lab owner
            result = await session.execute(
                select(LabMember, User)
                .join(User, LabMember.lab_owner_id == User.id)
                .where(LabMember.id == member_id)
            )
            row = result.one_or_none()

            if not row:
                logger.warning(f"Member {member_id} not found for reminder")
                return {"status": "skipped", "reason": "member_not_found"}

            member, lab_owner = row

            # Check if still pending
            if member.invitation_status != InvitationStatus.PENDING.value:
                logger.info(
                    f"Skipping reminder for {member.member_email} - status is {member.invitation_status}"
                )
                return {"status": "skipped", "reason": "not_pending"}

            # Check if not expired
            if (
                member.invitation_expires_at
                and member.invitation_expires_at < datetime.now(timezone.utc)
            ):
                logger.info(f"Skipping reminder for {member.member_email} - already expired")
                return {"status": "skipped", "reason": "expired"}

            # Check if SendGrid is configured
            if not settings.sendgrid_api_key:
                logger.warning(
                    f"SendGrid not configured - would send reminder to {member.member_email}"
                )
                return {"status": "skipped", "reason": "sendgrid_not_configured"}

            import sendgrid
            from sendgrid.helpers.mail import Content, Email, Mail, To

            sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)

            from_email = Email(settings.from_email, settings.from_name)
            to_email = To(member.member_email)
            subject = f"Reminder: Your invitation to join {lab_owner.institution or 'a team'} expires soon"

            accept_url = f"{settings.frontend_url}/team/accept?token={member.invitation_token}"
            expires_in = (
                member.invitation_expires_at - datetime.now(timezone.utc)
            ).days

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
                    <h2 style="color: #333; margin-top: 0;">Your Invitation is Expiring Soon</h2>
                    <p>Hi there,</p>
                    <p>This is a friendly reminder that your invitation from <strong>{lab_owner.name or lab_owner.email}</strong> to join <strong>{lab_owner.institution or 'their team'}</strong> will expire in <strong>{expires_in} day{'s' if expires_in != 1 else ''}</strong>.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{accept_url}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Accept Invitation</a>
                    </div>
                    <p style="color: #666; font-size: 14px;">If you don't want to join, you can simply ignore this email.</p>
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        If the button doesn't work, copy and paste this link into your browser:<br>
                        <a href="{accept_url}" style="color: #667eea; word-break: break-all;">{accept_url}</a>
                    </p>
                </div>
            </body>
            </html>
            """

            plain_content = f"""
            Your Invitation is Expiring Soon

            Hi there,

            This is a friendly reminder that your invitation from {lab_owner.name or lab_owner.email} to join {lab_owner.institution or 'their team'} will expire in {expires_in} day{'s' if expires_in != 1 else ''}.

            Accept the invitation: {accept_url}

            If you don't want to join, you can simply ignore this email.

            - The {settings.app_name} Team
            """

            mail = Mail(
                from_email, to_email, subject, Content("text/plain", plain_content)
            )
            mail.add_content(Content("text/html", html_content))

            response = sg.send(mail)

            logger.info(
                f"Invitation reminder sent to {member.member_email}, "
                f"status_code={response.status_code}"
            )

            return {
                "status": "sent",
                "email": member.member_email,
                "status_code": response.status_code,
            }

        except Exception as e:
            logger.error(
                f"Failed to send invitation reminder for member {member_id}: {e}",
                exc_info=True,
            )
            return {
                "status": "failed",
                "member_id": str(member_id),
                "error": str(e),
            }


# =============================================================================
# Expire Old Invitations Task
# =============================================================================


@celery_app.task(queue="normal")
def expire_old_invitations() -> dict:
    """
    Mark expired invitations as expired.

    Should be run daily via Celery Beat.

    Returns:
        Dictionary with expiration statistics.
    """
    import asyncio

    return asyncio.run(_expire_old_invitations_async())


async def _expire_old_invitations_async() -> dict:
    """
    Async implementation of expiring old invitations.

    Returns:
        Dictionary with expiration statistics.
    """
    async for session in get_async_session():
        try:
            now = datetime.now(timezone.utc)

            # Find all pending invitations that have expired
            result = await session.execute(
                select(LabMember).where(
                    and_(
                        LabMember.invitation_status == InvitationStatus.PENDING.value,
                        LabMember.invitation_expires_at.isnot(None),
                        LabMember.invitation_expires_at < now,
                    )
                )
            )
            expired_invitations = result.scalars().all()

            expired_count = 0
            for member in expired_invitations:
                member.invitation_status = InvitationStatus.EXPIRED.value
                member.invitation_token = None
                expired_count += 1

            await session.commit()

            logger.info(f"Expired {expired_count} old invitations")

            # Schedule reminders for invitations expiring in 2 days
            two_days_from_now = now + timedelta(days=2)
            one_day_from_now = now + timedelta(days=1)

            reminder_result = await session.execute(
                select(LabMember.id).where(
                    and_(
                        LabMember.invitation_status == InvitationStatus.PENDING.value,
                        LabMember.invitation_expires_at.isnot(None),
                        LabMember.invitation_expires_at >= one_day_from_now,
                        LabMember.invitation_expires_at <= two_days_from_now,
                    )
                )
            )
            reminder_ids = [row[0] for row in reminder_result.all()]

            reminders_scheduled = 0
            for member_id in reminder_ids:
                send_invitation_reminder.delay(str(member_id))
                reminders_scheduled += 1

            logger.info(f"Scheduled {reminders_scheduled} invitation reminders")

            return {
                "status": "completed",
                "expired_count": expired_count,
                "reminders_scheduled": reminders_scheduled,
            }

        except Exception as e:
            logger.error(
                f"Error expiring old invitations: {e}",
                exc_info=True,
            )
            return {
                "status": "failed",
                "error": str(e),
            }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "send_invitation_email",
    "send_invitation_reminder",
    "expire_old_invitations",
]
