"""
Filter Options API Endpoints
Provides distinct values for filter dropdowns on the dashboard.
"""

from typing import Any

from fastapi import APIRouter
from sqlalchemy import distinct, func, select, text

from backend.api.deps import AsyncSessionDep
from backend.models import Grant

router = APIRouter(prefix="/api/filters", tags=["Filters"])


@router.get(
    "/options",
    summary="Get filter options",
    description="Get available values for dashboard filter dropdowns.",
)
async def get_filter_options(db: AsyncSessionDep) -> dict[str, Any]:
    """
    Get all available filter options for the dashboard.

    Returns distinct values for agencies, categories, and sources
    to populate filter dropdowns.
    """
    # Get distinct agencies (non-null, non-empty, limit to 200)
    agencies_query = (
        select(Grant.agency)
        .where(Grant.agency.isnot(None))
        .where(Grant.agency != "")
        .distinct()
        .order_by(Grant.agency)
        .limit(200)
    )
    agencies_result = await db.execute(agencies_query)
    agencies = [r[0] for r in agencies_result.all()]

    # Get distinct categories (unnest the array)
    # Use raw SQL for array unnesting as it's more reliable
    categories_query = text("""
        SELECT DISTINCT unnest(categories) as category
        FROM grants
        WHERE categories IS NOT NULL
        ORDER BY category
        LIMIT 200
    """)
    categories_result = await db.execute(categories_query)
    categories = [r[0] for r in categories_result.all() if r[0]]

    # Get distinct sources
    sources_query = select(distinct(Grant.source)).where(Grant.source.isnot(None)).order_by(Grant.source)
    sources_result = await db.execute(sources_query)
    sources = [r[0] for r in sources_result.all()]

    # Get funding amount ranges for UI hints
    amount_stats_query = select(
        func.min(Grant.amount_min).label("min_amount"),
        func.max(Grant.amount_max).label("max_amount"),
    )
    amount_result = await db.execute(amount_stats_query)
    amount_row = amount_result.one_or_none()

    return {
        "agencies": agencies,
        "categories": categories,
        "sources": sources,
        "amount_range": {
            "min": amount_row.min_amount if amount_row else 0,
            "max": amount_row.max_amount if amount_row else 10000000,
        },
        # Predefined options for advanced filters
        "career_stages": [
            {"value": "undergraduate", "label": "Undergraduate"},
            {"value": "graduate", "label": "Graduate Student"},
            {"value": "postdoc", "label": "Postdoctoral"},
            {"value": "early_career", "label": "Early Career (0-5 years)"},
            {"value": "mid_career", "label": "Mid-Career (5-15 years)"},
            {"value": "senior", "label": "Senior/Established"},
        ],
        "citizenship_options": [
            {"value": "us_citizen_only", "label": "US Citizen Only"},
            {"value": "us_citizen_or_pr", "label": "US Citizen or Permanent Resident"},
            {"value": "any_visa", "label": "Any Visa Status"},
            {"value": "international_ok", "label": "International Applicants Welcome"},
        ],
        "institution_types": [
            {"value": "r1_university", "label": "R1 Research University"},
            {"value": "r2_university", "label": "R2 Research University"},
            {"value": "liberal_arts", "label": "Liberal Arts College"},
            {"value": "hbcu", "label": "HBCU"},
            {"value": "hsi", "label": "Hispanic-Serving Institution"},
            {"value": "community_college", "label": "Community College"},
            {"value": "nonprofit", "label": "Non-profit Organization"},
            {"value": "forprofit", "label": "For-profit Company"},
        ],
        "award_types": [
            {"value": "research", "label": "Research Grant"},
            {"value": "training", "label": "Training Grant"},
            {"value": "fellowship", "label": "Fellowship"},
            {"value": "career_development", "label": "Career Development (K Award)"},
            {"value": "equipment", "label": "Equipment/Infrastructure"},
            {"value": "conference", "label": "Conference/Workshop"},
            {"value": "seed", "label": "Seed/Pilot Funding"},
        ],
        "award_durations": [
            {"value": "lt_1", "label": "Less than 1 year"},
            {"value": "1_2", "label": "1-2 years"},
            {"value": "2_3", "label": "2-3 years"},
            {"value": "3_5", "label": "3-5 years"},
            {"value": "gt_5", "label": "More than 5 years"},
        ],
        "geographic_scopes": [
            {"value": "national", "label": "National"},
            {"value": "regional", "label": "Regional"},
            {"value": "state", "label": "State-specific"},
            {"value": "international", "label": "International"},
        ],
        "indirect_cost_policies": [
            {"value": "full", "label": "Full Indirect Costs"},
            {"value": "capped", "label": "Capped Indirect Costs"},
            {"value": "none", "label": "No Indirect Costs"},
            {"value": "training_rate", "label": "Training Grant Rate"},
        ],
    }
