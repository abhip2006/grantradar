"""
Win Probability Service
Calculates estimated success probability for grant applications.
"""
from typing import Optional
from dataclasses import dataclass

# Historical NIH success rates by mechanism (2020-2024 averages)
# Source: https://report.nih.gov/funding/nih-budget-and-spending-data-past-fiscal-years/success-rates
NIH_SUCCESS_RATES = {
    # Research grants
    "R01": 0.21,  # 21% success rate
    "R21": 0.18,  # 18% - exploratory/developmental
    "R03": 0.25,  # 25% - small grants
    "R15": 0.28,  # 28% - AREA grants
    "R35": 0.15,  # 15% - outstanding investigator
    "U01": 0.22,  # 22% - cooperative agreements

    # Career development
    "K01": 0.35,  # 35% - mentored research scientist
    "K08": 0.38,  # 38% - mentored clinical scientist
    "K23": 0.40,  # 40% - patient-oriented research
    "K99": 0.32,  # 32% - pathway to independence

    # Training
    "F31": 0.28,  # 28% - predoctoral fellowship
    "F32": 0.30,  # 30% - postdoctoral fellowship
    "T32": 0.25,  # 25% - training grants

    # Program/Center grants
    "P01": 0.18,  # 18% - research program project
    "P30": 0.20,  # 20% - center core grants
    "P50": 0.15,  # 15% - specialized centers

    # SBIR/STTR
    "R41": 0.22,  # SBIR Phase I
    "R42": 0.45,  # SBIR Phase II (higher if Phase I funded)
    "R43": 0.22,  # STTR Phase I
    "R44": 0.45,  # STTR Phase II
}

# NSF success rates by program type (approximate)
NSF_SUCCESS_RATES = {
    "CAREER": 0.18,  # 18% - Faculty Early Career
    "Standard": 0.25,  # 25% - standard research grants
    "RAPID": 0.40,  # 40% - rapid response
    "EAGER": 0.35,  # 35% - high-risk research
    "Conference": 0.50,  # 50% - conference grants
}

# Default rates by funder
DEFAULT_RATES = {
    "NIH": 0.22,
    "NSF": 0.25,
    "DOE": 0.20,
    "DOD": 0.18,
    "USDA": 0.25,
    "Foundation": 0.30,  # Private foundations generally higher
}


@dataclass
class WinProbabilityEstimate:
    """Win probability estimate with confidence and factors."""
    probability: float  # 0-1
    confidence: str  # "high", "medium", "low"
    mechanism_rate: Optional[float]
    factors: list[str]  # Explanatory factors


def extract_mechanism(title: str, description: str = "") -> Optional[str]:
    """Extract grant mechanism from title or description."""
    text = f"{title} {description}".upper()

    # Check NIH mechanisms
    for mechanism in NIH_SUCCESS_RATES.keys():
        if mechanism in text or f"({mechanism})" in text:
            return mechanism

    # Check NSF mechanisms
    for mechanism in NSF_SUCCESS_RATES.keys():
        if mechanism in text:
            return f"NSF_{mechanism}"

    return None


def calculate_win_probability(
    grant_title: str,
    grant_agency: Optional[str] = None,
    grant_description: Optional[str] = None,
    user_career_stage: Optional[str] = None,  # "early", "mid", "senior"
    user_prior_grants: int = 0,
    is_resubmission: bool = False,
) -> WinProbabilityEstimate:
    """
    Calculate estimated win probability for a grant.

    Returns probability estimate with confidence level and explanatory factors.
    """
    factors = []

    # Extract mechanism
    mechanism = extract_mechanism(grant_title, grant_description or "")

    # Get base rate
    base_rate = None
    if mechanism:
        if mechanism.startswith("NSF_"):
            base_rate = NSF_SUCCESS_RATES.get(mechanism[4:])
            factors.append(f"NSF {mechanism[4:]} mechanism")
        else:
            base_rate = NIH_SUCCESS_RATES.get(mechanism)
            factors.append(f"NIH {mechanism} mechanism")

    # Fall back to agency default
    if base_rate is None and grant_agency:
        agency_upper = grant_agency.upper()
        for agency_key, rate in DEFAULT_RATES.items():
            if agency_key in agency_upper:
                base_rate = rate
                factors.append(f"{agency_key} average rate")
                break

    # Final fallback
    if base_rate is None:
        base_rate = 0.22  # Overall NIH average
        factors.append("General research grant average")

    # Adjust for user factors
    probability = base_rate

    # Resubmission boost (resubmissions have ~10% higher success)
    if is_resubmission:
        probability *= 1.10
        factors.append("+10% resubmission boost")

    # Prior grant experience
    if user_prior_grants >= 3:
        probability *= 1.15
        factors.append("+15% established investigator")
    elif user_prior_grants >= 1:
        probability *= 1.05
        factors.append("+5% prior funding")

    # Career stage adjustments for K awards
    if mechanism and mechanism.startswith("K") and user_career_stage == "early":
        probability *= 1.10
        factors.append("+10% career stage match")

    # Cap probability at 0.60 (no grant is a sure thing)
    probability = min(probability, 0.60)

    # Determine confidence
    if mechanism and mechanism in NIH_SUCCESS_RATES:
        confidence = "high"
    elif grant_agency and any(a in grant_agency.upper() for a in DEFAULT_RATES.keys()):
        confidence = "medium"
    else:
        confidence = "low"

    return WinProbabilityEstimate(
        probability=round(probability, 3),
        confidence=confidence,
        mechanism_rate=base_rate,
        factors=factors,
    )
