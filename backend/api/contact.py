"""Contact form API endpoints."""

import logging
from fastapi import APIRouter, BackgroundTasks
from backend.schemas.contact import ContactFormRequest, ContactFormResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contact", tags=["contact"])


async def send_contact_email(data: ContactFormRequest):
    """Send contact form submission via email."""
    try:
        # Import here to avoid circular imports
        from agents.delivery.channels import SendGridChannel

        channel = SendGridChannel()

        subject_labels = {
            "general": "General Inquiry",
            "support": "Technical Support",
            "billing": "Billing Question",
            "enterprise": "Enterprise Sales",
            "partnership": "Partnership Opportunity",
            "feedback": "Product Feedback",
        }

        subject = f"[GrantRadar Contact] {subject_labels.get(data.subject, 'General')}: {data.name}"

        html_content = f"""
        <h2>New Contact Form Submission</h2>
        <p><strong>From:</strong> {data.name} ({data.email})</p>
        <p><strong>Subject:</strong> {subject_labels.get(data.subject, "General")}</p>
        <hr>
        <p><strong>Message:</strong></p>
        <p style="white-space: pre-wrap;">{data.message}</p>
        <hr>
        <p style="color: #666; font-size: 12px;">
            Reply directly to this email to respond to the user.
        </p>
        """

        # Send to support email
        await channel.send(
            to_email="support@grantradar.com", subject=subject, html_content=html_content, reply_to=data.email
        )

        logger.info(f"Contact form submitted: {data.subject} from {data.email}")

    except Exception as e:
        logger.error(f"Failed to send contact email: {e}")
        # Don't raise - we still want to return success to user
        # The form submission is logged, we can follow up manually


@router.post("", response_model=ContactFormResponse)
async def submit_contact_form(data: ContactFormRequest, background_tasks: BackgroundTasks):
    """
    Submit a contact form.

    The form is processed asynchronously - an email is sent to support
    and logged for follow-up.
    """
    # Log the submission immediately
    logger.info(f"Contact form received: subject={data.subject}, name={data.name}, email={data.email}")

    # Send email in background (don't block the response)
    background_tasks.add_task(send_contact_email, data)

    return ContactFormResponse(
        success=True, message="Thank you for contacting us. We'll get back to you within 24 hours."
    )
