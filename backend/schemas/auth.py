"""
Authentication schemas for user registration, login, and JWT tokens.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    name: Optional[str] = Field(None, description="User's full name")
    institution: Optional[str] = Field(None, description="Research institution")


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Schema for decoded token data."""

    user_id: Optional[UUID] = None
    email: Optional[str] = None
    exp: Optional[datetime] = None


class UserResponse(BaseModel):
    """Schema for user information response."""

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User's full name")
    institution: Optional[str] = Field(None, description="Research institution")
    phone: Optional[str] = Field(None, description="Phone number")
    created_at: datetime = Field(..., description="Account creation timestamp")
    has_profile: bool = Field(default=False, description="Whether user has completed profile")
    email_verified: bool = Field(default=False, description="Whether email has been verified")

    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""

    email: EmailStr = Field(..., description="User email address")


class ForgotPasswordResponse(BaseModel):
    """Schema for forgot password response."""

    message: str = Field(
        default="If an account with this email exists, a password reset link has been sent.",
        description="Response message"
    )


class ResetPasswordRequest(BaseModel):
    """Schema for reset password request."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


class ResetPasswordResponse(BaseModel):
    """Schema for reset password response."""

    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Whether the password was reset successfully")


# =============================================================================
# Email Verification Schemas
# =============================================================================


class SendVerificationRequest(BaseModel):
    """Schema for requesting verification email (resend)."""

    email: Optional[EmailStr] = Field(
        None,
        description="User email address (optional - uses current user's email if not provided)"
    )


class SendVerificationResponse(BaseModel):
    """Schema for send verification response."""

    message: str = Field(
        default="If this email is registered and not yet verified, a verification link has been sent.",
        description="Response message"
    )
    success: bool = Field(default=True, description="Whether the request was processed")


class VerifyEmailResponse(BaseModel):
    """Schema for email verification response."""

    message: str = Field(..., description="Response message")
    success: bool = Field(..., description="Whether the email was verified successfully")
    email_verified: bool = Field(..., description="Current email verification status")
