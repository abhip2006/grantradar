"""
Analytics API Endpoints
Track success rates, funding trends, and pipeline performance metrics.
"""
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import joinedload

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import ApplicationStage, Grant, GrantApplication
from backend.schemas.analytics import (
    AnalyticsSummaryResponse,
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

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# Stage order for funnel metrics
STAGE_ORDER = ["researching", "writing", "submitted", "awarded", "rejected"]


def calculate_success_rate(awarded: int, submitted: int) -> float:
    """Calculate success rate as percentage."""
    if submitted == 0:
        return 0.0
    return round((awarded / submitted) * 100, 1)


@router.get(
    "/success-rates",
    response_model=SuccessRatesResponse,
    summary="Get success rates",
    description="Get user's application success rates by stage, category, and funder.",
)
async def get_success_rates(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> SuccessRatesResponse:
    """
    Get comprehensive success rate analytics for the user's applications.

    Returns breakdown by:
    - Pipeline stage counts
    - Success rate by grant category
    - Success rate by funder/agency
    """
    # Fetch all applications with grant data
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(GrantApplication.user_id == current_user.id)
    )
    applications = result.unique().scalars().all()

    if not applications:
        return SuccessRatesResponse(
            total_applications=0,
            overall_success_rate=0.0,
            by_stage=[],
            by_category=[],
            by_funder=[],
        )

    # Count by stage
    stage_counts: dict[str, int] = defaultdict(int)
    for app in applications:
        stage_counts[app.stage.value] += 1

    by_stage = [
        SuccessRateByStage(stage=stage, count=stage_counts.get(stage, 0))
        for stage in STAGE_ORDER
    ]

    # Group by category
    category_stats: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "submitted": 0, "awarded": 0, "rejected": 0}
    )

    for app in applications:
        categories = app.grant.categories or ["Uncategorized"]
        for category in categories:
            category_stats[category]["total"] += 1
            if app.stage == ApplicationStage.SUBMITTED:
                category_stats[category]["submitted"] += 1
            elif app.stage == ApplicationStage.AWARDED:
                category_stats[category]["submitted"] += 1
                category_stats[category]["awarded"] += 1
            elif app.stage == ApplicationStage.REJECTED:
                category_stats[category]["submitted"] += 1
                category_stats[category]["rejected"] += 1

    by_category = [
        SuccessRateByCategory(
            category=cat,
            total=stats["total"],
            submitted=stats["submitted"],
            awarded=stats["awarded"],
            rejected=stats["rejected"],
            success_rate=calculate_success_rate(stats["awarded"], stats["submitted"]),
        )
        for cat, stats in sorted(category_stats.items(), key=lambda x: -x[1]["total"])
    ]

    # Group by funder/agency
    funder_stats: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "submitted": 0, "awarded": 0, "rejected": 0}
    )

    for app in applications:
        funder = app.grant.agency or "Unknown"
        funder_stats[funder]["total"] += 1
        if app.stage == ApplicationStage.SUBMITTED:
            funder_stats[funder]["submitted"] += 1
        elif app.stage == ApplicationStage.AWARDED:
            funder_stats[funder]["submitted"] += 1
            funder_stats[funder]["awarded"] += 1
        elif app.stage == ApplicationStage.REJECTED:
            funder_stats[funder]["submitted"] += 1
            funder_stats[funder]["rejected"] += 1

    by_funder = [
        SuccessRateByFunder(
            funder=funder,
            total=stats["total"],
            submitted=stats["submitted"],
            awarded=stats["awarded"],
            rejected=stats["rejected"],
            success_rate=calculate_success_rate(stats["awarded"], stats["submitted"]),
        )
        for funder, stats in sorted(funder_stats.items(), key=lambda x: -x[1]["total"])
    ]

    # Calculate overall success rate
    total_submitted = sum(
        1 for app in applications
        if app.stage in [ApplicationStage.SUBMITTED, ApplicationStage.AWARDED, ApplicationStage.REJECTED]
    )
    total_awarded = stage_counts.get("awarded", 0)
    overall_rate = calculate_success_rate(total_awarded, total_submitted)

    return SuccessRatesResponse(
        total_applications=len(applications),
        overall_success_rate=overall_rate,
        by_stage=by_stage,
        by_category=by_category,
        by_funder=by_funder,
    )


@router.get(
    "/funding-trends",
    response_model=FundingTrendsResponse,
    summary="Get funding trends",
    description="Get funding amounts over time (applied vs awarded).",
)
async def get_funding_trends(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    period: str = Query(
        default="monthly",
        description="Time period grouping (monthly, quarterly, yearly)",
    ),
    months: int = Query(
        default=12,
        ge=1,
        le=60,
        description="Number of months of data to return",
    ),
) -> FundingTrendsResponse:
    """
    Get funding trends showing applied and awarded amounts over time.

    Groups data by the specified period (monthly, quarterly, or yearly).
    """
    # Fetch applications with grant data
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(GrantApplication.user_id == current_user.id)
        .order_by(GrantApplication.created_at)
    )
    applications = result.unique().scalars().all()

    if not applications:
        return FundingTrendsResponse(
            data_points=[],
            total_applied_amount=0,
            total_awarded_amount=0,
            total_applied_count=0,
            total_awarded_count=0,
            period_type=period,
        )

    # Group by period
    def get_period_key(dt: datetime) -> str:
        if period == "yearly":
            return dt.strftime("%Y")
        elif period == "quarterly":
            quarter = (dt.month - 1) // 3 + 1
            return f"{dt.year}-Q{quarter}"
        else:  # monthly
            return dt.strftime("%Y-%m")

    period_data: dict[str, dict] = defaultdict(
        lambda: {"applied_amount": 0, "awarded_amount": 0, "applied_count": 0, "awarded_count": 0}
    )

    total_applied = 0
    total_awarded = 0
    total_applied_count = 0
    total_awarded_count = 0

    for app in applications:
        # Use updated_at for stage changes, created_at for initial tracking
        period_key = get_period_key(app.updated_at or app.created_at)

        # Calculate estimated grant amount (use max or average)
        grant_amount = 0
        if app.grant.amount_max:
            grant_amount = app.grant.amount_max
        elif app.grant.amount_min:
            grant_amount = app.grant.amount_min

        # Track submitted and awarded
        if app.stage in [ApplicationStage.SUBMITTED, ApplicationStage.AWARDED, ApplicationStage.REJECTED]:
            period_data[period_key]["applied_amount"] += grant_amount
            period_data[period_key]["applied_count"] += 1
            total_applied += grant_amount
            total_applied_count += 1

        if app.stage == ApplicationStage.AWARDED:
            period_data[period_key]["awarded_amount"] += grant_amount
            period_data[period_key]["awarded_count"] += 1
            total_awarded += grant_amount
            total_awarded_count += 1

    # Sort periods and create data points
    sorted_periods = sorted(period_data.keys())[-months:]  # Last N periods

    data_points = [
        FundingDataPoint(
            period=p,
            applied_amount=period_data[p]["applied_amount"],
            awarded_amount=period_data[p]["awarded_amount"],
            applied_count=period_data[p]["applied_count"],
            awarded_count=period_data[p]["awarded_count"],
        )
        for p in sorted_periods
    ]

    return FundingTrendsResponse(
        data_points=data_points,
        total_applied_amount=total_applied,
        total_awarded_amount=total_awarded,
        total_applied_count=total_applied_count,
        total_awarded_count=total_awarded_count,
        period_type=period,
    )


@router.get(
    "/pipeline-metrics",
    response_model=PipelineMetricsResponse,
    summary="Get pipeline metrics",
    description="Get pipeline conversion rates and funnel visualization data.",
)
async def get_pipeline_metrics(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> PipelineMetricsResponse:
    """
    Get pipeline funnel metrics showing conversion rates between stages.

    Tracks:
    - Count at each stage
    - Conversion rate from previous stage
    - Average time spent in each stage
    """
    # Fetch applications
    result = await db.execute(
        select(GrantApplication)
        .where(GrantApplication.user_id == current_user.id)
    )
    applications = result.scalars().all()

    if not applications:
        return PipelineMetricsResponse(
            stages=[],
            total_in_pipeline=0,
            overall_conversion_rate=0.0,
            avg_time_to_award=None,
        )

    # Count by stage (excluding rejected for funnel calculation)
    stage_counts: dict[str, int] = defaultdict(int)
    cumulative_counts: dict[str, int] = defaultdict(int)

    for app in applications:
        stage_counts[app.stage.value] += 1
        # Track cumulative progress (if awarded, they passed through all stages)
        stage_idx = STAGE_ORDER.index(app.stage.value)
        for i, stage in enumerate(STAGE_ORDER[:4]):  # Exclude rejected
            if i <= stage_idx or app.stage == ApplicationStage.REJECTED:
                if stage != "rejected":
                    cumulative_counts[stage] += 1

    # Build stage metrics
    stages = []
    prev_count = None
    funnel_stages = ["researching", "writing", "submitted", "awarded"]

    for i, stage in enumerate(funnel_stages):
        # For funnel, count all that reached or passed this stage
        count = cumulative_counts.get(stage, 0)

        conversion_rate = None
        if prev_count is not None and prev_count > 0:
            conversion_rate = round((count / prev_count) * 100, 1)

        stages.append(
            PipelineStageMetric(
                stage=stage,
                count=count,
                conversion_rate=conversion_rate,
                avg_days_in_stage=None,  # Would need historical stage change tracking
            )
        )
        prev_count = count

    # Add rejected as separate metric
    rejected_count = stage_counts.get("rejected", 0)
    stages.append(
        PipelineStageMetric(
            stage="rejected",
            count=rejected_count,
            conversion_rate=None,
            avg_days_in_stage=None,
        )
    )

    # Calculate overall conversion rate (researching -> awarded)
    researching_count = cumulative_counts.get("researching", 0)
    awarded_count = cumulative_counts.get("awarded", 0)
    overall_rate = 0.0
    if researching_count > 0:
        overall_rate = round((awarded_count / researching_count) * 100, 1)

    return PipelineMetricsResponse(
        stages=stages,
        total_in_pipeline=len(applications),
        overall_conversion_rate=overall_rate,
        avg_time_to_award=None,  # Would need historical data
    )


@router.get(
    "/category-breakdown",
    response_model=CategoryBreakdownResponse,
    summary="Get category breakdown",
    description="Get success rates by grant category/focus area.",
)
async def get_category_breakdown(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> CategoryBreakdownResponse:
    """
    Get detailed breakdown of applications by grant category.

    Shows counts at each stage and success rate per category.
    """
    # Fetch applications with grant data
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(GrantApplication.user_id == current_user.id)
    )
    applications = result.unique().scalars().all()

    if not applications:
        return CategoryBreakdownResponse(
            categories=[],
            total_categories=0,
        )

    # Group by category
    category_data: dict[str, dict] = defaultdict(
        lambda: {
            "total": 0,
            "researching": 0,
            "writing": 0,
            "submitted": 0,
            "awarded": 0,
            "rejected": 0,
            "total_amount": 0,
            "amount_count": 0,
        }
    )

    for app in applications:
        categories = app.grant.categories or ["Uncategorized"]
        stage_key = app.stage.value

        # Get grant amount for average calculation
        grant_amount = app.grant.amount_max or app.grant.amount_min or 0

        for category in categories:
            category_data[category]["total"] += 1
            category_data[category][stage_key] += 1

            if grant_amount > 0:
                category_data[category]["total_amount"] += grant_amount
                category_data[category]["amount_count"] += 1

    # Build response
    categories = []
    for cat, data in sorted(category_data.items(), key=lambda x: -x[1]["total"]):
        # Success rate based on submitted outcomes
        submitted_total = data["submitted"] + data["awarded"] + data["rejected"]
        success_rate = calculate_success_rate(data["awarded"], submitted_total)

        # Average funding amount
        avg_amount = None
        if data["amount_count"] > 0:
            avg_amount = data["total_amount"] / data["amount_count"]

        categories.append(
            CategoryBreakdownItem(
                category=cat,
                total=data["total"],
                researching=data["researching"],
                writing=data["writing"],
                submitted=data["submitted"],
                awarded=data["awarded"],
                rejected=data["rejected"],
                success_rate=success_rate,
                avg_funding_amount=avg_amount,
            )
        )

    return CategoryBreakdownResponse(
        categories=categories,
        total_categories=len(categories),
    )


@router.get(
    "/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Get analytics summary",
    description="Get dashboard summary stats for analytics overview.",
)
async def get_analytics_summary(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> AnalyticsSummaryResponse:
    """
    Get comprehensive summary statistics for the analytics dashboard.

    Combines key metrics from success rates, funding trends, and pipeline.
    """
    # Fetch all applications with grant data
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(GrantApplication.user_id == current_user.id)
    )
    applications = result.unique().scalars().all()

    if not applications:
        return AnalyticsSummaryResponse(
            total_applications=0,
            total_in_pipeline=0,
            total_submitted=0,
            total_awarded=0,
            total_rejected=0,
            overall_success_rate=0.0,
            total_funding_applied=0.0,
            total_funding_awarded=0.0,
            avg_funding_per_award=None,
            pipeline_conversion_rate=0.0,
            top_funder=None,
            top_category=None,
        )

    # Count by stage
    stage_counts: dict[str, int] = defaultdict(int)
    for app in applications:
        stage_counts[app.stage.value] += 1

    total_submitted = sum(
        1 for app in applications
        if app.stage in [ApplicationStage.SUBMITTED, ApplicationStage.AWARDED, ApplicationStage.REJECTED]
    )
    total_awarded = stage_counts.get("awarded", 0)
    total_rejected = stage_counts.get("rejected", 0)

    # Calculate funding amounts
    total_funding_applied = 0.0
    total_funding_awarded = 0.0

    for app in applications:
        grant_amount = app.grant.amount_max or app.grant.amount_min or 0
        if app.stage in [ApplicationStage.SUBMITTED, ApplicationStage.AWARDED, ApplicationStage.REJECTED]:
            total_funding_applied += grant_amount
        if app.stage == ApplicationStage.AWARDED:
            total_funding_awarded += grant_amount

    # Calculate averages and rates
    overall_success_rate = calculate_success_rate(total_awarded, total_submitted)
    avg_funding_per_award = total_funding_awarded / total_awarded if total_awarded > 0 else None

    # Pipeline conversion rate (researching -> awarded)
    researching_count = sum(1 for app in applications)  # All apps started in pipeline
    pipeline_conversion_rate = 0.0
    if researching_count > 0:
        pipeline_conversion_rate = round((total_awarded / researching_count) * 100, 1)

    # Find top performing funder
    funder_stats: dict[str, dict] = defaultdict(
        lambda: {"submitted": 0, "awarded": 0}
    )
    for app in applications:
        funder = app.grant.agency or "Unknown"
        if app.stage in [ApplicationStage.SUBMITTED, ApplicationStage.AWARDED, ApplicationStage.REJECTED]:
            funder_stats[funder]["submitted"] += 1
        if app.stage == ApplicationStage.AWARDED:
            funder_stats[funder]["awarded"] += 1

    top_funder = None
    top_funder_rate = 0.0
    for funder, stats in funder_stats.items():
        if stats["submitted"] >= 1:  # At least 1 submission
            rate = calculate_success_rate(stats["awarded"], stats["submitted"])
            if rate > top_funder_rate:
                top_funder_rate = rate
                top_funder = funder

    # Find top performing category
    category_stats: dict[str, dict] = defaultdict(
        lambda: {"submitted": 0, "awarded": 0}
    )
    for app in applications:
        categories = app.grant.categories or ["Uncategorized"]
        for category in categories:
            if app.stage in [ApplicationStage.SUBMITTED, ApplicationStage.AWARDED, ApplicationStage.REJECTED]:
                category_stats[category]["submitted"] += 1
            if app.stage == ApplicationStage.AWARDED:
                category_stats[category]["awarded"] += 1

    top_category = None
    top_category_rate = 0.0
    for category, stats in category_stats.items():
        if stats["submitted"] >= 1:  # At least 1 submission
            rate = calculate_success_rate(stats["awarded"], stats["submitted"])
            if rate > top_category_rate:
                top_category_rate = rate
                top_category = category

    return AnalyticsSummaryResponse(
        total_applications=len(applications),
        total_in_pipeline=len(applications),
        total_submitted=total_submitted,
        total_awarded=total_awarded,
        total_rejected=total_rejected,
        overall_success_rate=overall_success_rate,
        total_funding_applied=total_funding_applied,
        total_funding_awarded=total_funding_awarded,
        avg_funding_per_award=avg_funding_per_award,
        pipeline_conversion_rate=pipeline_conversion_rate,
        top_funder=top_funder,
        top_category=top_category,
    )
