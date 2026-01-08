"""
Forecast Service for GrantRadar
Predict upcoming grant opportunities based on historical patterns.
"""
import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Grant, LabProfile, User
from backend.utils.fiscal_calendar import (
    FiscalCalendar,
    is_federal_funder,
)


MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


@dataclass
class FunderPattern:
    """Historical pattern for a funder."""

    funder_name: str
    typical_months: list[int]
    avg_amount_min: Optional[int]
    avg_amount_max: Optional[int]
    categories: list[str]
    grant_count: int
    last_deadline: Optional[date]
    source: Optional[str]
    sample_title: Optional[str]
    historical_dates: list[date] = None  # Actual historical deadline dates

    def __post_init__(self):
        if self.historical_dates is None:
            self.historical_dates = []


@dataclass
class ForecastResult:
    """Result of a grant forecast."""

    funder_name: str
    predicted_open_date: date
    confidence: float
    historical_amount_min: Optional[int]
    historical_amount_max: Optional[int]
    focus_areas: list[str]
    title: Optional[str]
    historical_deadline_month: Optional[int]
    recurrence_pattern: str
    last_seen_date: Optional[date]
    source: Optional[str]
    grant_id: Optional[UUID] = None
    fiscal_quarter: Optional[int] = None  # Federal fiscal quarter (1-4)
    is_federal_funder: bool = False  # Whether this is a federal funding agency


@dataclass
class SeasonalTrendResult:
    """Result of seasonal trend analysis."""

    month: int
    month_name: str
    grant_count: int
    avg_amount: Optional[float]
    top_categories: list[str]
    top_funders: list[str]


@dataclass
class RecommendationResult:
    """Result of a recommendation with profile matching."""

    forecast: ForecastResult
    match_score: float
    match_reasons: list[str]
    profile_overlap: list[str]


def calculate_recurrence_pattern(months: list[int]) -> str:
    """Determine the recurrence pattern from historical months."""
    if not months:
        return "unknown"

    unique_months = set(months)

    if len(unique_months) >= 10:
        return "monthly"
    elif len(unique_months) >= 4:
        return "quarterly"
    elif len(unique_months) >= 2:
        return "biannual"
    else:
        return "annual"


def calculate_confidence(grant_count: int, years_span: int, consistency: float) -> float:
    """
    Calculate confidence score for a forecast.

    Args:
        grant_count: Number of historical grants from this funder
        years_span: How many years the data spans
        consistency: How consistent the timing is (0-1)
    """
    # Base confidence from grant count (more data = higher confidence)
    count_factor = min(grant_count / 10.0, 1.0)

    # Years of data (more years = more reliable pattern)
    years_factor = min(years_span / 3.0, 1.0)

    # Combine factors with weights
    confidence = (count_factor * 0.4 + years_factor * 0.3 + consistency * 0.3)

    return round(min(confidence, 1.0), 2)


def calculate_typical_day(
    historical_dates: list[date],
    target_month: int,
) -> tuple[int, float]:
    """
    Calculate the typical day-of-month for deadlines based on historical data.

    Args:
        historical_dates: List of actual historical deadline dates
        target_month: The month we're predicting for

    Returns:
        Tuple of (predicted_day, day_confidence)
        - predicted_day: The most likely day of month (1-28/30/31)
        - day_confidence: How consistent the day is (0-1)
    """
    if not historical_dates:
        return 1, 0.0

    # Get days from dates in the target month (if available)
    month_days = [d.day for d in historical_dates if d.month == target_month]

    # If no dates in target month, use all dates
    if not month_days:
        month_days = [d.day for d in historical_dates]

    if not month_days:
        return 1, 0.0

    # Calculate mean and standard deviation
    avg_day = sum(month_days) / len(month_days)

    if len(month_days) == 1:
        # Single data point - medium confidence
        return round(avg_day), 0.5

    # Calculate variance
    variance = sum((d - avg_day) ** 2 for d in month_days) / len(month_days)
    std_dev = variance ** 0.5

    # Confidence based on consistency:
    # std_dev of 0 = perfect consistency = 1.0 confidence
    # std_dev of 15 (half month) = low consistency = ~0.0 confidence
    day_confidence = max(0.0, 1.0 - (std_dev / 15.0))

    # Round to nearest day, clamping to valid range
    predicted_day = max(1, min(28, round(avg_day)))  # Use 28 as safe max

    return predicted_day, round(day_confidence, 2)


def predict_next_opening(
    typical_months: list[int],
    historical_dates: list[date],
    last_deadline: Optional[date],
    lookahead_months: int = 6,
) -> tuple[date, int, float]:
    """
    Predict when a grant will next open based on historical patterns.

    Args:
        typical_months: List of months when this funder typically has deadlines
        historical_dates: Actual historical deadline dates for day-level accuracy
        last_deadline: The most recent deadline date
        lookahead_months: How many months ahead to look

    Returns:
        Tuple of (predicted_date, deadline_month, day_confidence)
        - predicted_date: The predicted opening date with day-level accuracy
        - deadline_month: The month of the predicted deadline
        - day_confidence: Confidence in the day prediction (0-1)
    """
    today = date.today()

    if not typical_months:
        # No pattern - predict based on last deadline
        if last_deadline:
            # Assume annual recurrence, use the actual day from last deadline
            next_year = today.year + 1 if date(today.year, last_deadline.month, last_deadline.day) <= today else today.year
            # Handle edge case for Feb 29
            day = min(last_deadline.day, calendar.monthrange(next_year, last_deadline.month)[1])
            next_date = date(next_year, last_deadline.month, day)
            if next_date <= today:
                next_year += 1
                day = min(last_deadline.day, calendar.monthrange(next_year, last_deadline.month)[1])
                next_date = date(next_year, last_deadline.month, day)
            return next_date, last_deadline.month, 0.5  # Medium confidence for single-point prediction
        # Default to 3 months from now, 1st of month
        future = today + timedelta(days=90)
        return date(future.year, future.month, 1), future.month, 0.0

    # Find the next month in the pattern
    for month_offset in range(lookahead_months + 12):
        check_month = ((today.month - 1 + month_offset) % 12) + 1
        check_year = today.year + ((today.month - 1 + month_offset) // 12)

        if check_month in typical_months:
            # Calculate the predicted day for this month
            predicted_day, day_confidence = calculate_typical_day(historical_dates, check_month)

            # Ensure the day is valid for this month
            max_day = calendar.monthrange(check_year, check_month)[1]
            predicted_day = min(predicted_day, max_day)

            check_date = date(check_year, check_month, predicted_day)

            if check_date > today:
                return check_date, check_month, day_confidence

    # Fallback: use the most common month next year
    most_common_month = max(set(typical_months), key=typical_months.count)
    year = today.year if today.month < most_common_month else today.year + 1

    # Still calculate day-level prediction for fallback
    predicted_day, day_confidence = calculate_typical_day(historical_dates, most_common_month)
    max_day = calendar.monthrange(year, most_common_month)[1]
    predicted_day = min(predicted_day, max_day)

    return date(year, most_common_month, predicted_day), most_common_month, day_confidence


async def analyze_funder_patterns(
    db: AsyncSession,
    min_grants: int = 2,
    years_lookback: int = 3,
) -> list[FunderPattern]:
    """
    Analyze historical grant data to find recurring funder patterns.

    Args:
        db: Database session
        min_grants: Minimum grants from a funder to consider
        years_lookback: How many years of data to analyze
    """
    cutoff_date = datetime.now() - timedelta(days=years_lookback * 365)

    # Query grants grouped by agency
    # Note: We skip categories aggregation due to PostgreSQL array issues with nulls
    query = (
        select(
            Grant.agency,
            Grant.source,
            func.count(Grant.id).label("grant_count"),
            func.array_agg(extract("month", Grant.deadline)).label("deadline_months"),
            func.array_agg(Grant.deadline).label("deadline_dates"),  # Collect actual dates
            func.avg(Grant.amount_min).label("avg_min"),
            func.avg(Grant.amount_max).label("avg_max"),
            func.max(Grant.deadline).label("last_deadline"),
            func.max(Grant.title).label("sample_title"),
        )
        .where(
            and_(
                Grant.agency.isnot(None),
                Grant.deadline.isnot(None),
                Grant.created_at >= cutoff_date,
            )
        )
        .group_by(Grant.agency, Grant.source)
        .having(func.count(Grant.id) >= min_grants)
    )

    result = await db.execute(query)
    rows = result.all()

    patterns = []
    for row in rows:
        # Extract months (filter out None values)
        months = [int(m) for m in (row.deadline_months or []) if m is not None]

        # Extract actual deadline dates (filter out None values and convert to date)
        historical_dates = []
        for d in (row.deadline_dates or []):
            if d is not None:
                if isinstance(d, datetime):
                    historical_dates.append(d.date())
                elif isinstance(d, date):
                    historical_dates.append(d)

        # Categories are not aggregated due to PostgreSQL array handling issues with nulls
        # TODO: Could fetch categories separately if needed
        top_cats: list[str] = []

        patterns.append(
            FunderPattern(
                funder_name=row.agency,
                typical_months=months,
                avg_amount_min=int(row.avg_min) if row.avg_min else None,
                avg_amount_max=int(row.avg_max) if row.avg_max else None,
                categories=top_cats,
                grant_count=row.grant_count,
                last_deadline=row.last_deadline.date() if row.last_deadline else None,
                source=row.source,
                sample_title=row.sample_title,
                historical_dates=historical_dates,
            )
        )

    return patterns


async def get_upcoming_forecasts(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    lookahead_months: int = 6,
    limit: int = 20,
) -> list[ForecastResult]:
    """
    Predict upcoming grant opportunities.

    Args:
        db: Database session
        user_id: Optional user ID for profile matching
        lookahead_months: How many months to look ahead
        limit: Maximum number of forecasts
    """
    patterns = await analyze_funder_patterns(db)

    forecasts = []
    today = date.today()
    target_date = today + timedelta(days=lookahead_months * 30)

    for pattern in patterns:
        predicted_date, deadline_month, day_confidence = predict_next_opening(
            pattern.typical_months,
            pattern.historical_dates,
            pattern.last_deadline,
            lookahead_months,
        )

        # Check if this is a federal funder for fiscal calendar awareness
        funder_is_federal = is_federal_funder(pattern.funder_name)

        # Apply fiscal calendar adjustment for federal funders
        if funder_is_federal and pattern.historical_dates:
            predicted_date = FiscalCalendar.adjust_prediction_for_fiscal_patterns(
                predicted_date=predicted_date,
                funder_name=pattern.funder_name,
                historical_dates=pattern.historical_dates,
            )
            # Update deadline_month if the date was adjusted
            deadline_month = predicted_date.month

        # Only include if within lookahead window
        if predicted_date > target_date:
            continue

        # Calculate confidence (incorporate day_confidence into overall confidence)
        unique_months = set(pattern.typical_months)
        consistency = len(unique_months) / max(len(pattern.typical_months), 1)
        years_span = 3  # From our lookback
        base_confidence = calculate_confidence(pattern.grant_count, years_span, 1 - consistency)
        # Blend base confidence with day confidence (day confidence is a bonus factor)
        confidence = round(base_confidence * 0.8 + day_confidence * 0.2, 2)

        recurrence = calculate_recurrence_pattern(pattern.typical_months)

        # Get fiscal quarter for the predicted date
        fiscal_quarter = FiscalCalendar.get_fiscal_quarter(predicted_date)

        forecasts.append(
            ForecastResult(
                funder_name=pattern.funder_name,
                predicted_open_date=predicted_date,
                confidence=confidence,
                historical_amount_min=pattern.avg_amount_min,
                historical_amount_max=pattern.avg_amount_max,
                focus_areas=pattern.categories,
                title=pattern.sample_title,
                historical_deadline_month=deadline_month,
                recurrence_pattern=recurrence,
                last_seen_date=pattern.last_deadline,
                source=pattern.source,
                fiscal_quarter=fiscal_quarter,
                is_federal_funder=funder_is_federal,
            )
        )

    # Sort by predicted date, then confidence
    forecasts.sort(key=lambda x: (x.predicted_open_date, -x.confidence))

    return forecasts[:limit]


async def get_seasonal_trends(
    db: AsyncSession,
    user_focus_areas: Optional[list[str]] = None,
) -> list[SeasonalTrendResult]:
    """
    Analyze grant availability by month.

    Args:
        db: Database session
        user_focus_areas: Optional list of focus areas to filter by
    """
    # Build base query
    base_query = select(
        extract("month", Grant.deadline).label("month"),
        func.count(Grant.id).label("grant_count"),
        func.avg(
            func.coalesce(Grant.amount_max, Grant.amount_min, 0)
        ).label("avg_amount"),
        func.array_agg(Grant.categories).label("all_categories"),
        func.array_agg(Grant.agency).label("all_agencies"),
    ).where(
        Grant.deadline.isnot(None)
    )

    # Filter by focus areas if provided
    if user_focus_areas:
        or_conditions = [
            Grant.categories.overlap(user_focus_areas)
        ]
        base_query = base_query.where(or_(*or_conditions))

    query = base_query.group_by(extract("month", Grant.deadline))

    result = await db.execute(query)
    rows = result.all()

    # Build month data
    month_data = {i: None for i in range(1, 13)}

    for row in rows:
        month = int(row.month)

        # Count categories
        cat_counts = defaultdict(int)
        for cat_list in (row.all_categories or []):
            if cat_list:
                for cat in cat_list:
                    cat_counts[cat] += 1
        top_cats = sorted(cat_counts.keys(), key=lambda x: cat_counts[x], reverse=True)[:5]

        # Count agencies
        agency_counts = defaultdict(int)
        for agency in (row.all_agencies or []):
            if agency:
                agency_counts[agency] += 1
        top_agencies = sorted(
            agency_counts.keys(), key=lambda x: agency_counts[x], reverse=True
        )[:5]

        month_data[month] = SeasonalTrendResult(
            month=month,
            month_name=MONTH_NAMES[month],
            grant_count=row.grant_count,
            avg_amount=float(row.avg_amount) if row.avg_amount else None,
            top_categories=top_cats,
            top_funders=top_agencies,
        )

    # Fill in missing months with zeros
    trends = []
    for month in range(1, 13):
        if month_data[month]:
            trends.append(month_data[month])
        else:
            trends.append(
                SeasonalTrendResult(
                    month=month,
                    month_name=MONTH_NAMES[month],
                    grant_count=0,
                    avg_amount=None,
                    top_categories=[],
                    top_funders=[],
                )
            )

    return trends


async def get_recommendations(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 10,
) -> list[RecommendationResult]:
    """
    Get AI-powered grant recommendations based on user profile.

    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of recommendations
    """
    # Get user's lab profile
    profile_result = await db.execute(
        select(LabProfile).where(LabProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()

    if not profile:
        # No profile - return generic forecasts
        forecasts = await get_upcoming_forecasts(db, limit=limit)
        return [
            RecommendationResult(
                forecast=f,
                match_score=0.5,
                match_reasons=["Complete your profile for personalized recommendations"],
                profile_overlap=[],
            )
            for f in forecasts
        ]

    # Get forecasts
    forecasts = await get_upcoming_forecasts(db, user_id=user_id, limit=limit * 2)

    # Score each forecast against user profile
    recommendations = []
    user_areas = set(profile.research_areas or [])
    user_methods = set(profile.methods or [])

    for forecast in forecasts:
        forecast_areas = set(forecast.focus_areas)

        # Calculate match score
        area_overlap = user_areas & forecast_areas
        area_score = len(area_overlap) / max(len(user_areas), 1) if user_areas else 0

        # Boost for recent activity
        recency_boost = 0.1 if forecast.last_seen_date and (
            date.today() - forecast.last_seen_date
        ).days < 365 else 0

        # Boost for high confidence
        confidence_boost = forecast.confidence * 0.2

        match_score = min(area_score * 0.7 + recency_boost + confidence_boost, 1.0)

        # Generate reasons
        reasons = []
        if area_overlap:
            reasons.append(f"Matches your research in: {', '.join(list(area_overlap)[:3])}")
        if forecast.confidence >= 0.7:
            reasons.append("Strong historical pattern")
        if forecast.recurrence_pattern == "annual":
            reasons.append("Annual grant cycle")
        if not reasons:
            reasons.append("Based on funder patterns")

        recommendations.append(
            RecommendationResult(
                forecast=forecast,
                match_score=round(match_score, 2),
                match_reasons=reasons,
                profile_overlap=list(area_overlap)[:5],
            )
        )

    # Sort by match score
    recommendations.sort(key=lambda x: x.match_score, reverse=True)

    return recommendations[:limit]
