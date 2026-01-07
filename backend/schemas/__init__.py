"""
GrantRadar Pydantic Schemas
Request/Response models for API endpoints.
"""
from backend.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
)
from backend.schemas.grants import (
    GrantDetail,
    GrantFilter,
    GrantList,
    GrantResponse,
    GrantSearch,
)
from backend.schemas.matches import (
    MatchAction,
    MatchDetail,
    MatchFeedback,
    MatchFilter,
    MatchList,
    MatchResponse,
)
from backend.schemas.preferences import (
    DigestFrequency,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
)
from backend.schemas.profile import (
    LabProfileCreate,
    LabProfileResponse,
    LabProfileUpdate,
    OnboardingData,
)
from backend.schemas.stats import DashboardStats

__all__ = [
    # Auth
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
    "Token",
    "TokenData",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    # Grants
    "GrantDetail",
    "GrantFilter",
    "GrantList",
    "GrantResponse",
    "GrantSearch",
    # Matches
    "MatchAction",
    "MatchDetail",
    "MatchFeedback",
    "MatchFilter",
    "MatchList",
    "MatchResponse",
    # Preferences
    "DigestFrequency",
    "NotificationPreferencesResponse",
    "NotificationPreferencesUpdate",
    # Profile
    "LabProfileCreate",
    "LabProfileResponse",
    "LabProfileUpdate",
    "OnboardingData",
    # Stats
    "DashboardStats",
]
