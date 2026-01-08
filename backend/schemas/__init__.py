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
from backend.schemas.saved_searches import (
    SavedSearchCreate,
    SavedSearchFilters,
    SavedSearchList,
    SavedSearchResponse,
    SavedSearchUpdate,
)
from backend.schemas.stats import DashboardStats
from backend.schemas.calendar import (
    CalendarDay,
    CalendarDeadlinesResponse,
    CalendarEvent,
    CalendarEventType,
    CalendarMonthResponse,
    UpcomingDeadline,
    UpcomingDeadlinesResponse,
    UrgencyLevel,
)
from backend.schemas.analytics import (
    CategoryBreakdownItem,
    CategoryBreakdownResponse,
    FundingDataPoint,
    FundingTrendsResponse,
    PipelineMetricsResponse,
    PipelineStageMetric,
    SuccessRateByCategory,
    SuccessRateByFunder,
    SuccessRateByStage,
    SuccessRatesResponse,
)
from backend.schemas.deadlines import (
    DeadlineCreate,
    DeadlineList,
    DeadlinePriority,
    DeadlineResponse,
    DeadlineStatus,
    DeadlineUpdate,
    LinkGrantRequest,
)
from backend.schemas.reminders import (
    BulkReminderCreate,
    ReminderScheduleCreate,
    ReminderScheduleResponse,
    ReminderSettingsResponse,
    ReminderSettingsUpdate,
)
from backend.schemas.integrations import (
    CalendarIntegrationResponse,
    CalendarStatusResponse,
    OAuthCallbackRequest,
    ProviderStatus,
    SyncResponse,
    UpdateIntegrationRequest,
)
from backend.schemas.templates import (
    TemplateCategoryResponse,
    TemplateCreate,
    TemplateListResponse,
    TemplateRenderRequest,
    TemplateRenderResponse,
    TemplateResponse,
    TemplateUpdate,
    TemplateVariable,
)

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
    # Saved Searches
    "SavedSearchCreate",
    "SavedSearchFilters",
    "SavedSearchList",
    "SavedSearchResponse",
    "SavedSearchUpdate",
    # Stats
    "DashboardStats",
    # Calendar
    "CalendarDay",
    "CalendarDeadlinesResponse",
    "CalendarEvent",
    "CalendarEventType",
    "CalendarMonthResponse",
    "UpcomingDeadline",
    "UpcomingDeadlinesResponse",
    "UrgencyLevel",
    # Analytics
    "CategoryBreakdownItem",
    "CategoryBreakdownResponse",
    "FundingDataPoint",
    "FundingTrendsResponse",
    "PipelineMetricsResponse",
    "PipelineStageMetric",
    "SuccessRateByCategory",
    "SuccessRateByFunder",
    "SuccessRateByStage",
    "SuccessRatesResponse",
    # Deadlines
    "DeadlineCreate",
    "DeadlineList",
    "DeadlinePriority",
    "DeadlineResponse",
    "DeadlineStatus",
    "DeadlineUpdate",
    "LinkGrantRequest",
    # Reminders
    "BulkReminderCreate",
    "ReminderScheduleCreate",
    "ReminderScheduleResponse",
    "ReminderSettingsResponse",
    "ReminderSettingsUpdate",
    # Integrations
    "CalendarIntegrationResponse",
    "CalendarStatusResponse",
    "OAuthCallbackRequest",
    "ProviderStatus",
    "SyncResponse",
    "UpdateIntegrationRequest",
    # Templates
    "TemplateCategoryResponse",
    "TemplateCreate",
    "TemplateListResponse",
    "TemplateRenderRequest",
    "TemplateRenderResponse",
    "TemplateResponse",
    "TemplateUpdate",
    "TemplateVariable",
]
