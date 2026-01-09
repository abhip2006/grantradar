"""Celery tasks for funding alert emails."""
from datetime import datetime, timezone
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from backend.celery_app import celery_app
from backend.core.config import settings
from backend.database import get_sync_session
from backend.models import User, FundingAlertPreference
from backend.services.funding_alerts import FundingAlertsService
from sqlalchemy import select

logger = logging.getLogger(__name__)


@celery_app.task(name="backend.tasks.funding_alerts.send_user_alert")
def send_funding_alert(user_id: str):
    """Send funding alert to a specific user."""
    import asyncio

    async def _send():
        from backend.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            # Get user
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                logger.warning("User not found for alert", extra={"user_id": user_id})
                return

            # Get preferences
            result = await db.execute(
                select(FundingAlertPreference).where(FundingAlertPreference.user_id == user_id)
            )
            prefs = result.scalar_one_or_none()

            if not prefs or not prefs.enabled:
                logger.info("Alerts disabled for user", extra={"user_id": user_id})
                return

            # Generate alert content
            service = FundingAlertsService()
            preview = await service.preview_alert(db, user)

            if not preview.would_send:
                logger.info("No content to send", extra={"user_id": user_id, "reason": preview.reason})
                return

            # Generate email HTML
            html_content = service.generate_email_html(user, preview)

            # Send via SendGrid
            if settings.sendgrid_api_key:
                try:
                    message = Mail(
                        from_email=f"{settings.from_name} <{settings.from_email}>",
                        to_emails=user.email,
                        subject=f"Your GrantRadar Funding Update - {datetime.now().strftime('%b %d')}",
                        html_content=html_content,
                    )

                    sg = SendGridAPIClient(settings.sendgrid_api_key)
                    response = sg.send(message)

                    logger.info(
                        "Funding alert sent",
                        extra={
                            "user_id": user_id,
                            "status_code": response.status_code,
                            "grants": len(preview.new_grants),
                            "deadlines": len(preview.upcoming_deadlines),
                        }
                    )

                    # Update last_sent_at
                    prefs.last_sent_at = datetime.now(timezone.utc)
                    await db.commit()

                except Exception as e:
                    logger.error("Failed to send alert email", extra={"user_id": user_id, "error": str(e)})
                    raise
            else:
                logger.warning("SendGrid not configured, skipping email", extra={"user_id": user_id})

    asyncio.run(_send())


@celery_app.task(name="backend.tasks.funding_alerts.send_scheduled_alerts")
def send_scheduled_alerts():
    """Send scheduled funding alerts based on user preferences."""
    import asyncio

    async def _send_all():
        from backend.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)

            # Find users due for alerts
            result = await db.execute(
                select(FundingAlertPreference)
                .where(FundingAlertPreference.enabled == True)
            )
            all_prefs = result.scalars().all()

            for prefs in all_prefs:
                # Check if due based on frequency
                if prefs.last_sent_at:
                    if prefs.frequency == "daily":
                        delta = now - prefs.last_sent_at
                        if delta.days < 1:
                            continue
                    elif prefs.frequency == "weekly":
                        delta = now - prefs.last_sent_at
                        if delta.days < 7:
                            continue
                    elif prefs.frequency == "monthly":
                        delta = now - prefs.last_sent_at
                        if delta.days < 30:
                            continue

                # Queue individual alert
                send_funding_alert.delay(str(prefs.user_id))
                logger.info("Queued funding alert", extra={"user_id": str(prefs.user_id)})

    asyncio.run(_send_all())


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "send_funding_alert",
    "send_scheduled_alerts",
]
