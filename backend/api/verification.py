"""
Email Verification API Endpoints
Send verification emails and verify email addresses.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from backend.api.deps import (
    AsyncSessionDep,
    CurrentUser,
    OptionalUser,
)
from backend.core.config import settings
from backend.core.rate_limit import RateLimitAuth
from backend.models import User
from backend.schemas.auth import (
    SendVerificationRequest,
    SendVerificationResponse,
    VerifyEmailResponse,
)

logger = logging.getLogger(__name__)

# Verification token settings
VERIFICATION_TOKEN_EXPIRE_HOURS = 24

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _hash_token(token: str) -> str:
    """
    Hash a verification token for secure storage.

    Uses SHA-256 which is sufficient for token hashing since:
    - Tokens are already cryptographically random (high entropy)
    - We're not storing passwords, just random tokens
    - Fast lookup is more important than bcrypt's slowness

    Args:
        token: The raw verification token.

    Returns:
        Hex-encoded SHA-256 hash of the token.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_verification_token() -> tuple[str, str, datetime]:
    """
    Generate a secure verification token and its hash.

    Returns:
        Tuple of (raw_token, token_hash, expiration_datetime).
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires = datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
    return raw_token, token_hash, expires


async def generate_and_send_verification_email(
    user: User,
    db,
) -> None:
    """
    Generate a verification token for a user and send the verification email.

    This is a helper function used both during registration and for resending
    verification emails.

    Args:
        user: The user to send verification email to.
        db: Database session.
    """
    # Generate new verification token
    raw_token, token_hash, expires = _generate_verification_token()

    # Store hashed token in database
    user.email_verification_token_hash = token_hash
    user.email_verification_token_expires = expires
    await db.flush()

    # Queue verification email via Celery
    from backend.tasks.notifications import send_verification_email

    verification_url = f"{settings.frontend_url}/verify-email?token={raw_token}"
    send_verification_email.delay(
        email=user.email,
        name=user.name or "User",
        verification_url=verification_url,
    )

    logger.info(f"Verification email queued for user {user.id}")


@router.post(
    "/send-verification",
    response_model=SendVerificationResponse,
    summary="Send/resend verification email",
    description="Send or resend the email verification email. Rate limited to prevent abuse.",
)
async def send_verification(
    db: AsyncSessionDep,
    request: Optional[SendVerificationRequest] = None,
    current_user: OptionalUser = None,
    _rate_limit: RateLimitAuth = None,
) -> SendVerificationResponse:
    """
    Send or resend an email verification email.

    - If authenticated, sends to the current user's email
    - If email is provided in request body, looks up that user
    - Always returns success to prevent email enumeration
    - Rate limited to prevent abuse
    """
    email_to_verify = None

    # Determine which email to send verification to
    if current_user:
        email_to_verify = current_user.email
    elif request and request.email:
        email_to_verify = request.email
    else:
        # No email provided and not authenticated
        return SendVerificationResponse(message="Please provide an email address or authenticate first.", success=False)

    # Always return success to prevent email enumeration
    response = SendVerificationResponse()

    try:
        # Find user by email
        result = await db.execute(select(User).where(User.email == email_to_verify))
        user = result.scalar_one_or_none()

        if user:
            # Check if already verified
            if user.email_verified:
                logger.info(f"User {user.id} already verified, skipping email")
                return SendVerificationResponse(message="This email address is already verified.", success=True)

            # Check rate limiting - don't send too many emails
            if user.email_verification_token_expires:
                time_since_last = datetime.utcnow() - (
                    user.email_verification_token_expires - timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
                )
                # Only allow resend if at least 1 minute has passed since last send
                if time_since_last.total_seconds() < 60:
                    logger.warning(f"Rate limited verification email for user {user.id}")
                    return SendVerificationResponse(
                        message="Please wait before requesting another verification email.", success=False
                    )

            # Generate and send verification email
            await generate_and_send_verification_email(user, db)

        else:
            logger.info(f"Verification requested for non-existent email: {email_to_verify}")

    except Exception as e:
        # Log error but don't expose it to the user
        logger.error(f"Error sending verification email: {e}", exc_info=True)

    return response


@router.get(
    "/verify-email",
    response_model=VerifyEmailResponse,
    summary="Verify email address",
    description="Verify email using the token from the verification email.",
)
async def verify_email(
    token: str = Query(..., description="The verification token from the email"),
    db: AsyncSessionDep = None,
) -> VerifyEmailResponse:
    """
    Verify a user's email address using the verification token.

    - Validates the token is correct and not expired
    - Marks the email as verified
    - Invalidates the token after successful verification
    """
    try:
        # Hash the provided token
        token_hash = _hash_token(token)

        # Find user by token hash
        result = await db.execute(select(User).where(User.email_verification_token_hash == token_hash))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token")

        # Check if already verified
        if user.email_verified:
            return VerifyEmailResponse(message="Your email is already verified.", success=True, email_verified=True)

        # Check if token is expired
        if user.email_verification_token_expires:
            if datetime.utcnow() > user.email_verification_token_expires:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification token has expired. Please request a new one.",
                )

        # Mark email as verified
        user.email_verified = True
        user.email_verification_token_hash = None
        user.email_verification_token_expires = None
        await db.flush()

        logger.info(f"Email verified for user {user.id}")

        return VerifyEmailResponse(
            message="Your email has been verified successfully!", success=True, email_verified=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error occurred while verifying your email"
        )


@router.get(
    "/verification-status",
    response_model=VerifyEmailResponse,
    summary="Check verification status",
    description="Check the current email verification status for the authenticated user.",
)
async def get_verification_status(
    current_user: CurrentUser,
) -> VerifyEmailResponse:
    """
    Check the email verification status for the current user.

    Requires authentication.
    """
    if current_user.email_verified:
        return VerifyEmailResponse(message="Your email is verified.", success=True, email_verified=True)
    else:
        return VerifyEmailResponse(
            message="Your email is not verified. Please check your inbox for the verification email.",
            success=True,
            email_verified=False,
        )
