"""
GrandRadar Email Service
Jinja2-based email template rendering and sending via SendGrid.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import structlog
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from agents.delivery.channels import get_sendgrid_channel
from agents.delivery.models import DeliveryStatus
from backend.core.config import settings


logger = structlog.get_logger(__name__)


# Template directory path
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class EmailTemplateService:
    """
    Service for rendering and sending templated emails.

    Uses Jinja2 for template rendering and SendGrid for delivery.
    Provides both HTML and plain-text versions of emails.
    """

    def __init__(self):
        """Initialize the email template service with Jinja2 environment."""
        self._env: Optional[Environment] = None
        self._sendgrid = get_sendgrid_channel()

    @property
    def env(self) -> Environment:
        """Lazy-loaded Jinja2 environment."""
        if self._env is None:
            self._env = Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=True,
                trim_blocks=True,
                lstrip_blocks=True,
            )
        return self._env

    def _get_base_context(self) -> dict[str, Any]:
        """
        Get base context variables available in all templates.

        Returns:
            Dictionary with common template variables.
        """
        return {
            "app_name": settings.app_name,
            "frontend_url": settings.frontend_url,
            "backend_url": settings.backend_url,
            "current_year": datetime.now().year,
        }

    def render_template(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """
        Render a Jinja2 template with the given context.

        Args:
            template_name: Name of the template file (e.g., "welcome.html").
            context: Dictionary of variables to pass to the template.

        Returns:
            Rendered template as a string.

        Raises:
            TemplateNotFound: If the template file doesn't exist.
        """
        full_context = {**self._get_base_context(), **context}
        template = self.env.get_template(template_name)
        return template.render(**full_context)

    def render_email(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> tuple[str, str]:
        """
        Render both HTML and plain-text versions of an email template.

        Args:
            template_name: Base name of the template (without extension).
            context: Dictionary of variables to pass to the template.

        Returns:
            Tuple of (html_content, text_content).
        """
        html_content = self.render_template(f"{template_name}.html", context)

        # Try to load plain text version, fall back to empty string
        try:
            text_content = self.render_template(f"{template_name}.txt", context)
        except TemplateNotFound:
            logger.warning(
                "plain_text_template_not_found",
                template=f"{template_name}.txt",
            )
            text_content = ""

        return html_content, text_content

    def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict[str, Any],
        to_name: Optional[str] = None,
        tracking_id: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> DeliveryStatus:
        """
        Render and send a templated email.

        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            template_name: Base name of the template (without extension).
            context: Dictionary of variables to pass to the template.
            to_name: Optional recipient name.
            tracking_id: Optional tracking ID for webhook correlation.
            reply_to: Optional reply-to email address.

        Returns:
            DeliveryStatus with send result.
        """
        if not self._sendgrid.is_configured():
            logger.warning(
                "sendgrid_not_configured",
                to_email=to_email,
                template=template_name,
            )
            return DeliveryStatus(
                alert_id=None,
                match_id=UUID(tracking_id) if tracking_id else None,
                channel="email",
                status="skipped",
                error_message="SendGrid not configured",
            )

        try:
            html_content, text_content = self.render_email(template_name, context)

            status = self._sendgrid.send_email_sync(
                to_email=to_email,
                subject=subject,
                body_html=html_content,
                body_text=text_content,
                to_name=to_name,
                tracking_id=tracking_id,
                reply_to=reply_to,
            )

            logger.info(
                "templated_email_sent",
                to_email=to_email,
                template=template_name,
                status=status.status,
            )

            return status

        except Exception as e:
            logger.error(
                "templated_email_failed",
                to_email=to_email,
                template=template_name,
                error=str(e),
            )
            raise

    # ==========================================================================
    # Convenience methods for specific email types
    # ==========================================================================

    def send_password_reset(
        self,
        to_email: str,
        user_name: str,
        reset_link: str,
        expiry_hours: int = 1,
    ) -> DeliveryStatus:
        """
        Send a password reset email.

        Args:
            to_email: Recipient email address.
            user_name: User's name for personalization.
            reset_link: Password reset URL with token.
            expiry_hours: Hours until the reset link expires.

        Returns:
            DeliveryStatus with send result.
        """
        context = {
            "user_name": user_name,
            "reset_link": reset_link,
            "expiry_hours": expiry_hours,
        }

        return self.send_email(
            to_email=to_email,
            subject=f"Reset Your {settings.app_name} Password",
            template_name="password_reset",
            context=context,
            to_name=user_name,
        )

    def send_welcome(
        self,
        to_email: str,
        user_name: str,
        dashboard_url: Optional[str] = None,
    ) -> DeliveryStatus:
        """
        Send a welcome email to a new user.

        Args:
            to_email: Recipient email address.
            user_name: User's name for personalization.
            dashboard_url: Optional custom dashboard URL.

        Returns:
            DeliveryStatus with send result.
        """
        context = {
            "user_name": user_name,
            "dashboard_url": dashboard_url or f"{settings.frontend_url}/dashboard",
        }

        return self.send_email(
            to_email=to_email,
            subject=f"Welcome to {settings.app_name}!",
            template_name="welcome",
            context=context,
            to_name=user_name,
        )

    def send_notification(
        self,
        to_email: str,
        user_name: str,
        notification_title: str,
        notification_message: str,
        notification_type: Optional[str] = None,
        notification_category: Optional[str] = None,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        preview_text: Optional[str] = None,
        additional_notes: Optional[str] = None,
        secondary_action_url: Optional[str] = None,
        secondary_action_text: Optional[str] = None,
    ) -> DeliveryStatus:
        """
        Send a generic notification email.

        Args:
            to_email: Recipient email address.
            user_name: User's name for personalization.
            notification_title: Title of the notification.
            notification_message: Main message content.
            notification_type: Type badge (success, warning, error, info).
            notification_category: Category shown in header.
            action_url: Primary CTA button URL.
            action_text: Primary CTA button text.
            details: Optional details box with title and items dict.
            preview_text: Email preview text.
            additional_notes: Optional notes section.
            secondary_action_url: Secondary link URL.
            secondary_action_text: Secondary link text.

        Returns:
            DeliveryStatus with send result.
        """
        context = {
            "user_name": user_name,
            "notification_title": notification_title,
            "notification_message": notification_message,
            "notification_type": notification_type,
            "notification_category": notification_category,
            "action_url": action_url,
            "action_text": action_text,
            "details": details,
            "preview_text": preview_text,
            "additional_notes": additional_notes,
            "secondary_action_url": secondary_action_url,
            "secondary_action_text": secondary_action_text,
        }

        return self.send_email(
            to_email=to_email,
            subject=notification_title,
            template_name="notification",
            context=context,
            to_name=user_name,
        )

    def send_deadline_reminder(
        self,
        to_email: str,
        user_name: str,
        grant_title: str,
        deadline_date: str,
        time_remaining: str,
        days_remaining: int,
        view_url: str,
        funder: Optional[str] = None,
        mechanism: Optional[str] = None,
        amount_range: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None,
        grant_url: Optional[str] = None,
        deadline_type: str = "grant",
        tracking_id: Optional[str] = None,
    ) -> DeliveryStatus:
        """
        Send a deadline reminder email.

        Args:
            to_email: Recipient email address.
            user_name: User's name for personalization.
            grant_title: Title of the grant/deadline.
            deadline_date: Formatted deadline date string.
            time_remaining: Human-readable time remaining (e.g., "3 days").
            days_remaining: Number of days until deadline.
            view_url: URL to view the grant/deadline in the app.
            funder: Optional funder name.
            mechanism: Optional grant mechanism.
            amount_range: Optional formatted funding amount.
            priority: Optional priority level (high, medium, low).
            status: Optional current status.
            notes: Optional user notes.
            grant_url: Optional external grant URL.
            deadline_type: Type of deadline (grant or custom).
            tracking_id: Optional tracking ID.

        Returns:
            DeliveryStatus with send result.
        """
        context = {
            "user_name": user_name,
            "grant_title": grant_title,
            "deadline_date": deadline_date,
            "time_remaining": time_remaining,
            "days_remaining": days_remaining,
            "view_url": view_url,
            "funder": funder,
            "mechanism": mechanism,
            "amount_range": amount_range,
            "priority": priority,
            "status": status,
            "notes": notes,
            "grant_url": grant_url,
            "deadline_type": deadline_type,
        }

        subject = f"Deadline Reminder: {grant_title} - Due in {time_remaining}"

        return self.send_email(
            to_email=to_email,
            subject=subject,
            template_name="deadline_reminder",
            context=context,
            to_name=user_name,
            tracking_id=tracking_id,
        )

    def send_grant_match(
        self,
        to_email: str,
        user_name: str,
        grant_title: str,
        match_score: float,
        agency: Optional[str] = None,
        amount_range: Optional[str] = None,
        deadline_date: Optional[str] = None,
        grant_url: str = None,
        view_url: str = None,
        grant_id: Optional[str] = None,
    ) -> DeliveryStatus:
        """
        Send a high match alert email.

        Args:
            to_email: Recipient email address.
            user_name: User's name for personalization.
            grant_title: Title of the matched grant.
            match_score: Match score (0.0 to 1.0).
            agency: Optional funding agency.
            amount_range: Optional formatted funding amount.
            deadline_date: Optional formatted deadline.
            grant_url: External grant URL.
            view_url: URL to view in app.
            grant_id: Optional grant ID for tracking.

        Returns:
            DeliveryStatus with send result.
        """
        match_pct = int(match_score * 100)

        context = {
            "user_name": user_name,
            "notification_title": f"Excellent Match ({match_pct}%): {grant_title}",
            "notification_message": f"We've found a grant opportunity that's an excellent match for your research profile.",
            "notification_type": "success",
            "notification_category": "Grant Match",
            "action_url": view_url or grant_url,
            "action_text": "View Grant Details",
            "details": {
                "title": grant_title,
                "items": {
                    k: v
                    for k, v in {
                        "Match Score": f"{match_pct}%",
                        "Agency": agency,
                        "Funding": amount_range,
                        "Deadline": deadline_date,
                    }.items()
                    if v
                },
            },
            "preview_text": f"{match_pct}% match! {grant_title}",
            "additional_notes": "High-match grants are opportunities where your research expertise aligns strongly with the funding criteria.",
        }

        if grant_url and view_url:
            context["secondary_action_url"] = grant_url
            context["secondary_action_text"] = "Visit Funder's Website"

        return self.send_email(
            to_email=to_email,
            subject=f"Excellent Match ({match_pct}%): {grant_title}",
            template_name="notification",
            context=context,
            to_name=user_name,
            tracking_id=grant_id,
        )


# Singleton instance
_email_service: Optional[EmailTemplateService] = None


def get_email_service() -> EmailTemplateService:
    """Get or create the email template service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailTemplateService()
    return _email_service


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "EmailTemplateService",
    "get_email_service",
]
