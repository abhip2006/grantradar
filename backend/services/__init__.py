"""
Backend services for external integrations and business logic.
"""

from backend.services.deadline_history import (
    add_deadline_record,
    bulk_add_deadline_records,
    extract_deadline_history_from_grants,
    get_all_funder_patterns,
    get_deadline_history_stats,
    get_deadline_patterns,
    get_funder_deadline_history,
    predict_next_deadline,
)
from backend.services.deep_research import DeepResearchService
from backend.services.notification_service import (
    InAppNotificationService,
    NotificationType,
)
from backend.services.permission_template_service import (
    PermissionTemplateService,
    DEFAULT_TEMPLATES,
)
from backend.services.win_probability import (
    WinProbabilityEstimate,
    calculate_win_probability,
    extract_mechanism,
    NIH_SUCCESS_RATES,
    NSF_SUCCESS_RATES,
    DEFAULT_RATES,
)
from backend.services.effort_estimation import (
    EffortEstimate,
    estimate_effort,
    format_effort_display,
    extract_mechanism_from_grant,
    MECHANISM_EFFORT,
    DEFAULT_EFFORT,
)
from backend.services.review_criteria import (
    ReviewCriteriaService,
    review_criteria_service,
    NIH_CRITERIA,
    NSF_CRITERIA,
)
from backend.services.writing_assistant import (
    WritingAssistantService,
    writing_assistant,
)
from backend.services.specific_aims import (
    SpecificAimsAnalyzer,
    get_analyzer as get_aims_analyzer,
    analyze_aims_structure,
    check_aim_scope,
    detect_common_issues,
    suggest_improvements,
    compare_to_funded,
    get_mechanism_template,
    get_funded_examples,
    MECHANISM_GUIDELINES,
)
from backend.services.audit import (
    AuditService,
    audit_action,
    log_audit_action,
)
from backend.services.email import (
    EmailTemplateService,
    get_email_service,
)

# ML forecast requires pandas/prophet - optional dependency
try:
    from backend.services.ml_forecast import (
        GrantDeadlinePredictor,
        MLPredictionResult,
        get_predictor,
    )

    _ML_AVAILABLE = True
except ImportError:
    GrantDeadlinePredictor = None
    MLPredictionResult = None
    get_predictor = None
    _ML_AVAILABLE = False

__all__ = [
    # Deadline history service
    "extract_deadline_history_from_grants",
    "add_deadline_record",
    "get_funder_deadline_history",
    "get_deadline_patterns",
    "get_all_funder_patterns",
    "predict_next_deadline",
    "bulk_add_deadline_records",
    "get_deadline_history_stats",
    # Deep research service
    "DeepResearchService",
    # In-app notification service
    "InAppNotificationService",
    "NotificationType",
    # Permission template service
    "PermissionTemplateService",
    "DEFAULT_TEMPLATES",
    # Win probability service
    "WinProbabilityEstimate",
    "calculate_win_probability",
    "extract_mechanism",
    "NIH_SUCCESS_RATES",
    "NSF_SUCCESS_RATES",
    "DEFAULT_RATES",
    # Effort estimation service
    "EffortEstimate",
    "estimate_effort",
    "format_effort_display",
    "extract_mechanism_from_grant",
    "MECHANISM_EFFORT",
    "DEFAULT_EFFORT",
    # ML forecast (optional)
    "GrantDeadlinePredictor",
    "MLPredictionResult",
    "get_predictor",
    "_ML_AVAILABLE",
    # Review criteria service
    "ReviewCriteriaService",
    "review_criteria_service",
    "NIH_CRITERIA",
    "NSF_CRITERIA",
    # Writing assistant service
    "WritingAssistantService",
    "writing_assistant",
    # Specific aims analysis service
    "SpecificAimsAnalyzer",
    "get_aims_analyzer",
    "analyze_aims_structure",
    "check_aim_scope",
    "detect_common_issues",
    "suggest_improvements",
    "compare_to_funded",
    "get_mechanism_template",
    "get_funded_examples",
    "MECHANISM_GUIDELINES",
    # Audit service
    "AuditService",
    "audit_action",
    "log_audit_action",
    # Email template service
    "EmailTemplateService",
    "get_email_service",
]
