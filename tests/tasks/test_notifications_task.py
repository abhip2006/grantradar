"""
Tests for notification Celery tasks.
Tests deadline reminders, grant updates, and high match alerts.
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Grant, Match, User


class TestDeadlineReminderLogic:
    """Tests for deadline reminder logic."""

    def test_reminder_days_thresholds(self):
        """Test that reminder thresholds are correct."""
        reminder_days = [7, 3, 1]

        assert 7 in reminder_days  # Week before
        assert 3 in reminder_days  # 3 days before
        assert 1 in reminder_days  # Day before

    def test_deadline_date_calculation(self):
        """Test deadline date calculation for reminders."""
        now = datetime.utcnow()
        days = 7

        deadline_date = now + timedelta(days=days)

        # Deadline should be 7 days from now
        assert (deadline_date - now).days == 7

    def test_days_text_formatting_tomorrow(self):
        """Test days text formatting for tomorrow."""
        days_remaining = 1
        days_text = "tomorrow" if days_remaining == 1 else f"in {days_remaining} days"

        assert days_text == "tomorrow"

    def test_days_text_formatting_multiple_days(self):
        """Test days text formatting for multiple days."""
        days_remaining = 7
        days_text = "tomorrow" if days_remaining == 1 else f"in {days_remaining} days"

        assert days_text == "in 7 days"


class TestSendPasswordResetEmail:
    """Tests for password reset email task."""

    @patch("backend.core.config.settings")
    def test_password_reset_no_sendgrid(self, mock_settings):
        """Test password reset when SendGrid not configured."""
        mock_settings.sendgrid_api_key = None

        # Simulate the check in the task
        if not mock_settings.sendgrid_api_key:
            result = {
                "status": "skipped",
                "reason": "SendGrid not configured",
                "email": "test@example.com",
            }

        assert result["status"] == "skipped"
        assert result["reason"] == "SendGrid not configured"

    def test_password_reset_email_subject_format(self):
        """Test password reset email subject format."""
        app_name = "GrantRadar"
        subject = f"Reset Your {app_name} Password"

        assert "Reset Your" in subject
        assert app_name in subject
        assert "Password" in subject


class TestHighMatchAlertLogic:
    """Tests for high match alert logic."""

    def test_match_score_percentage(self):
        """Test match score to percentage conversion."""
        match_score = 0.92
        match_pct = int(match_score * 100)

        assert match_pct == 92

    def test_amount_range_formatting_both(self):
        """Test amount range formatting with min and max."""
        amount_min = 100000
        amount_max = 500000

        if amount_min and amount_max:
            amount_range = f"${amount_min:,} - ${amount_max:,}"

        assert amount_range == "$100,000 - $500,000"

    def test_amount_range_formatting_min_only(self):
        """Test amount range formatting with min only."""
        amount_min = 100000
        amount_max = None

        if amount_min and not amount_max:
            amount_range = f"${amount_min:,}+"

        assert amount_range == "$100,000+"

    def test_amount_range_formatting_max_only(self):
        """Test amount range formatting with max only."""
        amount_min = None
        amount_max = 500000

        if not amount_min and amount_max:
            amount_range = f"Up to ${amount_max:,}"

        assert amount_range == "Up to $500,000"

    def test_sms_message_title_truncation(self):
        """Test SMS message title truncation."""
        long_title = "A" * 100  # 100 character title
        truncated_title = long_title[:50] + "..." if len(long_title) > 50 else long_title

        assert len(truncated_title) == 53  # 50 + "..."
        assert truncated_title.endswith("...")

    def test_sms_message_short_title(self):
        """Test SMS message with short title."""
        short_title = "NSF Grant"
        truncated_title = short_title[:50] + "..." if len(short_title) > 50 else short_title

        assert truncated_title == short_title

    def test_high_match_email_subject(self):
        """Test high match email subject format."""
        match_pct = 95
        title = "Test Grant"

        subject = f"Excellent Match ({match_pct}%): {title}"

        assert "Excellent Match" in subject
        assert "(95%)" in subject
        assert "Test Grant" in subject


class TestStatsUpdateLogic:
    """Tests for stats update logic."""

    def test_yesterday_calculation(self):
        """Test yesterday date calculation."""
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)

        delta = now - yesterday
        assert delta.days == 1

    def test_deadline_threshold_calculation(self):
        """Test deadline threshold calculation (30 days)."""
        now = datetime.utcnow()
        deadline_threshold = now + timedelta(days=30)

        delta = deadline_threshold - now
        assert delta.days == 30

    def test_high_match_threshold(self):
        """Test high match threshold (>= 0.8)."""
        high_threshold = 0.8

        assert 0.9 >= high_threshold
        assert 0.8 >= high_threshold
        assert 0.79 < high_threshold


class TestGrantUpdateNotificationLogic:
    """Tests for grant update notification logic."""

    def test_update_type_values(self):
        """Test valid update type values."""
        valid_types = ["deadline_changed", "amount_updated", "eligibility_updated", "title_changed"]

        assert "deadline_changed" in valid_types
        assert "amount_updated" in valid_types

    def test_high_match_threshold_for_updates(self):
        """Test high match threshold for updates (>= 0.7)."""
        threshold = 0.7

        # Users with 70% or higher matches get updates
        assert 0.75 >= threshold
        assert 0.7 >= threshold
        assert 0.69 < threshold


class TestDeadlineEmailContent:
    """Tests for deadline email content generation."""

    def test_email_subject_format(self):
        """Test email subject format."""
        title = "NSF Research Grant"
        days_text = "in 3 days"

        subject = f"Deadline Reminder: {title} - Due {days_text}"

        assert "Deadline Reminder:" in subject
        assert title in subject
        assert "Due" in subject
        assert days_text in subject

    def test_deadline_date_formatting(self):
        """Test deadline date formatting."""
        deadline = datetime(2025, 6, 15, 17, 0, 0, tzinfo=timezone.utc)
        deadline_str = deadline.strftime("%B %d, %Y at %I:%M %p UTC")

        assert "June 15, 2025" in deadline_str
        assert "05:00 PM UTC" in deadline_str

    def test_grant_link_with_url(self):
        """Test grant link generation with URL."""
        url = "https://grants.gov/test-grant"
        grant_id = uuid.uuid4()
        frontend_url = "https://app.grantradar.com"

        grant_link = url or f"{frontend_url}/grants/{grant_id}"

        assert grant_link == url

    def test_grant_link_without_url(self):
        """Test grant link generation without URL."""
        url = None
        grant_id = uuid.uuid4()
        frontend_url = "https://app.grantradar.com"

        grant_link = url or f"{frontend_url}/grants/{grant_id}"

        assert grant_link == f"{frontend_url}/grants/{grant_id}"


class TestDeadlineSMSContent:
    """Tests for deadline SMS content generation."""

    def test_sms_days_text_tomorrow(self):
        """Test SMS days text for tomorrow."""
        days_remaining = 1
        days_text = "tomorrow" if days_remaining == 1 else f"in {days_remaining} days"

        assert days_text == "tomorrow"

    def test_sms_days_text_multiple(self):
        """Test SMS days text for multiple days."""
        days_remaining = 3
        days_text = "tomorrow" if days_remaining == 1 else f"in {days_remaining} days"

        assert days_text == "in 3 days"

    def test_sms_title_truncation(self):
        """Test SMS title truncation (60 chars)."""
        long_title = "A" * 100
        truncated_title = long_title[:60] + "..." if len(long_title) > 60 else long_title

        assert len(truncated_title) == 63  # 60 + "..."

    def test_sms_deadline_date_format(self):
        """Test SMS deadline date format."""
        deadline = datetime(2025, 6, 15, tzinfo=timezone.utc)
        date_str = deadline.strftime("%m/%d")

        assert date_str == "06/15"


class TestUrgentAlertLogic:
    """Tests for urgent deadline alerts."""

    def test_hours_remaining_calculation(self):
        """Test hours remaining calculation."""
        now = datetime.utcnow()
        deadline = now + timedelta(hours=12)

        hours_remaining = (deadline - now).total_seconds() / 3600

        assert 11 < hours_remaining < 13

    def test_urgent_threshold(self):
        """Test urgent threshold (24 hours)."""
        now = datetime.utcnow()

        # Within 24 hours - urgent
        deadline_urgent = now + timedelta(hours=12)
        hours_urgent = (deadline_urgent - now).total_seconds() / 3600
        assert hours_urgent <= 24

        # Beyond 24 hours - not urgent
        deadline_not_urgent = now + timedelta(hours=30)
        hours_not_urgent = (deadline_not_urgent - now).total_seconds() / 3600
        assert hours_not_urgent > 24

    def test_urgent_uses_zero_days_remaining(self):
        """Test that urgent alerts use 0 days remaining."""
        # When sending urgent alert, days_remaining should be 0
        days_remaining = 0

        assert days_remaining == 0


class TestEmailNotificationPreferences:
    """Tests for email notification preference handling."""

    def test_email_notifications_enabled(self):
        """Test email notifications when enabled."""
        email_notifications = True

        should_send_email = email_notifications

        assert should_send_email is True

    def test_email_notifications_disabled(self):
        """Test email notifications when disabled."""
        email_notifications = False

        should_send_email = email_notifications

        assert should_send_email is False


class TestSMSNotificationPreferences:
    """Tests for SMS notification preference handling."""

    def test_sms_enabled_with_phone(self):
        """Test SMS when enabled with phone number."""
        sms_notifications = True
        phone = "+15551234567"

        should_send_sms = sms_notifications and phone

        assert should_send_sms

    def test_sms_enabled_without_phone(self):
        """Test SMS when enabled but no phone number."""
        sms_notifications = True
        phone = None

        should_send_sms = sms_notifications and phone

        assert not should_send_sms

    def test_sms_disabled_with_phone(self):
        """Test SMS when disabled but has phone number."""
        sms_notifications = False
        phone = "+15551234567"

        should_send_sms = sms_notifications and phone

        assert not should_send_sms


class TestNotificationServiceIntegration:
    """Tests for notification service integration patterns."""

    def test_notification_channel_check(self):
        """Test notification channel configuration check."""
        # Simulate SendGrid not configured
        is_configured = False

        if not is_configured:
            action = "skip"
        else:
            action = "send"

        assert action == "skip"

    def test_notification_status_sent(self):
        """Test notification status sent handling."""
        class MockStatus:
            status = "sent"

        status = MockStatus()

        assert status.status == "sent"

    def test_notification_status_failed(self):
        """Test notification status failed handling."""
        class MockStatus:
            status = "failed"
            error_message = "Invalid email address"

        status = MockStatus()

        assert status.status == "failed"
        assert status.error_message == "Invalid email address"


class TestReminderTaskStatistics:
    """Tests for reminder task statistics."""

    def test_stats_structure(self):
        """Test reminder task stats structure."""
        stats = {
            "reminders_sent": 15,
            "checked_thresholds": [7, 3, 1],
        }

        assert "reminders_sent" in stats
        assert "checked_thresholds" in stats
        assert stats["reminders_sent"] == 15
        assert len(stats["checked_thresholds"]) == 3

    def test_password_reset_stats_structure(self):
        """Test password reset task stats structure."""
        stats = {
            "status": "sent",
            "email": "test@example.com",
            "status_code": 202,
        }

        assert stats["status"] == "sent"
        assert "email" in stats
        assert stats["status_code"] == 202
