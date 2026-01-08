"""
Deadline History Service for GrantRadar
Manages historical deadline data extraction and pattern analysis.
"""
import logging
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Grant, GrantDeadlineHistory

logger = logging.getLogger(__name__)


async def extract_deadline_history_from_grants(db: AsyncSession) -> int:
    """
    Extract historical deadline data from the grants table and populate
    grant_deadline_history. Returns count of records created.

    Groups grants by funder/title pattern to build historical series.
    Uses explicit check-before-insert to handle deduplication.
    """
    # Query all grants with deadline and agency info
    query = select(Grant).where(
        and_(
            Grant.deadline.isnot(None),
            Grant.agency.isnot(None),
        )
    ).order_by(Grant.deadline.desc())

    result = await db.execute(query)
    grants = result.scalars().all()

    if not grants:
        logger.info("No grants found with deadline and agency data")
        return 0

    records_created = 0
    # Track what we've already processed in this batch to avoid duplicates
    processed_keys = set()

    for grant in grants:
        # Extract fiscal year from deadline
        deadline_dt = grant.deadline
        if isinstance(deadline_dt, datetime):
            deadline_date_obj = deadline_dt.date() if hasattr(deadline_dt, 'date') else deadline_dt
        else:
            deadline_date_obj = deadline_dt

        # Federal fiscal year typically starts October 1
        # If deadline is Oct-Dec, it's the next fiscal year
        if hasattr(deadline_date_obj, 'month'):
            if deadline_date_obj.month >= 10:
                fiscal_year = deadline_date_obj.year + 1
            else:
                fiscal_year = deadline_date_obj.year
        else:
            fiscal_year = datetime.now().year

        # Create a composite key for deduplication
        dedup_key = (grant.agency, grant.title, str(deadline_date_obj))
        if dedup_key in processed_keys:
            continue
        processed_keys.add(dedup_key)

        # Check if record already exists in database
        existing_query = select(GrantDeadlineHistory.id).where(
            and_(
                GrantDeadlineHistory.funder_name == grant.agency,
                GrantDeadlineHistory.grant_title == grant.title,
                func.date(GrantDeadlineHistory.deadline_date) == deadline_date_obj,
            )
        ).limit(1)

        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none() is not None:
            continue

        # Create new record
        try:
            record = GrantDeadlineHistory(
                grant_id=grant.id,
                funder_name=grant.agency,
                grant_title=grant.title,
                deadline_date=grant.deadline,
                open_date=grant.posted_at,
                announcement_date=grant.posted_at,
                fiscal_year=fiscal_year,
                amount_min=grant.amount_min,
                amount_max=grant.amount_max,
                categories=grant.categories,
                source=grant.source or "unknown",
            )
            db.add(record)
            records_created += 1
        except Exception as e:
            logger.warning(f"Error inserting deadline history for grant {grant.id}: {e}")
            continue

    await db.commit()
    logger.info(f"Created {records_created} deadline history records from {len(grants)} grants")

    return records_created


async def add_deadline_record(
    db: AsyncSession,
    funder_name: str,
    grant_title: str,
    deadline_date: date,
    open_date: Optional[date] = None,
    announcement_date: Optional[date] = None,
    fiscal_year: Optional[int] = None,
    amount_min: Optional[int] = None,
    amount_max: Optional[int] = None,
    categories: Optional[list[str]] = None,
    source: str = "manual",
    grant_id: Optional[UUID] = None,
) -> GrantDeadlineHistory:
    """
    Add a single deadline record.

    Handles deduplication - if a record with the same funder_name, grant_title,
    and deadline_date already exists, returns the existing record.

    Args:
        db: Database session
        funder_name: Name of the funding organization
        grant_title: Title of the grant opportunity
        deadline_date: The deadline date for this grant cycle
        open_date: When the grant opened for applications
        announcement_date: When the grant was announced
        fiscal_year: Fiscal year (auto-calculated if not provided)
        amount_min: Minimum funding amount
        amount_max: Maximum funding amount
        categories: Research categories/tags
        source: Data source identifier
        grant_id: Optional reference to a grant record

    Returns:
        The created or existing GrantDeadlineHistory record
    """
    # Convert date to datetime if needed
    if isinstance(deadline_date, date) and not isinstance(deadline_date, datetime):
        deadline_datetime = datetime.combine(deadline_date, datetime.min.time())
    else:
        deadline_datetime = deadline_date

    # Auto-calculate fiscal year if not provided
    if fiscal_year is None:
        if deadline_datetime.month >= 10:
            fiscal_year = deadline_datetime.year + 1
        else:
            fiscal_year = deadline_datetime.year

    # Convert open_date if provided
    open_datetime = None
    if open_date:
        if isinstance(open_date, date) and not isinstance(open_date, datetime):
            open_datetime = datetime.combine(open_date, datetime.min.time())
        else:
            open_datetime = open_date

    # Convert announcement_date if provided
    announcement_datetime = None
    if announcement_date:
        if isinstance(announcement_date, date) and not isinstance(announcement_date, datetime):
            announcement_datetime = datetime.combine(announcement_date, datetime.min.time())
        else:
            announcement_datetime = announcement_date

    # Check for existing record
    existing_query = select(GrantDeadlineHistory).where(
        and_(
            GrantDeadlineHistory.funder_name == funder_name,
            GrantDeadlineHistory.grant_title == grant_title,
            func.date(GrantDeadlineHistory.deadline_date) == deadline_datetime.date(),
        )
    )
    existing_result = await db.execute(existing_query)
    existing_record = existing_result.scalar_one_or_none()

    if existing_record:
        logger.debug(f"Deadline record already exists for {funder_name}/{grant_title} on {deadline_date}")
        return existing_record

    # Create new record
    record = GrantDeadlineHistory(
        grant_id=grant_id,
        funder_name=funder_name,
        grant_title=grant_title,
        deadline_date=deadline_datetime,
        open_date=open_datetime,
        announcement_date=announcement_datetime,
        fiscal_year=fiscal_year,
        amount_min=amount_min,
        amount_max=amount_max,
        categories=categories,
        source=source,
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info(f"Created deadline history record for {funder_name}/{grant_title}")
    return record


async def get_funder_deadline_history(
    db: AsyncSession,
    funder_name: str,
    years_back: int = 5,
) -> list[GrantDeadlineHistory]:
    """
    Get all historical deadlines for a funder.

    Args:
        db: Database session
        funder_name: Name of the funding organization (case-insensitive search)
        years_back: Number of years of history to retrieve (default 5)

    Returns:
        List of GrantDeadlineHistory records sorted by deadline date descending
    """
    cutoff_date = datetime.now() - timedelta(days=years_back * 365)

    # Use case-insensitive search with ILIKE
    query = (
        select(GrantDeadlineHistory)
        .where(
            and_(
                func.lower(GrantDeadlineHistory.funder_name).contains(funder_name.lower()),
                GrantDeadlineHistory.deadline_date >= cutoff_date,
            )
        )
        .order_by(GrantDeadlineHistory.deadline_date.desc())
    )

    result = await db.execute(query)
    records = result.scalars().all()

    return list(records)


async def get_deadline_patterns(
    db: AsyncSession,
    funder_name: str,
) -> dict:
    """
    Analyze deadline patterns for a funder.

    Examines historical deadline data to identify patterns in timing,
    which can be used for forecasting future grant cycles.

    Args:
        db: Database session
        funder_name: Name of the funding organization

    Returns:
        Dict containing:
        - typical_day_of_month: Most common day of month for deadlines
        - typical_months: List of months when deadlines typically occur
        - date_variance_days: Standard deviation of day-of-month
        - records_count: Number of records analyzed
        - avg_cycle_days: Average days between deadline cycles
        - earliest_deadline: Earliest recorded deadline
        - latest_deadline: Most recent recorded deadline
    """
    # Get all deadline history for this funder
    query = (
        select(GrantDeadlineHistory)
        .where(
            func.lower(GrantDeadlineHistory.funder_name).contains(funder_name.lower())
        )
        .order_by(GrantDeadlineHistory.deadline_date.asc())
    )

    result = await db.execute(query)
    records = result.scalars().all()

    if not records:
        return {
            "typical_day_of_month": None,
            "typical_months": [],
            "date_variance_days": None,
            "records_count": 0,
            "avg_cycle_days": None,
            "earliest_deadline": None,
            "latest_deadline": None,
            "grant_titles": [],
        }

    # Extract deadline dates
    deadline_dates = []
    days_of_month = []
    months = []
    grant_titles = set()

    for record in records:
        deadline_dt = record.deadline_date
        if isinstance(deadline_dt, datetime):
            deadline_dates.append(deadline_dt)
            days_of_month.append(deadline_dt.day)
            months.append(deadline_dt.month)
        grant_titles.add(record.grant_title)

    if not deadline_dates:
        return {
            "typical_day_of_month": None,
            "typical_months": [],
            "date_variance_days": None,
            "records_count": len(records),
            "avg_cycle_days": None,
            "earliest_deadline": None,
            "latest_deadline": None,
            "grant_titles": list(grant_titles),
        }

    # Calculate typical day of month (mode)
    day_counts = defaultdict(int)
    for day in days_of_month:
        day_counts[day] += 1
    typical_day = max(day_counts.keys(), key=lambda d: day_counts[d])

    # Calculate typical months (sorted by frequency)
    month_counts = defaultdict(int)
    for month in months:
        month_counts[month] += 1
    typical_months = sorted(
        month_counts.keys(),
        key=lambda m: month_counts[m],
        reverse=True
    )

    # Calculate standard deviation of day-of-month
    if len(days_of_month) > 1:
        date_variance_days = statistics.stdev(days_of_month)
    else:
        date_variance_days = 0.0

    # Calculate average cycle length (days between consecutive deadlines)
    cycle_lengths = []
    sorted_dates = sorted(deadline_dates)
    for i in range(1, len(sorted_dates)):
        delta = (sorted_dates[i] - sorted_dates[i-1]).days
        # Only consider cycles between 30 and 730 days (1 month to 2 years)
        if 30 <= delta <= 730:
            cycle_lengths.append(delta)

    avg_cycle_days = None
    if cycle_lengths:
        avg_cycle_days = statistics.mean(cycle_lengths)

    return {
        "typical_day_of_month": typical_day,
        "typical_months": typical_months,
        "date_variance_days": round(date_variance_days, 2),
        "records_count": len(records),
        "avg_cycle_days": round(avg_cycle_days, 1) if avg_cycle_days else None,
        "earliest_deadline": min(deadline_dates),
        "latest_deadline": max(deadline_dates),
        "grant_titles": list(grant_titles)[:10],  # Limit to 10 titles
    }


async def get_all_funder_patterns(
    db: AsyncSession,
    min_records: int = 2,
    years_back: int = 5,
) -> list[dict]:
    """
    Get deadline patterns for all funders with sufficient history.

    Args:
        db: Database session
        min_records: Minimum number of records required to include a funder
        years_back: Number of years of history to analyze

    Returns:
        List of pattern dictionaries, one per funder, sorted by record count
    """
    cutoff_date = datetime.now() - timedelta(days=years_back * 365)

    # Get funders with enough records
    funder_query = (
        select(
            GrantDeadlineHistory.funder_name,
            func.count(GrantDeadlineHistory.id).label("record_count"),
        )
        .where(GrantDeadlineHistory.deadline_date >= cutoff_date)
        .group_by(GrantDeadlineHistory.funder_name)
        .having(func.count(GrantDeadlineHistory.id) >= min_records)
        .order_by(func.count(GrantDeadlineHistory.id).desc())
    )

    result = await db.execute(funder_query)
    funders = result.all()

    patterns = []
    for funder_row in funders:
        funder_name = funder_row.funder_name
        pattern = await get_deadline_patterns(db, funder_name)
        pattern["funder_name"] = funder_name
        patterns.append(pattern)

    return patterns


async def predict_next_deadline(
    db: AsyncSession,
    funder_name: str,
    grant_title: Optional[str] = None,
) -> Optional[dict]:
    """
    Predict the next deadline for a funder based on historical patterns.

    Args:
        db: Database session
        funder_name: Name of the funding organization
        grant_title: Optional specific grant title to match

    Returns:
        Dict with prediction details or None if insufficient data
    """
    # Build query
    conditions = [
        func.lower(GrantDeadlineHistory.funder_name).contains(funder_name.lower())
    ]
    if grant_title:
        conditions.append(
            func.lower(GrantDeadlineHistory.grant_title).contains(grant_title.lower())
        )

    query = (
        select(GrantDeadlineHistory)
        .where(and_(*conditions))
        .order_by(GrantDeadlineHistory.deadline_date.desc())
        .limit(10)
    )

    result = await db.execute(query)
    records = list(result.scalars().all())

    if len(records) < 2:
        return None

    # Get the pattern analysis
    patterns = await get_deadline_patterns(db, funder_name)

    if not patterns["avg_cycle_days"]:
        return None

    # Get the most recent deadline
    latest_deadline = patterns["latest_deadline"]

    if not latest_deadline:
        return None

    # Predict next deadline based on average cycle
    predicted_date = latest_deadline + timedelta(days=int(patterns["avg_cycle_days"]))

    # Adjust to typical day of month if we have one
    if patterns["typical_day_of_month"]:
        try:
            predicted_date = predicted_date.replace(day=patterns["typical_day_of_month"])
        except ValueError:
            # Day doesn't exist in month (e.g., Feb 30)
            pass

    # Calculate confidence based on data quality
    confidence = 0.0
    if patterns["records_count"] >= 10:
        confidence += 0.4
    elif patterns["records_count"] >= 5:
        confidence += 0.25
    elif patterns["records_count"] >= 2:
        confidence += 0.1

    # Lower variance = higher confidence
    if patterns["date_variance_days"] is not None:
        if patterns["date_variance_days"] < 3:
            confidence += 0.4
        elif patterns["date_variance_days"] < 7:
            confidence += 0.25
        elif patterns["date_variance_days"] < 14:
            confidence += 0.1

    # Consistent months = higher confidence
    if len(patterns["typical_months"]) <= 2:
        confidence += 0.2
    elif len(patterns["typical_months"]) <= 4:
        confidence += 0.1

    confidence = min(confidence, 1.0)

    return {
        "funder_name": funder_name,
        "predicted_deadline": predicted_date,
        "confidence": round(confidence, 2),
        "based_on_records": patterns["records_count"],
        "typical_months": patterns["typical_months"][:3],
        "typical_day_of_month": patterns["typical_day_of_month"],
        "avg_cycle_days": patterns["avg_cycle_days"],
        "last_known_deadline": latest_deadline,
        "grant_titles": patterns["grant_titles"],
    }


async def bulk_add_deadline_records(
    db: AsyncSession,
    records: list[dict],
) -> tuple[int, int]:
    """
    Bulk add deadline records with deduplication.

    Args:
        db: Database session
        records: List of dicts with deadline record data. Each dict should have:
            - funder_name (required)
            - grant_title (required)
            - deadline_date (required)
            - open_date (optional)
            - fiscal_year (optional, auto-calculated)
            - amount_min (optional)
            - amount_max (optional)
            - categories (optional)
            - source (optional, defaults to 'bulk_import')

    Returns:
        Tuple of (records_created, records_skipped)
    """
    created = 0
    skipped = 0

    for record_data in records:
        # Validate required fields
        if not all(k in record_data for k in ["funder_name", "grant_title", "deadline_date"]):
            logger.warning(f"Skipping record with missing required fields: {record_data}")
            skipped += 1
            continue

        try:
            await add_deadline_record(
                db=db,
                funder_name=record_data["funder_name"],
                grant_title=record_data["grant_title"],
                deadline_date=record_data["deadline_date"],
                open_date=record_data.get("open_date"),
                announcement_date=record_data.get("announcement_date"),
                fiscal_year=record_data.get("fiscal_year"),
                amount_min=record_data.get("amount_min"),
                amount_max=record_data.get("amount_max"),
                categories=record_data.get("categories"),
                source=record_data.get("source", "bulk_import"),
                grant_id=record_data.get("grant_id"),
            )
            created += 1
        except Exception as e:
            logger.warning(f"Error adding deadline record: {e}")
            skipped += 1

    return created, skipped


async def get_deadline_history_stats(db: AsyncSession) -> dict:
    """
    Get aggregate statistics about the deadline history data.

    Args:
        db: Database session

    Returns:
        Dict with statistics about the deadline history table
    """
    # Total records
    total_query = select(func.count(GrantDeadlineHistory.id))
    total_result = await db.execute(total_query)
    total_records = total_result.scalar() or 0

    # Unique funders
    funders_query = select(func.count(func.distinct(GrantDeadlineHistory.funder_name)))
    funders_result = await db.execute(funders_query)
    unique_funders = funders_result.scalar() or 0

    # Unique grant titles
    titles_query = select(func.count(func.distinct(GrantDeadlineHistory.grant_title)))
    titles_result = await db.execute(titles_query)
    unique_titles = titles_result.scalar() or 0

    # Date range
    date_range_query = select(
        func.min(GrantDeadlineHistory.deadline_date),
        func.max(GrantDeadlineHistory.deadline_date),
    )
    date_result = await db.execute(date_range_query)
    date_row = date_result.one()

    # Sources breakdown
    sources_query = (
        select(
            GrantDeadlineHistory.source,
            func.count(GrantDeadlineHistory.id).label("count"),
        )
        .group_by(GrantDeadlineHistory.source)
        .order_by(func.count(GrantDeadlineHistory.id).desc())
    )
    sources_result = await db.execute(sources_query)
    sources = {row.source: row.count for row in sources_result.all()}

    # Top funders by record count
    top_funders_query = (
        select(
            GrantDeadlineHistory.funder_name,
            func.count(GrantDeadlineHistory.id).label("count"),
        )
        .group_by(GrantDeadlineHistory.funder_name)
        .order_by(func.count(GrantDeadlineHistory.id).desc())
        .limit(10)
    )
    top_funders_result = await db.execute(top_funders_query)
    top_funders = [
        {"funder": row.funder_name, "records": row.count}
        for row in top_funders_result.all()
    ]

    return {
        "total_records": total_records,
        "unique_funders": unique_funders,
        "unique_grant_titles": unique_titles,
        "earliest_deadline": date_row[0],
        "latest_deadline": date_row[1],
        "sources": sources,
        "top_funders": top_funders,
    }
