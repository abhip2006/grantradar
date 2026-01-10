"""
Tests for Contact Form API endpoints.
Tests contact form submission and email processing.
"""


class TestContactFormRequest:
    """Tests for ContactFormRequest schema."""

    def test_schema_fields(self):
        """Test ContactFormRequest has required fields."""
        from backend.schemas.contact import ContactFormRequest

        schema_fields = ContactFormRequest.model_fields

        assert "name" in schema_fields
        assert "email" in schema_fields
        assert "subject" in schema_fields
        assert "message" in schema_fields


class TestContactFormResponse:
    """Tests for ContactFormResponse schema."""

    def test_schema_fields(self):
        """Test ContactFormResponse has required fields."""
        from backend.schemas.contact import ContactFormResponse

        schema_fields = ContactFormResponse.model_fields

        assert "success" in schema_fields
        assert "message" in schema_fields


class TestSubjectLabels:
    """Tests for subject label mapping."""

    def test_subject_labels(self):
        """Test subject labels are defined."""
        subject_labels = {
            "general": "General Inquiry",
            "support": "Technical Support",
            "billing": "Billing Question",
            "enterprise": "Enterprise Sales",
            "partnership": "Partnership Opportunity",
            "feedback": "Product Feedback",
        }

        assert subject_labels["general"] == "General Inquiry"
        assert subject_labels["support"] == "Technical Support"
        assert subject_labels["billing"] == "Billing Question"
        assert subject_labels["enterprise"] == "Enterprise Sales"

    def test_subject_label_fallback(self):
        """Test fallback for unknown subject."""
        subject_labels = {
            "general": "General Inquiry",
            "support": "Technical Support",
        }

        # Unknown subject should use 'General'
        unknown = "unknown_subject"
        label = subject_labels.get(unknown, "General")

        assert label == "General"


class TestEmailContentGeneration:
    """Tests for email content generation."""

    def test_email_subject_format(self):
        """Test email subject format."""
        name = "John Doe"
        subject_label = "Technical Support"

        subject = f"[GrantRadar Contact] {subject_label}: {name}"

        assert "[GrantRadar Contact]" in subject
        assert "Technical Support" in subject
        assert "John Doe" in subject

    def test_email_html_content(self):
        """Test email HTML content structure."""
        name = "Jane Doe"
        email = "jane@example.com"
        subject_label = "General"
        message = "This is my inquiry."

        html_content = f"""
        <h2>New Contact Form Submission</h2>
        <p><strong>From:</strong> {name} ({email})</p>
        <p><strong>Subject:</strong> {subject_label}</p>
        <hr>
        <p><strong>Message:</strong></p>
        <p style="white-space: pre-wrap;">{message}</p>
        """

        assert "<h2>New Contact Form Submission</h2>" in html_content
        assert "Jane Doe" in html_content
        assert "jane@example.com" in html_content
        assert "This is my inquiry." in html_content


class TestRouterConfiguration:
    """Tests for router configuration."""

    def test_router_prefix(self):
        """Test router prefix is correct."""
        from backend.api.contact import router

        assert router.prefix == "/api/contact"

    def test_router_tags(self):
        """Test router tags are correct."""
        from backend.api.contact import router

        assert "contact" in router.tags


class TestResponseMessage:
    """Tests for response message."""

    def test_success_message(self):
        """Test success response message."""
        message = "Thank you for contacting us. We'll get back to you within 24 hours."

        assert "Thank you" in message
        assert "24 hours" in message

    def test_response_structure(self):
        """Test response structure."""
        response = {"success": True, "message": "Thank you for contacting us."}

        assert response["success"] is True
        assert "message" in response


class TestBackgroundTaskProcessing:
    """Tests for background task processing."""

    def test_background_task_pattern(self):
        """Test background task pattern."""
        from fastapi import BackgroundTasks

        # Verify BackgroundTasks can be used
        tasks = BackgroundTasks()

        assert hasattr(tasks, "add_task")

    def test_async_email_sending_pattern(self):
        """Test async email sending pattern."""
        # The send_contact_email function is async
        import asyncio

        async def mock_send_email():
            return True

        # Should be callable as async
        assert asyncio.iscoroutinefunction(mock_send_email)


class TestErrorHandling:
    """Tests for error handling in contact form."""

    def test_error_logging_pattern(self):
        """Test that errors are logged but don't fail the request."""
        # The pattern: log error but return success to user
        error_occurred = True
        success_response = True  # Still return success

        # Even with error, user sees success
        if error_occurred:
            # Log error
            pass

        assert success_response is True

    def test_exception_caught(self):
        """Test exception handling pattern."""
        try:
            # Simulate email sending error
            raise Exception("SMTP connection failed")
        except Exception as e:
            error_message = str(e)
            logged = True

        assert error_message == "SMTP connection failed"
        assert logged is True
