"""
Federal Fiscal Calendar Utilities for GrantRadar.

Federal fiscal year runs Oct 1 - Sep 30.
Many federal grants have predictable patterns around fiscal year:
- End of fiscal year (Sep) - use-it-or-lose-it spending
- Start of fiscal year (Oct-Nov) - new appropriations
- Q1 end (Dec) - quarterly deadlines
- Q2 end (Mar) - quarterly deadlines
- Q3 end (Jun) - quarterly deadlines
"""

from datetime import date
from typing import Optional


# List of federal agency abbreviations commonly used in grant funding
FEDERAL_AGENCIES = [
    "NIH",  # National Institutes of Health
    "NSF",  # National Science Foundation
    "DOE",  # Department of Energy
    "DOD",  # Department of Defense
    "NASA",  # National Aeronautics and Space Administration
    "USDA",  # United States Department of Agriculture
    "EPA",  # Environmental Protection Agency
    "NEH",  # National Endowment for the Humanities
    "NEA",  # National Endowment for the Arts
    "ED",  # Department of Education
    "HHS",  # Department of Health and Human Services
    "CDC",  # Centers for Disease Control and Prevention
    "SAMHSA",  # Substance Abuse and Mental Health Services Administration
    "HRSA",  # Health Resources and Services Administration
    "AHRQ",  # Agency for Healthcare Research and Quality
    "FDA",  # Food and Drug Administration
    "VA",  # Department of Veterans Affairs
    "NOAA",  # National Oceanic and Atmospheric Administration
    "NIST",  # National Institute of Standards and Technology
    "DOT",  # Department of Transportation
    "DHS",  # Department of Homeland Security
    "DOJ",  # Department of Justice
    "HUD",  # Department of Housing and Urban Development
    "DOI",  # Department of the Interior
    "USAID",  # United States Agency for International Development
    "NIJ",  # National Institute of Justice
    "DARPA",  # Defense Advanced Research Projects Agency
    "ARPA-E",  # Advanced Research Projects Agency-Energy
    "ARPA-H",  # Advanced Research Projects Agency for Health
]


def is_federal_funder(funder_name: str) -> bool:
    """
    Check if a funder is a federal agency.

    Performs a case-insensitive check against known federal agency abbreviations.
    Also checks if the funder name contains common federal agency identifiers.

    Args:
        funder_name: Name of the funding organization

    Returns:
        True if the funder appears to be a federal agency
    """
    if not funder_name:
        return False

    funder_upper = funder_name.upper().strip()

    # Direct match with agency abbreviations
    for agency in FEDERAL_AGENCIES:
        if agency in funder_upper:
            return True

    # Common federal identifiers
    federal_keywords = [
        "NATIONAL INSTITUTES",
        "NATIONAL SCIENCE FOUNDATION",
        "DEPARTMENT OF",
        "U.S.",
        "US ",
        "FEDERAL",
        "UNITED STATES",
    ]

    for keyword in federal_keywords:
        if keyword in funder_upper:
            return True

    return False


class FiscalCalendar:
    """Federal fiscal year calendar utilities."""

    # Federal fiscal year starts October 1
    FISCAL_YEAR_START_MONTH = 10

    # Quarter end months in fiscal year order (Q1=Dec, Q2=Mar, Q3=Jun, Q4=Sep)
    QUARTER_END_MONTHS = {
        1: 12,  # Q1 ends December
        2: 3,  # Q2 ends March
        3: 6,  # Q3 ends June
        4: 9,  # Q4 ends September (fiscal year end)
    }

    # Days before quarter end for "use-it-or-lose-it" patterns
    END_OF_YEAR_WINDOW_DAYS = 30  # September is particularly active

    @staticmethod
    def get_fiscal_year(check_date: date) -> int:
        """
        Get federal fiscal year for a date.

        FY2024 = Oct 1, 2023 - Sep 30, 2024

        Args:
            check_date: The date to check

        Returns:
            The fiscal year number
        """
        if check_date.month >= FiscalCalendar.FISCAL_YEAR_START_MONTH:
            return check_date.year + 1
        return check_date.year

    @staticmethod
    def get_fiscal_quarter(check_date: date) -> int:
        """
        Get fiscal quarter (1-4) for a date.

        Q1: Oct-Dec
        Q2: Jan-Mar
        Q3: Apr-Jun
        Q4: Jul-Sep

        Args:
            check_date: The date to check

        Returns:
            Quarter number (1-4)
        """
        month = check_date.month

        if month in (10, 11, 12):
            return 1
        elif month in (1, 2, 3):
            return 2
        elif month in (4, 5, 6):
            return 3
        else:  # 7, 8, 9
            return 4

    @staticmethod
    def get_quarter_end_dates(fiscal_year: int) -> list[date]:
        """
        Get all quarter end dates for a fiscal year.

        Args:
            fiscal_year: The fiscal year (e.g., 2024 for FY2024)

        Returns:
            List of quarter end dates in chronological order
        """
        # FY2024 runs Oct 2023 - Sep 2024
        calendar_year_start = fiscal_year - 1

        return [
            date(calendar_year_start, 12, 31),  # Q1 end - December 31
            date(fiscal_year, 3, 31),  # Q2 end - March 31
            date(fiscal_year, 6, 30),  # Q3 end - June 30
            date(fiscal_year, 9, 30),  # Q4 end - September 30 (FY end)
        ]

    @staticmethod
    def get_next_quarter_end(check_date: date) -> date:
        """
        Get the next quarter end date from the given date.

        Args:
            check_date: The reference date

        Returns:
            The next quarter end date
        """
        fiscal_year = FiscalCalendar.get_fiscal_year(check_date)
        quarter_ends = FiscalCalendar.get_quarter_end_dates(fiscal_year)

        for qe in quarter_ends:
            if qe >= check_date:
                return qe

        # If past all quarters in this FY, get first quarter of next FY
        next_fy_ends = FiscalCalendar.get_quarter_end_dates(fiscal_year + 1)
        return next_fy_ends[0]

    @staticmethod
    def is_near_quarter_end(check_date: date, days_threshold: int = 14) -> bool:
        """
        Check if date is within threshold of a quarter end.

        Args:
            check_date: The date to check
            days_threshold: Number of days before quarter end to consider "near"

        Returns:
            True if the date is within the threshold of a quarter end
        """
        fiscal_year = FiscalCalendar.get_fiscal_year(check_date)
        quarter_ends = FiscalCalendar.get_quarter_end_dates(fiscal_year)

        # Also check previous fiscal year's last quarter end
        prev_fy_ends = FiscalCalendar.get_quarter_end_dates(fiscal_year - 1)
        all_quarter_ends = prev_fy_ends + quarter_ends

        for qe in all_quarter_ends:
            days_to_qe = (qe - check_date).days
            if 0 <= days_to_qe <= days_threshold:
                return True
            # Also check if we're shortly after quarter end (within 7 days)
            if -7 <= days_to_qe < 0:
                return True

        return False

    @staticmethod
    def is_fiscal_year_end_period(check_date: date, days_before: int = 30) -> bool:
        """
        Check if a date is in the end-of-fiscal-year spending period.

        This is the "use-it-or-lose-it" period when agencies often release
        remaining funds. Typically late August through September.

        Args:
            check_date: The date to check
            days_before: Days before September 30 to consider as end-of-year period

        Returns:
            True if in the end-of-fiscal-year period
        """
        fiscal_year = FiscalCalendar.get_fiscal_year(check_date)
        fy_end = date(fiscal_year if check_date.month < 10 else check_date.year, 9, 30)

        days_to_end = (fy_end - check_date).days
        return 0 <= days_to_end <= days_before

    @staticmethod
    def is_fiscal_year_start_period(check_date: date, days_after: int = 60) -> bool:
        """
        Check if a date is in the start-of-fiscal-year period.

        This is when new appropriations become available. Typically October-November.

        Args:
            check_date: The date to check
            days_after: Days after October 1 to consider as start-of-year period

        Returns:
            True if in the start-of-fiscal-year period
        """
        fiscal_year = FiscalCalendar.get_fiscal_year(check_date)
        # FY start is October 1 of previous calendar year
        fy_start = date(fiscal_year - 1, 10, 1)

        days_since_start = (check_date - fy_start).days
        return 0 <= days_since_start <= days_after

    @staticmethod
    def get_nearest_quarter_end(check_date: date, max_days: int = 21) -> Optional[date]:
        """
        Get the nearest quarter end date if within max_days.

        Args:
            check_date: The date to check
            max_days: Maximum days before or after to consider

        Returns:
            The nearest quarter end date, or None if none within range
        """
        fiscal_year = FiscalCalendar.get_fiscal_year(check_date)
        quarter_ends = FiscalCalendar.get_quarter_end_dates(fiscal_year)

        # Also check adjacent fiscal years
        prev_fy_ends = FiscalCalendar.get_quarter_end_dates(fiscal_year - 1)
        next_fy_ends = FiscalCalendar.get_quarter_end_dates(fiscal_year + 1)
        all_quarter_ends = prev_fy_ends + quarter_ends + next_fy_ends

        nearest = None
        min_distance = float("inf")

        for qe in all_quarter_ends:
            distance = abs((qe - check_date).days)
            if distance <= max_days and distance < min_distance:
                min_distance = distance
                nearest = qe

        return nearest

    @staticmethod
    def analyze_historical_quarter_affinity(
        historical_dates: list[date],
        days_threshold: int = 14,
    ) -> float:
        """
        Analyze how strongly historical dates cluster around quarter ends.

        Args:
            historical_dates: List of historical grant dates
            days_threshold: Days within quarter end to count

        Returns:
            Affinity score from 0.0 (no affinity) to 1.0 (all dates near quarter ends)
        """
        if not historical_dates:
            return 0.0

        near_quarter_count = 0
        for hist_date in historical_dates:
            if FiscalCalendar.is_near_quarter_end(hist_date, days_threshold):
                near_quarter_count += 1

        return near_quarter_count / len(historical_dates)

    @staticmethod
    def adjust_prediction_for_fiscal_patterns(
        predicted_date: date,
        funder_name: str,
        historical_dates: list[date],
        snap_threshold_days: int = 21,
        min_quarter_affinity: float = 0.5,
    ) -> date:
        """
        Adjust a predicted date based on fiscal calendar patterns.

        If funder historically releases near quarter ends, snap to nearest quarter end.
        Federal funders are also checked for fiscal year-end patterns.

        Args:
            predicted_date: The initial predicted date
            funder_name: Name of the funding organization
            historical_dates: List of historical grant deadline/opening dates
            snap_threshold_days: Max days to snap to a quarter end
            min_quarter_affinity: Minimum historical quarter affinity to trigger snapping

        Returns:
            Adjusted prediction date, potentially snapped to a quarter end
        """
        if not is_federal_funder(funder_name):
            return predicted_date

        # Check if this funder historically releases near quarter ends
        quarter_affinity = FiscalCalendar.analyze_historical_quarter_affinity(historical_dates)

        if quarter_affinity >= min_quarter_affinity:
            # This funder tends to release near quarter ends
            nearest_qe = FiscalCalendar.get_nearest_quarter_end(predicted_date, snap_threshold_days)
            if nearest_qe:
                return nearest_qe

        # For federal funders, also check fiscal year-end pattern
        # If predicted date is in August, consider snapping to end of September
        if predicted_date.month == 8:
            fiscal_year = FiscalCalendar.get_fiscal_year(predicted_date)
            fy_end = date(fiscal_year if predicted_date.month < 10 else predicted_date.year, 9, 30)

            # Check if historical dates show end-of-year pattern
            end_of_year_dates = [d for d in historical_dates if d.month in (8, 9)]
            if len(end_of_year_dates) >= len(historical_dates) * 0.3:
                # Significant end-of-year activity, adjust to September
                return date(fy_end.year, 9, 15)

        # For federal funders with October/November activity, keep prediction
        # as these align with new appropriations
        if predicted_date.month in (10, 11):
            # Check if historical dates support this timing
            start_of_year_dates = [d for d in historical_dates if d.month in (10, 11)]
            if len(start_of_year_dates) >= len(historical_dates) * 0.3:
                # Pattern supports start-of-year timing
                return predicted_date

        return predicted_date


def get_fiscal_period_description(check_date: date) -> str:
    """
    Get a human-readable description of the fiscal period.

    Args:
        check_date: The date to describe

    Returns:
        Description of the fiscal period
    """
    fiscal_year = FiscalCalendar.get_fiscal_year(check_date)
    quarter = FiscalCalendar.get_fiscal_quarter(check_date)

    period_desc = f"FY{fiscal_year} Q{quarter}"

    if FiscalCalendar.is_fiscal_year_end_period(check_date):
        period_desc += " (End-of-Year Spending Period)"
    elif FiscalCalendar.is_fiscal_year_start_period(check_date):
        period_desc += " (New Appropriations Period)"
    elif FiscalCalendar.is_near_quarter_end(check_date):
        period_desc += " (Near Quarter End)"

    return period_desc
