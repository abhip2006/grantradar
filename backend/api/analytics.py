"""
Analytics API Endpoints
Track success rates, funding trends, and pipeline performance metrics.
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import joinedload

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import (
    ApplicationActivity,
    ApplicationStage,
    Grant,
    GrantApplication,
    Match,
)
from backend.schemas.analytics import (
    ActivityTimelineResponse,
    AnalyticsSummaryResponse,
    CategoryBreakdownItem,
    CategoryBreakdownResponse,
    DailyActivity,
    DayData,
    DeadlineHeatmapResponse,
    FunderLeaderboardResponse,
    FunderRanking,
    FundingDataPoint,
    FundingTrendsResponse,
    MatchQualityResponse,
    PipelineMetricsResponse,
    PipelineStageMetric,
    ScoreRangeBucket,
    StageTimingData,
    SuccessRateByCategory,
    SuccessRateByFunder,
    SuccessRateByStage,
    SuccessRatesResponse,
    TimeToAwardResponse,
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


@router.get(
    "/time-to-award",
    response_model=TimeToAwardResponse,
    summary="Get time to award metrics",
    description="Get metrics on time from submission to award.",
)
async def get_time_to_award_metrics(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    months: int = Query(
        default=12,
        ge=1,
        le=24,
        description="Number of months of data to analyze",
    ),
) -> TimeToAwardResponse:
    """
    Get metrics on time from submission to award.

    Calculates:
    - Average and median days from creation to award
    - Breakdown by category and funder
    - Monthly trend data
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

    # Get awarded applications with grant data
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(
            GrantApplication.user_id == current_user.id,
            GrantApplication.stage == ApplicationStage.AWARDED,
            GrantApplication.created_at >= cutoff,
        )
    )
    awarded_apps = result.unique().scalars().all()

    if not awarded_apps:
        return TimeToAwardResponse(
            overall_avg_days=0,
            overall_median_days=0,
            by_stage=[],
            by_category={},
            by_funder={},
            trend=[],
        )

    # Calculate days from created_at to updated_at for awarded applications
    days_list = []
    category_days: dict[str, list[int]] = defaultdict(list)
    funder_days: dict[str, list[int]] = defaultdict(list)
    month_days: dict[str, list[int]] = defaultdict(list)

    for app in awarded_apps:
        if app.updated_at and app.created_at:
            days = (app.updated_at - app.created_at).days
            days_list.append(days)

            # Group by category
            categories = app.grant.categories or ["Uncategorized"]
            for category in categories:
                category_days[category].append(days)

            # Group by funder
            funder = app.grant.agency or "Unknown"
            funder_days[funder].append(days)

            # Group by month for trend
            month_key = app.updated_at.strftime("%Y-%m")
            month_days[month_key].append(days)

    # Calculate overall stats
    avg_days = sum(days_list) / len(days_list) if days_list else 0
    sorted_days = sorted(days_list)
    median_days = sorted_days[len(sorted_days) // 2] if sorted_days else 0

    # Calculate category averages
    by_category = {
        cat: sum(days) / len(days) if days else 0
        for cat, days in category_days.items()
    }

    # Calculate funder averages
    by_funder = {
        funder: sum(days) / len(days) if days else 0
        for funder, days in funder_days.items()
    }

    # Build trend data
    trend = [
        {
            "period": month,
            "avg_days": sum(days) / len(days) if days else 0,
            "count": len(days),
        }
        for month, days in sorted(month_days.items())
    ]

    return TimeToAwardResponse(
        overall_avg_days=round(avg_days, 1),
        overall_median_days=float(median_days),
        by_stage=[],  # Would need stage transition tracking for detailed breakdown
        by_category={k: round(v, 1) for k, v in by_category.items()},
        by_funder={k: round(v, 1) for k, v in by_funder.items()},
        trend=trend,
    )


@router.get(
    "/funder-leaderboard",
    response_model=FunderLeaderboardResponse,
    summary="Get funder leaderboard",
    description="Get top funders ranked by success rate and total awarded.",
)
async def get_funder_leaderboard(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    limit: int = Query(
        default=10,
        ge=5,
        le=50,
        description="Number of funders to return",
    ),
) -> FunderLeaderboardResponse:
    """
    Get top funders ranked by success rate and total awarded.

    Includes:
    - Success rate ranking
    - Total awarded amounts
    - Performance trend (improving/declining)
    """
    # Fetch all applications with grant data
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(GrantApplication.user_id == current_user.id)
    )
    applications = result.unique().scalars().all()

    if not applications:
        return FunderLeaderboardResponse(
            rankings=[],
            total_funders=0,
            period_months=12,
        )

    # Group by funder
    funder_stats: dict[str, dict] = defaultdict(
        lambda: {
            "total": 0,
            "submitted": 0,
            "awarded": 0,
            "awarded_amount": 0,
            "recent_awarded": 0,
            "older_awarded": 0,
        }
    )

    # Calculate cutoff for trend (last 6 months vs previous)
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)

    for app in applications:
        funder = app.grant.agency or "Unknown"
        funder_stats[funder]["total"] += 1

        grant_amount = app.grant.amount_max or app.grant.amount_min or 0

        if app.stage in [
            ApplicationStage.SUBMITTED,
            ApplicationStage.AWARDED,
            ApplicationStage.REJECTED,
        ]:
            funder_stats[funder]["submitted"] += 1

        if app.stage == ApplicationStage.AWARDED:
            funder_stats[funder]["awarded"] += 1
            funder_stats[funder]["awarded_amount"] += grant_amount

            # Track for trend calculation
            if app.updated_at and app.updated_at >= six_months_ago:
                funder_stats[funder]["recent_awarded"] += 1
            else:
                funder_stats[funder]["older_awarded"] += 1

    # Build rankings
    rankings = []
    for funder, stats in funder_stats.items():
        submitted = stats["submitted"]
        awarded = stats["awarded"]
        success_rate = calculate_success_rate(awarded, submitted)

        # Determine trend
        if stats["recent_awarded"] > stats["older_awarded"]:
            trend = "up"
        elif stats["recent_awarded"] < stats["older_awarded"]:
            trend = "down"
        else:
            trend = "stable"

        avg_award = (
            stats["awarded_amount"] / awarded
            if awarded > 0
            else 0
        )

        rankings.append({
            "funder": funder,
            "success_rate": success_rate,
            "total_awarded": stats["awarded_amount"],
            "total_applications": submitted,
            "awarded_count": awarded,
            "avg_award_amount": round(avg_award, 2),
            "trend": trend,
        })

    # Sort by success rate (descending), then by total awarded
    rankings.sort(key=lambda x: (-x["success_rate"], -x["total_awarded"]))

    # Add rank and limit
    rankings_limited = [
        FunderRanking(rank=i + 1, **r)
        for i, r in enumerate(rankings[:limit])
    ]

    return FunderLeaderboardResponse(
        rankings=rankings_limited,
        total_funders=len(funder_stats),
        period_months=12,
    )


@router.get(
    "/match-quality",
    response_model=MatchQualityResponse,
    summary="Get match quality metrics",
    description="Get match algorithm quality metrics.",
)
async def get_match_quality_metrics(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> MatchQualityResponse:
    """
    Get match algorithm quality metrics.

    Includes:
    - Score distribution histogram
    - Conversion rates by score range
    - User action breakdown
    """
    # Fetch all matches for the user
    result = await db.execute(
        select(Match)
        .options(joinedload(Match.application))
        .where(Match.user_id == current_user.id)
    )
    matches = result.unique().scalars().all()

    if not matches:
        return MatchQualityResponse(
            total_matches=0,
            avg_score=0,
            score_distribution=[],
            action_breakdown={},
            conversion_by_score=[],
        )

    # Calculate average score
    scores = [m.match_score for m in matches]
    avg_score = sum(scores) / len(scores)

    # Define score buckets (0.0-0.2, 0.2-0.4, ..., 0.8-1.0)
    buckets = [
        (0.0, 0.2),
        (0.2, 0.4),
        (0.4, 0.6),
        (0.6, 0.8),
        (0.8, 1.0),
    ]

    bucket_data: dict[tuple, dict] = {
        bucket: {"count": 0, "saved": 0, "applied": 0, "awarded": 0}
        for bucket in buckets
    }

    # Action breakdown
    action_counts: dict[str, int] = defaultdict(int)

    for match in matches:
        # Find the bucket for this score
        for bucket_range in buckets:
            if bucket_range[0] <= match.match_score < bucket_range[1] or (
                bucket_range[1] == 1.0 and match.match_score == 1.0
            ):
                bucket_data[bucket_range]["count"] += 1

                # Track actions
                action = match.user_action or "none"
                action_counts[action] += 1

                if action == "saved":
                    bucket_data[bucket_range]["saved"] += 1
                elif action == "applied":
                    bucket_data[bucket_range]["applied"] += 1

                # Check if there's an awarded application from this match
                if match.application and match.application.stage == ApplicationStage.AWARDED:
                    bucket_data[bucket_range]["awarded"] += 1

                break

    # Build score distribution
    score_distribution = []
    for bucket_range, data in bucket_data.items():
        count = data["count"]
        score_distribution.append(
            ScoreRangeBucket(
                range_start=bucket_range[0],
                range_end=bucket_range[1],
                count=count,
                saved_rate=round((data["saved"] / count * 100) if count > 0 else 0, 1),
                applied_rate=round((data["applied"] / count * 100) if count > 0 else 0, 1),
                awarded_rate=round((data["awarded"] / count * 100) if count > 0 else 0, 1),
            )
        )

    # Build conversion by score data
    conversion_by_score = [
        {
            "range": f"{bucket[0]:.1f}-{bucket[1]:.1f}",
            "conversion_rate": round(
                (data["applied"] / data["count"] * 100) if data["count"] > 0 else 0,
                1,
            ),
        }
        for bucket, data in bucket_data.items()
    ]

    return MatchQualityResponse(
        total_matches=len(matches),
        avg_score=round(avg_score, 3),
        score_distribution=score_distribution,
        action_breakdown=dict(action_counts),
        conversion_by_score=conversion_by_score,
    )


@router.get(
    "/deadline-heatmap",
    response_model=DeadlineHeatmapResponse,
    summary="Get deadline heatmap",
    description="Get deadline density for calendar heatmap.",
)
async def get_deadline_heatmap(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    months: int = Query(
        default=6,
        ge=1,
        le=12,
        description="Number of months to look ahead",
    ),
) -> DeadlineHeatmapResponse:
    """
    Get deadline density for calendar heatmap.

    Returns:
    - Count of deadlines per day
    - Visual intensity based on count
    - Application counts per deadline
    """
    start_date = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end_date = start_date + timedelta(days=months * 30)

    # Fetch applications with upcoming grant deadlines
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(
            GrantApplication.user_id == current_user.id,
            GrantApplication.stage.in_([
                ApplicationStage.RESEARCHING,
                ApplicationStage.WRITING,
            ]),
        )
    )
    applications = result.unique().scalars().all()

    # Group by deadline date
    deadline_counts: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "applications": 0}
    )

    for app in applications:
        if app.grant.deadline and start_date <= app.grant.deadline <= end_date:
            date_key = app.grant.deadline.strftime("%Y-%m-%d")
            deadline_counts[date_key]["count"] += 1
            deadline_counts[date_key]["applications"] += 1

    if not deadline_counts:
        return DeadlineHeatmapResponse(
            days=[],
            max_count=0,
            total_deadlines=0,
        )

    # Calculate max for intensity scaling
    max_count = max(d["count"] for d in deadline_counts.values())

    # Determine intensity thresholds
    def get_intensity(count: int, max_c: int) -> str:
        if max_c == 0:
            return "low"
        ratio = count / max_c
        if ratio >= 0.75:
            return "critical"
        elif ratio >= 0.5:
            return "high"
        elif ratio >= 0.25:
            return "medium"
        return "low"

    # Build day data
    days = [
        DayData(
            date=date,
            count=data["count"],
            applications=data["applications"],
            intensity=get_intensity(data["count"], max_count),
        )
        for date, data in sorted(deadline_counts.items())
    ]

    total_deadlines = sum(d["count"] for d in deadline_counts.values())

    return DeadlineHeatmapResponse(
        days=days,
        max_count=max_count,
        total_deadlines=total_deadlines,
    )


@router.get(
    "/activity-timeline",
    response_model=ActivityTimelineResponse,
    summary="Get activity timeline",
    description="Get user activity over time for sparklines/charts.",
)
async def get_activity_timeline(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    days: int = Query(
        default=30,
        ge=7,
        le=90,
        description="Number of days of activity to return",
    ),
) -> ActivityTimelineResponse:
    """
    Get user activity over time for sparklines/charts.

    Tracks:
    - Daily counts of applications created
    - Stage changes
    - Matches saved
    - Cumulative totals
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Initialize daily buckets
    daily_data: dict[str, dict] = {}
    current = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    while current <= end:
        date_key = current.strftime("%Y-%m-%d")
        daily_data[date_key] = {
            "applications_created": 0,
            "stage_changes": 0,
            "matches_saved": 0,
        }
        current += timedelta(days=1)

    # Count applications created
    result = await db.execute(
        select(GrantApplication)
        .where(
            GrantApplication.user_id == current_user.id,
            GrantApplication.created_at >= cutoff,
        )
    )
    applications = result.scalars().all()

    for app in applications:
        date_key = app.created_at.strftime("%Y-%m-%d")
        if date_key in daily_data:
            daily_data[date_key]["applications_created"] += 1

    # Count stage changes from activity log
    result = await db.execute(
        select(ApplicationActivity)
        .join(GrantApplication)
        .where(
            GrantApplication.user_id == current_user.id,
            ApplicationActivity.action == "status_changed",
            ApplicationActivity.created_at >= cutoff,
        )
    )
    activities = result.scalars().all()

    for activity in activities:
        date_key = activity.created_at.strftime("%Y-%m-%d")
        if date_key in daily_data:
            daily_data[date_key]["stage_changes"] += 1

    # Count matches saved
    result = await db.execute(
        select(Match)
        .where(
            Match.user_id == current_user.id,
            Match.user_action == "saved",
            Match.created_at >= cutoff,
        )
    )
    saved_matches = result.scalars().all()

    for match in saved_matches:
        date_key = match.created_at.strftime("%Y-%m-%d")
        if date_key in daily_data:
            daily_data[date_key]["matches_saved"] += 1

    # Build response
    daily = [
        DailyActivity(
            date=date,
            applications_created=data["applications_created"],
            stage_changes=data["stage_changes"],
            matches_saved=data["matches_saved"],
            total_actions=(
                data["applications_created"]
                + data["stage_changes"]
                + data["matches_saved"]
            ),
        )
        for date, data in sorted(daily_data.items())
    ]

    # Calculate totals
    totals = {
        "applications_created": sum(d.applications_created for d in daily),
        "stage_changes": sum(d.stage_changes for d in daily),
        "matches_saved": sum(d.matches_saved for d in daily),
        "total_actions": sum(d.total_actions for d in daily),
    }

    # Calculate daily averages
    num_days = len(daily) or 1
    avg_daily = {
        "applications_created": round(totals["applications_created"] / num_days, 2),
        "stage_changes": round(totals["stage_changes"] / num_days, 2),
        "matches_saved": round(totals["matches_saved"] / num_days, 2),
        "total_actions": round(totals["total_actions"] / num_days, 2),
    }

    return ActivityTimelineResponse(
        daily=daily,
        totals=totals,
        avg_daily=avg_daily,
    )
