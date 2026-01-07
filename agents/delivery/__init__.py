"""
GrantRadar Alert Delivery Agent
Handles multi-channel alert delivery for grant matches.
"""
from agents.delivery.alerter import (
    AlertDeliveryAgent,
    celery_app,
    send_critical_alert,
    send_high_priority_alert,
    send_medium_priority_alert,
    process_digest_batch,
    process_all_digests,
)
from agents.delivery.channels import (
    SendGridChannel,
    TwilioChannel,
    SlackChannel,
    get_sendgrid_channel,
    get_twilio_channel,
    get_slack_channel,
)
from agents.delivery.models import (
    AlertPayload,
    AlertPriority,
    DeliveryChannel,
    DeliveryStatus,
    DigestBatch,
    EmailContent,
    GrantInfo,
    MatchInfo,
    SMSContent,
    SlackContent,
    UserInfo,
)

__all__ = [
    # Agent
    "AlertDeliveryAgent",
    # Celery
    "celery_app",
    "send_critical_alert",
    "send_high_priority_alert",
    "send_medium_priority_alert",
    "process_digest_batch",
    "process_all_digests",
    # Channels
    "SendGridChannel",
    "TwilioChannel",
    "SlackChannel",
    "get_sendgrid_channel",
    "get_twilio_channel",
    "get_slack_channel",
    # Models
    "AlertPayload",
    "AlertPriority",
    "DeliveryChannel",
    "DeliveryStatus",
    "DigestBatch",
    "EmailContent",
    "GrantInfo",
    "MatchInfo",
    "SMSContent",
    "SlackContent",
    "UserInfo",
]
