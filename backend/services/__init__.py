"""
Backend services for external integrations.
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
    # ML forecast (optional)
    "GrantDeadlinePredictor",
    "MLPredictionResult",
    "get_predictor",
    "_ML_AVAILABLE",
]
