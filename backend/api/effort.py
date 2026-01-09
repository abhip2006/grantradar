"""
Effort Estimation API Endpoints
"""
from typing import Optional
from fastapi import APIRouter, Query

from backend.services.effort_estimation import (
    estimate_effort,
    format_effort_display,
    MECHANISM_EFFORT,
    DEFAULT_EFFORT,
)

router = APIRouter(prefix="/api/effort", tags=["Effort Estimation"])


@router.get("/estimate")
async def get_effort_estimate(
    title: str = Query(..., description="Grant title"),
    agency: Optional[str] = Query(None, description="Funding agency"),
    description: Optional[str] = Query(None, description="Grant description"),
    is_resubmission: bool = Query(False, description="Is this a resubmission"),
    has_preliminary_data: bool = Query(True, description="Has preliminary data"),
):
    """Get effort estimate for a grant application."""
    estimate = estimate_effort(
        grant_title=title,
        grant_agency=agency,
        grant_description=description,
        is_resubmission=is_resubmission,
        has_preliminary_data=has_preliminary_data,
    )
    return format_effort_display(estimate)


@router.get("/mechanisms")
async def get_mechanism_efforts():
    """Get all known effort estimates by mechanism."""
    return {
        "mechanisms": MECHANISM_EFFORT,
        "default": DEFAULT_EFFORT,
    }
