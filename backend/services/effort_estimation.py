"""
Effort Estimation Service
Estimates time and effort required for grant applications.
"""
from dataclasses import dataclass
from typing import Optional

# Effort estimates by mechanism (in hours)
MECHANISM_EFFORT = {
    # NIH Research Grants
    "R01": {"hours_min": 80, "hours_max": 200, "complexity": "complex", "typical_weeks": 8},
    "R21": {"hours_min": 40, "hours_max": 80, "complexity": "moderate", "typical_weeks": 4},
    "R03": {"hours_min": 20, "hours_max": 40, "complexity": "simple", "typical_weeks": 2},
    "R15": {"hours_min": 60, "hours_max": 120, "complexity": "moderate", "typical_weeks": 6},
    "R35": {"hours_min": 100, "hours_max": 250, "complexity": "complex", "typical_weeks": 10},
    "U01": {"hours_min": 100, "hours_max": 200, "complexity": "complex", "typical_weeks": 8},

    # Career Development
    "K01": {"hours_min": 60, "hours_max": 120, "complexity": "moderate", "typical_weeks": 6},
    "K08": {"hours_min": 60, "hours_max": 120, "complexity": "moderate", "typical_weeks": 6},
    "K23": {"hours_min": 60, "hours_max": 120, "complexity": "moderate", "typical_weeks": 6},
    "K99": {"hours_min": 80, "hours_max": 160, "complexity": "complex", "typical_weeks": 8},

    # Training/Fellowship
    "F31": {"hours_min": 40, "hours_max": 80, "complexity": "moderate", "typical_weeks": 4},
    "F32": {"hours_min": 40, "hours_max": 80, "complexity": "moderate", "typical_weeks": 4},
    "T32": {"hours_min": 80, "hours_max": 160, "complexity": "complex", "typical_weeks": 8},

    # Program/Center
    "P01": {"hours_min": 200, "hours_max": 400, "complexity": "complex", "typical_weeks": 16},
    "P30": {"hours_min": 150, "hours_max": 300, "complexity": "complex", "typical_weeks": 12},
    "P50": {"hours_min": 200, "hours_max": 400, "complexity": "complex", "typical_weeks": 16},

    # SBIR/STTR
    "R41": {"hours_min": 40, "hours_max": 80, "complexity": "moderate", "typical_weeks": 4},
    "R42": {"hours_min": 80, "hours_max": 160, "complexity": "complex", "typical_weeks": 8},
    "R43": {"hours_min": 40, "hours_max": 80, "complexity": "moderate", "typical_weeks": 4},
    "R44": {"hours_min": 80, "hours_max": 160, "complexity": "complex", "typical_weeks": 8},

    # NSF
    "CAREER": {"hours_min": 80, "hours_max": 160, "complexity": "complex", "typical_weeks": 8},
    "Standard": {"hours_min": 60, "hours_max": 120, "complexity": "moderate", "typical_weeks": 6},
    "RAPID": {"hours_min": 20, "hours_max": 40, "complexity": "simple", "typical_weeks": 2},
    "EAGER": {"hours_min": 30, "hours_max": 60, "complexity": "simple", "typical_weeks": 3},
}

# Default for unknown mechanisms
DEFAULT_EFFORT = {"hours_min": 40, "hours_max": 80, "complexity": "moderate", "typical_weeks": 4}


@dataclass
class EffortEstimate:
    """Effort estimate for a grant application."""
    hours_min: int
    hours_max: int
    complexity: str  # simple, moderate, complex
    typical_weeks: int
    mechanism: Optional[str]
    confidence: str  # high, medium, low
    factors: list[str]


def extract_mechanism_from_grant(title: str, description: str = "", agency: str = "") -> Optional[str]:
    """Extract mechanism code from grant title or description."""
    text = f"{title} {description}".upper()

    # Check NIH mechanisms
    for mechanism in MECHANISM_EFFORT.keys():
        if mechanism in text or f"({mechanism})" in text:
            return mechanism

    # Check for NSF patterns
    if "NSF" in agency.upper() or "NATIONAL SCIENCE FOUNDATION" in agency.upper():
        if "CAREER" in text:
            return "CAREER"
        if "RAPID" in text:
            return "RAPID"
        if "EAGER" in text:
            return "EAGER"
        return "Standard"

    return None


def estimate_effort(
    grant_title: str,
    grant_agency: Optional[str] = None,
    grant_description: Optional[str] = None,
    is_resubmission: bool = False,
    has_preliminary_data: bool = True,
) -> EffortEstimate:
    """
    Estimate effort required for a grant application.

    Returns effort estimate with hours range, complexity, and factors.
    """
    factors = []

    # Extract mechanism
    mechanism = extract_mechanism_from_grant(
        grant_title,
        grant_description or "",
        grant_agency or ""
    )

    # Get base effort
    if mechanism and mechanism in MECHANISM_EFFORT:
        effort_data = MECHANISM_EFFORT[mechanism]
        confidence = "high"
        factors.append(f"Based on {mechanism} mechanism requirements")
    else:
        effort_data = DEFAULT_EFFORT
        confidence = "low"
        factors.append("Using average grant effort estimate")

    hours_min = effort_data["hours_min"]
    hours_max = effort_data["hours_max"]

    # Adjust for resubmission (typically 50-70% of original effort)
    if is_resubmission:
        hours_min = int(hours_min * 0.5)
        hours_max = int(hours_max * 0.7)
        factors.append("Reduced for resubmission (-30-50%)")

    # Adjust for preliminary data availability
    if not has_preliminary_data:
        hours_min = int(hours_min * 1.2)
        hours_max = int(hours_max * 1.3)
        factors.append("Increased for preliminary data collection (+20-30%)")

    return EffortEstimate(
        hours_min=hours_min,
        hours_max=hours_max,
        complexity=effort_data["complexity"],
        typical_weeks=effort_data["typical_weeks"],
        mechanism=mechanism,
        confidence=confidence,
        factors=factors,
    )


def format_effort_display(estimate: EffortEstimate) -> dict:
    """Format effort estimate for display."""
    # Calculate average hours
    avg_hours = (estimate.hours_min + estimate.hours_max) // 2

    # Format time display
    if avg_hours < 40:
        time_display = f"{estimate.hours_min}-{estimate.hours_max} hours"
    elif avg_hours < 80:
        weeks = estimate.typical_weeks
        time_display = f"~{weeks} weeks"
    else:
        weeks_min = estimate.hours_min // 20  # Assume 20 productive hours/week
        weeks_max = estimate.hours_max // 20
        time_display = f"{weeks_min}-{weeks_max} weeks"

    return {
        "time_display": time_display,
        "hours_range": f"{estimate.hours_min}-{estimate.hours_max}",
        "complexity": estimate.complexity,
        "mechanism": estimate.mechanism,
        "confidence": estimate.confidence,
        "factors": estimate.factors,
    }
