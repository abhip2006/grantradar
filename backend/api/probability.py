"""
Win Probability API Endpoints
"""

from typing import Optional
from fastapi import APIRouter, Query

from backend.services.win_probability import (
    calculate_win_probability,
    NIH_SUCCESS_RATES,
    NSF_SUCCESS_RATES,
    DEFAULT_RATES,
)

router = APIRouter(prefix="/api/probability", tags=["Win Probability"])


@router.get("/estimate")
async def get_probability_estimate(
    title: str = Query(..., description="Grant title"),
    agency: Optional[str] = Query(None, description="Funding agency"),
    description: Optional[str] = Query(None, description="Grant description"),
    career_stage: Optional[str] = Query(None, description="User career stage"),
    prior_grants: int = Query(0, ge=0, description="Number of prior grants"),
    is_resubmission: bool = Query(False, description="Is this a resubmission"),
):
    """Get win probability estimate for a grant."""
    estimate = calculate_win_probability(
        grant_title=title,
        grant_agency=agency,
        grant_description=description,
        user_career_stage=career_stage,
        user_prior_grants=prior_grants,
        is_resubmission=is_resubmission,
    )

    return {
        "probability": estimate.probability,
        "confidence": estimate.confidence,
        "mechanism_rate": estimate.mechanism_rate,
        "factors": estimate.factors,
    }


@router.get("/rates")
async def get_success_rates():
    """Get all known success rates by mechanism."""
    return {
        "nih": NIH_SUCCESS_RATES,
        "nsf": NSF_SUCCESS_RATES,
        "defaults": DEFAULT_RATES,
    }
